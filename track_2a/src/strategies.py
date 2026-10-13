"""Multi-call strategies for one case (robustness experiments, Kaan; all off by default).

Each strategy asks Apertus more than once about the same case and combines the answers. The caller (src/cli.py)
passes a `judge(claim_text, texts)` function that makes exactly the request the pipeline makes today for that
case (task A: the routed part's numbered paragraphs; task B: the reference's lines) and returns a Judgement.
So a strategy changes what is asked, never how one question is asked.

- "xlang"     (cross-language tournament). Only when the claim's language differs from the source's; otherwise
              the case runs as today (one call). Side S: the claim translated into the source's language against
              the original text. Side C: the original claim against the text translated into the claim's
              language (paragraph numbers kept, so cited numbers still point at the original verbatim text).
              Both sides give the same label: that label. Otherwise one tie-break call, today's request, decides.
              Translation is local (src/translate.py): no tokens, but its time counts.
- "negation"  Today's request, then Apertus rewrites the claim into its negation (prompt negate-claim) and the
              negation is judged on the same text. The negation's label implies a label for the claim (its
              entailment means the claim is contradicted, and the other way round; neutral stays neutral).
              Rule: if today's answer is neutral and the implied label is not, take the implied label (the
              negation found what the first look missed, the most common task A error); otherwise keep
              today's answer.
- "decompose" Claims of at least DECOMPOSE_MIN_CHARS characters are split by Apertus into at most four
              one-fact claims (prompt decompose-claim), each judged on its own: contradiction if any part is
              contradicted, entailment if every part is entailed, neutral otherwise. Shorter claims, and claims
              that come back as one part, run as today (one call).

Every sub-call's label, cited numbers, tokens and answer go into the record (raw["strategy"] in src/cli.py), so
other combination rules can be computed offline from the saved answers (scripts/strategy_analysis.py) without
new model calls. Tokens of every call are summed into the case's metrics.

If a model call fails, run() raises StrategyFailed with what was spent so far, and the caller answers the case
the normal way. A failed translation or an unreadable rewrite is not a failure: the case then runs as today.
"""

import time
from dataclasses import dataclass, field

from src import llm, nli, translate

STRATEGIES = ("off", "xlang", "negation", "decompose")
DECOMPOSE_MIN_CHARS = 180
REWRITE_MAX_TOKENS = 300
IMPLIED = {0: 2, 1: 1, 2: 0}  # the claim's label implied by its negation's label


@dataclass
class Judgement:
    label: object  # 0, 1, 2 or None (unreadable answer)
    numbers: list
    result: llm.LLMResult


@dataclass
class Outcome:
    label: object
    numbers: list
    input_tokens: int
    output_tokens: int
    record: dict
    last_result: llm.LLMResult


class StrategyFailed(RuntimeError):
    def __init__(self, message, record, input_tokens, output_tokens):
        super().__init__(message)
        self.record, self.input_tokens, self.output_tokens = record, input_tokens, output_tokens


@dataclass
class _Log:
    name: str
    calls: list = field(default_factory=list)
    extra: dict = field(default_factory=dict)
    input_tokens: int = 0
    output_tokens: int = 0
    last: object = None

    def add(self, role, result, label=None, numbers=None):
        self.input_tokens += result.input_tokens
        self.output_tokens += result.output_tokens
        self.last = result
        self.calls.append({"role": role, "label": label, "numbers": numbers, "input_tokens": result.input_tokens,
                           "output_tokens": result.output_tokens, "elapsed_ms": result.elapsed_ms,
                           "answer": result.text})

    def judge(self, judge, role, claim_text, texts):
        j = judge(claim_text, texts)
        self.add(role, j.result, j.label, j.numbers)
        return j

    def record(self, rule):
        return {"name": self.name, "rule": rule, "calls": self.calls, **self.extra}

    def outcome(self, label, numbers, rule):
        return Outcome(label, numbers, self.input_tokens, self.output_tokens, self.record(rule), self.last)


# ---------------------------------------------------------------- combination rules (pure, tested on their own)

def combine_tournament(side_s, side_c):
    """The agreed label, or None when the sides disagree or one is unreadable (then a tie-break decides)."""
    return side_s if side_s is not None and side_s == side_c else None


def combine_negation(original, negated):
    """The final label from the original claim's label and its negation's label (see the module docstring)."""
    if original == 1 and negated is not None and IMPLIED[negated] != 1:
        return IMPLIED[negated]
    return original


