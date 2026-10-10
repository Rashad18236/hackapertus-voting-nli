<!-- Written by scripts/taskb_analysis.py; the introduction comes from --intro. -->

# Task B errors: v3-topic-first on the 300 dev cases

Run: `docs/runs/2026-10-09_rashad_v3-topic-first_devB300-run1/` (task B
confirmation stage; Macro-F1 0.919, 24 of 300 wrong). The second run on the
same cases gave the same answer text in all 299 cases it answered, so this
list holds for both. The cases below are written by
`scripts/taskb_analysis.py`; the patterns were described by reading every case.

## The patterns in plain words

**1. An unrelated claim called a contradiction (17 of 24).** The dataset
builds its neutral cases by pairing a claim with the passage of another
ballot (in all 99 neutral dev cases the passage belongs to a different vote
than the claim). In these 17 the model said the passage refutes the claim
instead of "does not deal with it". 13 of the 17 claims attribute a statement
to a source ("according to the summary / the text put to the vote / the
committee / the Federal Council, X"), 4 begin "if the vote is accepted, X";
many state specific invented facts (a French law of 2023, a 2-billion
defence budget, joining the EU by 2025). 12 of the 17 are cross-language.
v3's rule says that such a claim is neutral when the text does not deal
with X; in these cases the model does not follow it. All neutral passages
are long (9,746 to 20,284 characters), and the errors are about as frequent
among the shorter ones (10 of 61 under 15,000 characters) as among the
longer (7 of 37).

**2. A refuted claim called neutral (5).** Each time, the refuting statement
is one detail of the passage, and the model did not use it:

- `1016` (French passage, German claim): the passage says the Federal
  Council *will* choose the type and number of aircraft if the people
  accept; the claim says it fixed them before the vote.
- `1138` (German, German): "75 % der Einnahmen sollen an die Kantone, 25 % an
  den Bund gehen"; the claim says half each. The passage is short (1,560
  characters), so length is not the reason here.
- `1167` (German passage, French claim): the committee has withdrawn the
  Glacier initiative on condition, and only after a "no" does it decide
  whether the initiative goes to the vote; the claim says it goes to the vote
  if the law is accepted.
- `1208` (German passage, French claim): the legal text's last article says
  the Federal Assembly recommends *rejecting* the initiative; the claim says
  accepting.
- `1468` (German passage, Italian claim): in a 19,312-character legal text,
  the Confederation pays 70 % (not all) of the cantons' hardship measures for
  firms with a turnover up to 5 million francs.

Four of the five are cross-language; three hinge on a number or a reversed
recommendation stated once.

**3. A supported claim called neutral (1).** `22` (German, German): the
passage says "Die Verfassung definiert die Ehe nicht als Verbindung zwischen
Frau und Mann", which is the claim's point.

**4. A supported claim called a contradiction (1).** `31` (French passage,
German claim): the passage says the initiative demands a ban on importing
food that contains synthetic pesticides or was produced with them, which is
the claim.

No wrong answer came from a failed call: run 1 had none, and its one
unreadable answer (a bare `1`, row 645) got the fallback label neutral, which
is its gold label.

## Every wrong case of `2026-10-09_rashad_v3-topic-first_devB300-run1` (24 of 300)

### Unrelated claim called a contradiction: the passage does not decide the claim, the model said it refutes it. (17)

- **`v1.1-row-500-B`**: passage it, claim de; gold neutral, predicted contradiction
  - Claim: Dem Abstimmungstext zufolge wird behauptet, die Revision des Bundesgesetzes über die direkte Bundessteuer sehe eine Anhebung des kantonalen Steuersatzes auf 120 Prozent vor.
  - Passage (first 300 characters): Finanziamento supplementare dell’AVS mediante l’aumento dell’imposta sul valore aggiunto Contesto: La stabilità finanziaria dell’AVS è in pericolo poiché le generazioni contraddistinte da una forte natalità raggiungono ora l’età di pensionamento. Nel contempo aumenta la speranza di vita media. Tra
- **`v1.1-row-528-B`**: passage it, claim de; gold neutral, predicted contradiction
  - Claim: Das Komitee vertritt die Auffassung, dass die Initiative die CO2-Emissionen in der Schweiz bis 2030 um mindestens 20 Prozent senken würde.
  - Passage (first 300 characters): Iniziativa popolare «Per il divieto di finanziare i produttori di materiale bellico» Contesto: Come la maggior parte dei Paesi, anche la Svizzera partecipa alla fabbricazione di materiale bellico. Da un lato, attraverso aziende svizzere che fabbricano armi o loro componenti, dall’altro, attraverso
