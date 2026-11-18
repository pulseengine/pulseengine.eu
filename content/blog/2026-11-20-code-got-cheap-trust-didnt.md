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
title_de = "Code ist billig geworden. Vertrauen nicht."
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

**Code ist billig geworden. Knapp ist jetzt der Nachweis, dass er stimmt.** Dieser
Nachweis zählt nur unter drei Bedingungen: Die Prüfung muss rot werden können. Ein anderer
als der Autor prüft, und jeder kann nachprüfen. Und was „richtig“ ist, ist
vereinbart. Unser Argument, aus einem kleinen Projekt heraus: Käufer
sicherheitskritischer Systeme brauchen Normen, unabhängige Prüfung und Nachweise
vor der Freigabe, auch bei KI-gebauter Software. Jetzt geht es
darum, das billig und offen zu machen.

</div>
</aside>
{% </lang> %}

{% <lang code="en"> %}
## The shift: generation is cheap, checking is not

For most of software's history, writing the code was the expensive part.
Reviews, tests and proofs were overhead you paid on top. Coding agents have
turned that around: writing got cheap, and the question "is it right?" did not.

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
## Code ist billig, Prüfen nicht

Programmieren war teuer. Reviews, Tests und Beweise kamen noch dazu. Mit
Coding-Agenten hat sich das gedreht: Code ist billig. Die Frage, ob er stimmt,
ist es nicht.

