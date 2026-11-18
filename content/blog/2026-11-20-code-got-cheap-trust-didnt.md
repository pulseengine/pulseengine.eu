+++
title = "Code got cheap. Trust didn't."
description = "When AI makes writing code cheap, the hard part is showing that it is right. Germany once turned a boiler explosion into independent inspection; this post asks what that means for verifying AI-built software in Europe. In English and German."
date = 2026-11-20
draft = true
ready = true
[taxonomies]
tags = ["verification", "europe", "standards", "ai-agents", "process", "deutsch"]
authors = ["Ralf Anton Beier"]
[extra]
bilingual = true
title_de = "Code schreibt sich fast von selbst. Vertrauen nicht."
+++

{% <lang code="en"> %}
<aside class="insight">
<div class="insight__label">Insight</div>
<div class="insight__body">

**When writing code becomes cheap, the scarce thing is evidence that it is
right.** Such evidence counts only if its checks can fail, if someone other than
the author checks it and anyone can re-run it, and if it is tied to an agreed
definition of "right". Our argument, from a small project, is that standards,
independent review and evidence before release are what safety-critical buyers
need from AI-built software, and that the work now is to make them cheap and open.

</div>
</aside>
{% </lang> %}

{% <lang code="de"> %}
<aside class="insight">
<div class="insight__label">Kernaussage</div>
<div class="insight__body">

**Code schreibt sich heute fast von selbst. Der Engpass heißt jetzt
Verifikation.** Ein Nachweis zählt nur unter drei Bedingungen: Ein Test, der nicht
fehlschlagen kann, prüft nichts. Vier-Augen-Prinzip, und für jeden nachvollziehbar.
Und die Abnahmekriterien sind vereinbart. Unsere These: Käufer
sicherheitskritischer Systeme brauchen von KI-gebauter Software Normen,
unabhängige Prüfung und Nachweise vor der Freigabe. Unser Ziel: das alles mit
wenig Aufwand und für jeden einsehbar.

</div>
</aside>
{% </lang> %}

{% <lang code="note"> %}
"cheap" → „schreibt sich fast von selbst“: es geht um Aufwand, nicht um Preis;
„billig“ klänge im Deutschen nach schlechter Ware. "the scarce thing" → „der Engpass“. "agreed definition of right" →
„vereinbarte Abnahmekriterien“. "make them cheap and open" → „wenig Aufwand, für
jeden einsehbar“. Die drei Bedingungen stehen im Deutschen als Regeln, nicht als
Nebensätze.
{% </lang> %}

{% <lang code="en"> %}
## The shift: generation is cheap, checking is not

For most of software's history, writing the code was the expensive part.
Reviews, tests and proofs were overhead you paid on top. Coding agents have
turned that around: writing got cheap, and the question "is it right?" did not.
By "code" we mean everything an agent now writes: requirements, architecture,
code and tests.
{% </lang> %}

{% <lang code="de"> %}
## Was sich geändert hat

Programmieren war teuer. Reviews, Tests und Beweise kamen noch dazu. Mit
Coding-Agenten hat sich das gedreht: Code schreibt sich heute fast von selbst. Die
Frage, ob er stimmt, kostet nicht weniger als früher. Mit „Code“ meinen wir alles,
was ein Agent heute schreibt: Anforderungen, Architektur, Code und Tests.
{% </lang> %}

{% <lang code="note"> %}
„Programmieren war teuer.“ ist der Satz des Autors. Das Deutsche beginnt mit der
Aussage selbst und lässt "for most of software's history" weg; die Überschrift heißt „Was sich
geändert hat“, damit sie nicht die Kernaussage wiederholt.
{% </lang> %}

