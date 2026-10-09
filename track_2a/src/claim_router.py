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
opening (lower case, NFKC, typographic apostrophes made plain, leading quotes,
dashes and spaces removed). They do not depend on the claim's stated language,
so a claim whose language field is wrong is still routed.

Session 8 added the patterns proposed after the router stress test of
2026-10-09 (docs/checks_no_model.md, P10; written for 300 reworded openings,
none from the dataset): more prepositions and verbs, "Bundesrat und Parlament"
without an article, "gemäß" with ß, plural committees, initiants and promotori,
the initiative or the law as the subject of "if accepted", "In Kürze / En bref /
In breve", other names for the text put to the vote, and the stripping of
leading quotes and dashes. A summary named within the first words overrides the
claim's grammatical subject ("Der Bundesrat ist laut Zusammenfassung ...").
They come first; the original patterns follow unchanged.

No model is involved: the router only chooses what Apertus reads.
"""

import re
import unicodedata

PARTS = ("summary", "council", "committee", "law", "detail")

# Leading quotes, dashes and spaces, removed before matching («, „, ", ', –, —, ...).
_LEAD = re.compile(r"^[\s\"'«»„“”‚‘’‹›–—-]+")

# (part, pattern on the start of the normalised claim), checked in this order.
_PATTERNS = [
    # Session 8 (P10). A summary named within the first words overrides the subject.
    ("summary", r"[^,.;:]{0,40}\b(laut|gemäss|gemäß) (der )?zusammenfassung\b"),
    ("summary", r"[^.;:]{0,40}\b(selon|d'après) le résumé\b"),
    ("summary", r"[^.;:]{0,40}\b(secondo il|stando al|nel) (riassunto|riepilogo)\b"),
    ("summary", r"(nach der zusammenfassung|wie die zusammenfassung|laut (der )?kurzfassung|in kürze\b)"),
    ("summary", r"(selon la synthèse|en bref\b|comme l'indique le résumé)"),
    ("summary", r"(in breve\b|in sintesi\b|secondo la sintesi|dal riassunto|come indica il riassunto)"),
    ("council", r"(bundesrat und parlament|nach (ansicht|meinung|auffassung) (des bundesrat(e)?s|von bundesrat)"
                r"|aus sicht des bundesrat(e)?s|für den bundesrat|gemäß (dem )?bundesrat)\b"),
    ("council", r"(conseil fédéral et (le )?parlement|pour le conseil fédéral|de l'avis du conseil fédéral"
                r"|aux yeux du conseil fédéral|selon l'avis du conseil fédéral)\b"),
    ("council", r"(consiglio federale e (il )?parlamento|secondo consiglio federale|a parere del consiglio federale"
                r"|ad avviso del consiglio federale|stando al consiglio federale|secondo il parere del consiglio"
                r" federale)\b"),
    ("committee", r"(die (initiativ|referendums)komitees|das [\w-]+ komitee|das initiativ-komitee|gemäss (dem )?komitee"
                  r"|dem komitee zufolge|nach ansicht des (initiativ|referendums)?komitees"
                  r"|aus sicht des (initiativ|referendums)?komitees|die initiant(inn)?en)\b"),
    ("committee", r"(les comités|pour le comité|de l'avis du comité|les initiants|les auteurs de l'initiative)\b"),
    ("committee", r"(i comitati|stando al comitato|a detta del comitato|a parere del comitato|i promotori"
                  r"|secondo i promotori)\b"),
    ("law", r"(nach dem abstimmungstext|laut (dem )?(initiativtext|gesetzestext|verfassungstext)"
            r"|gemäss (dem )?(initiativtext|gesetzestext|verfassungstext))\b"),
    ("law", r"((selon|d'après) le texte (de l'initiative|de loi|mis aux voix)|aux termes du texte soumis au vote"
            r"|le texte de loi)\b"),
    ("law", r"(secondo il testo (dell'iniziativa|della legge|di legge)|il testo di legge)\b"),
    ("detail", r"(wird die (initiative|gesetzesänderung)|wird das gesetz|wird der bundesbeschluss) angenommen\b"),
    ("detail", r"(bei annahme der initiative|wenn die initiative angenommen|falls die (vorlage|initiative) angenommen"
               r"|sollte die (vorlage|initiative) angenommen|bei einem ja\b|mit der annahme der (vorlage|initiative)"
               r"|nimmt das volk die (vorlage|initiative) an)"),
    ("detail", r"(si (l'initiative|la loi|la modification|la révision|le projet de loi|l'arrêté fédéral) (est|sera) "
               r"(accepté|approuvé|adopté)|en cas d'acceptation\b|en cas de oui\b|si le peuple accepte)"),
    ("detail", r"(se (l'iniziativa|la legge|la modifica|il decreto federale) (viene|verrà|sarà|è) "
               r"(accettat|approvat|accolt)|in caso di (approvazione|accettazione|sì)\b|se il popolo approva"
               r"|qualora il progetto|con l'accettazione)"),
    # The original patterns (session 6).
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
    opening = _LEAD.sub("", normalise(claim_text))
    for part, pattern in _COMPILED:
        if pattern.match(opening):
            return part
    return None
