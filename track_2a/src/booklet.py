"""Parse a Swiss federal voting booklet into its votes and each vote's parts.

Built in session 6 (Rashad, with Claude). Deterministic and local: no model,
no embeddings; it reads the page texts from src/parse.py.

Every booklet since 2020 has the same layout, in German, French and Italian:

- a table of contents near the front lists, per vote, the pages of its
  summary ("In Kürze 4 – 5" / "En bref" / "In breve"), its detailed section
  ("Im Detail 8" / "En détail" / "In dettaglio"), the arguments ("Argumente
  14" / "Arguments" / "Gli argomenti") and the text put to the vote
  ("Abstimmungstext 18" / "Texte soumis au vote" / "Il testo in votazione");
- the summaries come first, one after the other; then, per vote, the detailed
  section, the arguments (the committee's, then the Federal Council's and
  Parliament's) and the legal text;
- the summary pages hold one recommendation box per voice: the committee's,
  the Federal Council's and Parliament's, sometimes a parliamentary minority's,
  and Parliament's vote counts.

parse() returns a Booklet with one Vote per contents entry, or None when no
contents entry is found. Every start page from the contents is checked
against the heading printed on that page; a vote whose pages fail the check
gets no parts (Vote.ok is False), so callers fall back instead of guessing.

Parts of a vote (page numbers are 1-based PDF pages, as everywhere):

  "summary"     the summary pages (from the contents entry to the page before
                the next vote's summary, or before the first detailed section)
  "detail"      the detailed section, up to the page before the arguments
  "committee"   the committee's arguments (initiative or referendum committee)
  "parliament"  the parliamentary debate, where the arguments have such a section
  "council"     the Federal Council's and Parliament's arguments
  "law"         the text put to the vote, up to the page before the next
                vote's section (last vote: up to the page before the back cover)

and recommendation boxes on the summary pages, as verbatim text with their
page: "committee", "council", "parliament" (a parliamentary minority's
position, and the vote counts in both chambers).

Known gaps: some pages hold no extractable text (pypdf returns only the page
number; seen for the law text in a few booklets), so a part can be empty
text. The arguments' sub-sections are found from the per-vote list on the
detail page and from page headings; when both give a start page they must
agree, and the first sub-section must start where the contents say the
arguments start.
"""

import re
import unicodedata
from dataclasses import dataclass, field

from rapidfuzz import fuzz

PARTS = ("summary", "detail", "committee", "parliament", "council", "law")
VOICES = ("committee", "council", "parliament")

# Contents labels (normalised: lower case, single spaces, typographic apostrophes plain).
_LABELS = {
    "summary": r"in kürze|en bref|in breve",
    "overview": r"übersicht[^\d]*|vue d'ensemble[^\d]*|tabella riassuntiva[^\d]*",
    "detail": r"(?:vorlage )?im detail|(?:l'objet )?en détail|in dettaglio",
    "arguments": r"argumente|arguments|gli argomenti",
    "law": r"abstimmungstexte?|textes? soumis au vote|(?:il |i )?test[oi] in votazione",
}
_NUM = r"\d(?: ?\d){0,2}"  # page numbers are sometimes printed with spaces between digits ("1 4" = 14)
_ENTRY = re.compile(rf"^({'|'.join(f'(?P<{k}>{v})' for k, v in _LABELS.items())})\s+(?P<a>{_NUM})"
                    rf"(?:\s*[–-]\s*(?P<b>{_NUM}))?$")

# Headings checked on the start pages (anywhere on the page; pypdf may put them last). Matched with
# all spaces removed, because some booklets' text has stray spaces inside words (" a rgomenti").
_HEADINGS = {
    "summary": r"inkürze|enbref|inbreve",
    "detail": r"imdetail|endétail|indettaglio",
    "arguments": r"argumente|arguments|argomenti",
    "law": r"abstimmungstext|soumisauvote|invotazione|§",
}

# Sub-sections of the arguments, as named in the per-vote list on the detail page and as page headings.
_COMMITTEE = (r"argumente (?:des )?(?:initiativ|referendums)komitees?|arguments? (?:du |des )?comités? "
              r"(?:d'initiative|référendaires?)|gli argomenti (?:del comitato|dei comitati) "
              r"(?:d'iniziativa|referendari[oa]?)")
# "and Parliament" is optional: 2018-2019 booklets say "Argumente Bundesrat", "Les arguments du Conseil
# fédéral", "Gli argomenti del Consiglio federale" (session 8, P9).
_COUNCIL = (r"argumente (?:von |des )?bundesrat(?:es)?(?: und parlament)?"
            r"|arguments? (?:du )?conseil fédéral(?: et (?:du )?parlement)?"
            r"|gli argomenti del consiglio federale(?: e del parlamento)?")
