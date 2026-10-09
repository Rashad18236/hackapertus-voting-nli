"""Contract checks (docs/official_contract.md), end to end and without a real model.

The real CLI runs in a subprocess, as `python -m src.cli` would, against the fake model
(scripts/stub_llm.py) over HTTP, on real booklet PDFs: the example booklet
(examples/booklets/2020_09_27_fr.pdf), its first eight pages as a small booklet (fast to
embed), a broken and an empty PDF, and a path that does not exist.

Each run is checked for the contract: exit code 0, exactly one valid response per input id
(label and label_name agree, evidence items with text of at most 5,000 characters and a
1-based page for task A, metrics as non-negative integers), and that it wrote only to the
output folder and the temporary folder: every file write is recorded with a Python audit
hook, and the data folder (the container's /data) is hashed before and after.

No key is used (API_KEY is a dummy), nothing leaves the machine, and the developer's .env is
never read: the runner replaces src.env.load_env_file with a no-op (inside the Docker image
there is no .env either). Variables a developer may have exported (BASE_URL, API_KEY, MODEL,
LLM_*) are removed from the subprocess's environment.

The task A embedding (embed-e5-small) needs the e5 model files. If models/multilingual-e5-small
is missing, task A cases on that path get the fallback answer (still a valid response), and the
test that needs the real embedding is skipped. CONTRACT_SLOW=1 adds the order test with the
default context on the full example booklet (about 20 s per run, embedding the whole booklet).

The tests for repeated ids, a byte order mark and bytes that are not UTF-8 were expected failures
until src/cli.py read its input as bytes and skipped repeated ids (PR #13, proposals P1 to P4 in
docs/checks_no_model.md); they now pass. Session 8 made the same fix on its own branch and kept its
own reader at the merge, which also ends a line at a carriage return alone (test below).
StoppedRun kills the CLI in the middle of a run (P4).
"""

import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import stub_llm  # noqa: E402

EXAMPLE_BOOKLET = ROOT / "examples" / "booklets" / "2020_09_27_fr.pdf"
MODEL_DIR = ROOT / "models" / "multilingual-e5-small"
HAVE_E5 = (MODEL_DIR / "model.onnx").is_file() and (MODEL_DIR / "tokenizer.json").is_file()
SLOW = os.environ.get("CONTRACT_SLOW") == "1"
# Tests that need a real task A answer (label 0 from the fake model, with evidence) use the default context when
# the e5 model is there; without it they use the whole booklet ("full", no local model), since the default
# would give the fallback answer.
A_ARGS = [] if HAVE_E5 else ["--context-a", "full"]
NAMES = {0: "entailment", 1: "neutral", 2: "contradiction"}

# Runs src.cli.main() with an audit hook that records every file write, and without reading .env.
RUNNER = r"""
import json, os, sys
writes, recording = [], [True]
EVENTS = {"os.mkdir", "os.rename", "os.replace", "os.remove", "os.rmdir", "os.truncate", "os.symlink", "os.link",
          "os.chmod", "os.chown", "os.utime", "shutil.copyfile", "shutil.copymode", "shutil.copystat",
          "shutil.copytree", "shutil.rmtree", "shutil.move"}
def path_of(p):
    return os.path.abspath(os.fsdecode(p)) if isinstance(p, (str, bytes, os.PathLike)) else None
def hook(event, args):
    if not recording[0]:
        return
    if event == "open":
        path, mode, flags = (list(args) + [None, None, None])[:3]
        if path_of(path) is None:
            return
        if isinstance(mode, str):
            writing = any(c in mode for c in "wax+")
        else:
            writing = bool((flags or 0) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC))
        if writing:
            writes.append(["open", path_of(path)])
    elif event in EVENTS:
        writes.append([event] + [p for p in map(path_of, args[:2]) if p])
sys.addaudithook(hook)
import src.env
src.env.load_env_file = lambda *a, **k: None
from src import cli
code = 1
try:
    code = cli.main()
finally:
    recording[0] = False
    with open(os.environ["CONTRACT_WRITE_LOG"], "w", encoding="utf-8") as f:
        json.dump(writes, f)
sys.exit(code)
"""


def b_case(case_id, claim="Der Bund zahlt 40 Millionen Franken.", claim_language="de", reference="Le texte.",
           reference_language="fr", vote="Vote"):
    return {"id": case_id, "vote": vote, "claim": {"text": claim, "language": claim_language},
            "reference": {"text": reference, "language": reference_language}}


def a_case(case_id, claim="Le congé de paternité dure deux semaines.", claim_language="fr", path="booklets/small_fr.pdf",
           booklet_language="fr", vote=None):
    return {"id": case_id, "vote": vote or PATERNITY, "claim": {"text": claim, "language": claim_language},
            "booklet": {"path": path, "language": booklet_language}}


