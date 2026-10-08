# Baseline review (beginner task, dev split)

Run `baseline-v0`, prompt `v1-json`. Numbers: `docs/results.md`. Generated parts by `scripts/baseline_review.py`; analysis written by hand.

## 1. Self-checks

| Check | Result | Detail |
|---|---|---|
| unit tests pass (tests/: evaluate and parser) | PASS | 20 tests, 0 failures, 0 errors |
| Macro-F1 equals sklearn f1_score(average='macro') | PASS | 20 random prediction sets on dev (25 % invalid on average); max abs difference 1.11e-16 |
| always-neutral dummy matches the value expected from label counts | PASS | N=300, neutral=99; expected (2*99/(300+99))/3 = 0.1654; actual 0.1654 |
| random-label dummy scores near 0.33 | PASS | seed 42, uniform over 0/1/2: Macro-F1 0.3202 (accepted range 0.27-0.40, about 2 standard errors for N=300) |
| dev gold scored against itself gives 1.0 | PASS | Macro-F1 1.0, accuracy 1.0, all per-class and per-group scores 1.0: True. Evidence: 0 cases with gold evidence (the dataset has none), so evidence scores are n/a |
| test gold scored against itself gives 1.0 | PASS | Macro-F1 1.0, accuracy 1.0, all per-class and per-group scores 1.0: True. Evidence: 0 cases with gold evidence (the dataset has none), so evidence scores are n/a |
| dev inputs contain only id, reference, claim | PASS | key sets found: [('claim', 'id', 'reference')] |
| test inputs contain only id, reference, claim | PASS | key sets found: [('claim', 'id', 'reference')] |
| sample inputs contain only id, reference, claim | PASS | key sets found: [('claim', 'id', 'reference')] |
| no dev gold id in test inputs and no test gold id in dev inputs | PASS | ids are prefixed dev-/test-; each split's ids appear only in its own inputs file |
| inputs and gold files have the same ids, one-to-one | PASS | same order, same ids |
| no dev booklet appears in test | PASS | dev booklets 15, test booklets ['2020-02-09', '2021-03-07', '2022-02-13', '2022-05-15', '2025-09-28'] |
| no (claim, reference) pair shared by dev and test | PASS |  |
| sample cases (make run default) are not test cases | PASS |  |

<!-- ANALYSIS START -->

## 2. Headline

Macro-F1 on dev is **0.202**, below the random-label dummy (0.320) and only
just above "always neutral" (0.165). Accuracy is 0.310. scikit-learn gives the
same Macro-F1. The model answered contradiction 208 times, neutral 75 times
and entailment never; 17 cases have no label (8 parse failures, 9 failed
calls). The result is the same in every language pair (Macro-F1 0.19 to 0.24)
and for same-language (0.198) versus cross-lingual (0.204), so the problem is
the prompt or the model's reading of the labels, not language.

Confusion matrix (rows gold, columns predicted):

| gold \ predicted | entailment | neutral | contradiction | no label |
|---|---|---|---|---|
| entailment (102) | 0 | 73 | 23 | 6 |
| neutral (99) | 0 | 0 | 92 | 7 |
| contradiction (99) | 0 | 2 | 93 | 4 |

## 3. The three most common error patterns

1. **Everything is pushed one step towards "no".** Entailed claims are
   called neutral (73 of 102), and neutral claims are called contradiction
   (92 of 99). This is not a numbering mix-up: in 72 of the 73
   entailment-as-neutral cases the model also left the evidence empty, as the
   prompt asks for neutral, so it means "neutral". The model seems to want the
   reference to repeat the claim almost word for word before it accepts it,
   and it reads "the reference talks about something else" as "the claim is
   false". Examples: dev-0084 (the claim restates the Federal Council's view
   on marriage; the model said neutral) and dev-0174 (a claim about a health
   insurance revision against a reference about the 10-million initiative;
   the model said contradiction because the Federal Council recommends "no"
   there).
2. **Evidence is rewritten instead of copied.** Of the 208 contradiction
   answers, only about a third kept verbatim evidence. The others were
   paraphrased, stitched together from several sentences, translated into
   the claim's language, or simply the claim itself (dev-0224 returns the
   German claim as "evidence" for a French reference). 58 answers gave no
   evidence at all for an entailment or contradiction label.
