"""Which booklet text task A sends to the model: the registry of context variants.

Each variant is one file in src/contexts/ (file name = variant name with "-"
replaced by "_"):

- "full"            (contexts/full.py):           every page; the full-document baseline.
- "vote-section"    (contexts/vote_section.py):   only the pages about the ballot named in
                                                  `vote`, found from the page headers (no model).
- "embed-e5-small"  (contexts/embed_e5_small.py): only the 8 passages most similar to the
                                                  claim, found with a local embedding model.
- "vote-section-embed-e5-small", "embed-granite-97m-r2", "vote-section-embed-granite-97m-r2"
  (session 4): passages most similar to the claim, from the vote's section or the
  whole booklet, with e5 or Granite; shared code in contexts/retrieval.py.
- "vote-section-embed-e5-small-k12" (session 4): as vote-section-embed-e5-small with the top 12
  chunks, the setting the offline search grid chose.

Every variant runs locally: no Apertus call, no tokens. Apertus alone makes
the entailment decision; a variant only chooses what it reads.

Each variant file defines NAME, PROMPT_VERSION (a key of nli.PROMPTS_A) and
select(pages, vote, claim_text, cross_language=False) -> (prompt_text, shown), where
`cross_language` says whether the claim's language differs from the booklet's and `shown` is
{page: full page text} for every page the prompt text comes from; evidence is
taken only from those pages (src/cli.py).

Adding a variant: a new file in src/contexts/, one entry in VARIANTS below,
and a test. Never change what an existing name does; changed behaviour gets a
new name, so every recorded run names exactly what ran.
"""

from src.contexts import (embed_e5_small, embed_granite_97m_r2, full, vote_section, vote_section_embed_e5_small,
                          vote_section_embed_e5_small_k12, vote_section_embed_granite_97m_r2)

VARIANTS = {v.NAME: v for v in (full, vote_section, embed_e5_small, vote_section_embed_e5_small, embed_granite_97m_r2,
                                vote_section_embed_granite_97m_r2, vote_section_embed_e5_small_k12)}
MODES = tuple(VARIANTS)


def _variant(mode):
    if mode not in VARIANTS:
        raise ValueError(f"unknown context mode {mode!r}; known: {', '.join(MODES)}")
    return VARIANTS[mode]


def select(pages, vote, claim_text, mode, cross_language=False):
    """Return (prompt_text, shown) for the given context mode."""
    return _variant(mode).select(pages, vote, claim_text, cross_language=cross_language)


def prompt_version(mode):
    """The task A prompt version the mode uses."""
    return _variant(mode).PROMPT_VERSION
