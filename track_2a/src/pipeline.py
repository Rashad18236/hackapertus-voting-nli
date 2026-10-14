"""Background preparation of cases (session 10): local work runs while a model request is in flight.

The organisers count as local time everything the container does while no model request is in flight
(docs/official_scoring.md). Before session 10 the cases ran one after another: read and parse the booklet,
route the claim, embed if needed, build the messages, then send the request and wait. The local work of
every case therefore lay between two requests and counted in full.

Here background worker processes ("lanes", src/pipeline.Lanes) prepare the cases (src/cli.py's prepare())
while the main process sends the prepared ones (complete()), one request at a time by default:

- The main process sends the prepared cases in the order they become ready; a case is sent as soon as it is
  ready and no other request is in flight (in_flight=2 allows two at once; off by default).
- Each lane owns whole booklets (lane_key; src/cli.py: task A cases by booklet, task B cases in lane 0), so no
  booklet is read twice, and two lanes read two booklets at the same time on two CPUs.
- Within a lane the cases are prepared in an order chosen by the caller (order_key; src/cli.py's
  preparation_key): task B cases whose preparation needs no local model first, so the first requests go out
  while the embedding model is still loading; task A cases grouped by booklet, so each booklet's later cases are
  ready as soon as it has been read.
- Results do not depend on the order or the timing: a case's request depends only on the case and the
  booklet (all caches are keyed by content, src/memo.py), and the model answers each request on its own.
- If a case's preparation raises in a lane (or the lane dies), the case runs on the sequential path (prepare
  and complete in the main process), so a worker error never costs a case its answer.

Processes, not threads (measured in session 10): Python runs one thread at a time, and the PDF reader (pure
Python) and the creation of the ONNX session (up to 2.5 s in one piece) kept the thread that sends the requests
waiting; in a 300-case task B run the second request left 7.6 s late. The lanes are forked, so they start with
the modules already imported, and they are forked before this process starts any thread. processes=False runs
the workers as threads (tests with fake steps).
"""

import collections
import logging
import math
import multiprocessing
import os
import threading
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from pathlib import Path

from src import timing

log = logging.getLogger("pipeline")


def cgroup_cpus():
    """The container's CPU limit (docker run --cpus) from cgroup v2 or v1, or None if there is none."""
    try:
        quota, period = Path("/sys/fs/cgroup/cpu.max").read_text().split()[:2]
        if quota != "max":
            return int(quota) / int(period)
    except (OSError, ValueError):
        pass
    try:
        quota = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        period = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        if quota > 0 and period > 0:
            return quota / period
    except (OSError, ValueError):
        pass
    return None


def available_cpus():
    """CPUs this process may use: the CPUs it may run on, capped by the container's CPU limit."""
    try:
        cpus = len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        cpus = os.cpu_count() or 1
    limit = cgroup_cpus()
    if limit:
        cpus = min(cpus, max(1, math.floor(limit)))
    return max(1, cpus)


def cgroup_memory():
    """The container's memory limit in bytes (docker run --memory) from cgroup v2 or v1, or None if there is none."""
    for path in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            value = Path(path).read_text().strip()
        except OSError:
            continue
        if value != "max" and value.isdigit() and int(value) < 2**60:  # v1 reports a huge number for "no limit"
            return int(value)
    return None


# Session 11, step 5: the lanes' number from the container's memory limit (each lane that embeds holds its own copy
# of e5). None leaves the number to the CPUs alone, as in session 10.
MEMORY_FOR_TWO_LANES = 2684354560  # bytes (2.5 GiB; session 11, step 5, adopted); below it one lane
# Session 14, step 2: the same limit for a run in which no case can load e5 (src/cli.py's loads_no_e5: task A only, with
# model S as the ranker). Its lanes hold model S's table, not e5, so two of them fit in less memory: two lanes forced
# in today's image peaked at 230 MiB at most (dev, val and probe task A, 4g, 0.1 and 0.3 s per request); the limit is
# the smallest memory-grid limit of at least twice that, 512 MiB, where two lanes wrote every dev response with the
# labels of the 4g run. None: the run uses MEMORY_FOR_TWO_LANES like every other.
MEMORY_FOR_TWO_LANES_S = 536870912  # bytes (512 MiB; session 14, step 2)
MEMORY_FOR_ONE_LANE = None   # bytes; below it no lane (every case in turn in the main process)


def default_workers(without_e5=False):
    """Worker processes: two on a machine with at least two CPUs, else one. Each worker owns whole booklets
    (src/cli.py's lane_key), so no booklet is read twice; the main process needs little CPU. Session 11, step 5:
    fewer under a low memory limit (MEMORY_FOR_TWO_LANES, MEMORY_FOR_ONE_LANE). Session 14, step 2: a run in which no
    case can load e5 (without_e5) has one lane only below MEMORY_FOR_TWO_LANES_S."""
    workers = 2 if available_cpus() >= 2 else 1
    memory = cgroup_memory()
    if memory is not None and MEMORY_FOR_ONE_LANE is not None and memory < MEMORY_FOR_ONE_LANE:
        return 0
    two_lanes = MEMORY_FOR_TWO_LANES
    if without_e5 and MEMORY_FOR_TWO_LANES_S is not None:
        two_lanes = MEMORY_FOR_TWO_LANES_S
    if memory is not None and two_lanes is not None and memory < two_lanes:
        return min(workers, 1)
    return workers


LIGHT_FIRST = True  # session 11, step 4 (adopted): a lane prepares the cases that need no embedding model first (deferral.py)
SHARE_CPUS = True  # session 11, step 4 (adopted): the lanes share the CPUs for onnxruntime's threads (embedding_threads)
LANES = {"count": 0}  # lanes of this run, set before they are forked (each lane inherits it)


