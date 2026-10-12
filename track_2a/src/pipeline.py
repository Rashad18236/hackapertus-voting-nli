"""Background preparation of cases (session 10): local work runs while a model request is in flight.

The organisers count as local time everything the container does while no model request is in flight
(docs/official_scoring.md). Before session 10 the cases ran one after another: read and parse the booklet,
route the claim, embed if needed, build the messages, then send the request and wait. The local work of
every case therefore lay between two requests and counted in full.

Here a background worker process prepares the cases (src/cli.py's prepare()) while the main process sends
the prepared ones (complete()), one request at a time by default:

- The main process sends the prepared cases in the order they become ready; a case is sent as soon as it is
  ready and no other request is in flight (in_flight=2 allows two at once; off by default).
- The cases are prepared in an order chosen by the caller (order_key; src/cli.py's preparation_key): task B
  cases whose preparation needs no local model first, so the first requests go out while the embedding model
  is still loading; task A cases grouped by booklet, so each booklet's later cases are ready as soon as it has
  been read.
- Results do not depend on the order or the timing: a case's request depends only on the case and the
  booklet (all caches are keyed by content, src/memo.py), and the model answers each request on its own.
- If a case's preparation raises in the worker (or the worker dies), the case runs on the sequential path
  (prepare and complete in the main process), so a worker error never costs a case its answer.

A process, not threads (measured in session 10): Python runs one thread at a time, and the PDF reader (pure
Python) and the creation of the ONNX session (up to 2.5 s in one piece) kept the thread that sends the requests
waiting; in a 300-case task B run the second request left 7.6 s late. The worker process is forked, so it starts
with the modules already imported. processes=False runs the workers as threads (tests with fake steps).
"""

import collections
import logging
import math
import multiprocessing
import os
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, ThreadPoolExecutor, wait
from pathlib import Path

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


def default_workers():
    """One background worker process. A second one would read every booklet a second time (each process has its
    own caches), and the main process needs little CPU, so one worker also suits a single CPU."""
    return 1


def preparer_pool(workers, processes=True):
    """The executor that prepares cases: worker processes (forked where the platform allows), or threads."""
    if not processes:
        return ThreadPoolExecutor(max_workers=workers, thread_name_prefix="prepare")
    methods = multiprocessing.get_all_start_methods()
    context = multiprocessing.get_context("fork" if "fork" in methods else None)
    return ProcessPoolExecutor(max_workers=workers, mp_context=context)


def run(items, prepare, complete, fallback, emit, workers, in_flight=1, order_key=None, processes=True):
    """Answer every item.

    items: [(number, case)] in input order. prepare(case) -> prepared (in a worker; with processes=True it must
    be picklable, e.g. a module-level function or a functools.partial of one); complete(prepared) ->
    result (in the call thread; makes the model call); fallback(case) -> result (the sequential path, used
    when prepare raised); emit(number, case, result) (in this thread, as each case finishes).
    order_key(case) -> a sort key: the cases are prepared in this order (stable: input order for equal keys)."""
    order = list(items)
    if order_key is not None:
        order.sort(key=lambda item: order_key(item[1]))
    ready = collections.deque()  # (number, case, finished preparation future), in the order they became ready
    # The worker processes are forked at the first submit, before the call thread exists.
    with preparer_pool(workers, processes) as preparers, \
            ThreadPoolExecutor(max_workers=in_flight, thread_name_prefix="call") as callers:
        preparing = {preparers.submit(prepare, case): (number, case) for number, case in order}
        calling = {}
        while preparing or calling or ready:
            while ready and len(calling) < in_flight:
                number, case, future = ready.popleft()
                calling[callers.submit(_complete, future, case, complete, fallback)] = (number, case)
            done, _ = wait(set(preparing) | set(calling), return_when=FIRST_COMPLETED)
            for future in sorted(done, key=lambda f: (preparing.get(f) or calling.get(f))[0]):
                if future in preparing:
                    number, case = preparing.pop(future)
                    ready.append((number, case, future))
                else:
                    number, case = calling.pop(future)
                    emit(number, case, future.result())


def _complete(future, case, complete, fallback):
    try:
        prepared = future.result()
    except Exception as e:  # the worker failed (or died): run the case on the sequential path
        log.warning("%s: preparation failed in the background (%s); running it on the sequential path",
                    case.get("id") if isinstance(case, dict) else "?", type(e).__name__)
        return fallback(case)
    return complete(prepared)