{% <lang code="en"> %}
Microsoft's CEO said in an episode of The Pragmatic Engineer published on
16 November 2026: "In a world where code generation has become cheap, what has
become hard is verification"
([The Pragmatic Engineer](https://newsletter.pragmaticengineer.com/p/software-engineering-after-code-becomes),
at 11:50). In this post we ask what turns a claim about code into evidence. Our
working answer has three properties, numbered as in the list further down.

<pre class="mermaid">
flowchart LR
    D["3. Agreed definition of right"] --> B
    A["Claim"] --> B["1. Check that can fail"]
    B --> C["2. Checked by someone other than the author, re-runnable by anyone"]
    C --> E["Evidence"]
</pre>
{% </lang> %}

{% <lang code="de"> %}
Microsofts CEO sagt es im Podcast The Pragmatic Engineer vom 16. November 2026
so: "In a world where code generation has become cheap, what has become hard is
verification" – sinngemäß: Wo Code kaum noch etwas kostet, wird die Verifikation
zum schwierigen Teil
([The Pragmatic Engineer](https://newsletter.pragmaticengineer.com/p/software-engineering-after-code-becomes),
bei 11:50). Was macht aus einer Behauptung über Code einen Nachweis? Unsere
vorläufige Antwort: drei Bedingungen. Die Nummerierung gilt auch für die Liste
weiter unten.

<pre class="mermaid">
flowchart LR
    D["3. Vereinbarte Abnahmekriterien"] --> B
    A["Behauptung"] --> B["1. Test, der fehlschlagen kann"]
    B --> C["2. Vier-Augen-Prinzip, für jeden nachvollziehbar"]
    C --> E["Nachweis"]
</pre>
{% </lang> %}

{% <lang code="note"> %}
Zitate bleiben im englischen Original, mit einer sinngemäßen Übersetzung. Aus
"properties" werden „Bedingungen“: Eigenschaften hat ein Nachweis, Bedingungen
muss er erfüllen.
{% </lang> %}

{% <lang code="en"> %}
## A boiler explodes in Mannheim, and the three properties

In January 1865 a steam boiler exploded at a brewery in Mannheim, and on
6 January 1866 a group of boiler owners founded an inspection association
([Deutschlandmuseum](https://www.deutschlandmuseum.de/en/geschichte/kalender/1866-01-06-origin-of-the-tuev)).
Its aim was regular inspection of the members' boilers, its first full-time
expert started in 1868, and it became the starting point for technical
inspection in Germany
([TÜV SÜD history](https://www.tuvsud.com/en-gb/about-us/history/our-foundation-years-1866-1900)).
{% </lang> %}

{% <lang code="de"> %}
## Wie aus einer Kesselexplosion der TÜV wurde

Januar 1865: In einer Mannheimer Brauerei explodiert ein Dampfkessel. Am
6. Januar 1866 gründen Kesselbesitzer einen Überwachungsverein
([Deutschlandmuseum](https://www.deutschlandmuseum.de/en/geschichte/kalender/1866-01-06-origin-of-the-tuev)).
Er soll die Kessel seiner Mitglieder regelmäßig prüfen. 1868 kommt der erste
hauptamtliche Sachverständige. Daraus wird der Ausgangspunkt der technischen
Überwachung in Deutschland
([TÜV SÜD, Geschichte](https://www.tuvsud.com/en-gb/about-us/history/our-foundation-years-1866-1900)).
{% </lang> %}

{% <lang code="note"> %}
Die deutsche Überschrift erzählt die Geschichte, die drei Bedingungen folgen
im Text. Das Deutsche erzählt die Szene im Präsens, das Englische in der
Vergangenheit.
"technical inspection" → „technische Überwachung“, der eingeführte Begriff für
das, was der TÜV tut.
{% </lang> %}

{% <lang code="en"> %}
Our working definition is that evidence is worth something only if it has three
properties:

1. **It can fail.** A check that cannot go red on bad input proves nothing. You
   find out by feeding it something it must reject. Nadella describes the same
   habit in the agent teams he watches: "how do you take every failure and then
   build back the test case and make sure you truly verify the test" (12:19).
2. **It is checked by someone other than the author, and re-runnable by
   anyone.** These are two separate demands. Independence means the author does
   not mark their own work; re-checkability means a result does not have to be
   taken on anyone's word. A signature shows which key signed the bundle and that
   it has not changed since; it says nothing about whether the bundle is right.
   For agents, independence includes the model: "How do you have the critique?
   There's so much to be said about having a separate model family" (17:05).
3. **It is tied to an agreed definition of right.** "Correct" needs a
   requirement or a standard that says what correct means, written without
   ambiguity.
{% </lang> %}

{% <lang code="de"> %}
Unsere Arbeitsdefinition: Ein Nachweis zählt nur, wenn drei Bedingungen erfüllt
sind:

1. **Ein Test, der nicht fehlschlagen kann, prüft nichts.** Ob er fehlschlagen kann,
   sieht man erst, wenn man ihm etwas vorlegt, das er ablehnen muss. Nadella
   beschreibt dieselbe Gewohnheit in den Agenten-Teams, die er beobachtet: "how
   do you take every failure and then build back the test case and make sure you
   truly verify the test" – sinngemäß: aus jedem Fehler einen Testfall machen und
   den Test selbst wirklich überprüfen (12:19).
2. **Vier-Augen-Prinzip, und für jeden nachvollziehbar.** Das sind zwei
   Forderungen. Vier Augen heißt: Niemand prüft seine eigene Arbeit.
   Nachvollziehbar heißt: Niemand muss das Ergebnis glauben, jeder kann es selbst
   wiederholen. Eine Signatur zeigt nur, welcher Schlüssel ein Paket signiert hat
   und dass es seitdem unverändert ist. Ob der Inhalt stimmt, zeigt sie nicht.
   Bei Agenten gehört zur Unabhängigkeit auch das Modell: "How do you have the critique? There's so
   much to be said about having a separate model family" – sinngemäß: Wie kommt
   man zur Kritik? Zu einer anderen Modellfamilie gibt es viel zu sagen (17:05).
3. **Die Abnahmekriterien sind vereinbart.** Eine Anforderung oder Norm legt
   eindeutig fest, was als korrekt gilt.
{% </lang> %}

{% <lang code="note"> %}
"It can fail" → „Ein Test, der nicht fehlschlagen kann, prüft nichts.“ (Satz des
Autors): das Deutsche formuliert die Regel von der Gegenseite. "someone other
than the author" → „Vier-Augen-Prinzip“. "re-runnable" → „nachvollziehbar“.
"tied to an agreed definition" → „Abnahmekriterien sind vereinbart“.
{% </lang> %}

{% <lang code="en"> %}
In our reading, the boiler story has all three. An inspection that can find a
fault is a check that can fail. An expert of the association, not the operator,
is a checker other than the author, and a boiler inspected regularly is checked
again and again. An association that examines many boilers gives its examiners
a shared idea of what a sound boiler is, which ties the check to a definition.
{% </lang> %}

{% <lang code="de"> %}
Wir meinen: In Mannheim war schon alles da, was es braucht. Eine
Kesselprüfung, die einen Mangel finden kann, kann auch fehlschlagen. Es prüft
der Sachverständige des Vereins, nicht der Betreiber. Und weil der Kessel
regelmäßig geprüft wird, wird immer wieder nachgeprüft. Der Verein prüft viele
Kessel; so entsteht bei seinen Prüfern ein gemeinsames Bild davon, was ein
sicherer Kessel ist. Das bindet die Prüfung an eine Definition.
{% </lang> %}

{% <lang code="note"> %}
"In our reading" → „Nach unserer Einschätzung“, die übliche Abschwächung in
deutschen Fachtexten.
{% </lang> %}

{% <lang code="en"> %}
Independence can also be lost along the way. The final report on the Boeing
737 MAX prepared by the majority staff of the US House transportation committee
states, as one of several findings: "Excessive FAA delegation of certification
functions to Boeing on the 737 MAX eroded FAA's oversight effectiveness and the
safety of the public"
([House Transportation Committee report](https://democrats-transportation.house.gov/imo/media/doc/final_boeing_737_max_report.pdf)).
We read this as the same lesson as in Mannheim: the check has to be independent.

Our reading is also that standards work as a collective memory. They record
lessons in a rule, so that the next team does not have to learn them again, and
they supply the agreed definition that the third property asks for.
{% </lang> %}

{% <lang code="de"> %}
Unabhängigkeit kann verloren gehen. Den Abschlussbericht zur Boeing 737 MAX haben
Mitarbeiter der Mehrheit im Verkehrsausschuss des
US-Repräsentantenhauses geschrieben. Einer von mehreren Befunden: "Excessive FAA
delegation of certification functions to Boeing on the 737 MAX eroded FAA's
oversight effectiveness and the safety of the public" – sinngemäß: Die FAA hat bei der
737 MAX zu viel Zertifizierung an Boeing abgegeben. Das hat die Wirksamkeit ihrer Aufsicht
und die öffentliche Sicherheit geschwächt
([Bericht des Verkehrsausschusses](https://democrats-transportation.house.gov/imo/media/doc/final_boeing_737_max_report.pdf)).
Für uns ist das dieselbe Lehre wie in Mannheim: Wer prüft, muss unabhängig sein.

Normen wirken nach unserer Einschätzung außerdem wie ein kollektives Gedächtnis. Sie
machen aus Lehren Regeln, damit das nächste Team sie nicht noch einmal lernen
muss. Und sie liefern die Abnahmekriterien, die Bedingung 3 verlangt.
{% </lang> %}

{% <lang code="note"> %}
"the check has to be independent" → „Wer prüft, muss unabhängig sein.“ Das
Deutsche macht aus der Sache eine Person.
{% </lang> %}

{% <lang code="en"> %}
## When a constraint becomes the product

**It worked for certification.** Independent testing is a cost for every
manufacturer, and it became a paid business for the testers. TÜV SÜD reported
€3.4 billion of 2024 revenue
([press release](https://www.tuvsud.com/en-gb/press-and-media/2025/may/tuev-sued-achieves-significant-revenue-growth-in-2024))
and TÜV Rheinland €2.71 billion
([press release](https://www.tuv.com/press/en/press-releases/tuev-rheinland-results-2024.html)),
across all their services. In our reading, much of that demand exists because
inspection is required by law, so this trust business rests on a mandate, and
its weak spot is that certifiers are paid by the firms they certify.
{% </lang> %}

{% <lang code="de"> %}
## Aus der Auflage wird das Produkt

**Bei Prüfung und Zertifizierung hat das geklappt.** Für Hersteller kostet
unabhängige Prüfung Geld. Für die Prüfer wurde sie ein Geschäft. TÜV SÜD meldete
für 2024 einen Umsatz von 3,4 Milliarden Euro
([Pressemitteilung](https://www.tuvsud.com/en-gb/press-and-media/2025/may/tuev-sued-achieves-significant-revenue-growth-in-2024)),
TÜV Rheinland 2,71 Milliarden Euro
([Pressemitteilung](https://www.tuv.com/press/en/press-releases/tuev-rheinland-results-2024.html)),
jeweils über alle Geschäftsfelder. Nach unserer Einschätzung kommt viel davon aus
Prüfungen, die das Gesetz vorschreibt. Das Geschäft mit dem Vertrauen hängt also
an einer Pflicht, und seine Schwachstelle ist nach unserer Einschätzung, dass die
Prüfer von denen bezahlt werden, die sie prüfen.
{% </lang> %}

{% <lang code="note"> %}
"constraint" → „Auflage“, "mandate" → „Pflicht“: zwei Begriffe, die im Deutschen
getrennt bleiben müssen. Die Überschrift wird zur Aussage statt "When …".
{% </lang> %}

{% <lang code="en"> %}
**It failed for solar.** After feed-in tariffs drove a boom, Germany was once
the world's largest solar market. In May 2017 SolarWorld, the last major German
cell maker, filed for insolvency amid Chinese competition
([Clean Energy Wire](https://www.cleanenergywire.org/news/last-major-german-solar-cell-maker-surrenders-chinese-competition)).
The feed-in tariffs were a subsidy that created demand, not a constraint on
producers, and the demand was for a commodity that others could make more
cheaply.

The pattern, as we read the cases: **a constraint becomes a strength when it
produces a trust good that is hard to copy and that buyers must pay for. It stays
a cost when it only creates demand that anyone can serve more cheaply.** That is
our synthesis from a handful of cases, not a tested law.
{% </lang> %}

{% <lang code="de"> %}
**Bei der Solarindustrie ist es gescheitert.** Die Einspeisevergütung löste einen
Boom aus. Deutschland war eine Zeit lang der größte Solarmarkt der Welt. Im Mai
2017 meldete SolarWorld Insolvenz an, der letzte große deutsche Zellhersteller,
angesichts chinesischer Konkurrenz
([Clean Energy Wire](https://www.cleanenergywire.org/news/last-major-german-solar-cell-maker-surrenders-chinese-competition)).
Die Einspeisevergütung war eine Subvention. Sie schuf Nachfrage, sie war keine
Auflage für die Hersteller. Und gefragt war Massenware, die andere zu niedrigeren
Kosten herstellen konnten.

So schätzen wir die Fälle ein: **Eine Auflage wird zum Vorteil, wenn daraus ein
Vertrauensgut entsteht, das schwer zu kopieren ist und für das Käufer zahlen
müssen. Sie bleibt ein Kostenfaktor, wenn sie nur Nachfrage schafft, die jeder zu
niedrigeren Kosten bedienen kann.** Das ist kein belegtes Gesetz, sondern eine
Arbeitshypothese aus einer Handvoll Fälle.
{% </lang> %}

{% <lang code="note"> %}
"commodity" → „Massenware“. "not a tested law" → „kein belegtes Gesetz, sondern
eine Arbeitshypothese“. "more cheaply" → „zu niedrigeren Kosten“, wieder ohne
„billig“.
{% </lang> %}

{% <lang code="en"> %}
This seems to clash with our call for open evidence: if anyone can copy it, how
can it be hard to copy? Our answer is that open evidence stays hard to fake
because its checks can fail and anyone can re-run them. What gets cheap is
producing and publishing evidence, not trusting it. Verification evidence for
safety-critical software falls on the certification side of our line, as long
as it keeps those properties.
{% </lang> %}

{% <lang code="de"> %}
Das scheint unserer Forderung nach offenen Nachweisen zu widersprechen: Was jeder
kopieren kann, ist nicht schwer zu kopieren. Unsere Antwort: Offene Nachweise
lassen sich trotzdem schwer fälschen. Ihre Tests können fehlschlagen, und jeder
kann sie nachvollziehen. Der Aufwand sinkt beim Erstellen und Veröffentlichen von
Nachweisen, nicht beim Vertrauen in sie. Verifikationsnachweise für
sicherheitskritische Software gehören auf unserer Linie auf die Seite der
Zertifizierung, solange sie die drei Bedingungen erfüllen.
{% </lang> %}

{% <lang code="note"> %}
"What gets cheap" → „Der Aufwand sinkt“. Das Deutsche spricht über Aufwand, nicht
über Preis.
{% </lang> %}

{% <lang code="en"> %}
## Rulebooks and tooling are late

A March 2026 NBER working paper by Bick, Blandin, Deming, Fuchs-Schündeln and
Jessen reports that output per hour increased by 85% in the US between 1995 and
2025 against 29% in Europe, a gap that opened long before AI, and that about 43%
of US workers use AI at work against about 32% in its survey of European
workers. Industries that adopted AI more saw faster productivity growth, with no
clear employment changes. The authors report a correlation and do not claim it is
causal ([NBER working paper 34995](https://www.nber.org/papers/w34995)).
{% </lang> %}

{% <lang code="de"> %}
## Regelwerke und Werkzeuge hinken hinterher

Ein NBER-Arbeitspapier von Bick, Blandin, Deming, Fuchs-Schündeln und Jessen vom
März 2026 berichtet: Die Arbeitsproduktivität (Leistung je Arbeitsstunde) stieg
von 1995 bis 2025 in den USA um 85 %, in Europa um 29 %. Die Lücke entstand lange
vor der KI. Etwa 43 % der US-Beschäftigten nutzen KI bei der Arbeit, in ihrer
Befragung europäischer Beschäftigter etwa 32 %. Branchen mit stärkerer
KI-Nutzung wurden schneller produktiver, ohne dass sich die Beschäftigung
erkennbar veränderte. Die Autoren berichten eine Korrelation und behaupten keinen
ursächlichen Zusammenhang ([NBER-Arbeitspapier 34995](https://www.nber.org/papers/w34995)).
{% </lang> %}

{% <lang code="note"> %}
"Rulebooks" → „Regelwerke“ (ein „Regelbuch“ gibt es im Deutschen so nicht). "output
per hour" → „Arbeitsproduktivität“.
{% </lang> %}

{% <lang code="en"> %}
The rulebooks for AI-built and connected products are arriving late. The Council
gave final approval on 29 June 2026 to move the AI Act's high-risk deadlines to
2 December 2027 for stand-alone systems and 2 August 2028 for systems embedded in
regulated products
([Council via EEAS](https://www.eeas.europa.eu/delegations/chile/artificial-intelligence-council-gives-final-green-light-simplify-and-streamline-rules_en)).
The Cyber Resilience Act is a cybersecurity law for products with digital
elements, not a functional-safety law. Its reporting obligations have applied
since 11 September 2026, and its main obligations apply from 11 December 2027
([European Commission](https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act)).
{% </lang> %}

{% <lang code="de"> %}
Die Regelwerke für KI-gebaute und vernetzte Produkte kommen spät. Am 29. Juni
2026 hat der Rat der EU endgültig beschlossen, die Fristen der KI-Verordnung für
Hochrisiko-KI-Systeme zu verschieben: auf den 2. Dezember 2027 für eigenständige
Systeme, auf den 2. August 2028 für Systeme in regulierten Produkten
([Rat der EU über EEAS](https://www.eeas.europa.eu/delegations/chile/artificial-intelligence-council-gives-final-green-light-simplify-and-streamline-rules_en)).
Der Cyber Resilience Act (Cyberresilienz-Verordnung) regelt Cybersicherheit für
Produkte mit digitalen Elementen, nicht funktionale Sicherheit. Die
Meldepflichten gelten seit dem 11. September 2026, die wesentlichen Pflichten ab
dem 11. Dezember 2027
([Europäische Kommission](https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act)).
{% </lang> %}

{% <lang code="note"> %}
"AI Act" → „KI-Verordnung“, "high-risk systems" → „Hochrisiko-KI-Systeme“, "the
Council" → „der Rat der EU“: die üblichen deutschen Begriffe.
{% </lang> %}

{% <lang code="en"> %}
On the tooling side, rust-lang/rust#144999, merged on 8 August 2025, removed the
unstable MC/DC instrumentation
([rust-lang/rust#144999](https://github.com/rust-lang/rust/pull/144999)). The
2026 project goal aims at unstable support, and the goal page names DO-178C
level A among the standards that require MC/DC
([goal page](https://goals.rust-lang.org/2026/mcdc-coverage-support.html)).
Qualified Rust tooling does exist: Ferrous Systems announced in November 2023
that TÜV SÜD had qualified the Ferrocene 23.06.0 toolchain, which is open
source, as a tool for ISO 26262 (ASIL D) and IEC 61508 (SIL 4)
([Ferrous Systems](https://ferrous-systems.com/blog/officially-qualified-ferrocene/)).
That qualifies the compiler, not the software built with it. In the same
episode the host, Gergely Orosz, expects "blueprints and certifications in, I
don't know, five to 10 years" for agent-built systems (52:09). We read late
rulebooks and MC/DC support that is still only a goal as room for open
verification evidence in the meantime.
{% </lang> %}

{% <lang code="de"> %}
Zu den Werkzeugen: rust-lang/rust#144999 hat am 8. August 2025 die instabile
MC/DC-Instrumentierung entfernt
([rust-lang/rust#144999](https://github.com/rust-lang/rust/pull/144999)). Das
Rust-Projektziel für 2026 zielt auf instabile Unterstützung. Die Zielseite nennt
DO-178C Level A unter den Normen, die MC/DC verlangen
([Zielseite](https://goals.rust-lang.org/2026/mcdc-coverage-support.html)).
Qualifizierte Rust-Werkzeuge gibt es: Ferrous Systems gab im November 2023
bekannt, dass TÜV SÜD die quelloffene Werkzeugkette Ferrocene 23.06.0 als
Werkzeug für ISO 26262 (ASIL D) und IEC 61508 (SIL 4) qualifiziert hat
([Ferrous Systems](https://ferrous-systems.com/blog/officially-qualified-ferrocene/)).
Qualifiziert ist damit der Compiler, nicht die Software, die man damit baut. In
derselben Folge rechnet der Moderator Gergely Orosz für von Agenten gebaute
Systeme mit "blueprints and certifications in, I don't know, five to 10 years" –
sinngemäß: mit Bauplänen und Zertifizierungen in vielleicht fünf bis zehn Jahren
(52:09). Späte Regelwerke und eine MC/DC-Unterstützung, die noch ein bloßes Ziel
ist: Darin sehen wir Raum für offene Verifikationsnachweise bis dahin.
{% </lang> %}

{% <lang code="note"> %}
"toolchain" → „Werkzeugkette“, "open source" → „quelloffen“. "We read … as room"
→ „Darin sehen wir Raum“.
{% </lang> %}

{% <lang code="en"> %}
## What we are doing about it

PulseEngine is a work-in-progress WebAssembly Component Model engine aimed at
safety-critical targets, built largely by AI agents. Its job, as we see it, is to
make the "slow" parts fast and open. Our recent work maps onto the three
properties as follows.

- **Property 1, checks that can fail.** Our [previous post](/blog/green-by-default/)
  described planting bad inputs to see whether a check turns red. That is now a
  tool, [plant](https://github.com/pulseengine/plant).
- **Properties 2 and 3, review against a definition.** Two reviewers, AI agents
  started without the author's context, read the 29 requirements of our wohl
  project for ambiguity ([wohl#97](https://github.com/pulseengine/wohl/issues/97));
  the mechanical fixes are in [wohl#98](https://github.com/pulseengine/wohl/pull/98).
  Reading the code turned one finding, a safety check that never triggered in
  the scenario its own requirement describes, into a safety finding, which is
  still waiting for a design decision. Both reviewers came from the same project
  and the same model family as the author, so they were independent of the
  author's context, not of the organisation or the model, and every lead was
  checked against the code before anything changed.
- **Properties 1 and 2, evidence anyone can re-run.** wohl's
  [v0.7.0 release](https://github.com/pulseengine/wohl/releases/tag/v0.7.0)
  ships a signed evidence bundle with one verify command. A monthly workflow now
  runs it, with two planted failures that must go red
  ([pulseengine.eu#377](https://github.com/pulseengine/pulseengine.eu/pull/377)).
  That shows the bundle is intact and its checks can still fail, not that the
  software is correct.
{% </lang> %}

{% <lang code="de"> %}
## Was wir tun

PulseEngine ist eine Engine für das WebAssembly Component Model, noch in Arbeit,
gedacht für sicherheitskritische Einsätze und zum großen Teil von KI-Agenten
gebaut. Ihre Aufgabe sehen wir darin, die „langsamen“ Teile schnell und für jeden
einsehbar zu machen. Was wir zuletzt getan haben, nach den drei Bedingungen:

- **Bedingung 1, Tests, die fehlschlagen können.** Im
  [vorigen Beitrag](/blog/green-by-default/) haben wir Prüfungen gezielt falsche
  Eingaben vorgelegt und geprüft, ob sie fehlschlagen. Daraus ist ein Werkzeug
  geworden: [plant](https://github.com/pulseengine/plant).
- **Bedingungen 2 und 3, Prüfung gegen vereinbarte Kriterien.** Zwei Prüfer,
  KI-Agenten ohne den Kontext des Autors, haben die 29 Anforderungen unseres
  Projekts `wohl` auf Mehrdeutigkeiten hin durchgesehen
  ([wohl#97](https://github.com/pulseengine/wohl/issues/97)). Die mechanischen
  Korrekturen stehen in [wohl#98](https://github.com/pulseengine/wohl/pull/98).
  Im Code wurde aus einem Befund ein Sicherheitsbefund: Eine Sicherheitsprüfung
  löste im Szenario ihrer eigenen Anforderung nie aus. Die Designentscheidung dazu
  steht noch aus. Beide Prüfer kamen aus demselben Projekt und derselben
  Modellfamilie wie der Autor. Unabhängig waren sie also vom Kontext des Autors,
  nicht von der Organisation oder vom Modell. Jeder Hinweis wurde am Code
  überprüft, bevor wir etwas geändert haben.
- **Bedingungen 1 und 2, Nachweise, die jeder nachvollziehen kann.** Das
  `wohl`-Release
  [v0.7.0](https://github.com/pulseengine/wohl/releases/tag/v0.7.0) enthält ein
  signiertes Nachweispaket, prüfbar mit einem einzigen Befehl. Ein monatlicher Lauf
  prüft es jetzt, mit zwei absichtlich eingebauten Fehlern, bei denen der Test
  fehlschlagen muss
  ([pulseengine.eu#377](https://github.com/pulseengine/pulseengine.eu/pull/377)).
  Das zeigt: Das Paket ist unversehrt, und seine Tests können noch fehlschlagen.
  Dass die Software korrekt ist, zeigt es nicht.
{% </lang> %}

{% <lang code="note"> %}
"work-in-progress" → „noch in Arbeit“. "planting bad inputs" → „gezielt falsche
Eingaben vorgelegt“ („unterschieben“ klänge nach Betrug).
{% </lang> %}

{% <lang code="en"> %}
Next we concentrate on verifiers designed so that their qualification evidence
can be produced and published openly; on signed, machine-readable evidence
bundles that can be mapped onto the Cyber Resilience Act's standards if and when
they are published; on traceability from each proof or test to the clause it
covers, including changes written by AI agents; and on MC/DC coverage for Rust
and WebAssembly.
{% </lang> %}

{% <lang code="de"> %}
Als Nächstes: Prüfwerkzeuge, die wir so bauen, dass sich ihre
Qualifizierungsnachweise offen erzeugen und veröffentlichen lassen. Signierte,
maschinenlesbare Nachweispakete, die sich auf die Normen zum
Cyber Resilience Act abbilden lassen, falls und sobald sie veröffentlicht sind.
Rückverfolgbarkeit von jedem Beweis und Test zu der Klausel, die er abdeckt, auch
bei Änderungen durch KI-Agenten. Und MC/DC-Abdeckung für Rust und WebAssembly.
{% </lang> %}

{% <lang code="en"> %}
## Limits

This is an argument from a small project, not a market study. We found no
reliable figure for the size of the market for safety-critical verification
tools, and no buyer has paid us anything. The rule about when a constraint
becomes a strength is our reading of a few cases. Most evidence we found about
the quality of AI-written code still comes from vendors.

What would change our mind: a published evidence format for the Cyber Resilience
Act that makes our bundles irrelevant, a pilot in which nobody cares about open
qualification evidence, or an independent study showing that AI-written
safety-critical code needs less checking, not more.
{% </lang> %}

{% <lang code="de"> %}
## Grenzen

Das ist ein Argument aus einem kleinen Projekt, keine Marktstudie. Eine
verlässliche Zahl zur Größe des Marktes für Verifikationswerkzeuge in der
sicherheitskritischen Entwicklung haben wir nicht gefunden. Bezahlt hat uns
bisher kein Käufer. Wann eine Auflage zum Vorteil wird, ist unsere Einschätzung
aus wenigen Fällen. Die meisten Belege zur Qualität von KI-geschriebenem Code, die
wir gefunden haben, stammen noch von Anbietern.

Was uns umstimmen würde: ein veröffentlichtes Nachweisformat für den
Cyber Resilience Act, das unsere Pakete überflüssig macht. Ein Pilotprojekt, in
dem sich niemand für offene Qualifizierungsnachweise interessiert. Oder eine
unabhängige Studie, die zeigt, dass KI-geschriebener sicherheitskritischer Code
weniger Prüfung braucht, nicht mehr.
{% </lang> %}

{% <lang code="en"> %}
## Bloopers

Writing this post in two languages was its own test. Our first German drafts
were correct and stiff: "Früher war das Programmieren der teure Teil" became, in
the author's hand, "Programmieren war teuer." The word "cheap" had to go
altogether: in German, "billig" sounds like poor goods, so the German version
speaks of effort, not price. The checks caught the other kind of slip. One draft
added "genau" (exactly) and made a claim stronger than the English; another
turned "agreed" into "fixed beforehand"; a third made the Cyber Resilience Act's
"main obligations" into "all the remaining ones". Each was a check that could
fail, and did.
{% </lang> %}

{% <lang code="de"> %}
## Pannen

Diesen Beitrag zweisprachig zu schreiben, war ein eigener Test. Unsere ersten
deutschen Entwürfe waren richtig und steif: Aus „Früher war das Programmieren der
teure Teil“ wurde in der Hand des Autors „Programmieren war teuer.“ Das Wort
„billig“ musste ganz raus: Billig klingt im Deutschen nach schlechter Ware, deshalb
spricht die deutsche Fassung von Aufwand, nicht von Preis. Die Tests fanden die
andere Sorte Fehler. Ein Entwurf fügte „genau“ ein und machte eine Aussage
stärker als im Englischen. Ein anderer machte aus „vereinbart“ ein „steht vorher
fest“. Ein dritter machte aus den „wesentlichen Pflichten“ des
Cyber Resilience Act „alle übrigen“. Jedes Mal ein Test, der fehlschlagen
konnte und fehlschlug.
{% </lang> %}