def embedding_threads():
    """onnxruntime threads for one process's embedding model: every CPU (session 10), or with SHARE_CPUS each lane
    its share of them, so that two lanes embedding at once do not run more threads than there are CPUs (an idle
    onnxruntime thread spins and takes CPU time from the other lane)."""
    cpus = available_cpus()
    if SHARE_CPUS and LANES["count"] > 1:
        return max(1, cpus // LANES["count"])
    return cpus


class Lanes:
    """Worker processes ("lanes"), each preparing its own list of cases in order and sending each result back
    through a pipe as soon as it is ready. A lane gets its list when it is forked, so nothing is sent to it; all
    lanes are forked before this process starts any thread (forking a process that runs threads can deadlock the
    child). If a lane dies, its unfinished cases fail and run on the sequential path (pipeline.run)."""

    def __init__(self, groups, prepare):
        methods = multiprocessing.get_all_start_methods()
        context = multiprocessing.get_context("fork" if "fork" in methods else None)
        self.futures = {number: Future() for group in groups for number, _ in group}
        self.processes, readers = [], []
        for group in groups:
            receive, send = context.Pipe(duplex=False)
            process = context.Process(target=_lane, args=(group, prepare, send), daemon=True)
            process.start()
            send.close()  # this process's copy of the write end: the pipe ends when the lane ends
            self.processes.append(process)
            readers.append(threading.Thread(target=self._read, args=(receive, group), daemon=True))
        for reader in readers:  # only now, after every fork
            reader.start()

    def _read(self, receive, group):
        pending = {number for number, _ in group}
        try:
            while pending:
                number, ok, value = receive.recv()
                pending.discard(number)
                if ok:
                    self.futures[number].set_result(value)
                else:
                    self.futures[number].set_exception(RuntimeError(value))
        except (EOFError, OSError):
            pass
        for number in pending:  # the lane ended before preparing these
            self.futures[number].set_exception(RuntimeError("worker process ended"))

    def close(self):
        for process in self.processes:
            process.join(timeout=5)


def _lane(group, prepare, send):
    """A worker process: prepare each case of its list and send (number, ok, result or error text).

    Session 11, step 4 (src/deferral.py): first every case that needs no embedding model, in list order; a case that
    would need the model is put aside and prepared in a second pass, in list order."""
    from src import deferral, timing
    deferred = []
    for passes, cases in (("first", group), ("second", deferred)):
        deferral.DEFER["on"] = passes == "first" and LIGHT_FIRST
        for number, case in list(cases):
            try:
                message = (number, True, prepare(case))
            except deferral.NeedsModel:
                deferred.append((number, case))
                continue
            except Exception as e:
                message = (number, False, f"{type(e).__name__}: {e}")
            try:
                send.send(message)
            except Exception as e:  # e.g. a result that cannot be sent
                send.send((number, False, f"{type(e).__name__}: {e}"))
    deferral.DEFER["on"] = False
    timing.report("lane")
    send.close()


def run(items, prepare, complete, fallback, emit, workers, in_flight=1, order_key=None, processes=True,
        lane_key=None):
    """Answer every item.

    items: [(number, case)] in input order. prepare(case) -> prepared (in a worker); complete(prepared) -> result
    (in the call thread; makes the model call); fallback(case) -> result (the sequential path, used when prepare
    raised); emit(number, case, result) (in this thread, as each case finishes).
    order_key(case) -> a sort key: the cases are prepared in this order (stable: input order for equal keys).
    lane_key(case) -> an int: with processes=True, the case goes to worker process lane_key % workers (default 0);
    with processes=False, `workers` threads share all cases (tests with fake steps)."""
    order = list(items)
    if order_key is not None:
        order.sort(key=lambda item: order_key(item[1]))
    ready = collections.deque()  # (number, case, finished preparation future), in the order they became ready
    lanes = None
    if processes:
        groups = [[] for _ in range(max(1, workers))]
        for number, case in order:
            groups[(lane_key(case) if lane_key else 0) % len(groups)].append((number, case))
        LANES["count"] = sum(1 for g in groups if g)
        lanes = Lanes([g for g in groups if g], prepare)  # forked before any thread below starts
        preparing = {lanes.futures[number]: (number, case) for number, case in order}
        preparers = None
    else:
        preparers = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="prepare")
        preparing = {preparers.submit(prepare, case): (number, case) for number, case in order}
    try:
        with ThreadPoolExecutor(max_workers=in_flight, thread_name_prefix="call") as callers:
            calling = {}
            while preparing or calling or ready:
                while ready and len(calling) < in_flight:
                    number, case, future = ready.popleft()
                    calling[callers.submit(_complete, future, case, complete, fallback)] = (number, case)
                idle = not calling and not ready  # session 11, step 4a: nothing to send, waiting for a lane
                started = time.perf_counter()
                done, _ = wait(set(preparing) | set(calling), return_when=FIRST_COMPLETED)
                if idle:
                    timing.add("main_wait_no_case", time.perf_counter() - started)
                for future in sorted(done, key=lambda f: (preparing.get(f) or calling.get(f))[0]):
                    if future in preparing:
                        number, case = preparing.pop(future)
                        ready.append((number, case, future))
                    else:
                        number, case = calling.pop(future)
                        emit(number, case, future.result())
    finally:
        timing.report("main")
        if preparers is not None:
            preparers.shutdown()
        if lanes is not None:
            lanes.close()


def _complete(future, case, complete, fallback):
    try:
        prepared = future.result()
    except Exception as e:  # the worker failed (or died): run the case on the sequential path
        log.warning("%s: preparation failed in the background (%s); running it on the sequential path",
                    case.get("id") if isinstance(case, dict) else "?", type(e).__name__)
        return fallback(case)
    return complete(prepared)