- **`v1.1-row-554-B`**: passage fr, claim de; gold neutral, predicted contradiction
  - Claim: Das Komitee ist der Ansicht, dass ein landesweiter Mindestlohn von 20 Franken pro Stunde die Armut in der Schweiz dauerhaft bekämpfen würde.
  - Passage (first 300 characters): Initiative populaire « Non à l’élevage intensif en Suisse (initiative sur l’élevage intensif) » Contexte: La loi suisse sur la protection des animaux est l’une des plus strictes au monde. La dignité et le bien-être des animaux sont protégés, indépendamment du nombre d’animaux détenus au même endro
- **`v1.1-row-608-B`**: passage fr, claim de; gold neutral, predicted contradiction
  - Claim: Laut der Zusammenfassung sieht die Initiative vor, die Mehrwertsteuer auf Lebensmittel um zwei Prozentpunkte anzuheben.
  - Passage (first 300 characters): Initiative populaire « Non à l’élevage intensif en Suisse (initiative sur l’élevage intensif) » Contexte: La loi suisse sur la protection des animaux est l’une des plus strictes au monde. La dignité et le bien-être des animaux sont protégés, indépendamment du nombre d’animaux détenus au même endro
- **`v1.1-row-633-B`**: passage de, claim de; gold neutral, predicted contradiction
  - Claim: Die Zusammenfassung besagt, dass die Vorlage auch das Steuerrecht beeinflusst.
  - Passage (first 300 characters): Änderung des Obligationenrechts (Mietrecht: Untermiete) Ausgangslage: Mieterinnen und Mieter dürfen ihre Wohnung oder einzelne Zimmer vorübergehend untervermieten. Das Gleiche gilt für Geschäftsräume. Manchmal fehlt jedoch die erforderliche Zustimmung der Vermieterin oder des Vermieters oder die W
- **`v1.1-row-666-B`**: passage de, claim fr; gold neutral, predicted contradiction
  - Claim: Si le vote est approuvé, cela veut dire que la Suisse supprimera le service militaire obligatoire.
  - Passage (first 300 characters): Volksinitiative «Für tiefere Prämien – Kostenbremse im Gesundheitswesen (Kostenbremse-Initiative)» Ausgangslage: Alle Menschen in der Schweiz profitieren von einer guten medizinischen Versorgung und erhalten die nötigen Behandlungen. Die Kosten dafür übernimmt die obligatorische Krankenversicherun
- **`v1.1-row-670-B`**: passage fr, claim fr; gold neutral, predicted contradiction
  - Claim: Le texte de vote affirme qu’en 2023, la France a adopté une loi imposant aux entreprises de plus de 50 salariés de négocier un accord sur le télétravail.
  - Passage (first 300 characters): Initiative populaire « Maximum 10 % du revenu pour les primes d’assurance-maladie (initiative d’allègement des primes) » Contexte: En Suisse, chacun reçoit les soins médicaux dont il a besoin, grâce à l’assurance-maladie obligatoire qui prend en charge les coûts. Ces coûts ont beaucoup augmenté ce
- **`v1.1-row-688-B`**: passage fr, claim fr; gold neutral, predicted contradiction
  - Claim: Si le vote est approuvé, les entreprises suisses profiteront d’une baisse de l’impôt sur les bénéfices dès 2025.
  - Passage (first 300 characters): Initiative populaire pour une eau potable propre et une alimentation saine Contexte: Pour recevoir des paiements directs de la Confédération, les agriculteurs doivent respecter une série d’exigences environnementales, appelées prestations écologiques requises, qui concernent notamment la protectio
- **`v1.1-row-767-B`**: passage fr, claim fr; gold neutral, predicted contradiction
  - Claim: Le résumé précise que la réforme de l’imposition des entreprises (RIE III) prévoyait de faire passer le taux fédéral d’imposition des bénéfices des entreprises de 12,5 % à 13,6 %.
  - Passage (first 300 characters): Initiative populaire « Non à l’élevage intensif en Suisse (initiative sur l’élevage intensif) » Contexte: La loi suisse sur la protection des animaux est l’une des plus strictes au monde. La dignité et le bien-être des animaux sont protégés, indépendamment du nombre d’animaux détenus au même endro
- **`v1.1-row-770-B`**: passage fr, claim fr; gold neutral, predicted contradiction
  - Claim: Si le vote est approuvé, les trains de nuit seront supprimés sur l’ensemble du réseau ferroviaire suisse.
  - Passage (first 300 characters): Initiative populaire « Entreprises responsables – pour protéger l’être humain et l’environnement » Contexte: On attend des entreprises suisses qu’elles respectent également à l’étranger les droits de l’homme et les normes environnementales. La Suisse a participé activement à l’élaboration de norme
