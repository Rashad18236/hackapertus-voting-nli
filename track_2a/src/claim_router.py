"""Which part of a vote's booklet section a claim is about, from the claim's opening words.

The dataset's claims open with a formula naming their source, in German,
French or Italian (seen on all 300 dev claims, session 6):

  part         German                           French                          Italian
  "summary"    Laut der Zusammenfassung ...     Le résumé précise que ...       Il riassunto afferma che ...
  "council"    Der Bundesrat vertritt ...       Le Conseil fédéral estime ...   Il Consiglio federale ritiene ...
  "committee"  Das Komitee ist der Ansicht ...  Le comité affirme que ...       Il comitato afferma che ...
  "law"        Laut dem Abstimmungstext ...     Selon le texte soumis au vote   Stando al testo di voto ...
  "detail"     Wird die Abstimmung angenommen   Si le vote est accepté ...      Se il voto viene approvato ...

route() returns one of these part names, or None when no pattern matches; it
never guesses. The patterns are checked in a fixed order on the normalised
opening (lower case, NFKC, typographic apostrophes made plain). They do not
depend on the claim's stated language, so a claim whose language field is
wrong is still routed.

No model is involved: the router only chooses what Apertus reads.
"""

import re
import unicodedata

PARTS = ("summary", "council", "committee", "law", "detail")

# (part, pattern on the start of the normalised claim), checked in this order.
_PATTERNS = [
    # summary
    ("summary", r"(laut|gemäss|gemäß) (der )?zusammenfassung\b"),
    ("summary", r"(der zusammenfassung zufolge|die zusammenfassung|in der zusammenfassung)\b"),
    ("summary", r"(le résumé|selon le résumé|d'après le résumé|dans le résumé)\b"),
    ("summary", r"(il riassunto|nel riassunto|secondo il riassunto|stando al riassunto|il riepilogo|nel riepilogo"
                r"|secondo il riepilogo)\b"),
    # the text put to the vote (the legal text)
    ("law", r"(laut|gemäss|gemäß) (dem )?abstimmungstext\b"),
    ("law", r"(dem abstimmungstext zufolge|der abstimmungstext|im abstimmungstext)\b"),
    ("law", r"(selon|d'après) le texte (soumis au vote|soumis à la votation|de (la )?vot(e|ation))\b"),
    ("law", r"le texte (soumis au vote|de (la )?vot(e|ation))\b"),
    ("law", r"(stando al|secondo il|in base al|nel) testo (di voto|sottoposto|della votazione|in votazione)\b"),
    ("law", r"il testo (di voto|sottoposto|della votazione|in votazione)\b"),
    # the Federal Council
    ("council", r"(der bundesrat|laut (dem )?bundesrat|gemäss (dem )?bundesrat|dem bundesrat zufolge)\b"),
    ("council", r"(le conseil fédéral|selon le conseil fédéral|d'après le conseil fédéral)\b"),
    ("council", r"(il consiglio federale|secondo il consiglio federale|per il consiglio federale)\b"),
    # the committee (initiative or referendum committee)
    ("committee", r"(das (initiativ|referendums)?komitee|laut (dem )?(initiativ|referendums)?komitee)\b"),
    ("committee", r"(le comité|selon le comité|d'après le comité)\b"),
    ("committee", r"(il comitato|secondo il comitato|per il comitato)\b"),
    # if the vote is accepted
    ("detail", r"(wird die (abstimmung|vorlage) angenommen|bei annahme der (abstimmung|vorlage)"
               r"|wenn die (abstimmung|vorlage) angenommen)\b"),
    ("detail", r"si (le vote|la votation|l'objet|le projet|cette proposition|la proposition|la motion) (est|sera) "
               r"(accepté|approuvé|adopté)"),
    ("detail", r"l'(adoption|acceptation) (du vote|de la votation|de l'objet|du projet)\b"),
    ("detail", r"se (il voto|la votazione|la proposta|il progetto) (viene|verrà|sarà|riceverà|è)\b"),
]
_COMPILED = [(part, re.compile(pattern)) for part, pattern in _PATTERNS]


def normalise(text):
    text = unicodedata.normalize("NFKC", text).replace("’", "'").replace("`", "'")
    return re.sub(r"\s+", " ", text).strip().lower()


def route(claim_text):
    """The part the claim's opening names (one of PARTS), or None."""
    opening = normalise(claim_text)
    for part, pattern in _COMPILED:
        if pattern.match(opening):
            return part
    return None