# The parliamentary debate, a section of the arguments in a few booklets (matched with all spaces removed).
# 2018-09-23 calls it "Le deliberazioni in Parlamento" (session 8, P9).
_DEBATE = (r"debatte(?:im)?parlament|débats?(?:au)?parlement|dibattit[oi](?:parlamentar[ei]|(?:in|al)?parlamento)"
           r"|deliberazion[ei](?:in|al)?parlamento")
_DEBATE_LISTED = (r"debatte (?:im )?parlament|débats? (?:au )?parlement"
                  r"|dibattit[oi] (?:parlamentar[ei]|(?:in |al )?parlamento)"
                  r"|deliberazion[ei] (?:in |al )?parlamento")
# When a vote's arguments open with the parliamentary debate, that page carries no "Argumente" heading:
# the debate's heading counts as the arguments' start heading too (session 8, P9).
_HEADINGS["arguments"] += "|" + _DEBATE

# Recommendation boxes: who speaks. Matched with all spaces removed; the voice named first wins
# (a committee's box may say what it thinks of "Bundesrat und Parlament").
_VOICES = {
    "council": re.compile(r"bundesratund(?:das)?parlament|conseilfédéralet(?:le)?parlement"
                          r"|consigliofederalee(?:il)?parlamento"),
    "committee": re.compile(r"komitee|comité|comitat[oi]"),
    "parliament": re.compile(r"minderheit|minorité|minoranza|mitglieder(?:des|von)|membres(?:du|de)|membri(?:del|di)"),
}
_URL = re.compile(r"\w\.ch\b|\.ch/")
_ANSWER = re.compile(r"^(?:ja|nein|oui|non|sì|si|no)$")
_COUNTS = re.compile(r"^\d{1,3} (?:ja|nein|enthaltungen?|oui|non|abstentions?|sì|si|no|astensioni|astensione)$")


@dataclass
class Vote:
    title: str                      # the contents entry's title lines (may carry layout noise)
    entry: dict                     # contents page numbers: summary (start, end), detail, arguments, law
    parts: dict = field(default_factory=dict)  # part -> [page numbers]
    boxes: dict = field(default_factory=dict)  # voice -> [(page, verbatim text)]
    ok: bool = False                # every check passed
    problems: list = field(default_factory=list)


@dataclass
class Booklet:
    votes: list


def norm(text):
    text = unicodedata.normalize("NFKC", text).replace("\xad", "").replace("’", "'")
    return re.sub(r"\s+", " ", text).strip().lower()


def _number(s):
    return int(s.replace(" ", ""))


def contents_entries(pages, first_pages=6):
    """[(page, label, a, b)] for every contents line on the first pages, in reading order."""
    found = []
    for p in sorted(pages)[:first_pages]:
        for line in pages[p].splitlines():
            m = _ENTRY.match(norm(line))
            if m:
                label = next(k for k in _LABELS if m.group(k))
                b = _number(m.group("b")) if m.group("b") else None
                found.append((p, label, _number(m.group("a")), b, line))
    return found


def _blocks(pages):
    """Contents blocks: one per vote, each starting with a summary line on a contents page."""
    entries = contents_entries(pages)
    contents_pages = {p for p, label, a, *_ in entries if label == "summary" and a > p}
    blocks, current = [], None
    for p in sorted(contents_pages):
        title_lines = []
        for line in pages[p].splitlines():
            m = _ENTRY.match(norm(line))
            if not m:
                title_lines.append(line.strip())
                continue
            label = next(k for k in _LABELS if m.group(k))
            a, b = _number(m.group("a")), (_number(m.group("b")) if m.group("b") else None)
            if label == "summary":
                current = {"title": " ".join(t for t in title_lines if t), "summary": (a, b if b else a)}
                blocks.append(current)
                title_lines = []
            elif current is not None and label not in current:
                current[label] = a
                title_lines = []
    return blocks


def _has(text, pattern):
    return re.search(pattern, norm(text).replace(" ", "")) is not None


def _sub_starts(pages, vote_pages, args_start, law_start):
    """Start pages of the committee's and the council's arguments: per-vote list first, page headings second."""
    listed = {}
    for p in vote_pages:
        flat = norm(pages[p])
        for name, pattern in (("committee", _COMMITTEE), ("council", _COUNCIL), ("parliament", _DEBATE_LISTED)):
            for m in re.finditer(rf"(?:{pattern}) ({_NUM})(?!\d)", flat):
                n = _number(m.group(1))
                if args_start <= n < law_start:
                    listed.setdefault(name, n)
    headed = {}
    for p in range(args_start, law_start):
        flat = norm(re.sub(r"\d", " ", pages.get(p, "")))  # numbers removed: list lines must not count
        for name, pattern in (("committee", _COMMITTEE), ("council", _COUNCIL)):
            if name not in headed and re.search(pattern, flat):
                headed[name] = p
        lines = (norm(line).replace(" ", "") for line in pages.get(p, "").splitlines())
        if "parliament" not in headed and any(re.fullmatch(_DEBATE, line) for line in lines):
            headed["parliament"] = p  # a heading line, not a mention in the text
    return listed, headed