3. **Long quotes break the JSON.** 5 of the 8 parse failures are answers cut
   off at the 400-token limit in the middle of a long "evidence" quote, so the
   closing brace never arrives. The other 3 are malformed JSON (for example
   `{"label": 2, "evidence": ""]`). Asking for a shorter quote, or for the
   label before a separate short quote, should remove most of these.

## 3b. Surprises in the data and the run

- **Neutral claims are usually about a different vote.** Of the four wrong
  neutral cases in section 5, all four claims concern another ballot than the
  reference (a road, the CO2 law, health insurance, a minimum wage). Measured
  on the 100 same-language dev cases: on average 29 % of a neutral claim's
  words (5+ letters) appear in the reference, against 69 % for entailment and
  65 % for contradiction, and no neutral claim goes above 44 %. Neutral should
  therefore be the *easiest* label, yet the model never got one right. This
  also means the dataset's neutrals test "is this about the same vote?" far
  more than "is this detail covered?". Remember this when reading results.
- **22.5 % of the raw dataset is exact duplicates** (335 of 1,488 rows), and
  the dataset has **no gold evidence** and **no label definitions** (the
  README contains only the licence). Evidence metrics cannot be computed yet.
- **The endpoint is slow and sometimes times out.** 9 of 300 calls ended in
  HTTP 504 from the Public AI gateway after about 61 s; they took 9 of the
  run's 21 minutes. Completed calls averaged 2.4 s. With our no-retry rule
  these cases are lost; a judge-side endpoint may behave differently.
- **Input cost is about 2,000 tokens per case** (1,998 mean over completed
  calls), almost all of it the reference text; the prompt itself is small.
- **The model never outputs label 0**, not even for claims that restate a
  reference sentence. Whether that comes from the label wording, the numeric
  labels or the model is the first thing to test in the next stage (for
  example: label names instead of numbers, or an explicit example per label).

<!-- ANALYSIS END -->

## 4. Twenty random dev rows

Drawn with seed 42. References are cut after 700 characters; the full text is in `data/dev_inputs.jsonl`.

### dev-0013: gold 1 (neutral), claim fr, reference de

**Claim:** Si le vote est approuvé, tous les véhicules pourront circuler gratuitement sur les autoroutes suisses.

**Reference:**

> Volksinitiative «Für ein besseres Leben im Alter (Initiative für eine 13. AHV-Rente)»
>
>
> Ausgangslage: Die Alters- und Hinterlassenenversicherung (AHV) ist das Fundament der schweizerischen Altersvorsorge. Mehr als 2,5 Millionen Pensionierte erhalten gegenwärtig eine AHV-Rente. Die AHV-Rente soll den Existenzbedarf im Alter angemessen decken. Die meisten Pensionierten haben weitere Einkommen, insbesondere eine Pensionskassenrente. Wer seinen Lebensunterhalt damit nicht bestreiten kann, hat Anspruch auf Ergänzungsleistungen (EL).
>
> Die Initiative: Die Initiative will die Altersrenten der AHV um eine Monatsrente erhöhen. Zu den 12 Monatsrenten käme jedes Jahr eine 13. Rente dazu. Die Initiative [...] (13022 characters in total)

### dev-0014: gold 2 (contradiction), claim de, reference it

**Claim:** Wird die Abstimmung angenommen, kann die Mindestbesteuerung frühestens ab 2030 eingeführt werden.

**Reference:**

> Attuazione del progetto dell’OCSE e del G20 sull’imposizione dei grandi gruppi di imprese
>
>
> CONTESTO
> In Svizzera risiedono molti gruppi di imprese attivi a livello internazionale. Essi costituiscono un pilastro importante della nostra economia. Un lavoratore dipendente su quattro è impiegato in uno di questi gruppi di imprese1. Tali gruppi apprezzano le condizioni quadro attrattive del nostro Paese e contribuiscono in modo importante alle entrate fiscali di Confederazione, Cantoni e Comuni.
> IL PROGETTO DELL’OCSE E DEL G20
> L’Organizzazione per la cooperazione e lo sviluppo economico (OCSE) e il Gruppo dei 20 grandi Paesi industrializzati ed emergenti (G20) vogliono adeguare le norme sull’impo [...] (7963 characters in total)

