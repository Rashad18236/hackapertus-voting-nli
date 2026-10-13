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
    valid: set = field(default_factory=set)  # session 11: parts that passed their own checks (all PARTS when ok)


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
    """Booklet with its votes, or None when no contents entry is found.

    Session 11: per-part validity. A vote keeps every part that passes its own checks when another part fails
    (Vote.valid); Vote.ok still means that every check passed, and for such a vote the parts are exactly those of
    session 10. A booklet in the older layout (2016 to mid-2018, one contents entry per vote) is read by
    _parse_old_layout.
    """
    blocks = _blocks(pages)
    if not blocks:
        return _parse_old_layout(pages)
    blocks.sort(key=lambda b: b["summary"][0])
    last_page = max(pages)
    first_detail = min((b.get("overview", b.get("detail", 10**6)) for b in blocks), default=None)
    votes = []
    for i, b in enumerate(blocks):
        vote = Vote(title=b["title"], entry={k: v for k, v in b.items() if k != "title"})
        votes.append(vote)
        _parse_vote(pages, blocks, i, b, first_detail, last_page, vote)
    return Booklet(votes=votes)


def _parse_vote(pages, blocks, i, b, first_detail, last_page, vote):
    """Fill vote.parts, vote.valid, vote.boxes, vote.ok and vote.problems for contents block b."""
    missing = [k for k in ("summary", "detail", "arguments", "law") if k not in b]
    if missing:
        vote.problems.append(f"contents entry without {', '.join(missing)}")
    s0, s1 = b["summary"]  # a block always starts with its summary line
    nxt = blocks[i + 1] if i + 1 < len(blocks) else None
    s_end = (nxt["summary"][0] - 1) if nxt else (first_detail - 1 if first_detail else s1)
    # Section starts of all votes (overview pages, such as "Übersicht Volksinitiativen", can be
    # shared by two votes): a part ends before the next start.
    starts = sorted({x[k] for x in blocks for k in ("overview", "detail") if k in x})
    law = b.get("law")
    later = [n for n in starts if law is not None and n > law]
    law_end = (later[0] - 1) if later else last_page - 1  # the last page is the back cover
    overview = []
    if "overview" in b and "detail" in b:
        ov = b["overview"]
        overview = list(range(ov, min(n for n in starts + [b["detail"] + 1] if n > ov)))
    sequence = [max(s1, s_end)] + [b[k] for k in ("detail", "arguments", "law") if k in b]
    if not (s0 <= sequence[0] and all(x < y for x, y in zip(sequence, sequence[1:]))
            and (law is None or law <= law_end) and all(s_end < n < b["detail"] for n in overview[:1])):
        vote.problems.append("contents page numbers out of order")
        return
    headed = set()
    for part, page in (("summary", s0), ("detail", b.get("detail")), ("arguments", b.get("arguments")), ("law", law)):
        if page is None:
            continue
        if page not in pages or not _has(pages[page], _HEADINGS[part]):
            vote.problems.append(f"no {part} heading on page {page}")
        else:
            headed.add(part)
    if "arguments" in b and "arguments" not in headed and law is not None:
        # The text layer can lose a page's heading. The arguments' start still counts as confirmed when the
        # detail page's own list of sub-sections names the contents' arguments page (two sources agree).
        listed, _ = _sub_starts(pages, range(s0, law), b["arguments"], law)
        if b["arguments"] in listed.values():
            vote.problems.append(f"arguments start on page {b['arguments']} confirmed by the per-vote list only")
            headed.add("arguments")
    args_start = b.get("arguments") if "arguments" in headed else None
    if "arguments" not in b and {"detail", "law"} <= headed:
        args_start = _arguments_without_entry(pages, s0, b["detail"], law)
        if args_start is None:
            vote.problems.append("no arguments heading after the detailed section")
    sub = _sub_parts(pages, range(s0, law if law is not None else last_page), args_start, law, vote) \
        if args_start is not None and law is not None else None
    parts, valid = {}, set()
    if "summary" in headed:
        parts["summary"] = list(range(s0, max(s1, s_end) + 1))
        valid.add("summary")
    if "detail" in headed and args_start is not None:
        parts["detail"] = sorted(set(overview) | set(range(b["detail"], args_start)))
        valid.add("detail")
    parts["committee"], parts["parliament"] = [], []
    if sub is not None:
        parts.update(sub)
        valid |= {"committee", "parliament", "council"}
    if "law" in headed:
        parts["law"] = list(range(law, law_end + 1))
        valid.add("law")
    vote.parts = {k: parts[k] for k in ("summary", "detail", "committee", "parliament", "council", "law") if k in parts}
    vote.valid = valid
    vote.boxes = _boxes(pages, parts["summary"]) if "summary" in valid else {}
    vote.ok = not vote.problems
    if vote.ok:
        vote.valid = set(PARTS)


