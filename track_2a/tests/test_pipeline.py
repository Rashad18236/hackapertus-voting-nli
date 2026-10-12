"""Background preparation (session 10, src/pipeline.py): every case is answered exactly once, whatever fails where,
and the requests are the same as on the sequential path (--workers 0).

Unit tests drive pipeline.run() with fake steps. The end-to-end tests run the real CLI with --workers 1 (a worker process) against
the fake model (scripts/stub_llm.py): in a subprocess (tests/test_contract.py's runner) for failures of the
model and the booklet and for a killed run, and in this process where a step must be made to fail on purpose
(a preparation that raises in a worker, a model call that times out).
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

from src import cli, env, llm, pipeline
from tests.test_contract import (A_ARGS, ROOT, ROUTED, RUNNER, ContractBase, a_case, b_case, contract_problems,
                                 stub_llm)


def pid_of(case):
    return os.getpid()


def die(case):
    """A preparation that kills its worker process (module level, so that it can be sent to the process)."""
    os._exit(1)


def emitted_by(items, prepare, complete, fallback, **kwargs):
    """pipeline.run with threads as workers (the fake steps are local functions, which a process cannot receive)."""
    out = []
    pipeline.run(items, prepare, complete, fallback, lambda number, case, result: out.append(result),
                 processes=False, **kwargs)
    return out


class RunWithFakeSteps(unittest.TestCase):
    def test_every_item_once_and_a_failed_preparation_takes_the_fallback(self):
        items = [(i, {"id": f"c{i}"}) for i in range(1, 21)]

        def prepare(case):
            if case["id"] in ("c3", "c7"):
                raise RuntimeError("worker failed")
            time.sleep(0.001 * (int(case["id"][1:]) % 3))
            return case["id"]
        out = emitted_by(items, prepare, lambda p: ("done", p), lambda case: ("fallback", case["id"]), workers=2)
        self.assertEqual(sorted(i for _, i in out), sorted(c["id"] for _, c in items))
        self.assertEqual(sorted(i for kind, i in out if kind == "fallback"), ["c3", "c7"])

    def test_at_most_in_flight_calls_at_once(self):
        for in_flight in (1, 2):
            busy, most, lock = [0], [0], threading.Lock()

            def complete(prepared):
                with lock:
                    busy[0] += 1
                    most[0] = max(most[0], busy[0])
                time.sleep(0.01)
                with lock:
                    busy[0] -= 1
                return prepared
            items = [(i, {"id": i}) for i in range(12)]
            out = emitted_by(items, lambda c: c["id"], complete, lambda c: None, workers=2, in_flight=in_flight)
            self.assertEqual(sorted(out), list(range(12)))
            self.assertLessEqual(most[0], in_flight)
            if in_flight == 1:
                self.assertEqual(most[0], 1)

    def test_cases_are_prepared_in_the_order_of_the_key_then_input_order(self):
        order = []
        items = [(i, {"id": i, "light": i % 3 != 0}) for i in range(1, 10)]
        emitted_by(items, lambda c: order.append(c["id"]) or c, lambda p: p, lambda c: c, workers=1,
                   order_key=lambda c: not c["light"])
        self.assertEqual(order, [1, 2, 4, 5, 7, 8, 3, 6, 9])

    def test_preparation_key_light_task_b_first_then_by_booklet(self):
        long_ref = "Titel\n\n" + "\n\n".join("Absatz " * 300 for _ in range(10))
        todo = [(1, a_case("a1", path="booklets/x.pdf")), (2, b_case("b-long", reference=long_ref)),
                (3, a_case("a2", path="booklets/y.pdf")), (4, a_case("a3", path="booklets/x.pdf")), (5, b_case("b1"))]
        key = cli.preparation_key(todo, cli.Settings(context_b="cut"))  # with B-cut, a long reference needs e5
        self.assertEqual([c["id"] for _, c in sorted(todo, key=lambda item: key(item[1]))],
                         ["a1", "a3", "b1", "a2", "b-long"])

    def test_a_case_is_sent_as_soon_as_it_is_ready(self):
        def prepare(case):
            time.sleep(0.3 if case["id"] == 1 else 0)
            return case["id"]
        out = emitted_by([(1, {"id": 1}), (2, {"id": 2})], prepare, lambda p: p, lambda c: None, workers=2)
        self.assertEqual(out, [2, 1])

    def test_default_workers(self):
        with mock.patch.object(pipeline, "available_cpus", return_value=1):
            self.assertEqual(pipeline.default_workers(), 1)
        with mock.patch.object(pipeline, "available_cpus", return_value=4):
            self.assertEqual(pipeline.default_workers(), 2)

    def test_each_lane_is_its_own_process_and_gets_its_cases(self):
        items = [(i, {"id": i, "booklet": i % 3}) for i in range(9)]
        out = []
        pipeline.run(items, pid_of, lambda p: p, lambda case: ("fallback", case["id"]),
                     lambda number, case, result: out.append((case["booklet"], result)), workers=3,
                     lane_key=lambda case: case["booklet"])
        pids = {}
        for book, pid in out:
            pids.setdefault(book, set()).add(pid)
        self.assertTrue(all(len(p) == 1 for p in pids.values()))  # one process per booklet
        self.assertEqual(len(set().union(*pids.values())), 3)     # three different processes
        self.assertNotIn(os.getpid(), set().union(*pids.values()))

    def test_a_worker_process_that_dies_leaves_every_case_to_the_fallback(self):
        items = [(i, {"id": i}) for i in range(4)]
        out = []
        pipeline.run(items, die, lambda p: ("done", p), lambda case: ("fallback", case["id"]),
                     lambda number, case, result: out.append(result), workers=1)
        self.assertEqual(sorted(out), [("fallback", i) for i in range(4)])


class WorkersEndToEnd(ContractBase):
    """The real CLI with --workers 1 (a worker process) in a subprocess, against the fake model."""

    def test_failures_of_the_model_and_the_booklet_during_background_work(self):
        cases = [a_case("a-ok"), b_case("b-ok"),
                 b_case("b-500-once", claim="STUB_FAIL_ONCE Der Bund zahlt."), a_case("a-500-once", claim="STUB_FAIL_ONCE"),
                 b_case("b-429-once", claim="STUB_429_ONCE Der Bund zahlt."), a_case("a-429-once", claim="STUB_429_ONCE"),
                 b_case("b-fail", claim="STUB_FAIL"), a_case("a-garbage", claim="STUB_GARBAGE"),
                 a_case("a-broken", path="booklets/broken.pdf"), a_case("a-empty", path="booklets/empty.pdf"),
                 a_case("a-missing", path="booklets/nope.pdf"), a_case("a-ok-2", claim="Deux semaines de congé.")]
        run = self.run_cli(cases, "--workers", "1", *A_ARGS)
        self.assertContract(run, cases)
        for case_id in ("a-ok", "b-ok", "b-500-once", "a-500-once", "b-429-once", "a-429-once", "a-ok-2"):
            self.assertEqual(run.by_id[case_id]["label"], 0, case_id)  # the fake model's answer, not the fallback
        for case_id in ("b-fail", "a-garbage", "a-broken", "a-empty", "a-missing"):
            self.assertEqual(run.by_id[case_id]["label"], 1, case_id)
        self.assertGreater(run.by_id["b-500-once"]["metrics"]["input_tokens"], 0)

    def test_same_requests_and_answers_as_the_sequential_path(self):
        cases = ROUTED + [a_case("a-small"), b_case("b-1"), b_case("b-2", claim="Le texte parle du loup."),
                          b_case("b-long", reference="Titre\n\n" + "\n\n".join(f"Paragraphe {i}. " + "mot " * 200
                                                                           for i in range(12)))]
        results = {}
        for workers in ("0", "1"):
            run = self.run_cli(cases, "--workers", workers)
            self.assertContract(run, cases)
            with self.server.config.lock:
                hashes = Counter(c["request_sha256"] for c in self.server.config.calls)
            results[workers] = (hashes, {p["id"]: (p["label"], p["evidence"]) for p in run.preds})
        self.assertEqual(results["0"][0], results["1"][0])  # the same requests
        self.assertEqual(results["0"][1], results["1"][1])  # the same labels and evidence

    def test_killed_run_keeps_one_valid_line_per_finished_case(self):
        server, url = stub_llm.start(delay=0.25)
        root = Path(tempfile.mkdtemp(dir=self.tmp, prefix="kill-workers-"))
        try:
            cases = [b_case(f"k{i:02d}", claim=f"Claim number {i}.") for i in range(40)]
            (root / "cases.jsonl").write_text("".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8")
            out = root / "predictions.jsonl"
            environment = {k: v for k, v in os.environ.items()
                           if k not in ("BASE_URL", "API_KEY", "MODEL", "LLM_BASE_URL", "LLM_API_KEY", "LLM_NAME")}
            environment.update({"BASE_URL": url, "API_KEY": "stub", "CONTRACT_WRITE_LOG": str(root / "writes.json"),
                                "TMPDIR": str(root), "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost"})
            proc = subprocess.Popen([sys.executable, "-c", RUNNER, "--input", str(root / "cases.jsonl"),
                                     "--output", str(out), "--workers", "1"], cwd=ROOT, env=environment,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            deadline = time.time() + 60
            while time.time() < deadline and (not out.exists() or out.read_bytes().count(b"\n") < 5):
                time.sleep(0.05)
            proc.kill()
            proc.wait(timeout=30)
            data = out.read_bytes()
            self.assertTrue(data.endswith(b"\n"), "the last line is cut off")
            preds = [json.loads(line) for line in data.decode("utf-8").splitlines()]
            self.assertGreaterEqual(len(preds), 5)
            self.assertLess(len(preds), len(cases), "the run finished before it was killed")
            ids = [p["id"] for p in preds]
            self.assertEqual(len(ids), len(set(ids)), "an id was answered twice")
            self.assertEqual(contract_problems(preds, {c["id"]: c for c in cases if c["id"] in ids}), [])
        finally:
            server.shutdown()


def raise_in_worker(original, parent_pid):
    """prepare_b that raises for a RAISE_IN_WORKER claim in the worker process only (the forked worker inherits
    the patched module)."""
    def prepare_b(case, *args, **kwargs):
        if "RAISE_IN_WORKER" in case["claim"]["text"] and os.getpid() != parent_pid:
            raise RuntimeError("worker failed")
        return original(case, *args, **kwargs)
    return prepare_b


class WorkersInProcess(unittest.TestCase):
    """cli.main() in this process, so that a step can be made to fail on purpose."""

    def run_main(self, cases, *args, slow_seconds=None):
        server, url = stub_llm.start()
        if slow_seconds is not None:
            server.config.slow_seconds = slow_seconds
        tmp = Path(tempfile.mkdtemp(prefix="pipeline-"))
        (tmp / "cases.jsonl").write_text("".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8")
        argv = ["cli", "--input", str(tmp / "cases.jsonl"), "--output", str(tmp / "out.jsonl"), *args]
        llm.reset_run_state()
        try:
            with mock.patch.dict(os.environ, {"BASE_URL": url, "API_KEY": "stub", "NO_PROXY": "127.0.0.1",
                                              "no_proxy": "127.0.0.1"}), \
                    mock.patch.object(env, "load_env_file", lambda *a, **k: None), \
                    mock.patch.object(sys, "argv", argv):
                for name in ("MODEL", "LLM_NAME", "LLM_MIN_INTERVAL"):
                    os.environ.pop(name, None)
                self.assertEqual(cli.main(), 0)
        finally:
            server.shutdown()
            llm.reset_run_state()
        preds = [json.loads(line) for line in (tmp / "out.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(contract_problems(preds, {c["id"]: c for c in cases}), [])
        return {p["id"]: p for p in preds}, server.config.calls

    def test_a_preparation_that_raises_in_the_worker_runs_on_the_sequential_path(self):
        cases = [b_case("b-ok"), b_case("b-raise", claim="RAISE_IN_WORKER Der Bund zahlt."), b_case("b-ok-2")]
        with mock.patch.object(cli, "prepare_b", raise_in_worker(cli.prepare_b, os.getpid())):
            preds, calls = self.run_main(cases, "--workers", "1")
        self.assertEqual({k: p["label"] for k, p in preds.items()}, {"b-ok": 0, "b-raise": 0, "b-ok-2": 0})
        self.assertEqual(len(calls), 3)

    def test_a_model_call_that_times_out_gets_the_fallback_and_the_rest_are_answered(self):
        cases = [b_case("b-ok"), b_case("b-slow", claim="STUB_SLOW Der Bund zahlt."), b_case("b-ok-2")]
        with mock.patch.object(llm, "TIMEOUT_SECONDS", 0.5), mock.patch.object(llm, "RETRY_PAUSE_SECONDS", 0):
            preds, calls = self.run_main(cases, "--workers", "1", slow_seconds=1.5)
        self.assertEqual({k: p["label"] for k, p in preds.items()}, {"b-ok": 0, "b-slow": 1, "b-ok-2": 0})
        self.assertEqual(len(calls), 4)  # b-slow: the first attempt and one retry after the timeout


if __name__ == "__main__":
    unittest.main()


def heavy_if_odd(case):
    """A fake preparation: an odd case needs the embedding model (src/deferral.py), an even one does not. The result
    carries when the case was prepared."""
    from src import deferral
    if case % 2:
        deferral.check()
    return case * 10, time.monotonic_ns()


class LightFirst(unittest.TestCase):
    """Session 11, step 4: a lane prepares the cases that need no embedding model first (pipeline.LIGHT_FIRST)."""

    def run_lanes(self, light_first):
        order = []
        items = [(n, n) for n in range(8)]
        with mock.patch.object(pipeline, "LIGHT_FIRST", light_first):
            pipeline.run(items, heavy_if_odd, lambda p: p, lambda c: -1,
                         lambda number, case, result: order.append((number, result)), workers=1)
        return order

    def prepared_order(self, results):
        return [n for n, (value, when) in sorted(results, key=lambda r: r[1][1])]

    def test_light_cases_are_prepared_first_and_every_case_answered_once(self):
        results = self.run_lanes(True)
        self.assertEqual(sorted((n, v) for n, (v, _) in results), [(n, n * 10) for n in range(8)])
        self.assertEqual(self.prepared_order(results), [0, 2, 4, 6, 1, 3, 5, 7])

    def test_off_keeps_the_list_order(self):
        self.assertEqual(self.prepared_order(self.run_lanes(False)), list(range(8)))

    def test_needs_model_is_not_an_ordinary_exception(self):
        from src import deferral
        self.assertFalse(issubclass(deferral.NeedsModel, Exception))
        with mock.patch.dict(deferral.DEFER, {"on": True}), self.assertRaises(deferral.NeedsModel):
            try:
                deferral.check()
            except Exception:  # what the fallbacks in src/ catch
                self.fail("NeedsModel was caught as an ordinary exception")