- **`v1.1-row-797-B`**: passage it, claim fr; gold neutral, predicted contradiction
  - Claim: Si le vote est approuvé, la Suisse augmentera de 2 milliards de francs son budget de défense afin de moderniser son armée.
  - Passage (first 300 characters): Legge sul CO2 Contesto: A causa dei cambiamenti climatici si assiste a un aumento generalizzato delle temperature. Esso è dovuto in primo luogo alle emissioni di gas a effetto sera, e in particolare di diossido di carbonio (CO2), prodotto, ad esempio, dai riscaldamenti a olio e dalla combustione d
- **`v1.1-row-854-B`**: passage de, claim it; gold neutral, predicted contradiction
  - Claim: Il Consiglio federale consiglia di ridurre a 63 anni l’età pensionabile degli uomini.
  - Passage (first 300 characters): Volksinitiative «Für ein besseres Leben im Alter (Initiative für eine 13. AHV-Rente)» Ausgangslage: Die Alters- und Hinterlassenenversicherung (AHV) ist das Fundament der schweizerischen Altersvorsorge. Mehr als 2,5 Millionen Pensionierte erhalten gegenwärtig eine AHV-Rente. Die AHV-Rente soll den
- **`v1.1-row-869-B`**: passage fr, claim it; gold neutral, predicted contradiction
  - Claim: Il riassunto sostiene che la Svizzera ha stabilito di entrare nell’Unione Europea entro il 2025.
  - Passage (first 300 characters): Initiative populaire « Entreprises responsables – pour protéger l’être humain et l’environnement » Contexte: On attend des entreprises suisses qu’elles respectent également à l’étranger les droits de l’homme et les normes environnementales. La Suisse a participé activement à l’élaboration de norme
- **`v1.1-row-904-B`**: passage de, claim it; gold neutral, predicted contradiction
  - Claim: Stando al testo sottoposto a votazione, la legge sul CO₂ stabilisce che entro il 2030 le emissioni di gas serra vengano ridotte del 55%.
  - Passage (first 300 characters): Zusatzfinanzierung der AHV durch eine Erhöhung der Mehrwertsteuer Ausgangslage: Die finanzielle Stabilität der AHV ist in Gefahr, weil geburtenstarke Jahrgänge das Pensionsalter erreichen und die Lebenserwartung steigt. Die Einnahmen der AHV reichen in wenigen Jahren nicht mehr aus, um alle Renten
- **`v1.1-row-946-B`**: passage fr, claim it; gold neutral, predicted contradiction
  - Claim: Il riassunto sostiene che il progetto contempla l’introduzione di una tassa sul carbonio per contenere le emissioni di CO2 entro il 2030.
  - Passage (first 300 characters): Mise en œuvre du projet de l’OCDE et du G20 sur l’imposition des grands groupes d’entreprises Contexte: La Suisse s’est engagée, avec quelque 140 autres États, à ce que les grands groupes d’entreprises actifs à l’échelle internationale soient imposés à un taux d’au moins 15 %. Si un tel groupe est
- **`v1.1-row-948-B`**: passage fr, claim it; gold neutral, predicted contradiction
  - Claim: Secondo il testo della votazione, la Svizzera avrebbe abolito il servizio militare obbligatorio nel 2024.
  - Passage (first 300 characters): Initiative populaire « Pour une prévoyance vieillesse sûre et pérenne (initiative sur les rentes) » Contexte: Le financement des rentes de l’AVS est assuré ces prochaines années. Ces cinq dernières années, deux réformes y ont largement contribué : l’une augmente les cotisations salariales et la TV
- **`v1.1-row-981-B`**: passage de, claim it; gold neutral, predicted contradiction
  - Claim: Stando al testo di voto, dal 2025 la Svizzera ha introdotto una tassa sul carbonio per diminuire le emissioni di CO2 nel settore dei trasporti.
  - Passage (first 300 characters): Änderung des Obligationenrechts (Mietrecht: Untermiete) Ausgangslage: Mieterinnen und Mieter dürfen ihre Wohnung oder einzelne Zimmer vorübergehend untervermieten. Das Gleiche gilt für Geschäftsräume. Manchmal fehlt jedoch die erforderliche Zustimmung der Vermieterin oder des Vermieters oder die W

### Refuted claim called neutral: the passage refutes the claim, the model said it does not decide it. (5)