### dev-0016: gold 2 (contradiction), claim fr, reference fr

**Claim:** Le Conseil fédéral estime que l’initiative est indispensable et qu’elle ne mettra en péril ni l’approvisionnement en énergie ni le développement des énergies renouvelables.

**Reference:**

> Initiative populaire « Pour l’avenir de notre nature et de notre paysage (Initiative biodiversité) »
>
>
> NON. Pour le Conseil fédéral et le Parlement, l’initiative va trop loin. Des biotopes, paysages et localités de grande valeur sont déjà protégés et la biodiversité est déjà encouragée. L’acceptation de l’initiative entraverait trop fortement des intérêts importants, en particulier l’approvisionnement en énergie, l’agriculture et le développement de l’habitat.
>
>
>
> La Confédération et les cantons protègent déjà la nature, les paysages et la physionomie des localités. L’initiative traite de sujets importants, mais elle va trop loin en limitant trop fortement la marge de manœuvre de la Confédéra [...] (3686 characters in total)

### dev-0017: gold 1 (neutral), claim it, reference fr

**Claim:** Se il voto verrà approvato, la Svizzera adotterà una nuova legge per proteggere le acque sotterranee.

**Reference:**

> Initiative sur les soins infirmiers
>
>
> Contexte: Élément majeur de la prise en charge médicale, les soins infirmiers sont appelés à faire face au grand défi du vieillissement de la population. Pour préserver la qualité des soins, il faut former davantage de personnel infirmier. Il faut également créer les conditions nécessaires pour que les soignants exercent leur profession plus longtemps.
>
> L’initiative: L’initiative demande que la Confédération et les cantons soutiennent les soins infirmiers et veillent à ce que ceux-ci soient suffisants, accessibles à tous et de qualité. Suffisamment d’infirmiers diplômés devront être formés et les soignants devront effectuer des tâches qui correspondent à [...] (13183 characters in total)

### dev-0045: gold 2 (contradiction), claim de, reference it

**Claim:** Wird die Abstimmung angenommen, muss die Bundesregierung weniger Geld für den Schutz der Biodiversität aufwenden, und Eingriffe in die Natur, Landschaften und charakteristische Orte werden erleichtert.

**Reference:**

> Iniziativa popolare «Per il futuro della nostra natura e del nostro paesaggio (Iniziativa biodiversità)»
>
>
> CONTESTO
> Nuovi insediamenti, impianti energetici, linee ferroviarie, strade oppure attività agricole possono pregiudicare la natura, nonché paesaggi e siti caratteristici. La varietà di animali e piante è pertanto da tempo in diminuzione; anche siti caratteristici e paesaggi pregiati sono sotto pressione. La Confederazione e i Cantoni hanno reagito a questa evoluzione introducendo e attuando varie misure. Ad esempio, nel 2012 la Confederazione ha adottato la «Strategia Biodiversità Svizzera», a cui nel 2017 è seguito un piano d’azione volto alla protezione della biodiversità. Negli ulti [...] (6423 characters in total)

### dev-0048: gold 0 (entailment), claim de, reference it

**Claim:** Laut dem Abstimmungstext empfiehlt die Bundesversammlung Volk und Kantonen, die Initiative abzulehnen.

**Reference:**

> Iniziativa popolare «Per il futuro della nostra natura e del nostro paesaggio (Iniziativa biodiversità)»
>
>
> Il testo in votazione Decreto federale concernente l’iniziativa popolare federale «Per il futuro della nostra natura e del nostro paesaggio (Iniziativa biodiversità)» del 22 dicembre 2023 L’Assemblea federale della Confederazione Svizzera, visto l’articolo 139 capoverso 5 della Costituzione federale1; esaminata l’iniziativa popolare «Per il futuro della nostra natura e del nostro paesaggio (Iniziativa biodiversità)», depositata l’8 settembre 20202; visto il messaggio del Consiglio federale del 4 marzo 20223, decreta: Art. 1 1 L’iniziativa popolare dell’8 settembre 2020 «Per il futuro de [...] (2683 characters in total)