Microsofts CEO sagt es im Podcast The Pragmatic Engineer vom 16. November 2026
so: "In a world where code generation has become cheap, what has become hard is
verification" – sinngemäß: Code zu erzeugen ist billig geworden, schwer ist jetzt
das Prüfen
([The Pragmatic Engineer](https://newsletter.pragmaticengineer.com/p/software-engineering-after-code-becomes),
bei 11:50). Was macht aus einer Behauptung über Code einen Nachweis? Unsere
vorläufige Antwort: drei Bedingungen. Die Nummern gelten auch in der Liste
weiter unten.

<pre class="mermaid">
flowchart LR
    D["3. Vereinbart, was richtig ist"] --> B
    A["Behauptung"] --> B["1. Prüfung, die rot werden kann"]
    B --> C["2. Vier-Augen-Prinzip, von jedem nachprüfbar"]
    C --> E["Nachweis"]
</pre>
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

In our reading, the boiler story has all three. An inspection that can find a
fault is a check that can fail. An expert of the association, not the operator,
is a checker other than the author, and a boiler inspected regularly is checked
again and again. An association that examines many boilers gives its examiners
a shared idea of what a sound boiler is, which ties the check to a definition.

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
## Ein Kessel explodiert in Mannheim

Januar 1865: In einer Mannheimer Brauerei explodiert ein Dampfkessel. Am
6. Januar 1866 gründen Kesselbesitzer einen Überwachungsverein
([Deutschlandmuseum](https://www.deutschlandmuseum.de/en/geschichte/kalender/1866-01-06-origin-of-the-tuev)).
Er soll die Kessel seiner Mitglieder regelmäßig prüfen. 1868 kommt der erste
hauptamtliche Sachverständige. Daraus wird der Ausgangspunkt der technischen
Überwachung in Deutschland
([TÜV SÜD, Geschichte](https://www.tuvsud.com/en-gb/about-us/history/our-foundation-years-1866-1900)).

Unsere Arbeitsdefinition: Ein Nachweis taugt nur unter drei Bedingungen.

1. **Eine Prüfung muss rot werden können.** Bleibt sie bei falscher Eingabe
   grün, beweist sie nichts. Das zeigt sich erst, wenn man ihr etwas vorlegt, das
   sie ablehnen muss. Nadella beschreibt dieselbe Gewohnheit in den Agenten-Teams, die er
   beobachtet:
   "how do you take every failure and then build back the test case and make sure
   you truly verify the test" – sinngemäß: aus jedem Fehler einen Testfall machen
   und sicherstellen, dass der Test wirklich prüft (12:19).
2. **Vier-Augen-Prinzip: Ein anderer prüft, und jeder kann es nachprüfen.** Das
   sind zwei Forderungen. Unabhängig heißt: Keiner nimmt seine eigene Arbeit ab.
   Nachprüfbar heißt: Keiner muss das Ergebnis glauben. Eine Signatur zeigt nur,
   welcher Schlüssel ein Paket signiert hat und dass es seitdem unverändert ist.
   Ob der Inhalt stimmt, zeigt sie nicht. Bei Agenten gehört das Modell dazu:
   "How do you have the critique? There's so much to be said about having a
   separate model family" – sinngemäß: Wie kommt man zur Kritik? Zu einer eigenen
   Modellfamilie gibt es viel zu sagen (17:05).
3. **Was „richtig“ ist, ist vereinbart.** Dafür braucht es eine Anforderung
   oder Norm, die das eindeutig sagt.

Nach unserer Lesart erfüllt die Mannheimer Geschichte alle drei. Wer einen
Mangel finden kann, kann auch rot melden. Es prüft der Sachverständige des
Vereins, nicht der Betreiber. Und weil der Kessel regelmäßig drankommt, wird
immer wieder nachgeprüft. Der Verein prüft viele Kessel. So entsteht bei seinen
Prüfern ein gemeinsames Bild davon, was ein sicherer Kessel ist, und die Prüfung
hängt an einer Definition.

Unabhängigkeit kann verloren gehen. Den Abschlussbericht zur Boeing 737 MAX haben
Mitarbeiter der Mehrheitsfraktion im Verkehrsausschuss des
US-Repräsentantenhauses geschrieben. Einer von mehreren Befunden: "Excessive FAA
delegation of certification functions to Boeing on the 737 MAX eroded FAA's
oversight effectiveness and the safety of the public" – sinngemäß: Die FAA hat
zu viel Zertifizierung an Boeing abgegeben. Das hat die Wirksamkeit ihrer Aufsicht
und die öffentliche Sicherheit geschwächt
([Bericht des Verkehrsausschusses](https://democrats-transportation.house.gov/imo/media/doc/final_boeing_737_max_report.pdf)).
Für uns ist das dieselbe Lehre wie in Mannheim: Wer prüft, muss unabhängig sein.

Normen sind für uns außerdem ein kollektives Gedächtnis. Sie machen aus Lehren
Regeln, damit das nächste Team sie nicht noch einmal lernen muss. Und sie liefern
die vereinbarte Definition, die Bedingung 3 verlangt.
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

This seems to clash with our call for open evidence: if anyone can copy it, how
can it be hard to copy? Our answer is that open evidence stays hard to fake
because its checks can fail and anyone can re-run them. What gets cheap is
producing and publishing evidence, not trusting it. Verification evidence for
safety-critical software falls on the certification side of our line, as long
as it keeps those properties.
{% </lang> %}

{% <lang code="de"> %}
## Wenn aus der Auflage ein Produkt wird

**Bei Prüfung und Zertifizierung hat das geklappt.** Für Hersteller kostet
unabhängige Prüfung Geld. Für die Prüfer wurde sie ein Geschäft. TÜV SÜD meldete
für 2024 einen Umsatz von 3,4 Milliarden Euro
([Pressemitteilung](https://www.tuvsud.com/en-gb/press-and-media/2025/may/tuev-sued-achieves-significant-revenue-growth-in-2024)),
TÜV Rheinland 2,71 Milliarden Euro
([Pressemitteilung](https://www.tuv.com/press/en/press-releases/tuev-rheinland-results-2024.html)),
jeweils über alle Geschäftsfelder. Nach unserer Lesart kommt viel davon aus
Prüfungen, die das Gesetz vorschreibt. Das Geschäft mit dem Vertrauen hängt also
an einer Pflicht. Und seine Schwachstelle ist, nach unserer Lesart, dass die
Prüfer von denen bezahlt werden, die sie prüfen.

**Bei der Solarindustrie ist es gescheitert.** Die Einspeisevergütung löste einen
Boom aus. Deutschland war eine Zeit lang der größte Solarmarkt der Welt. Im Mai
2017 meldete SolarWorld Insolvenz an, der letzte große deutsche Zellhersteller,
unter dem Druck chinesischer Konkurrenz
([Clean Energy Wire](https://www.cleanenergywire.org/news/last-major-german-solar-cell-maker-surrenders-chinese-competition)).
Die Einspeisevergütung war eine Subvention. Sie schuf Nachfrage, sie war keine
Auflage für die Hersteller. Und gefragt war Massenware, die andere billiger bauen
konnten.

So lesen wir die Fälle: **Eine Auflage wird zur Stärke, wenn daraus ein
Vertrauensgut entsteht, das schwer zu kopieren ist und für das Käufer zahlen
müssen. Sie bleibt ein Kostenfaktor, wenn sie nur Nachfrage schafft, die jeder
billiger bedienen kann.** Das schließen wir aus einer Handvoll Fälle. Eine
getestete Gesetzmäßigkeit ist es nicht.

Das scheint unserer Forderung nach offenen Nachweisen zu widersprechen. Was jeder
kopieren kann, ist nicht schwer zu kopieren. Unsere Antwort: Fälschen lassen sich
offene Nachweise trotzdem schwer. Ihre Prüfungen können rot werden, und jeder
kann sie wiederholen. Billig wird das Erstellen und Veröffentlichen, nicht das
Vertrauen. Verifikationsnachweise für sicherheitskritische Software gehören auf
unserer Linie auf die Seite der Zertifizierung, solange sie die drei Bedingungen erfüllen.
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

The rulebooks for AI-built and connected products are arriving late. The Council
gave final approval on 29 June 2026 to move the AI Act's high-risk deadlines to
2 December 2027 for stand-alone systems and 2 August 2028 for systems embedded in
regulated products
([Council via EEAS](https://www.eeas.europa.eu/delegations/chile/artificial-intelligence-council-gives-final-green-light-simplify-and-streamline-rules_en)).
The Cyber Resilience Act is a cybersecurity law for products with digital
elements, not a functional-safety law. Its reporting obligations have applied
since 11 September 2026, and its main obligations apply from 11 December 2027
([European Commission](https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act)).

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
## Regeln und Werkzeuge kommen spät

Ein NBER-Arbeitspapier von Bick, Blandin, Deming, Fuchs-Schündeln und Jessen vom
März 2026 berichtet: Die Arbeitsproduktivität (Leistung je Arbeitsstunde) stieg
von 1995 bis 2025 in den USA um 85 %, in Europa um 29 %. Die Lücke entstand lange
vor der KI. Etwa 43 % der US-Beschäftigten nutzen KI bei der Arbeit, in der Befragung
europäischer Beschäftigter etwa 32 %. Branchen mit mehr KI wurden schneller
produktiver. Die Beschäftigung änderte sich dabei nicht erkennbar. Die Autoren
berichten eine Korrelation und behaupten keine Ursache
([NBER-Arbeitspapier 34995](https://www.nber.org/papers/w34995)).

Die Regeln für KI-gebaute und vernetzte Produkte kommen spät. Am 29. Juni 2026 hat
der Rat der EU endgültig beschlossen, die Fristen der KI-Verordnung für
Hochrisiko-KI-Systeme zu verschieben: auf den 2. Dezember 2027 für eigenständige
Systeme, auf den 2. August 2028 für Systeme in regulierten Produkten
([Rat der EU über EEAS](https://www.eeas.europa.eu/delegations/chile/artificial-intelligence-council-gives-final-green-light-simplify-and-streamline-rules_en)).
Das Cyberresilienzgesetz (Cyber Resilience Act) regelt Cybersicherheit für
Produkte mit digitalen Elementen, nicht funktionale Sicherheit. Die Meldepflichten
gelten seit dem 11. September 2026, die wesentlichen Pflichten ab dem
11. Dezember 2027
([Europäische Kommission](https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act)).

Zu den Werkzeugen: rust-lang/rust#144999 hat am 8. August
2025 die instabile MC/DC-Instrumentierung entfernt
([rust-lang/rust#144999](https://github.com/rust-lang/rust/pull/144999)). Das
Rust-Projektziel für 2026 zielt auf instabile Unterstützung. Die Zielseite nennt
DO-178C Level A unter den Normen, die MC/DC verlangen
([Zielseite](https://goals.rust-lang.org/2026/mcdc-coverage-support.html)).
Qualifizierte Rust-Werkzeuge gibt es: Ferrous Systems gab im November 2023
bekannt, dass TÜV SÜD die quelloffene Werkzeugkette Ferrocene 23.06.0 als
Werkzeug für ISO 26262 (ASIL D) und IEC 61508 (SIL 4) qualifiziert hat
([Ferrous Systems](https://ferrous-systems.com/blog/officially-qualified-ferrocene/)).
Qualifiziert ist damit der Compiler, nicht die Software, die man damit baut. In
derselben Folge rechnet der Moderator Gergely Orosz für agentengebaute Systeme
mit "blueprints and certifications in, I don't know, five to 10 years" –
sinngemäß: mit Bauplänen und Zertifizierungen in vielleicht fünf bis zehn
Jahren (52:09).
Späte Regeln und MC/DC, das erst noch kommen soll: Darin sehen wir Raum für
offene Verifikationsnachweise bis dahin.
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

Next we concentrate on verifiers designed so that their qualification evidence
can be produced and published openly; on signed, machine-readable evidence
bundles that can be mapped onto the Cyber Resilience Act's standards if and when
they are published; on traceability from each proof or test to the clause it
covers, including changes written by AI agents; and on MC/DC coverage for Rust
and WebAssembly.
{% </lang> %}

{% <lang code="de"> %}
## Was wir tun

PulseEngine ist eine WebAssembly-Component-Model-Engine, noch in Arbeit, gedacht
für sicherheitskritische Einsätze und zum großen Teil von KI-Agenten gebaut.
Ihre Aufgabe sehen wir so: die „langsamen“ Teile schnell und offen machen. Was
wir zuletzt getan haben, nach Bedingung:

- **Bedingung 1, Prüfungen, die rot werden können.** Im
  [vorigen Beitrag](/blog/green-by-default/) haben wir Prüfungen gezielt falsche
  Eingaben untergeschoben und geschaut, ob sie rot werden. Daraus ist ein Werkzeug
  geworden: [plant](https://github.com/pulseengine/plant).
- **Bedingungen 2 und 3, Prüfung gegen eine Definition.** Zwei Prüfer, KI-Agenten
  ohne den Kontext des Autors, haben die 29 Anforderungen unseres Projekts `wohl`
  auf Mehrdeutigkeiten gelesen
  ([wohl#97](https://github.com/pulseengine/wohl/issues/97)). Die mechanischen
  Korrekturen stehen in [wohl#98](https://github.com/pulseengine/wohl/pull/98).
  Im Code wurde aus einem Befund ein Sicherheitsbefund: Eine
  Sicherheitsprüfung löste im Szenario ihrer eigenen Anforderung nie aus. Die
  Designentscheidung dazu steht noch aus. Beide Prüfer kamen aus demselben Projekt
  und derselben Modellfamilie wie der Autor. Unabhängig waren sie also vom Kontext
  des Autors, nicht von der Organisation oder vom Modell. Jeder Hinweis wurde am
  Code überprüft, bevor wir etwas geändert haben.
- **Bedingungen 1 und 2, Nachweise, die jeder wiederholen kann.** Das
  `wohl`-Release
  [v0.7.0](https://github.com/pulseengine/wohl/releases/tag/v0.7.0) enthält ein
  signiertes Nachweispaket, prüfbar mit einem einzigen Befehl. Ein monatlicher Lauf
  prüft es jetzt, mit zwei absichtlich eingebauten Fehlern, die rot werden müssen
  ([pulseengine.eu#377](https://github.com/pulseengine/pulseengine.eu/pull/377)).
  Das zeigt: Das Paket ist unversehrt, und seine Prüfungen können noch rot werden.
  Dass die Software korrekt ist, zeigt es nicht.

Als Nächstes: Prüfwerkzeuge, die wir so bauen, dass sich ihre
Qualifizierungsnachweise offen erzeugen und veröffentlichen lassen. Signierte, maschinenlesbare Nachweispakete, die sich auf
die Normen zum Cyberresilienzgesetz abbilden lassen, falls und sobald sie
veröffentlicht sind. Rückverfolgbarkeit von jedem Beweis und Test zu der Klausel,
die er abdeckt, auch bei Änderungen durch KI-Agenten. Und MC/DC-Abdeckung für Rust
und WebAssembly.
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
sicherheitskritischen Entwicklung haben wir nicht gefunden. Bezahlt hat uns bisher
kein Käufer. Wann eine Auflage zur Stärke wird, haben wir aus wenigen Fällen
geschlossen. Die meisten Belege zur Qualität von KI-geschriebenem Code, die wir
gefunden haben, stammen noch von Anbietern.

Was uns umstimmen würde: ein veröffentlichtes Nachweisformat für das
Cyberresilienzgesetz, das unsere Pakete überflüssig macht. Ein Pilotprojekt, in
dem sich niemand für offene Qualifizierungsnachweise interessiert. Oder eine
unabhängige Studie, die zeigt, dass KI-geschriebener sicherheitskritischer Code
weniger Prüfung braucht, nicht mehr.
{% </lang> %}