def _boxes(pages, summary_pages):
    """Recommendation boxes on the summary pages: voice -> [(page, verbatim text)]."""
    boxes = {v: [] for v in VOICES}
    for p in summary_pages:
        lines = pages.get(p, "").splitlines()
        i = 0
        while i < len(lines):
            if _ANSWER.match(norm(lines[i]).replace(" ", "")):
                j = i + 1
                while j < len(lines) and not _URL.search(lines[j]) and not _ANSWER.match(norm(lines[j]).replace(" ", "")):
                    j += 1
                body = "\n".join(lines[i:j]).strip()
                text = norm(body).replace(" ", "")
                url = norm(lines[j]).replace(" ", "") if j < len(lines) and _URL.search(lines[j]) else ""
                if "admin.ch" in url:  # the Federal Council's box links to admin.ch
                    voice = "council"
                elif re.search(r"parlament\.ch|parlement\.ch|parlamento\.ch", url):  # a parliamentary minority
                    voice = "parliament"
                elif url:  # the committee links to its own site
                    voice = "committee"
                else:
                    first = sorted((m.start(), v) for v, rx in _VOICES.items() for m in [rx.search(text)] if m)
                    voice = first[0][1] if first else None
                if voice and len(text) > 40:
                    boxes[voice].append((p, body))
                i = j
            else:
                i += 1
        counts = [line for line in lines if _COUNTS.match(norm(line))]
        if counts:
            boxes["parliament"].append((p, "\n".join(c.strip() for c in counts)))
    return boxes


def parse(pages):
    """Booklet with its votes, or None when no contents entry is found."""
    blocks = _blocks(pages)
    if not blocks:
        return None
    blocks.sort(key=lambda b: b["summary"][0])
    last_page = max(pages)
    first_detail = min((b.get("overview", b.get("detail", 10**6)) for b in blocks), default=None)
    votes = []
    for i, b in enumerate(blocks):
        vote = Vote(title=b["title"], entry={k: v for k, v in b.items() if k != "title"})
        votes.append(vote)
        missing = [k for k in ("summary", "detail", "arguments", "law") if k not in b]
        if missing:
            vote.problems.append(f"contents entry without {', '.join(missing)}")
            continue
        s0, s1 = b["summary"]
        nxt = blocks[i + 1] if i + 1 < len(blocks) else None
        s_end = (nxt["summary"][0] - 1) if nxt else (first_detail - 1 if first_detail else s1)
        # Section starts of all votes (overview pages, such as "Übersicht Volksinitiativen", can be
        # shared by two votes): a part ends before the next start.
        starts = sorted({x[k] for x in blocks for k in ("overview", "detail") if k in x})
        later = [n for n in starts if n > b["law"]]
        law_end = (later[0] - 1) if later else last_page - 1  # the last page is the back cover
        overview = []
        if "overview" in b:
            ov = b["overview"]
            overview = list(range(ov, min(n for n in starts + [b["detail"] + 1] if n > ov)))
        if not (s0 <= max(s1, s_end) < b["detail"] < b["arguments"] < b["law"] <= law_end
                and all(s_end < n < b["detail"] for n in overview[:1])):
            vote.problems.append("contents page numbers out of order")
            continue
        for part, page in (("summary", s0), ("detail", b["detail"]), ("arguments", b["arguments"]), ("law", b["law"])):
            if page not in pages or not _has(pages[page], _HEADINGS[part]):
                vote.problems.append(f"no {part} heading on page {page}")
        if vote.problems:
            continue
        vote_pages = range(s0, b["law"])
        listed, headed = _sub_starts(pages, vote_pages, b["arguments"], b["law"])
        starts = {}
        for name in ("committee", "council", "parliament"):
            if name in listed and name in headed and listed[name] != headed[name]:
                vote.problems.append(f"{name}: listed on page {listed[name]}, heading on page {headed[name]}")
            elif name in listed or name in headed:
                starts[name] = listed.get(name, headed.get(name))
        if vote.problems:
            continue
        if "council" not in starts:
            vote.problems.append("no start page for the council's arguments")
            continue
        order = sorted((page, name) for name, page in starts.items())
        if order[0][0] != b["arguments"] or len({page for page, _ in order}) < len(order):
            vote.problems.append(f"arguments start on page {b['arguments']}, sub-sections at {order}")
            continue
        # Each sub-section of the arguments runs to the page before the next one (the last: before the law text).
        ends = [page for page, _ in order[1:]] + [b["law"]]
        vote.parts = {
            "summary": list(range(s0, max(s1, s_end) + 1)),
            "detail": sorted(set(overview) | set(range(b["detail"], b["arguments"]))),
            "committee": [],
            "parliament": [],
            **{name: list(range(page, end)) for (page, name), end in zip(order, ends)},
            "law": list(range(b["law"], law_end + 1)),
        }
        vote.boxes = _boxes(pages, vote.parts["summary"])
        vote.ok = True
    return Booklet(votes=votes)