PATERNITY = ("Modification de la loi sur les allocations pour perte de gain (contre-projet indirect à l’initiative "
             "populaire « Pour un congé de paternité raisonnable – en faveur de toute la famille »)")
FIGHTER_JETS = "Arrêté fédéral relatif à l’acquisition de nouveaux avions de combat"
HUNTING = "Modification de la loi sur la chasse"

# Claims on the full example booklet whose openings the router knows (one per part), in three languages.
ROUTED = [
    a_case("r-detail", "Wird die Abstimmung angenommen, haben alle erwerbstätigen Väter Anspruch auf zwei Wochen "
                       "Vaterschaftsurlaub.", "de", "booklets/full_fr.pdf"),
    a_case("r-council", "Le Conseil fédéral préconise que la population rejette l’arrêté fédéral concernant l’achat "
                        "de nouveaux avions de combat.", "fr", "booklets/full_fr.pdf", vote=FIGHTER_JETS),
    a_case("r-committee", "Le comité estime que les PME ne disposent pas des ressources nécessaires.", "fr",
           "booklets/full_fr.pdf"),
    a_case("r-summary", "Il riassunto afferma che l’indennità per il congedo di paternità corrisponde all’80% del "
                        "reddito.", "it", "booklets/full_fr.pdf"),
    a_case("r-law", "Laut dem Abstimmungstext wird der Wolf nicht mehr geschützt.", "de", "booklets/full_fr.pdf",
           vote=HUNTING),
]


def contract_problems(preds, cases):
    """Contract violations of a predictions list against the requests (ids must be readable)."""
    problems = []
    counts = {}
    for p in preds:
        counts[p.get("id")] = counts.get(p.get("id"), 0) + 1
    for case_id, case in cases.items():
        if counts.get(case_id, 0) != 1:
            problems.append(f"{case_id}: {counts.get(case_id, 0)} responses")
    problems += [f"{i}: response for an id that is not in the input" for i in counts if i not in cases]
    for p in preds:
        case = cases.get(p.get("id"), {})
        task_a = isinstance(case, dict) and "booklet" in case
        label = p.get("label")
        if not isinstance(label, int) or isinstance(label, bool) or label not in NAMES:
            problems.append(f"{p.get('id')}: invalid label {label!r}")
        elif p.get("label_name") != NAMES[label]:
            problems.append(f"{p.get('id')}: label_name {p.get('label_name')!r} does not match label {label}")
        evidence = p.get("evidence")
        if not isinstance(evidence, list):
            problems.append(f"{p.get('id')}: evidence is not a list")
            evidence = []
        for item in evidence:
            if not isinstance(item, dict) or not isinstance(item.get("text"), str) or not item["text"].strip():
                problems.append(f"{p.get('id')}: evidence item without text")
                continue
            if len(item["text"]) > 5000:
                problems.append(f"{p.get('id')}: evidence item over 5,000 characters")
            page = item.get("page")
            if task_a and not (isinstance(page, int) and not isinstance(page, bool) and page >= 1):
                problems.append(f"{p.get('id')}: task A evidence page {page!r} is not an int >= 1")
            if not task_a and page is not None:
                problems.append(f"{p.get('id')}: task B evidence page is not null")
        metrics = p.get("metrics")
        for key in ("input_tokens", "output_tokens", "inference_time_ms"):
            value = metrics.get(key) if isinstance(metrics, dict) else None
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                problems.append(f"{p.get('id')}: metrics.{key} = {value!r}")
    return problems


def tree_hash(folder):
    """{relative path: SHA-256} of every file under folder, plus the folders themselves."""
    out = {}
    for path in sorted(Path(folder).rglob("*")):
        rel = str(path.relative_to(folder))
        out[rel] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "dir"
    return out


class Run:
    def __init__(self, code, preds, stderr, writes, root):
        self.code, self.preds, self.stderr, self.writes, self.root = code, preds, stderr, writes, root
        self.by_id = {}
        for p in preds:
            self.by_id.setdefault(p.get("id"), p)