### dev-0053: gold 0 (entailment), claim de, reference it

**Claim:** Das Komitee vertritt die Auffassung, dass eine Kündigung wegen persönlichen Bedarfs schon heute möglich ist und deshalb keine neuen Vorschriften nötig sind.

**Reference:**

> Modifica del Codice delle obbligazioni (Diritto di locazione: disdetta per bisogno personale)
>
>
> NO. Il comitato referendario sottolinea che la disdetta per un bisogno personale è possibile già oggi. A suo giudizio, il reale obiettivo delle nuove norme è agevolare le disdette per poi aumentare ulteriormente le pigioni. Ritiene il progetto parte di un massiccio attacco contro la protezione degli inquilini.
>
>
>
> La disdetta per bisogno personale è usata come pretesto per indebolire la protezione degli inquilini. Insieme alla modifica delle norme sulla sublocazione, il progetto è un massiccio attacco contro i diritti degli inquilini. La potente lobby immobiliare vuole agevolare le disdette per poi [...] (3309 characters in total)

### dev-0058: gold 2 (contradiction), claim fr, reference de

**Claim:** Le Conseil fédéral estime que la nouvelle fiscalité attirerait des personnes fortunées, ce qui accroîtrait les recettes fiscales de la Confédération et des cantons.

**Reference:**

> Volksinitiative «Für eine soziale Klimapolitik – steuerlich gerecht finanziert (Initiative für eine Zukunft)»
>
>
> NEIN. Für Bundesrat und Parlament ist die Initiative der falsche Weg, um die Klimaziele der Schweiz zu erreichen. Zudem könnte die Umsetzung der Initiative vermögende Personen und Unternehmen dazu bewegen, die Schweiz zu verlassen. Dies könnte Arbeitsplätze gefährden und statt zu höheren sogar zu tieferen Steuereinnahmen als heute führen.
>
>
>
> Der Bundesrat und das Parlament teilen das Ziel der Initiative, die Klimaerwärmung zu bekämpfen. Sie erachten jedoch die mit der Initiative vorgeschlagene Finanzierung der Klimapolitik als problematisch und nicht zielführend. Die Initiative kön [...] (3309 characters in total)

### dev-0072: gold 1 (neutral), claim fr, reference it

**Claim:** Le comité estime que la réforme de la formation professionnelle devrait s’accompagner d’un renforcement des compétences des enseignants des écoles professionnelles.

**Reference:**

> Legge federale su un approvvigionamento elettrico sicuro con le energie rinnovabili
>
>
> Contesto: È diventato più difficile assicurare l’approvvigionamento energetico costante della Svizzera su tutto l’arco dell’anno. A causa della trasformazione dei sistemi di approvvigionamento elettrico in Europa e dei conflitti internazionali, nei mesi invernali possono verificarsi situazioni di penuria se non è possibile importare sufficiente elettricità. Inoltre, in Svizzera il fabbisogno di elettricità cresce, ad esempio per soddisfare le esigenze dell’economia, ma anche per le auto elettriche e le pompe di calore. Per garantire la sicurezza dell’approvvigionamento, il Parlamento ha adottato la legge fe [...] (16858 characters in total)

### dev-0102: gold 1 (neutral), claim it, reference it

**Claim:** Il comitato afferma che, per garantire la sicurezza energetica del Paese nel lungo periodo, è necessario costruire nuove centrali idroelettriche.

**Reference:**

> Modifica del Codice delle obbligazioni (Diritto di locazione: disdetta per bisogno personale)
>
>
> Contesto: Il Codice delle obbligazioni prevede che il proprietario possa recuperare rapidamente le abitazioni o i locali commerciali locati per adibirli a uso proprio. Il cosiddetto bisogno personale è rilevante in particolare in tre casi. In primo luogo, la disdetta per bisogno personale può essere data da chi acquista un immobile; il termine di preavviso è di tre mesi per le abitazioni e di sei mesi per i locali commerciali, anche se il contratto prevede un termine più lungo. In secondo luogo, il proprietario può dare la disdetta per un bisogno personale anche durante il periodo di attesa di tre [...] (10997 characters in total)