- **`v1.1-row-1016-B`**: passage fr, claim de; gold contradiction, predicted neutral
  - Claim: Wird die Abstimmung angenommen, heißt das, dass der Bundesrat Typ und Anzahl der anzuschaffenden Flugzeuge bereits vor der Abstimmung festgelegt hat.
  - Passage (first 300 characters): Arrêté fédéral relatif à l’acquisition de nouveaux avions de combat LE MONDE EST DEVENU MOINS SÛR Le monde et donc le contexte dans lequel évolue la Suisse sont devenus moins sûrs au cours des dernières années1. Partout, et notamment aux abords de l’Europe, les tensions internationales se sont acc
- **`v1.1-row-1138-B`**: passage de, claim de; gold contradiction, predicted neutral
  - Claim: Laut der Zusammenfassung werden die Einnahmen aus der Ergänzungssteuer je zur Hälfte zwischen den Kantonen und dem Bund aufgeteilt.
  - Passage (first 300 characters): Umsetzung des OECD/G20- Projekts zur Besteuerung grosser Unternehmensgruppen Ausgangslage: Die Schweiz hat sich mit rund 140 weiteren Staaten dazu bekannt, dass grosse international tätige Unternehmensgruppen mindestens 15 % Steuern bezahlen sollen. Bezahlt eine Unternehmensgruppe in einem Land we
- **`v1.1-row-1167-B`**: passage de, claim fr; gold contradiction, predicted neutral
  - Claim: Si le vote est approuvé, la Gletscher-Initiative sera elle aussi soumise au vote populaire.
  - Passage (first 300 characters): Bundesgesetz über die Ziele im Klimaschutz, die Innovation und die Stärkung der Energiesicherheit (indirekter Gegenvorschlag zur Gletscher-Initiative) AUSGANGSLAGE Die Schweiz als Alpenland ist vom Klimawandel besonders stark betroffen. Massnahmen gegen die Klimaerwärmung sind deshalb von grosser
- **`v1.1-row-1208-B`**: passage de, claim fr; gold contradiction, predicted neutral
  - Claim: D’après le texte soumis au vote, l’Assemblée fédérale recommande au peuple et aux cantons d’accepter l’initiative.
  - Passage (first 300 characters): Volksinitiative «Keine 10-Millionen-Schweiz! (Nachhaltigkeitsinitiative)» Abstimmungstext Bundesbeschluss zur Volksinitiative «Keine 10-Millionen-Schweiz! (Nachhaltigkeitsinitiative)» vom 19. Dezember 2025 2 Sie lautet: Die Bundesversammlung der Schweizerischen Eidgenossenschaft, gestützt auf Arti
- **`v1.1-row-1468-B`**: passage de, claim it; gold contradiction, predicted neutral
  - Claim: Stando al testo di voto, il Consiglio federale copre interamente i costi delle misure cantonali di emergenza destinate alle imprese con un fatturato annuo fino a 5 milioni di franchi.
  - Passage (first 300 characters): Änderung vom 19. März 2021 des Covid-19-Gesetzes Abstimmungstext Bundesgesetz über die gesetzlichen Grundlagen für Verordnungen des Bundesrates zur Bewältigung der Covid-19-Epidemie (Covid-19-Gesetz) (Härtefälle, Arbeitslosenversicherung, familienergänzende Kinderbetreuung, Kulturschaffende, Veran

### Supported claim called neutral: the passage supports the claim, the model said it does not decide it. (1)

- **`v1.1-row-22-B`**: passage de, claim de; gold entailment, predicted neutral
  - Claim: Der Bundesrat vertritt die Auffassung, dass die Verfassung die Ehe nicht als Verbindung zwischen einer Frau und einem Mann festlegt und deshalb für die Öffnung der Ehe keine Verfassungsänderung nötig ist.
  - Passage (first 300 characters): Ehe für alle JA. Bundesrat und Parlament wollen die Ehe für gleichgeschlechtliche Paare öffnen. Damit soll die heutige Ungleichbehandlung beseitigt werden. Alle Paare sollen heiraten können und so die gleichen Rechte und Pflichten haben. Die Vorlage trägt einem Bedürfnis vieler Menschen Rechnung.

### Supported claim called a contradiction: the passage supports the claim, the model said it refutes it. (1)

- **`v1.1-row-31-B`**: passage fr, claim de; gold entailment, predicted contradiction
  - Claim: Wird die Abstimmung angenommen, ist der Import von Lebensmitteln untersagt, die synthetische Pestizide enthalten oder mithilfe solcher Pestizide hergestellt wurden.
  - Passage (first 300 characters): Initiative populaire « Pour une Suisse libre de pesticides de synthèse » CONTEXTE Les pesticides servent à protéger les végétaux, les êtres humains, les animaux, les denrées alimentaires et les matériaux contre les insectes nuisibles, les agents pathogènes et les mauvaises herbes. Afin de garantir