def _arguments_without_entry(pages, s0, detail, law):
    """The arguments' start page when the contents name none (session 11).

    General cause: a contents block can lack its arguments line (the text layer drops it), while the detail page's
    per-vote list and the page headings still name the sub-sections. The start is the earliest sub-section start
    found after the detailed section's first page (the same list-and-heading search as for every vote), and that
    page must carry an arguments heading, as a contents entry's start page must."""
    listed, headed = _sub_starts(pages, range(s0, law), detail + 1, law)
    found = sorted(set(listed.values()) | set(headed.values()))
    if found and found[0] in pages and _has(pages[found[0]], _HEADINGS["arguments"]):
        return found[0]
    return None


def _sub_parts(pages, vote_pages, args_start, law, vote):
    """{committee, parliament, council: pages} from the arguments' start, or None (with a problem) on a conflict."""
    listed, headed = _sub_starts(pages, vote_pages, args_start, law)
    starts = {}
    problems = []
    for name in ("committee", "council", "parliament"):
        if name in listed and name in headed and listed[name] != headed[name]:
            problems.append(f"{name}: listed on page {listed[name]}, heading on page {headed[name]}")
        elif name in listed or name in headed:
            starts[name] = listed.get(name, headed.get(name))
    if not problems and "council" not in starts:
        problems.append("no start page for the council's arguments")
    if not problems:
        order = sorted((page, name) for name, page in starts.items())
        if order[0][0] != args_start or len({page for page, _ in order}) < len(order):
            problems.append(f"arguments start on page {args_start}, sub-sections at {order}")
    if problems:
        vote.problems += problems
        return None
    # Each sub-section of the arguments runs to the page before the next one (the last: before the law text).
    ends = [page for page, _ in order[1:]] + [law]
    return {name: list(range(page, end)) for (page, name), end in zip(order, ends)}


# ---------------------------------------------------------------- the older layout (session 11)

# Booklets until mid-2018 list one contents entry per vote ("Informationen zur Vorlage Seiten 4–11",
# "Explications pages 4–11", "Spiegazioni pagine 4–11") and the pages of its legal text ("Der Abstimmungstext
# Seite 8", "Texte soumis au vote pages 9–10", "Testo in votazione pagina 8"; a block with two legal texts names
# each: "Der Text des Bundesgesetzes Seiten 26–61"). Inside a vote's pages, each part starts on a page whose
# heading names it. Seen on all 27 booklets from 2016-02-28 to 2018-06-10 (session 11, parser coverage).
def _spaced(word):
    """A word that may carry stray spaces between its letters in the text layer ("sei ten", "se iten")."""
    return r"\s?".join(re.escape(c) if c != " " else r"\s+" for c in word)


_OLD_PAGES = (rf"(?:{_spaced('seiten')}|{_spaced('seite')}|{_spaced('pages')}|{_spaced('page')}|{_spaced('pagine')}"
              rf"|{_spaced('pagina')})\s+(?P<a>{_NUM})(?:\s*[–-]\s*(?P<b>{_NUM}))?")
_OLD_BLOCK = re.compile(rf"^(?:{_spaced('informationen zur vorlage')}|{_spaced('explications')}|{_spaced('spiegazioni')})"
                        rf"\s+{_OLD_PAGES}(?:\s+\d+)?$")
_OLD_LAW = re.compile(rf"^(?:der abstimmungstext|texte soumis au vote|testo in votazione"
                      rf"|der text des (?:bundesbeschlusses|bundesgesetzes)|texte de (?:l'arrêté fédéral|la loi fédérale)"
                      rf"|testo (?:del decreto federale|della legge federale))\s+{_OLD_PAGES}$")