class ContractBase(unittest.TestCase):
    """Starts one fake model and builds the booklet folder once; run() runs the CLI on given lines."""

    @classmethod
    def setUpClass(cls):
        cls.server, cls.url = stub_llm.start()
        cls.tmp = Path(tempfile.mkdtemp(prefix="contract-"))
        booklets = cls.tmp / "booklets"
        booklets.mkdir()
        shutil.copy(EXAMPLE_BOOKLET, booklets / "full_fr.pdf")
        from pypdf import PdfReader, PdfWriter
        writer = PdfWriter()
        for page in PdfReader(str(EXAMPLE_BOOKLET)).pages[:8]:
            writer.add_page(page)
        with open(booklets / "small_fr.pdf", "wb") as f:
            writer.write(f)
        (booklets / "broken.pdf").write_bytes(b"%PDF-1.4\nthis is not a PDF\n")
        (booklets / "empty.pdf").write_bytes(b"")
        cls.booklets = booklets

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_cli(self, lines, *args, env=None, cache_dir=None, server=None, url=None, check=True, raw_input=None):
        """Run the CLI on these lines (dicts are written as JSON, str and bytes as given, each followed by a
        line break), or on raw_input, bytes written to the input file exactly as given."""
        server, url = server or self.server, url or self.url
        with server.config.lock:
            server.config.calls.clear()
            server.config.failed_once.clear()
        root = Path(tempfile.mkdtemp(dir=self.tmp, prefix="run-"))
        data, output, tmp = root / "data", root / "output", root / "tmp"
        shutil.copytree(self.booklets, data / "booklets")
        output.mkdir()
        tmp.mkdir()
        raw = b"".join((json.dumps(x, ensure_ascii=False).encode("utf-8") if isinstance(x, dict)
                        else x.encode("utf-8") if isinstance(x, str) else x) + b"\n" for x in lines)
        (data / "cases.jsonl").write_bytes(raw if raw_input is None else raw_input)
        before = tree_hash(data)
        environment = {k: v for k, v in os.environ.items()
                       if k not in ("BASE_URL", "API_KEY", "MODEL", "LLM_BASE_URL", "LLM_API_KEY", "LLM_NAME")}
        environment.update({
            "BASE_URL": url, "API_KEY": "stub-key-must-not-appear", "PYTHONDONTWRITEBYTECODE": "1",
            "BOOKLET_CACHE_DIR": str(cache_dir or tmp / "booklet-cache"), "TMPDIR": str(tmp),
            "EMBED_MODEL_DIR": str(MODEL_DIR if HAVE_E5 else root / "no-model"),
            "CONTRACT_WRITE_LOG": str(root / "writes.json"),
            "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
        })
        for key, value in (env or {}).items():
            if value is None:
                environment.pop(key, None)
            else:
                environment[key] = value
        done = subprocess.run([sys.executable, "-c", RUNNER, "--input", str(data / "cases.jsonl"),
                               "--output", str(output / "predictions.jsonl"), *args],
                              cwd=ROOT, env=environment, capture_output=True, text=True, timeout=900)
        out_file = output / "predictions.jsonl"
        preds = [json.loads(line) for line in out_file.read_text(encoding="utf-8").splitlines()] \
            if out_file.exists() else []
        writes = json.loads((root / "writes.json").read_text()) if (root / "writes.json").exists() else []
        run = Run(done.returncode, preds, done.stderr, writes, root)
        if check:
            self.assertEqual(done.returncode, 0, done.stderr[-3000:])
            # Only /output and /tmp are written; the data folder is unchanged.
            allowed = (str(output), str(tmp), str(cache_dir) if cache_dir else str(tmp))
            outside = [w for w in writes if not all(p.startswith(allowed) for p in w[1:])]
            self.assertEqual(outside, [], "writes outside the output and temporary folders")
            self.assertEqual(tree_hash(data), before, "the data folder changed")
            self.assertNotIn("stub-key-must-not-appear", done.stderr + out_file.read_text(encoding="utf-8"))
        return run

    def assertContract(self, run, cases):
        problems = contract_problems(run.preds, {c["id"]: c for c in cases})
        self.assertEqual(problems, [], "\n".join(problems))


