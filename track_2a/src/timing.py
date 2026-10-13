"""Phase timing for the local-time profile (session 11, step 4a). Off unless PROFILE_PHASES=1; never changes a result.

With PROFILE_PHASES=1, each process adds up the seconds spent in named phases (PDF reading, booklet parsing, loading
e5, embedding, preparing a case, the main process waiting with no prepared case) and writes one line
"PHASES {pid, role, totals}" to stderr when it ends (src/pipeline.py calls report() at the end of a lane and of the
run). scripts/local_time.py's stderr.log keeps these lines.
"""

import json
import os
import sys
import time
from contextlib import contextmanager

ENABLED = os.environ.get("PROFILE_PHASES") == "1"
_totals = {}
_counts = {}


@contextmanager
def phase(name):
    if not ENABLED:
        yield
        return
    start = time.perf_counter()
    try:
        yield
    finally:
        _totals[name] = _totals.get(name, 0.0) + time.perf_counter() - start
        _counts[name] = _counts.get(name, 0) + 1


def add(name, seconds):
    if ENABLED:
        _totals[name] = _totals.get(name, 0.0) + seconds
        _counts[name] = _counts.get(name, 0) + 1


def report(role):
    if ENABLED:
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # kilobytes on Linux
        print("PHASES " + json.dumps({"pid": os.getpid(), "role": role, "max_rss_mib": round(peak, 1),
                                       "seconds": {k: round(v, 3) for k, v in _totals.items()}, "counts": _counts}),
              file=sys.stderr, flush=True)
