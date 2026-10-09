"""Task B context variants (session 9, phase C): how much of the reference passage Apertus reads.

The default since session 9 is "cut" (phase C: the rule held on dev and val). The passage's words are never
changed, only cut or numbered:

- "full": the whole reference text with task B's prompt (v3-topic-first), the default until session 9.
- "cut" (B-cut, default): a reference over CUT_CHARS characters becomes its first line (the ballot's title) plus the
  TOP_K paragraphs most similar to the claim (multilingual-e5-small, ranked as section-route ranks a long
  part), in their order; the prompt is unchanged. Shorter references stay whole.
- "para" (B-para): the same text as numbered paragraphs ("[1] ..."), with task A's paragraph prompt and answer
  schema (A-v4-section-route); the answer's paragraph numbers are not used (task B evidence stays []).

Paragraphs come from src/booklet.py's page_paragraphs (the same splitting section-route uses): consecutive
lines, verbatim, fragments under 40 characters dropped. If the passage gives no paragraphs, the whole text is
used.
"""

from src import booklet
from src.contexts import section_route

MODES = ("full", "cut", "para")
CUT_CHARS = 8000
TOP_K = 8
PART_LINE = ("a passage from the booklet's section on the ballot named in VOTE; its first paragraph is the "
             "ballot's title (voice: as stated in the passage)")


def split(reference_text):
    """(first line, [paragraphs of the rest]) of a reference passage."""
    lines = reference_text.strip().splitlines()
    if not lines:
        return "", []
    return lines[0].strip(), booklet.page_paragraphs("\n".join(lines[1:]))


def is_long(reference_text):
    return len(reference_text) > CUT_CHARS


def cut_paragraphs(reference_text, claim_text):
    """(first line, paragraphs): all of them for a short reference, the TOP_K most similar to the claim (in their
    order) for a long one."""
    first, paragraphs = split(reference_text)
    if is_long(reference_text) and len(paragraphs) > TOP_K:
        paragraphs = [text for _, text in section_route.most_similar([(0, p) for p in paragraphs], claim_text,
                                                                     TOP_K)]
    return first, paragraphs


def cut_text(reference_text, claim_text):
    """B-cut's reference text: unchanged if short; else the first line and the kept paragraphs, verbatim."""
    if not is_long(reference_text):
        return reference_text
    first, paragraphs = cut_paragraphs(reference_text, claim_text)
    if not paragraphs:
        return reference_text
    return "\n\n".join([first] + paragraphs)


def para_texts(reference_text, claim_text):
    """B-para's numbered paragraphs, as shown to the model: the first line, then the (kept) paragraphs."""
    first, paragraphs = cut_paragraphs(reference_text, claim_text)
    if not paragraphs:
        return [section_route.display(reference_text)]
    return [first] + [section_route.display(p) for p in paragraphs]