def find_vote(booklet, vote_name, min_score=80, min_lead=5):
    """The Vote whose contents title holds `vote_name` best (fuzzy), or None if none is clear.

    On dev the right vote scores 81 to 100 and leads the next one by at least 7.8
    points; the lowest is "Modifica del diritto di locazione" against the title
    "Modifica del Codice delle obbligazioni (Diritto di locazione: ...)".
    """
    if booklet is None or not vote_name.strip():
        return None
    key = norm(vote_name)
    # partial_ratio slides the shorter text along the longer: the vote name inside a title that also
    # names a second ballot or carries layout noise still scores high.
    scored = sorted(((fuzz.partial_ratio(key, norm(v.title)), i) for i, v in enumerate(booklet.votes)), reverse=True)
    if not scored or scored[0][0] < min_score:
        return None
    if len(scored) > 1 and scored[1][0] > scored[0][0] - min_lead:
        return None  # two votes match about equally well: do not guess
    return booklet.votes[scored[0][1]]


# ---------------------------------------------------------------- paragraphs

# Running headers ("Erste Vorlage: Biodiversitätsinitiative", "Premier objet : loi sur le CO2",
# "Secondo e terzo oggetto: AVS"), with or without the page number in front.
_ORDINALS = (r"(?:erste|zweite|dritte|vierte|fünfte|sechste)(?: und (?:zweite|dritte|vierte|fünfte|sechste))? "
             r"vorlagen?|(?:premier|deuxième|troisième|quatrième|cinquième|sixième)(?: et (?:deuxième|troisième"
             r"|quatrième|cinquième|sixième))? objets?|(?:primo|secondo|terzo|quarto|quinto|sesto)(?: e (?:secondo"
             r"|terzo|quarto|quinto|sesto))? oggett[oi]")
_RUNNING_HEADER = re.compile(rf"^\d*\s*(?:{_ORDINALS})\s*:")
_PAGE_NUMBER = re.compile(r"^\d{1,3}(?: ?\d{1,3})?$")  # "14", "1414", "13 13": printed page numbers
_ARTIFACT = re.compile(r"^[-–§\s]*$")                  # lone hyphens and section signs left by the PDF text
_END = re.compile(r"[.!?:;»«\"“”)]$")
MIN_PARAGRAPH_CHARS = 40


def _clean_lines(text):
    """The page's lines without running headers, page numbers and artifacts (right-stripped, otherwise verbatim)."""
    out = []
    for line in text.splitlines():
        flat = norm(line)
        if not flat or _PAGE_NUMBER.match(flat) or _ARTIFACT.match(flat) or _RUNNING_HEADER.match(flat):
            continue
        out.append(line.rstrip())
    return out


def page_paragraphs(text):
    """Split one page's text into paragraphs: lists of consecutive lines, verbatim.

    A paragraph ends after a line that ends a sentence and is clearly shorter
    than the page's full lines (the last line of a paragraph), and around a
    short line without final punctuation (a heading or label). Fragments under
    MIN_PARAGRAPH_CHARS characters are dropped (margin headings, box labels,
    chart numbers, the ballot question's last line).
    """
    lines = _clean_lines(text)
    lengths = sorted(len(line.strip()) for line in lines if len(line.strip()) >= 30)
    full = lengths[int(0.75 * (len(lengths) - 1))] if lengths else 60
    paragraphs, current = [], []
    for line in lines:
        s = line.strip()
        heading = len(s) < 40 and not _END.search(s)
        if heading and current:
            paragraphs.append(current)
            current = []
        current.append(line)
        if heading or (_END.search(s) and len(s) < 0.85 * full):
            paragraphs.append(current)
            current = []
    if current:
        paragraphs.append(current)
    texts = ["\n".join(p).strip() for p in paragraphs]
    return [t for t in texts if len(norm(t)) >= MIN_PARAGRAPH_CHARS]


def part_paragraphs(pages, vote, part):
    """[(page, verbatim paragraph text)] of a vote's part, in page order.

    The committee's and the council's parts also get their recommendation
    boxes from the summary pages (which come first in the booklet).
    """
    out = []
    if part in ("committee", "council", "parliament"):
        out += [(p, text) for p, text in vote.boxes.get(part, []) if not _COUNTS.match(norm(text.splitlines()[0]))]
    for p in vote.parts.get(part, []):
        out += [(p, text) for text in page_paragraphs(pages.get(p, ""))]
    return out
