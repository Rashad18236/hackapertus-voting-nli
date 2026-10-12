"""Compute-once caches that are safe with several threads (session 10, background preparation).

Since session 10 the cases are prepared in background threads (src/pipeline.py). Every cache in src/ is keyed
by content (a booklet's SHA-256, a text's SHA-256, a claim), so its value never depends on which case asked
first. once() keeps it that way with threads and makes sure a value is computed only once: a second thread
that needs the same key waits for the first instead of doing the same work again.
"""

import threading

_guard = threading.Lock()
_locks = {}  # (id of the cache dict, key) -> lock


def once(cache, key, compute):
    """cache[key]; if missing, compute() is called once (other threads asking for the key wait) and stored."""
    try:
        return cache[key]
    except KeyError:
        pass
    with _guard:
        lock = _locks.setdefault((id(cache), key), threading.Lock())
    with lock:
        if key not in cache:
            cache[key] = compute()
    return cache[key]