### dev-0112: gold 1 (neutral), claim it, reference fr

**Claim:** Se la votazione verrà approvata, la Svizzera introdurrà un nuovo sistema di tassazione delle criptovalute a partire dal 2025.

**Reference:**

> Modification du 16 décembre 2022 de la loi COVID-19
>
>
> Contexte: Le coronavirus reste imprévisible. Nul ne sait avec certitude comment il va évoluer et il n’est pas exclu que des variants dangereux émergent à nouveau. C’est pourquoi le Parlement a prolongé jusqu’au 30 juin 2024 la base légale de certaines mesures inscrite dans la loi COVID-19. Les autorités pourront ainsi agir rapidement en cas de nécessité afin de protéger les personnes vulnérables et le système de santé. Cette prolongation a fait l’objet d’une demande de référendum.
>
> Le projet: Les dispositions prolongées permettent de continuer à importer et utiliser des médicaments contre des formes graves de COVID-19, même lorsque leur m [...] (14687 characters in total)

### dev-0115: gold 2 (contradiction), claim it, reference it

**Claim:** Nel riassunto si dice che il controprogetto indiretto entra in vigore se l’iniziativa viene accettata, purché non venga richiesto il referendum.

**Reference:**

> Iniziativa sulle cure infermieristiche
>
>
> Contesto: Pilastro importante dell’assistenza medica, il settore delle cure infermieristiche sta affrontando grandi difficoltà a causa dell’invecchiamento della popolazione. Per poter preservare la qualità delle cure, occorre formare più infermieri. Vanno inoltre create le condizioni che favoriscano una permanenza più lunga nella professione.
>
> L’iniziativa: I promotori dell’iniziativa chiedono che la Confederazione e i Cantoni promuovano le cure infermieristiche e garantiscano che queste siano sufficienti, accessibili a tutti e di qualità. L'iniziativa esige che vi siano abbastanza infermieri diplomati e che gli operatori del settore delle cure inferm [...] (1707 characters in total)

### dev-0120: gold 1 (neutral), claim de, reference fr

**Claim:** Wird die Abstimmung angenommen, werden die Krankenkassenprämien in der Schweiz ab 2025 um 10 Prozent sinken.

**Reference:**

> Arrêté fédéral sur l’étape d’aménagement 2023 des routes nationales
>
>
> Contexte: La population et l’économie ont besoin d’infrastructures de transport modernes et performantes. C’est pourquoi la Confédération ne cesse d’investir dans le réseau routier et ferroviaire. Toutefois, comme le trafic a plus que doublé sur les routes nationales depuis 1990, des embouteillages se forment régulièrement en divers endroits. Les camions et les voitures se rabattent par conséquent sur les routes traversant les villages et les quartiers d’habitation. Ce trafic d’évitement réduit la sécurité et la qualité de vie de la population. La Confédération et les cantons sont chargés de prendre des mesures pour y remé [...] (14714 characters in total)

### dev-0126: gold 2 (contradiction), claim de, reference fr

**Claim:** Der Bundesrat rät der Bevölkerung, den Bundesbeschluss zur Beschaffung neuer Kampfjets abzulehnen, da die derzeitigen Flugzeuge noch einsatzfähig genug seien und nicht ersetzt werden müssten.

**Reference:**

> Arrêté fédéral relatif à l’acquisition de nouveaux avions de combat
>
>
> OUI. Le Conseil fédéral et le Parlement veulent continuer à protéger la population suisse contre les menaces aériennes. Il faut pour cela acheter de nouveaux avions de combat, étant donné que la flotte actuelle devra être retirée du service vers 2030. Les nouveaux avions sont un gage de sécurité à long terme et ils renforceront notre neutralité.
>
>
>
> Les nouveaux avions de combat sont nécessaires pour protéger la population. Leur acquisition est un investissement à long terme pour la sécurité. Financée au moyen du budget ordinaire de l’armée, elle ne sera pas à la charge des autres tâches de la Confédération. Ces avions renf [...] (3608 characters in total)

### dev-0141: gold 0 (entailment), claim fr, reference it

