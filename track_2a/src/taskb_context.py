"""Task B context variants (session 9, phase C): how much of the reference passage Apertus reads.

The default was "cut" in session 9 and is "full" again since session 10, step 2 (B-cut's embedding costs local
time when the model is fast). The passage's words are never changed, only cut or numbered:

- "full" (default): the whole reference text with task B's prompt (v3-topic-first).
- "cut" (B-cut): a reference over CUT_CHARS characters becomes its first line (the ballot's title) plus the
  TOP_K paragraphs most similar to the claim (multilingual-e5-small, ranked as section-route ranks a long
  part), in their order; the prompt is unchanged. Shorter references stay whole.
- "cut4" (B-cut4, session 10, step 5): the same with CUT4_CHARS and CUT4_TOP_K: a reference over 3,000
  characters becomes its first line plus the 4 most similar paragraphs.
- "para" (B-para): the same text as numbered paragraphs ("[1] ..."), with task A's paragraph prompt and answer
  schema (A-v4-section-route); the answer's paragraph numbers are not used (task B evidence stays []).

Paragraphs come from src/booklet.py's page_paragraphs (the same splitting section-route uses): consecutive
lines, verbatim, fragments under 40 characters dropped. If the passage gives no paragraphs, the whole text is
used.
"""

from src import booklet
from src.contexts import section_route

MODES = ("full", "cut", "para", "cut4")
CUT_CHARS = 8000
TOP_K = 8
CUT4_CHARS = 3000
CUT4_TOP_K = 4
LIMITS = {"cut": (CUT_CHARS, TOP_K), "para": (CUT_CHARS, TOP_K), "cut4": (CUT4_CHARS, CUT4_TOP_K)}
PART_LINE = ("a passage from the booklet's section on the ballot named in VOTE; its first paragraph is the "
             "ballot's title (voice: as stated in the passage)")


def split(reference_text):
    """(first line, [paragraphs of the rest]) of a reference passage."""
    lines = reference_text.strip().splitlines()
    if not lines:
        return "", []
    return lines[0].strip(), booklet.page_paragraphs("\n".join(lines[1:]))


def is_long(reference_text, mode="cut"):
    return len(reference_text) > LIMITS.get(mode, (CUT_CHARS, TOP_K))[0]


def cut_paragraphs(reference_text, claim_text, mode="cut"):
    """(first line, paragraphs): all of them for a short reference, the top_k most similar to the claim (in their
    order) for a long one (CUT_CHARS and TOP_K, or the mode's own limits)."""
    top_k = LIMITS.get(mode, (CUT_CHARS, TOP_K))[1]
    first, paragraphs = split(reference_text)
    if is_long(reference_text, mode) and len(paragraphs) > top_k:
        paragraphs = [text for _, text in section_route.most_similar([(0, p) for p in paragraphs], claim_text,
                                                                     top_k)]
    return first, paragraphs


def cut_text(reference_text, claim_text, mode="cut"):
    """B-cut's (or B-cut4's) reference text: unchanged if short; else the first line and the kept paragraphs,
    verbatim."""
    if not is_long(reference_text, mode):
        return reference_text
    first, paragraphs = cut_paragraphs(reference_text, claim_text, mode)
    if not paragraphs:
        return reference_text
    return "\n\n".join([first] + paragraphs)


def para_texts(reference_text, claim_text):
    """B-para's numbered paragraphs, as shown to the model: the first line, then the (kept) paragraphs."""
    first, paragraphs = cut_paragraphs(reference_text, claim_text)
    if not paragraphs:
        return [section_route.display(reference_text)]
    return [first] + [section_route.display(p) for p in paragraphs]
