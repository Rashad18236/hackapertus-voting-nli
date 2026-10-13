"""Light cases first (session 11, step 4): a worker process prepares every case that needs no embedding model
first, and the others in a second pass.

The organisers count local time: a gap between two requests counts, model latency does not. The long gaps of a
task A run came from cases whose routed part is long, so that e5 has to embed the whole part before the 8 paragraphs
can be chosen (up to 7 s for one long law text): while a lane embedded, the main process had nothing to send. With
DEFER on (src/pipeline.py turns it on for a lane's first pass), the embedding model refuses to load or embed and
raises NeedsModel; the lane puts the case aside and prepares it in its second pass, when the main process has the
light cases to send. A cached result needs no model, so it never raises. Only the order of the work changes: every
request is the same (gates G1, G2).

NeedsModel derives from BaseException, not Exception, so that no "except Exception" fallback in src/ mistakes it
for a failure (a routing error would otherwise send the case down another path).
"""

DEFER = {"on": False}


class NeedsModel(BaseException):
    """Raised by the embedding model while DEFER is on: this case needs the model."""


def check():
    if DEFER["on"]:
        raise NeedsModel()
