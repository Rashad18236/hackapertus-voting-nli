"""Background preparation of cases (session 10): local work runs while a model request is in flight.

The organisers count as local time everything the container does while no model request is in flight
(docs/official_scoring.md). Before session 10 the cases ran one after another: read and parse the booklet,
route the claim, embed if needed, build the messages, then send the request and wait. The local work of
every case therefore lay between two requests and counted in full.

Here up to `workers` background threads prepare the cases (src/cli.py's prepare()) while the main loop sends
the prepared ones (complete()), one request at a time by default:

- The main loop sends the prepared cases in the order they become ready; a case is sent as soon as it is
  ready and no other request is in flight (in_flight=2 allows two at once; off by default).
- Cases whose preparation needs no local model come first (light_first), so the first request goes out
  while the embedding model is still loading.
- Results do not depend on the order or the timing: a case's request depends only on the case and the
  booklet (all caches are keyed by content, src/memo.py), and the model answers each request on its own.
- If a case's preparation raises in a worker, the case runs on the sequential path (prepare and complete in
  the call thread), so a worker error never costs a case its answer.

Threads, not processes: the PDF parser, the parsed booklets and the embedding model are then shared, the
embedding model is loaded once (onnxruntime and the tokenizer release the GIL while they compute), and the
main loop mostly waits for the network.
"""

import collections
import logging
import math
import os
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
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
    """Two background workers, one on a machine with a single CPU (the main loop needs little CPU)."""
    return 2 if available_cpus() >= 2 else 1


def run(items, prepare, complete, fallback, emit, workers, in_flight=1, light_first=None):
    """Answer every item.

    items: [(number, case)] in input order. prepare(case) -> prepared (in a worker); complete(prepared) ->
    result (in the call thread; makes the model call); fallback(case) -> result (the sequential path, used
    when prepare raised); emit(number, case, result) (in this thread, as each case finishes).
    light_first(case) -> True for cases whose preparation needs no local model; they are prepared first."""
    order = list(items)
    if light_first is not None:
        order.sort(key=lambda item: not light_first(item[1]))  # stable: input order within each group
    ready = collections.deque()  # (number, case, finished preparation future), in the order they became ready
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="prepare") as preparers, \
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
    except Exception as e:  # the worker failed: run the case on the sequential path
        log.warning("%s: preparation failed in the background (%s); running it on the sequential path",
                    case.get("id") if isinstance(case, dict) else "?", type(e).__name__)
        return fallback(case)
    return complete(prepared)