**Claim:** Le Conseil fédéral estime que le contre-projet reprend des formulations juridiques établies, claires et éprouvées en pratique, tandis que l’initiative utilise de nouvelles formulations qui suscitent inutilement des questions d’interprétation.

**Reference:**

> Iniziativa popolare « Sì a una valuta svizzera indipendente e libera con monete o banconote (Il denaro contante è libertà) » e controprogetto diretto (decreto federale concernente l’unità monetaria svizzera e l’approvvigionamento in numerario)
>
>
> SÌ. Anziché come sinora solo nella legge, dovrà essere iscritto anche nella Costituzione che l’approvvigionamento in numerario è garantito e che il franco è l’unità monetaria svizzera. Contrariamente all’iniziativa, il controprogetto riprende formulazioni giuridiche consolidate, univoche e facilmente applicabili nella prassi.
>
>
>
> Sia l’iniziativa popolare sia il controprogetto intendono iscrivere nella Costituzione l’approvvigionamento di denaro conta [...] (3583 characters in total)

### dev-0215: gold 1 (neutral), claim it, reference de

**Claim:** Nel riassunto si sostiene che la riforma delle pensioni AVS 21 è stata approvata con il 62% dei voti.

**Reference:**

> Volksinitiative « Ja zu einer unabhängigen, freien Schweizer Währung mit Münzen oder Banknoten (Bargeld ist Freiheit) » und direkter Gegenentwurf (Bundesbeschluss über die schweizerische Währung und die Bargeldversorgung)
>
>
> Ausgangslage: In der Schweiz bezahlen die Menschen vermehrt bargeldlos, zum Beispiel mit Debit- und Kreditkarten oder Bezahl-Apps. Dennoch möchten die meisten Menschen, dass Bargeld als Zahlungsmittel erhalten bleibt. Heute regelt das Gesetz, dass die Schweizerische Nationalbank die Bargeldversorgung gewährleistet und dass der Franken die schweizerische Währung ist.
>
> Die Initiative: Die Initiative will die Verfügbarkeit des Bargelds und den Franken als schweizerische Währ [...] (11002 characters in total)

### dev-0217: gold 1 (neutral), claim it, reference it

**Claim:** Nel riassunto si sostiene che nel 2024 il popolo svizzero abbia approvato, tramite referendum, la riforma della legge sull’asilo.

**Reference:**

> Decreto federale sulla Fase di potenziamento 2023 delle strade nazionali
>
>
> Contesto: La disponibilità di infrastrutture di trasporto moderne ed efficienti è di vitale importanza per la popolazione e l’economia. La Confederazione investe perciò continuamente nella rete ferroviaria e stradale. Dal 1990 il volume di traffico sulle strade nazionali è più che raddoppiato e provoca regolarmente colonne in diversi tratti della rete. Per evitarle, gli automobilisti e i camionisti ripiegano su percorsi che attraversano villaggi e quartieri residenziali, compromettendo la sicurezza e la qualità di vita degli abitanti. La Confederazione e i Cantoni hanno il compito di porre rimedio a questa situazione; [...] (15332 characters in total)

### dev-0259: gold 1 (neutral), claim de, reference fr

**Claim:** Wird die Abstimmung angenommen, werden die AHV-Renten ab 2035 um 20 Monate vorgezogen.

**Reference:**

> Modification de la loi fédérale sur l’assurance-maladie (financement uniforme des prestations)
>
>
> Contexte: En Suisse, les prestations couvertes par l’assurance obligatoire des soins (AOS) ne sont pas financées de manière uniforme. Pour les traitements ambulatoires (en cabinet médical, chez un thérapeute ou à l’hôpital sans nuitée), c’est la caisse-maladie qui paie. En revanche, pour les traitements hospitaliers (avec nuitée à l’hôpital) et pour les soins dispensés à domicile ou en établissement médico-social (EMS), le canton prend en charge respectivement une part minimale de 55 % et près de 50 % des coûts, le solde étant couvert par la caisse-maladie. Cette situation crée de mauvaises incit [...] (17539 characters in total)

### dev-0280: gold 1 (neutral), claim de, reference fr