# Part headings, matched against a whole line near the top of a page (spaces removed).
_OLD_HEADINGS = {
    "summary": r"daswichtigsteinkürze|l'essentielenbref|l'essenzialeinbreve",
    "detail": r"dievorlageimdetail|l'objetendétail|ilprogettoindettaglio",
    "law": r"abstimmungstext|textesoumisauvote|testoinvotazione",
    "parliament": r"dieberatungenimparlament|lesdélibérationsparlementaires|ledeliberazioniinparlamento",
    "council": r"dieargumente(?:desbundesrates(?:unddesparlaments)?|vonbundesratundparlament)"
               r"|lesargumentsduconseilfédéral(?:etduparlement)?"
               r"|gliargomentidelconsigliofederale(?:edelparlamento)?",
    "committee": r"dieargumentedes(?:initiativ|referendums)komitees|lesargumentsducomité(?:d'initiative|référendaire)"
                 r"|gliargomentidelcomitato(?:d'iniziativa|referendario)",
}


def _old_heading(text):
    """The part whose heading is a whole line of the page (spaces removed), or None. The text layer does not always
    put the heading first, so every line is looked at; a heading must be the entire line, so a mention in the
    running text does not count."""
    lines = {norm(line).replace(" ", "") for line in text.splitlines()}
    for part, pattern in _OLD_HEADINGS.items():
        if any(re.fullmatch(pattern, line) for line in lines):
            return part
    return None


def _parse_old_layout(pages, first_pages=6):
    """Booklet in the older layout, or None when its contents entries are not found either."""
    entries, laws, title_lines = [], [], []
    for p in sorted(pages)[:first_pages]:
        for line in pages[p].splitlines():
            flat = norm(line)
            block, law = _OLD_BLOCK.match(flat), _OLD_LAW.match(flat)
            if block:
                a = _number(block.group("a"))
                b = _number(block.group("b")) if block.group("b") else a
                entries.append({"title": " ".join(t for t in title_lines if t), "range": (a, b), "law": []})
                title_lines = []
            elif law:
                a = _number(law.group("a"))
                b = _number(law.group("b")) if law.group("b") else a
                laws.append((len(entries) - 1, (a, b)))  # the entry read last, in case no range holds it
                title_lines = []
            elif flat:
                title_lines.append(line.strip())
    entries = [e for e in entries if e["range"][0] > first_pages // 2 and e["range"][0] <= e["range"][1]]
    if not entries:
        return None
    for before, (a, b) in laws:  # a legal text belongs to the vote whose pages hold it, else to the entry before it
        holder = [e for e in entries if e["range"][0] <= a <= e["range"][1]]
        if holder:
            holder[0]["law"].append((a, b))
        elif 0 <= before < len(entries):
            entries[before]["law"].append((a, b))
    votes = []
    for e in entries:
        a, b = e["range"]
        vote = Vote(title=e["title"], entry={"block": (a, b), "law": e["law"]})
        votes.append(vote)
        law_pages = sorted({n for x, y in e["law"] for n in range(x, y + 1)})
        if law_pages and not _has(pages.get(law_pages[0], ""), _HEADINGS["law"]):
            vote.problems.append(f"no law heading on page {law_pages[0]}")
            law_pages = []
        starts, seen = [], set()
        for p in range(a, b + 1):
            part = None if p in law_pages else _old_heading(pages.get(p, ""))
            if part and part not in seen and not (part == "law" and law_pages):
                starts.append((p, part))
                seen.add(part)
        if law_pages and law_pages[0] <= b:
            starts.append((law_pages[0], "law"))
        starts.sort()
        parts = {}
        for (page, part), nxt in zip(starts, [x for x, _ in starts[1:]] + [b + 1]):
            parts[part] = [n for n in range(page, nxt) if part == "law" or n not in law_pages]
        if law_pages:
            parts["law"] = law_pages
        if "summary" in parts and starts and starts[0][1] == "summary":
            parts["summary"] = list(range(a, starts[0][0])) + parts["summary"]  # the vote's overview page
        for part in ("summary", "detail", "council", "law"):
            if not parts.get(part):
                vote.problems.append(f"no {part} heading in pages {a}-{b}")
        vote.parts = {k: parts.get(k, []) for k in PARTS}
        vote.valid = {k for k in PARTS if parts.get(k)}
        vote.ok = not vote.problems
        if vote.ok:
            vote.valid = set(PARTS)
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