def combine_parts(labels):
    """Contradiction if any part is contradicted, entailment if every part is entailed, else neutral.
    An unreadable part counts as neutral."""
    if any(label == 2 for label in labels):
        return 2
    if labels and all(label == 0 for label in labels):
        return 0
    return 1


def _numbers(*judgements, label):
    """Cited numbers of the judgements that gave `label`, in order, without repeats."""
    out = []
    for j in judgements:
        if j is not None and j.label == label:
            out += [n for n in j.numbers if n not in out]
    return out


# ---------------------------------------------------------------- the strategies

def run(name, judge, claim_text, texts, claim_lang, source_lang, min_chars=DECOMPOSE_MIN_CHARS):
    """Answer one case with strategy `name`; see the module docstring. texts: the paragraphs or lines the judge
    shows, in order."""
    log = _Log(name)
    try:
        if name == "xlang":
            return _xlang(log, judge, claim_text, texts, claim_lang, source_lang)
        if name == "negation":
            return _negation(log, judge, claim_text, texts)
        if name == "decompose":
            return _decompose(log, judge, claim_text, texts, min_chars)
        raise ValueError(f"unknown strategy {name!r}")
    except llm.LLMError as e:
        raise StrategyFailed(str(e), log.record("failed"), log.input_tokens, log.output_tokens) from e


def _xlang(log, judge, claim_text, texts, claim_lang, source_lang):
    if not claim_lang or not source_lang or claim_lang == source_lang:
        j = log.judge(judge, "base", claim_text, texts)
        return log.outcome(j.label, j.numbers, "same language: one call")
    start = time.perf_counter()
    try:
        claim_s = translate.translate([claim_text], claim_lang, source_lang)[0]
        texts_c = translate.translate(texts, source_lang, claim_lang)
        log.extra["mt_ms"] = round((time.perf_counter() - start) * 1000)
    except translate.TranslationError as e:
        log.extra["translation_error"] = str(e)
        j = log.judge(judge, "base", claim_text, texts)
        return log.outcome(j.label, j.numbers, "no translation: one call")
    log.extra.update(claim_translated=claim_s, texts_translated=texts_c, direction=f"{claim_lang}->{source_lang}")
    side_s = log.judge(judge, "side_s", claim_s, texts)
    side_c = log.judge(judge, "side_c", claim_text, texts_c)
    agreed = combine_tournament(side_s.label, side_c.label)
    if agreed is not None:
        return log.outcome(agreed, _numbers(side_s, side_c, label=agreed), "both sides agree")
    base = log.judge(judge, "tie_break", claim_text, texts)
    return log.outcome(base.label, base.numbers, "sides disagree: tie-break")


def _rewrite(log, version, claim_text, key):
    result = llm.chat(nli.build_messages_claim(version, claim_text), max_tokens=REWRITE_MAX_TOKENS,
                      json_schema=nli.CLAIM_SCHEMAS[version])
    claims = nli.parse_claims(result.text, key)
    log.add(version, result)
    return claims


def _negation(log, judge, claim_text, texts):
    base = log.judge(judge, "base", claim_text, texts)
    negated = _rewrite(log, "negate-claim", claim_text, "claim")
    if not negated:
        return log.outcome(base.label, base.numbers, "negation unreadable: base")
    log.extra["negated_claim"] = negated[0]
    neg = log.judge(judge, "negated", negated[0], texts)
    label = combine_negation(base.label, neg.label)
    if label == base.label:
        return log.outcome(label, base.numbers, "base kept")
    return log.outcome(label, neg.numbers, "neutral replaced by the negation's implied label")


def _decompose(log, judge, claim_text, texts, min_chars):
    if len(claim_text) < min_chars:
        j = log.judge(judge, "base", claim_text, texts)
        return log.outcome(j.label, j.numbers, "short claim: one call")
    parts = _rewrite(log, "decompose-claim", claim_text, "claims")[:4]
    log.extra["parts"] = parts
    if len(parts) <= 1:
        j = log.judge(judge, "base", claim_text, texts)
        return log.outcome(j.label, j.numbers, "one part: one call")
    judged = [log.judge(judge, f"part_{i}", part, texts) for i, part in enumerate(parts, start=1)]
    label = combine_parts([j.label for j in judged])
    return log.outcome(label, _numbers(*judged, label=label), "parts combined")