**Claim:** Das Komitee argumentiert, die Anhebung der CO₂-Abgabe auf 210 Franken pro Tonne mache die Schweizer Industrie unattraktiv und führe langfristig dazu, dass Arbeitsplätze ins Ausland verlagert werden.

**Reference:**

> Modification du code des obligations (droit du bail : résiliation pour besoin propre)
>
>
> Contexte: Le code des obligations prévoit que les propriétaires de logements ou de locaux commerciaux occupés par des locataires puissent les utiliser eux-mêmes rapidement. Le « besoin propre » du propriétaire joue un rôle notamment dans trois cas. Premièrement, le propriétaire qui vient d’acheter un bien immobilier a le droit de résilier le bail des locataires dans les délais légaux (3 mois pour les logements et 6 mois pour les locaux commerciaux), même si le contrat de bail prévoit un délai plus long. Deuxièmement, le propriétaire peut, en cas de besoin propre, résilier le bail même durant la période de [...] (11106 characters in total)

### dev-0288: gold 2 (contradiction), claim de, reference fr

**Claim:** Laut dem Abstimmungstext kann der Vermieter seine Zustimmung zur Untervermietung verweigern, wenn die geplante Dauer der Untervermietung mehr als fünf Jahre beträgt.

**Reference:**

> Modification du code des obligations (droit du bail : sous-location)
>
>
> Texte soumis au vote Code des obligations (Droit du bail: sous-location) Modification du 29 septembre 2023 L’Assemblée fédérale de la Confédération suisse, vu le rapport de la Commission des affaires juridiques du Conseil national du 18 août 20221, vu l’avis du Conseil fédéral du 19 octobre 20222, arrête: I Le code des obligations3 est modifié comme suit: Art. 262 1 Le locataire peut sous-louer tout ou partie de la chose avec le consentement écrit du bailleur. 2 À moins que les parties en aient convenu autrement par écrit, le locataire soumet au bailleur une demande écrite de sous-location qui contient: a. le nom du sous- [...] (3680 characters in total)

## 5. Ten baseline predictions next to gold

Five drawn from the wrong predictions and five from the right ones (seed 42). The dataset has no gold evidence, so only the model's evidence is shown.