class EveryIdGetsOneValidResponse(ContractBase):
    def test_mixed_file_of_task_a_and_task_b(self):
        cases = [b_case("b-de-fr"), a_case("a-small"), b_case("b-it-de", "Il Consiglio federale ritiene X.", "it",
                                                                "Der Bundesrat.", "de"),
                 a_case("a-full", path="booklets/full_fr.pdf", claim="Laut der Zusammenfassung dauert der "
                                                                       "Vaterschaftsurlaub zwei Wochen.",
                        claim_language="de"),
                 b_case("b-fr-it", "Le comité affirme Y.", "fr", "Il comitato.", "it")]
        run = self.run_cli(cases, "--context-a", "section-route")
        self.assertContract(run, cases)
        self.assertEqual(len(run.preds), 5)
        # Task B: evidence is empty (not scored); task A label 0 (the fake model's answer) has evidence pages.
        self.assertEqual(run.by_id["b-de-fr"]["evidence"], [])
        self.assertEqual(run.by_id["a-full"]["label"], 0)
        self.assertTrue(run.by_id["a-full"]["evidence"])
        self.assertGreater(run.by_id["b-de-fr"]["metrics"]["input_tokens"], 0)

    def test_all_nine_language_pairs_and_unknown_languages(self):
        cases = []
        for source in ("de", "fr", "it"):
            for claim in ("de", "fr", "it"):
                cases.append(b_case(f"b-{source}-{claim}", claim_language=claim, reference_language=source))
                cases.append(a_case(f"a-{source}-{claim}", claim_language=claim, booklet_language=source))
        cases += [b_case("b-en", claim_language="en"), b_case("b-rm", reference_language="rm"),
                  a_case("a-en", claim_language="en", booklet_language="xx"),
                  {**b_case("b-nolang"), "claim": {"text": "Der Bund zahlt."}},
                  {**a_case("a-nolang"), "booklet": {"path": "booklets/small_fr.pdf"}}]
        run = self.run_cli(cases, *A_ARGS)
        self.assertContract(run, cases)
        # Languages only describe the request; an unknown or missing one changes nothing.
        self.assertEqual({p["label"] for p in run.preds}, {0})

    def test_malformed_lines_are_skipped_and_the_rest_answered(self):
        good = [b_case("good-1"), a_case("good-2"), b_case("good-3")]
        lines = [good[0], "{not json", "", "   ", "[1, 2, 3]", "null", '"just a string"', "42", good[1],
                 '{"vote": "no id", "claim": {"text": "c"}, "reference": {"text": "r"}}', good[2]]
        run = self.run_cli(lines)
        self.assertContract(run, good)
        self.assertIn("unreadable line or missing id", run.stderr)

    def test_missing_and_wrong_fields_get_the_fallback_answer(self):
        cases = [
            {"id": "no-source", "vote": "v", "claim": {"text": "c", "language": "de"}},
            {**a_case("both-sources"), "reference": {"text": "r", "language": "fr"}},
            {"id": "a-no-vote", "claim": {"text": "c", "language": "de"}, "booklet": {"path": "booklets/small_fr.pdf"}},
            {**a_case("a-no-path"), "booklet": {"language": "fr"}},
            {**a_case("a-booklet-null"), "booklet": None},
            {**a_case("a-booklet-string"), "booklet": "booklets/small_fr.pdf"},
            {**a_case("a-no-claim"), "claim": None},
            {**a_case("a-claim-string"), "claim": "Le congé dure deux semaines."},
            {**a_case("a-claim-number"), "claim": {"text": 42, "language": "fr"}},
            {**b_case("b-no-reference-text"), "reference": {"language": "fr"}},
            {**b_case("b-reference-null"), "reference": None},
            {**b_case("b-no-claim-text"), "claim": {"language": "de"}},
            {**b_case("b-no-vote"), "vote": None},
            {"id": "only-id"},
        ]
        run = self.run_cli(cases)
        self.assertContract(run, cases)
        for case_id in ("no-source", "both-sources", "a-no-vote", "a-no-path", "a-booklet-null", "a-booklet-string",
                        "a-no-claim", "a-claim-string", "b-no-reference-text", "b-reference-null", "b-no-claim-text",
                        "only-id"):
            self.assertEqual((run.by_id[case_id]["label"], run.by_id[case_id]["evidence"]), (1, []), case_id)
        self.assertEqual(run.by_id["b-no-vote"]["label"], 0)  # task B does not need the vote name

    def test_missing_broken_and_empty_booklets(self):
        cases = [a_case("missing", path="booklets/does_not_exist.pdf"), a_case("broken", path="booklets/broken.pdf"),
                 a_case("empty", path="booklets/empty.pdf"), a_case("folder", path="booklets"),
                 a_case("outside", path="../../no/such/file.pdf"), a_case("fine")]
        run = self.run_cli(cases, *A_ARGS)
        self.assertContract(run, cases)
        for case_id in ("missing", "broken", "empty", "folder", "outside"):
            self.assertEqual((run.by_id[case_id]["label"], run.by_id[case_id]["evidence"]), (1, []), case_id)
            self.assertEqual(run.by_id[case_id]["metrics"]["input_tokens"], 0)  # no model call
        self.assertEqual(run.by_id["fine"]["label"], 0)
        self.assertIn("booklet not found", run.stderr)
        self.assertIn("booklet could not be parsed", run.stderr)

    def test_empty_claim(self):
        cases = [b_case("b-empty", claim=""), a_case("a-empty", claim=""), b_case("b-blank", claim="   "),
                 a_case("a-blank", claim=" ")]
        run = self.run_cli(cases, "--context-a", "section-route")
        self.assertContract(run, cases)

    def test_blank_input_gives_an_empty_output_file(self):
        run = self.run_cli(["", "  "])
        self.assertEqual(run.preds, [])
        self.assertTrue((run.root / "output" / "predictions.jsonl").exists())

    def test_duplicate_ids_get_exactly_one_response(self):
        cases = [b_case("dup"), b_case("dup", claim="Another claim."), b_case("single")]
        run = self.run_cli(cases)
        # The starter's scorer marks an id with two responses as invalid (counted wrong).
        self.assertEqual(sorted(p["id"] for p in run.preds), ["dup", "single"])

    def test_duplicate_ids_answer_their_first_line(self):  # session 8
        cases = [b_case("dup"), b_case("dup", claim="STUB_LABEL_2 Another claim."), b_case("single")]
        run = self.run_cli(cases)
        self.assertEqual(sorted(p["id"] for p in run.preds), ["dup", "single"])
        # The first line is the one answered (the second would have given label 2).
        self.assertEqual([p["label"] for p in run.preds if p["id"] == "dup"], [0])
        self.assertIn("already answered", run.stderr)

    def test_duplicate_ids_never_stop_the_run(self):
        cases = [b_case("dup"), b_case("dup", claim="Another claim."), b_case("single")]
        run = self.run_cli(cases)
        self.assertEqual(run.code, 0)
        self.assertEqual(sum(p["id"] == "single" for p in run.preds), 1)

    def test_byte_order_mark_does_not_lose_the_first_case(self):
        cases = [b_case("first"), b_case("second")]
        lines = [b"\xef\xbb\xbf" + json.dumps(cases[0]).encode("utf-8"), cases[1]]
        run = self.run_cli(lines)
        self.assertContract(run, cases)

    def test_invalid_utf8_line_does_not_stop_the_run(self):
        # The bytes that are not UTF-8 sit inside a claim string: they become U+FFFD and the case is answered too.
        cases = [b_case("before"), {"id": "bad-bytes", "claim": {"text": "??"}, "reference": {"text": "r"}},
                 b_case("after")]
        lines = [cases[0], b'{"id": "bad-bytes", "claim": {"text": "\xff\xfe"}, "reference": {"text": "r"}}', cases[2]]
        run = self.run_cli(lines, check=False)
        self.assertEqual(run.code, 0, run.stderr[-2000:])
        self.assertEqual(contract_problems(run.preds, {c["id"]: c for c in cases}), [])

    def test_line_separators_inside_a_claim(self):
        """U+2028 and U+0085 are line breaks for str.splitlines() but ordinary characters inside a JSON string."""
        cases = [b_case("b-separators", claim="Der Bund\u2028zahlt\u0085 40 Millionen Franken."), b_case("b-after"),
                 a_case("a-separators", claim="Le congé\u2028dure deux\u0085semaines.")]
        lines = [json.dumps(c, ensure_ascii=False) for c in cases]  # the two characters stay raw, not escaped
        self.assertIn("\u2028", lines[0])
        run = self.run_cli(lines, *A_ARGS)
        self.assertContract(run, cases)
        self.assertEqual(run.by_id["b-separators"]["label"], 0)

    def test_carriage_returns_and_a_missing_final_line_break(self):
        cases = [b_case("crlf-1"), b_case("crlf-2"), b_case("last-without-newline")]
        raw = (json.dumps(cases[0]) + "\r\n" + json.dumps(cases[1]) + "\r\n" + json.dumps(cases[2])).encode("utf-8")
        run = self.run_cli([], raw_input=raw)
        self.assertContract(run, cases)

    def test_each_response_is_written_as_soon_as_it_is_ready(self):
        """While the second case waits for the (slow) model, the output file already holds the first response."""
        cases = [b_case("first"), b_case("second", claim="STUB_SLOW Der Bund zahlt.")]
        root = Path(tempfile.mkdtemp(dir=self.tmp, prefix="stream-"))
        (root / "cases.jsonl").write_text("".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8")
        out = root / "out" / "predictions.jsonl"
        raw = root / "out" / "raw.jsonl"
        self.server.config.slow_seconds = 5.0
        with self.server.config.lock:
            self.server.config.calls.clear()
        environment = {k: v for k, v in os.environ.items()
                       if k not in ("BASE_URL", "API_KEY", "MODEL", "LLM_BASE_URL", "LLM_API_KEY", "LLM_NAME")}
        environment.update({"BASE_URL": self.url, "API_KEY": "stub", "PYTHONDONTWRITEBYTECODE": "1",
                            "CONTRACT_WRITE_LOG": str(root / "writes.json"), "NO_PROXY": "127.0.0.1,localhost",
                            "no_proxy": "127.0.0.1,localhost", "BOOKLET_CACHE_DIR": str(root / "cache")})
        proc = subprocess.Popen([sys.executable, "-c", RUNNER, "--input", str(root / "cases.jsonl"),
                                 "--output", str(out), "--raw", str(raw)],
                                cwd=ROOT, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.time() + 60
            while time.time() < deadline and len(self.server.config.calls) < 2:
                time.sleep(0.05)
            self.assertEqual(len(self.server.config.calls), 2, "the second case never reached the model")
            self.assertIsNone(proc.poll(), "the run ended before the second case was answered")
            written = out.read_text(encoding="utf-8").splitlines()
            self.assertEqual([json.loads(line)["id"] for line in written], ["first"])
            self.assertEqual([json.loads(line)["id"] for line in raw.read_text(encoding="utf-8").splitlines()],
                             ["first"])
            proc.wait(timeout=60)
        finally:
            if proc.poll() is None:
                proc.kill()
            self.server.config.slow_seconds = stub_llm.Config.slow_seconds
        self.assertEqual(proc.returncode, 0, proc.stderr.read()[-2000:])
        self.assertEqual([json.loads(line)["id"] for line in out.read_text(encoding="utf-8").splitlines()],
                         ["first", "second"])

    def test_carriage_return_only_line_endings(self):
        """Lines that end with a carriage return alone (old Mac style): every case is answered."""
        cases = [b_case("cr-1"), b_case("cr-2"), a_case("cr-3"), b_case("cr-4")]
        raw = "\r".join(json.dumps(c) for c in cases).encode("utf-8") + b"\r"
        self.assertNotIn(b"\n", raw)
        run = self.run_cli([], *A_ARGS, raw_input=raw)
        self.assertContract(run, cases)


class StoppedRun(ContractBase):
    """P4 (session 8): the CLI writes each response as soon as it is ready, so a run killed in the middle
    keeps every finished case as a complete, valid line."""

    def test_killed_run_keeps_the_finished_cases_as_valid_lines(self):
        server, url = stub_llm.start(delay=0.25)  # a slow model, so the run is still going when it is killed
        root = Path(tempfile.mkdtemp(dir=self.tmp, prefix="kill-"))
        try:
            cases = [b_case(f"k{i:02d}", claim=f"Claim number {i}.") for i in range(40)]
            (root / "cases.jsonl").write_text("".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8")
            out = root / "predictions.jsonl"
            environment = {k: v for k, v in os.environ.items()
                           if k not in ("BASE_URL", "API_KEY", "MODEL", "LLM_BASE_URL", "LLM_API_KEY", "LLM_NAME")}
            environment.update({"BASE_URL": url, "API_KEY": "stub-key-must-not-appear",
                                "CONTRACT_WRITE_LOG": str(root / "writes.json"), "TMPDIR": str(root),
                                "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost"})
            proc = subprocess.Popen([sys.executable, "-c", RUNNER, "--input", str(root / "cases.jsonl"),
                                     "--output", str(out)], cwd=ROOT, env=environment,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            deadline = time.time() + 60
            while time.time() < deadline and (not out.exists() or out.read_bytes().count(b"\n") < 5):
                time.sleep(0.05)
            proc.kill()  # SIGKILL: no clean-up code runs
            proc.wait(timeout=30)
            data = out.read_bytes()
            self.assertTrue(data.endswith(b"\n"), "the last line is cut off")
            preds = [json.loads(line) for line in data.decode("utf-8").splitlines()]
            self.assertGreaterEqual(len(preds), 5)
            self.assertLess(len(preds), len(cases), "the run finished before it was killed")
            # The finished cases, in input order, each a valid response.
            self.assertEqual([p["id"] for p in preds], [c["id"] for c in cases[:len(preds)]])
            done = {c["id"]: c for c in cases[:len(preds)]}
            self.assertEqual(contract_problems(preds, done), [])
        finally:
            server.shutdown()


class FailedAndGarbageModelAnswers(ContractBase):
    def test_every_kind_of_failure_still_gives_a_valid_response(self):
        cases = [
            b_case("b-fail", claim="STUB_FAIL"), a_case("a-fail", claim="STUB_FAIL"),
            b_case("b-garbage", claim="STUB_GARBAGE"), a_case("a-garbage", claim="STUB_GARBAGE"),
            b_case("b-empty", claim="STUB_EMPTY"), a_case("a-empty", claim="STUB_EMPTY"),
            b_case("b-html", claim="STUB_HTML"), a_case("a-html", claim="STUB_HTML"),
            b_case("b-400", claim="STUB_400"), a_case("a-400", claim="STUB_400"),
            b_case("b-no-usage", claim="STUB_NO_USAGE"),
            a_case("a-bad-pages", claim="STUB_BAD_PAGES"),
            b_case("b-ok"), a_case("a-ok"),
        ]
        run = self.run_cli(cases, *A_ARGS)
        self.assertContract(run, cases)
        for case_id in ("b-fail", "a-fail", "b-garbage", "a-garbage", "b-empty", "a-empty", "b-html", "a-html",
                        "b-400", "a-400"):
            self.assertEqual((run.by_id[case_id]["label"], run.by_id[case_id]["evidence"]), (1, []), case_id)
        # Tokens of an answer that came back but could not be read still count; failed calls report none.
        self.assertEqual(run.by_id["b-garbage"]["metrics"]["input_tokens"], 100)
        self.assertEqual(run.by_id["b-fail"]["metrics"]["input_tokens"], 0)
        self.assertEqual(run.by_id["b-no-usage"]["label"], 0)
        self.assertEqual(run.by_id["b-no-usage"]["metrics"]["input_tokens"], 0)
        # Cited pages that were not sent give no evidence; the label stays (format-valid, evidence not found).
        self.assertEqual((run.by_id["a-bad-pages"]["label"], run.by_id["a-bad-pages"]["evidence"]), (0, []))
        self.assertEqual(run.by_id["b-ok"]["label"], 0)
        # A 5xx is retried exactly once: two calls for each STUB_FAIL case.
        kinds = [c["kind"] for c in self.server.config.calls]
        self.assertEqual(kinds.count("fail"), 4)

    def test_one_failed_attempt_is_retried_and_its_answer_used(self):
        cases = [b_case("b-once", claim="STUB_FAIL_ONCE STUB_LABEL_2"), a_case("a-once", claim="STUB_FAIL_ONCE")]
        start = time.perf_counter()
        run = self.run_cli(cases, *A_ARGS)
        self.assertContract(run, cases)
        self.assertEqual(run.by_id["b-once"]["label"], 2)
        self.assertEqual(run.by_id["b-once"]["metrics"]["input_tokens"], 100)
        self.assertGreaterEqual(run.by_id["b-once"]["metrics"]["inference_time_ms"], 2000)  # the retry pause
        self.assertEqual(run.by_id["a-once"]["label"], 0)
        self.assertTrue(run.by_id["a-once"]["evidence"])
        self.assertGreater(time.perf_counter() - start, 4)

    def test_failures_chosen_by_call_number(self):
        server, url = stub_llm.start(garbage_calls=[1], fail_calls=[2, 3], html_calls=[5], error_calls=[6])
        try:
            cases = [b_case(f"b{i}") for i in range(1, 7)]
            run = self.run_cli(cases, server=server, url=url)
        finally:
            server.shutdown()
        self.assertContract(run, cases)
        # call 1 garbage; calls 2 and 3 fail (case 2 and its retry); call 4 answers case 3; call 5 HTML;
        # call 6 HTTP 400 (not retried); call 7 answers case 6.
        self.assertEqual([run.by_id[f"b{i}"]["label"] for i in range(1, 7)], [1, 1, 0, 1, 1, 0])

    def test_no_endpoint_configured(self):
        cases = [b_case("b"), a_case("a")]
        run = self.run_cli(cases, env={"BASE_URL": None, "API_KEY": None})
        self.assertContract(run, cases)
        self.assertEqual([p["label"] for p in run.preds], [1, 1])
        self.assertIn("model call failed", run.stderr)

    def test_endpoint_not_reachable(self):
        cases = [b_case("b")]
        run = self.run_cli(cases, env={"BASE_URL": "http://127.0.0.1:9/v1"})
        self.assertContract(run, cases)
        self.assertEqual(run.preds[0]["label"], 1)


class EnvironmentVariables(ContractBase):
    def test_official_names_model_and_headers(self):
        run = self.run_cli([b_case("b")], env={"MODEL": "swiss-ai/Apertus-v1.5-70B-Instruct"})
        self.assertEqual(run.preds[0]["label"], 0)
        call = self.server.config.calls[0]
        self.assertEqual(call["model"], "swiss-ai/Apertus-v1.5-70B-Instruct")
        self.assertTrue(call["authorization"])
        self.assertEqual(call["user_agent"], "hackapertus-voting-nli/0.1")

    def test_default_model_and_base_url_without_v1(self):
        self.run_cli([b_case("b")], env={"BASE_URL": self.url[:-len("/v1")]})
        self.assertEqual(self.server.config.calls[0]["model"], "swiss-ai/Apertus-v1.5-8B")

    def test_local_names_are_the_fallback(self):
        run = self.run_cli([b_case("b")], env={"BASE_URL": None, "API_KEY": None, "LLM_BASE_URL": self.url,
                                               "LLM_API_KEY": "stub", "LLM_NAME": "local-name"})
        self.assertEqual(run.preds[0]["label"], 0)
        self.assertEqual(self.server.config.calls[0]["model"], "local-name")


class OrderIndependence(ContractBase):
    """The same cases in three orders give identical labels and evidence per id.

    The first order runs with an empty booklet cache, the other two reuse its cache, so a
    cached parse must also give what a fresh parse gives.
    """

    def check_orders(self, cases, *args):
        orders = [list(cases), list(reversed(cases)), random.Random(42).sample(cases, len(cases))]
        cache = self.tmp / f"shared-cache-{len(args)}-{len(cases)}"
        results = []
        for order in orders:
            run = self.run_cli(order, *args, cache_dir=cache)
            self.assertContract(run, cases)
            results.append({p["id"]: (p["label"], p["evidence"]) for p in run.preds})
        self.assertNotEqual([c["id"] for c in orders[0]], [c["id"] for c in orders[2]])
        for other in results[1:]:
            for case_id in results[0]:
                self.assertEqual(other[case_id], results[0][case_id], case_id)
        return results[0]

    def mixed_cases(self):
        return [a_case("a1"), b_case("b1"), a_case("a2", "Le Conseil fédéral estime que le congé coûte trop cher.",
                                                     booklet_language="fr"),
                b_case("b2", "Il comitato afferma Z. STUB_LABEL_2", "it"), a_case("a3", "STUB_LABEL_2 Väter.", "de"),
                b_case("b3", "STUB_GARBAGE"), a_case("a4", "STUB_FAIL"), a_case("a5", "Les avions de combat.", "fr"),
                b_case("b4", "Der Bundesrat empfiehlt ein Nein.", "de", "Il Consiglio federale.", "it")]

    def test_default_settings(self):
        result = self.check_orders(self.mixed_cases())
        if HAVE_E5:  # with the embedding, label 0 and 2 answers on a booklet carry evidence
            self.assertTrue(result["a1"][1] and result["a3"][1])

    def test_section_route(self):
        cases = ROUTED + [c for c in self.mixed_cases() if c["id"] in ("a1", "b1", "b2", "b3", "b4")]
        result = self.check_orders(cases, "--context-a", "section-route")
        for case in ROUTED:
            # The hunting law's text has more than 8,000 characters, so section-route ranks its paragraphs with e5;
            # without the model files that case gets the fallback answer (still a valid response).
            if case["id"] == "r-law" and not HAVE_E5:
                self.assertEqual(result[case["id"]], (1, []))
            else:
                self.assertTrue(result[case["id"]][1], case["id"])  # routed: the cited paragraph is the evidence

    @unittest.skipUnless(SLOW, "set CONTRACT_SLOW=1 (embeds the whole example booklet in each of three runs)")
    def test_default_settings_on_the_full_booklet(self):
        cases = [dict(c, booklet=dict(c["booklet"], path="booklets/full_fr.pdf")) for c in self.mixed_cases()
                 if "booklet" in c] + ROUTED + [c for c in self.mixed_cases() if "reference" in c]
        self.check_orders(cases)


class WritesOnlyToOutputAndTmp(ContractBase):
    def test_the_write_record_is_not_empty(self):
        """The audit hook sees the pipeline's writes (output file, booklet cache), so its silence elsewhere counts."""
        run = self.run_cli([a_case("a"), b_case("b")], *A_ARGS)
        written = {p for w in run.writes for p in w[1:]}
        self.assertIn(str(run.root / "output" / "predictions.jsonl"), written)
        self.assertTrue(any(p.startswith(str(run.root / "tmp" / "booklet-cache")) for p in written), written)

    def test_unwritable_cache_folder_is_not_an_error(self):
        cases = [a_case("a")]
        blocker = self.tmp / "a-file"
        blocker.write_text("not a folder")
        run = self.run_cli(cases, *A_ARGS, cache_dir=blocker / "cache")
        self.assertContract(run, cases)
        self.assertEqual(run.preds[0]["label"], 0)


@unittest.skipUnless(HAVE_E5, "needs models/multilingual-e5-small (see Dockerfile for the pinned download)")
class DefaultContextUsesTheEmbedding(ContractBase):
    def test_task_a_default_answers_from_selected_pages(self):
        cases = [a_case("a", "STUB_LABEL_2 Le congé de paternité dure deux semaines.")]
        run = self.run_cli(cases)
        self.assertContract(run, cases)
        self.assertEqual(run.preds[0]["label"], 2)
        self.assertTrue(run.preds[0]["evidence"])
        self.assertNotIn("context selection failed", run.stderr)


class FakeModel(unittest.TestCase):
    """scripts/stub_llm.py answers in the format the pipeline asks for."""

    def test_answers_match_the_requested_schema(self):
        cfg = stub_llm.Config(label=2)
        schema = lambda *keys: {"response_format": {"json_schema": {"schema": {"properties": dict.fromkeys(keys)}}}}  # noqa: E731
        msg = lambda text: {"messages": [{"role": "user", "content": text}]}  # noqa: E731
        self.assertEqual(stub_llm.answer_for({**msg("x"), **schema("paragraphs", "label")}, 2),
                         {"paragraphs": [1], "label": 2})
        self.assertEqual(stub_llm.answer_for({**msg("=== PAGE 7 ===\nt"), **schema("pages", "label")}, 0),
                         {"pages": [7], "label": 0})
        self.assertEqual(stub_llm.answer_for(msg("x"), 1), {"label": 1})
        self.assertEqual(stub_llm.decide(msg("STUB_FAIL_ONCE"), cfg, 1), ("fail", 2))
        self.assertEqual(stub_llm.decide(msg("STUB_FAIL_ONCE"), cfg, 2), ("ok", 2))
        self.assertEqual(stub_llm.decide(msg("STUB_FAIL"), cfg, 3), ("fail", 2))
        self.assertEqual(stub_llm.decide(msg("STUB_LABEL_1 STUB_GARBAGE"), cfg, 4), ("garbage", 1))


if __name__ == "__main__":
    unittest.main()