| id | langs | gold | predicted | evidence kept | model's raw answer |
|---|---|---|---|---|---|
| dev-0002 | de->it | 1 neutral | contradiction **wrong** | no (evidence not verbatim) | {"label": 2, "evidence": "Nessun effetto pratico: N\u00e9 l\u2019iniziativa n\u00e9 il controprogetto comporterebbero cambiamenti nella vita quotidiana. Non ne deriverebbero nuovi compiti n\u00e9 costi aggiuntivi. La BNS adempie gi\u00e0 oggi al mandato di garantire l\u2019approvvigionamento in numerario in Svizzera e la legge sancisce gi\u00e0 che il franco \u00e8 l\u2019unita monetaria nazionale |
| dev-0058 | fr->de | 2 contradiction | contradiction | no (evidence not verbatim) | {"label": 2, "evidence": "Die neue Erbschafts- und Schenkungssteuer würde die Attraktivität der Schweiz für vermögende Personen und deren Unternehmen stark vermindern. Ein Grossteil der Personen, die von der Initiative betroffen sind, dürfte aus der Schweiz wegziehen, und Zuzüge von vermögenden Personen würden ausbleiben. Die Initiative gefährdet Arbeitsplätze, weil von der Steuer betroffene Unter |
| dev-0084 | de->de | 0 entailment | neutral **wrong** | no | {"label": 1, "evidence": ""} |
| dev-0106 | it->de | 2 contradiction | contradiction | yes | {"label": 2, "evidence": "Die Mehrheit der Parlamentarierinnen und Parlamentarier ist der Ansicht, dass die Schweiz mit den internationalen Entwicklungen mitziehen muss, auch wenn dadurch die Wettbewerbsfähigkeit eingeschränkt wird. Ohne Umsetzung der Mindestbesteuerung würden die Einnahmen im Ausland anfallen und die Schweiz ginge leer aus. Für die Minderheit ist eine Mindestbesteuerung ein Schri |
| dev-0109 | it->fr | 1 neutral | contradiction **wrong** | no (evidence not verbatim) | {"label": 2, "evidence": "Il progetto: La modifica della legge permetterà anche ai coppie di stesso sesso di concludere un matrimonio civile. Così, questi ultimi saranno posti su un piede di parità con gli altri coppie, sia sul piano istituzionale che sul piano giuridico. L\u0027epouse straniera di una Svizzera o l\u0027epoux straniero di un\u0027 Svizzera potrà, ad esempio, chiedere la naturalizz |
| dev-0129 | fr->it | 2 contradiction | contradiction | yes | {"label": 2, "evidence": "Nell'aprile del 2020 il Consiglio federale ha preannunciato l'intento di convertire in una legge federale urgente le ordinanze adottate grazie al diritto di necessità. Ci si trovava nel pieno del lockdown e si ignorava del tutto quali effetti avrebbe prodotto. Eppure le basi legali necessarie al prolungamento delle disposizioni erano già pronte. Nel messaggio concernente  |
| dev-0162 | fr->fr | 2 contradiction | contradiction | yes | {"label": 2, "evidence": "Le Conseil fédéral et le Parlement rejettent l’initiative, notamment pour les raisons suivantes."} |
| dev-0174 | de->de | 1 neutral | contradiction **wrong** | no (evidence not verbatim) | {"label": 2, "evidence": "Der Bundesrat empfiehlt, die Nachhaltigkeitsinitiative abzulehnen. Nein"} |
| dev-0224 | de->fr | 1 neutral | contradiction **wrong** | no (evidence not verbatim) | {"label": 2, "evidence": "Das Komitee ist der Ansicht, dass ein landesweiter Mindestlohn von 20 Franken pro Stunde die Armut in der Schweiz dauerhaft bek\u00e4mpfen w\u00fcrde."} |
| dev-0290 | de->it | 2 contradiction | contradiction | no (evidence not verbatim) | {"label": 2, "evidence": "La stabilizzazione delle finanze dell\u2019AVS unicamente mediante risparmi significherebbe ridurre in modo massiccio le prestazioni."} |

Claims of these ten cases:

- **dev-0002**: Der Bundesrat spricht sich dafür aus, die Bundesstrasse 7 zwischen Bern und Thun im Rahmen des Ausbauprogramms 2030 auszubauen.
- **dev-0058**: Le Conseil fédéral estime que la nouvelle fiscalité attirerait des personnes fortunées, ce qui accroîtrait les recettes fiscales de la Confédération et des cantons.
- **dev-0084**: Der Bundesrat vertritt die Auffassung, dass die Verfassung die Ehe nicht als Verbindung zwischen einer Frau und einem Mann festlegt und deshalb für die Öffnung der Ehe keine Verfassungsänderung nötig ist.
- **dev-0106**: Il comitato afferma che la Svizzera non deve introdurre la tassazione minima e che le entrate rimarranno nel Paese, dato che la competitività fiscale svizzera è garantita anche senza cambiamenti.
- **dev-0109**: Il riassunto afferma che nel 2021 il popolo svizzero ha approvato il referendum sulla tassa sul CO2.
- **dev-0129**: Le comité affirme que la loi a été conçue à l’issue d’une vaste consultation populaire et que les aides financières accordées aux médias sont directement liées à la pandémie.
- **dev-0162**: Le Conseil fédéral recommande à la population d’accepter l’initiative populaire « Maximum 10 % du revenu pour les primes d’assurance-maladie ».
- **dev-0174**: Der Bundesrat empfiehlt, die Revision des Bundesgesetzes über die Krankenversicherung (KVG) in ihrer aktuellen Form abzulehnen, weil die Kostensteigerungen für die Prämienzahler nicht tragbar seien.
- **dev-0224**: Das Komitee ist der Ansicht, dass ein landesweiter Mindestlohn von 20 Franken pro Stunde die Armut in der Schweiz dauerhaft bekämpfen würde.
- **dev-0290**: Der Bundesrat vertritt die Auffassung, dass sich die Finanzen der AVS nur durch Einsparungen stabilisieren liessen und eine Erhöhung der Mehrwertsteuer dafür nicht nötig sei.
