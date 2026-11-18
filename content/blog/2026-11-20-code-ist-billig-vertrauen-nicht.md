+++
title = "Code ist billig geworden. Vertrauen nicht."
description = "Wenn KI das Schreiben von Code billig macht, wird der Nachweis schwer, dass er stimmt. Deutschland hat aus explodierenden Dampfkesseln einmal unabhängige Prüfung gemacht; dieser Beitrag fragt, was das für die Verifikation KI-gebauter Software in Europa bedeutet."
date = 2026-11-20
draft = true
ready = true
[taxonomies]
tags = ["verification", "europe", "standards", "ai-agents", "process", "deutsch"]
authors = ["Ralf Anton Beier"]
+++

*Dies ist die deutsche Fassung von [„Code got cheap. Trust didn't."](/blog/code-got-cheap-trust-didnt/).
Zitate stehen im englischen Original, mit einer sinngemäßen Übersetzung.*

{% <insight> %}
**Wenn das Schreiben von Code billig wird, ist der Nachweis knapp, dass er
stimmt.** Ein solcher Nachweis zählt nur, wenn seine Prüfungen fehlschlagen
können, wenn jemand anderes als der Autor prüft und jeder die Prüfung
wiederholen kann, und wenn er an eine vereinbarte Definition von „richtig"
gebunden ist. Unser Argument, aus einem kleinen Projekt heraus: Normen,
unabhängige Prüfung und Nachweise vor der Freigabe sind das, was Käufer
sicherheitskritischer Systeme von KI-gebauter Software brauchen, und die Aufgabe
ist jetzt, sie billig und offen zu machen.
{% </insight> %}

## Die Verschiebung: Erzeugen ist billig, Prüfen nicht

Den größten Teil der Softwaregeschichte war das Schreiben des Codes der teure
Teil. Code-Reviews, Tests und Beweise kamen als Aufwand obendrauf. Coding-Agenten
haben das umgedreht: Das Schreiben wurde billig, die Frage „stimmt das?" nicht.

Microsofts CEO sagte in einer Folge von The Pragmatic Engineer, veröffentlicht am
16. November 2026: "In a world where code generation has become cheap, what has
become hard is verification" (sinngemäß: Wo das Erzeugen von Code billig geworden
ist, ist die Verifikation das Schwere)
([The Pragmatic Engineer](https://newsletter.pragmaticengineer.com/p/software-engineering-after-code-becomes),
bei 11:50). In diesem Beitrag fragen wir, was aus einer Behauptung über Code einen
Nachweis macht. Unsere Arbeitsantwort hat drei Eigenschaften, nummeriert wie in
der Liste weiter unten.

{% <mermaid> %}
flowchart LR
    D["3. Vereinbarte Definition von richtig"] --> B
    A["Behauptung"] --> B["1. Prüfung, die fehlschlagen kann"]
    B --> C["2. Geprüft von jemand anderem als dem Autor, von jedem wiederholbar"]
    C --> E["Nachweis"]
{% </mermaid> %}

## Ein Kessel explodiert in Mannheim, und die drei Eigenschaften

Im Januar 1865 explodierte in einer Mannheimer Brauerei ein Dampfkessel, und am
6. Januar 1866 gründete eine Gruppe von Kesselbetreibern einen
Überwachungsverein
([Deutschlandmuseum](https://www.deutschlandmuseum.de/en/geschichte/kalender/1866-01-06-origin-of-the-tuev)).
Sein Ziel war die regelmäßige Prüfung der Kessel seiner Mitglieder, sein erster
hauptamtlicher Sachverständiger begann 1868, und er wurde zum Ausgangspunkt der
technischen Überwachung in Deutschland
([TÜV SÜD, Geschichte](https://www.tuvsud.com/en-gb/about-us/history/our-foundation-years-1866-1900)).

Unsere Arbeitsdefinition: Ein Nachweis ist nur etwas wert, wenn er drei
Eigenschaften hat.

1. **Er kann fehlschlagen.** Eine Prüfung, die bei schlechter Eingabe nicht rot
   werden kann, beweist nichts. Man findet es heraus, indem man ihr etwas gibt,
   das sie ablehnen muss. Nadella beschreibt dieselbe Gewohnheit in den
   Agenten-Teams, die er beobachtet: "how do you take every failure and then
   build back the test case and make sure you truly verify the test" (sinngemäß:
   aus jedem Fehler einen Testfall zurückbauen und sicherstellen, dass der Test
   wirklich prüft; 12:19).
2. **Er wird von jemand anderem als dem Autor geprüft und ist von jedem
   wiederholbar.** Das sind zwei getrennte Forderungen. Unabhängigkeit heißt, dass
   der Autor seine Arbeit nicht selbst abnimmt; Wiederholbarkeit heißt, dass man
   ein Ergebnis niemandem aufs Wort glauben muss. Eine Signatur zeigt, welcher
   Schlüssel ein Paket signiert hat und dass es seitdem unverändert ist; ob der
   Inhalt stimmt, sagt sie nicht. Bei Agenten gehört das Modell zur
   Unabhängigkeit: "How do you have the critique? There's so much to be said
   about having a separate model family" (sinngemäß: Wie holt man die
   Kritik ein? Vieles spricht für eine getrennte Modellfamilie; 17:05).
3. **Er ist an eine vereinbarte Definition von richtig gebunden.** „Korrekt"
   braucht eine Anforderung oder eine Norm, die sagt, was korrekt heißt, eindeutig
   formuliert.

Nach unserer Lesart hat die Kesselgeschichte alle drei. Eine Prüfung, die einen
Mangel finden kann, ist eine Prüfung, die fehlschlagen kann. Ein Sachverständiger
des Vereins, nicht der Betreiber, ist ein Prüfer, der nicht der Autor ist, und
ein regelmäßig geprüfter Kessel wird immer wieder geprüft. Ein Verein, der viele
Kessel prüft, gibt seinen Prüfern eine gemeinsame Vorstellung davon, was ein
sicherer Kessel ist, und bindet die Prüfung damit an eine Definition.

Unabhängigkeit kann auch verloren gehen. Der Abschlussbericht zur Boeing 737 MAX,
erstellt von den Mitarbeitern der Mehrheitsfraktion im Verkehrsausschuss des
US-Repräsentantenhauses, hält als einen von mehreren Befunden fest: "Excessive FAA
delegation of certification functions to Boeing on the 737 MAX eroded FAA's
oversight effectiveness and the safety of the public" (sinngemäß: Die übermäßige
Übertragung von Zertifizierungsaufgaben der FAA an Boeing hat die Wirksamkeit der
Aufsicht und die öffentliche Sicherheit geschwächt)
([Bericht des Verkehrsausschusses](https://democrats-transportation.house.gov/imo/media/doc/final_boeing_737_max_report.pdf)).
Wir lesen das als dieselbe Lektion wie in Mannheim: Die Prüfung muss unabhängig
sein.

Nach unserer Lesart wirken Normen außerdem als kollektives Gedächtnis. Sie halten
Lehren in einer Regel fest, damit das nächste Team sie nicht noch einmal lernen
muss, und sie liefern die vereinbarte Definition, die die dritte Eigenschaft
verlangt.

## Wenn aus einer Auflage das Produkt wird

**Bei der Zertifizierung hat es funktioniert.** Unabhängige Prüfung ist für jeden
Hersteller ein Kostenfaktor, und für die Prüfer wurde sie ein bezahltes Geschäft.
TÜV SÜD meldete für 2024 einen Umsatz von 3,4 Milliarden Euro
([Pressemitteilung](https://www.tuvsud.com/en-gb/press-and-media/2025/may/tuev-sued-achieves-significant-revenue-growth-in-2024)),
TÜV Rheinland 2,71 Milliarden Euro
([Pressemitteilung](https://www.tuv.com/press/en/press-releases/tuev-rheinland-results-2024.html)),
jeweils über alle Dienstleistungen. Nach unserer Lesart besteht ein großer Teil
dieser Nachfrage, weil Prüfung gesetzlich vorgeschrieben ist; dieses
Vertrauensgeschäft beruht also auf einer Pflicht, und seine Schwachstelle ist,
dass die Prüfer von den Firmen bezahlt werden, die sie prüfen.

**Bei der Solarindustrie ist es gescheitert.** Nachdem Einspeisevergütungen einen
Boom ausgelöst hatten, war Deutschland einmal der größte Solarmarkt der Welt. Im
Mai 2017 meldete SolarWorld, der letzte große deutsche Zellhersteller, angesichts
chinesischer Konkurrenz Insolvenz an
([Clean Energy Wire](https://www.cleanenergywire.org/news/last-major-german-solar-cell-maker-surrenders-chinese-competition)).
Die Einspeisevergütung war eine Subvention, die Nachfrage schuf, keine Auflage
für die Hersteller, und die Nachfrage galt einem Massenprodukt, das andere
billiger herstellen konnten.

Das Muster, wie wir die Fälle lesen: **Eine Auflage wird zur Stärke, wenn sie ein
Vertrauensgut hervorbringt, das schwer zu kopieren ist und für das Käufer zahlen
müssen. Sie bleibt ein Kostenfaktor, wenn sie nur Nachfrage schafft, die jeder
billiger bedienen kann.** Das ist unsere Synthese aus einer Handvoll Fällen, keine
gesicherte Gesetzmäßigkeit.

Das scheint unserer Forderung nach offenen Nachweisen zu widersprechen: Wenn jeder
sie kopieren kann, wie können sie schwer zu kopieren sein? Unsere Antwort: Offene
Nachweise bleiben schwer zu fälschen, weil ihre Prüfungen fehlschlagen können und
jeder sie wiederholen kann. Billig wird das Erzeugen und Veröffentlichen von
Nachweisen, nicht das Vertrauen in sie. Verifikationsnachweise für
sicherheitskritische Software liegen auf der Seite der Zertifizierung, solange
sie diese Eigenschaften behalten.

## Regelwerke und Werkzeuge kommen spät

Ein NBER-Arbeitspapier von Bick, Blandin, Deming, Fuchs-Schündeln und Jessen vom
März 2026 berichtet, dass die Produktion je Arbeitsstunde zwischen 1995 und
2025 in den USA um 85 % stieg, in Europa um 29 %, eine Lücke, die lange vor der KI
entstand, und dass etwa 43 % der US-Beschäftigten KI bei der Arbeit nutzen,
gegenüber etwa 32 % in der Befragung europäischer Beschäftigter. Branchen, die KI
stärker einsetzten, hatten ein schnelleres Produktivitätswachstum, ohne klare
Veränderung der Beschäftigung. Die Autoren berichten eine Korrelation und
behaupten keinen ursächlichen Zusammenhang
([NBER-Arbeitspapier 34995](https://www.nber.org/papers/w34995)).

Die Regelwerke für KI-gebaute und vernetzte Produkte kommen spät. Der Rat der EU hat am
29. Juni 2026 endgültig zugestimmt, die Fristen der KI-Verordnung für
Hochrisiko-KI-Systeme auf den 2. Dezember 2027 für eigenständige Systeme und den
2. August 2028 für in regulierte Produkte eingebettete Systeme zu verschieben
([Rat über EEAS](https://www.eeas.europa.eu/delegations/chile/artificial-intelligence-council-gives-final-green-light-simplify-and-streamline-rules_en)).
Das Cyberresilienzgesetz (Cyber Resilience Act) ist ein Cybersicherheitsgesetz für Produkte mit
digitalen Elementen, kein Gesetz zur funktionalen Sicherheit. Seine
Meldepflichten gelten seit dem 11. September 2026, seine Hauptpflichten ab dem
11. Dezember 2027
([Europäische Kommission](https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act)).

Bei den Werkzeugen hat rust-lang/rust#144999, übernommen am 8. August 2025, die
instabile MC/DC-Instrumentierung entfernt
([rust-lang/rust#144999](https://github.com/rust-lang/rust/pull/144999)). Das
Projektziel für 2026 strebt instabile Unterstützung an, und die Zielseite nennt
DO-178C Level A unter den Normen, die MC/DC verlangen
([Zielseite](https://goals.rust-lang.org/2026/mcdc-coverage-support.html)).
Qualifizierte Rust-Werkzeuge gibt es: Ferrous Systems gab im November 2023
bekannt, dass TÜV SÜD die Werkzeugkette Ferrocene 23.06.0, die Open Source ist, als
Werkzeug für ISO 26262 (ASIL D) und IEC 61508 (SIL 4) qualifiziert hat
([Ferrous Systems](https://ferrous-systems.com/blog/officially-qualified-ferrocene/)).
Damit ist der Compiler qualifiziert, nicht die damit gebaute Software. In
derselben Folge erwartet der Moderator Gergely Orosz "blueprints and
certifications in, I don't know, five to 10 years" (sinngemäß: Blaupausen und
Zertifizierungen in, ich weiß nicht, fünf bis zehn Jahren) für agentengebaute
Systeme (52:09). Späte Regelwerke und eine MC/DC-Unterstützung, die noch ein Ziel
ist, lesen wir als Raum für offene Verifikationsnachweise bis dahin.

## Was wir tun

PulseEngine ist eine WebAssembly-Component-Model-Engine in Arbeit, ausgerichtet
auf sicherheitskritische Ziele und zum großen Teil von KI-Agenten gebaut. Ihre
Aufgabe ist aus unserer Sicht, die „langsamen" Teile schnell und offen zu machen.
Unsere jüngste Arbeit lässt sich den drei Eigenschaften so zuordnen:

- **Eigenschaft 1, Prüfungen, die fehlschlagen können.** Unser
  [vorheriger Beitrag](/blog/green-by-default/) beschrieb, wie man schlechte
  Eingaben einschleust, um zu sehen, ob eine Prüfung rot wird. Daraus ist ein
  Werkzeug geworden, [plant](https://github.com/pulseengine/plant).
- **Eigenschaften 2 und 3, Prüfung gegen eine Definition.** Zwei Prüfer,
  KI-Agenten ohne den Kontext des Autors gestartet, lasen die 29 Anforderungen
  unseres Projekts `wohl` auf Mehrdeutigkeit
  ([wohl#97](https://github.com/pulseengine/wohl/issues/97)); die mechanischen
  Korrekturen stehen in [wohl#98](https://github.com/pulseengine/wohl/pull/98).
  Das Lesen des Codes machte aus einem Befund, einer Sicherheitsprüfung, die im
  Szenario ihrer eigenen Anforderung nie auslöste, einen Sicherheitsbefund, der
  noch auf eine Entwurfsentscheidung wartet. Beide Prüfer kamen aus demselben
  Projekt und derselben Modellfamilie wie der Autor; sie waren also unabhängig
  vom Kontext des Autors, nicht von der Organisation oder vom Modell, und jeder
  Hinweis wurde am Code geprüft, bevor sich etwas änderte.
- **Eigenschaften 1 und 2, Nachweise, die jeder wiederholen kann.** Die
  [Veröffentlichung v0.7.0](https://github.com/pulseengine/wohl/releases/tag/v0.7.0) von
  `wohl` liefert ein signiertes Nachweispaket mit einem einzigen Prüfbefehl. Ein
  monatlicher Arbeitsablauf führt es jetzt aus, mit zwei eingeschleusten Fehlern, die
  rot werden müssen
  ([pulseengine.eu#377](https://github.com/pulseengine/pulseengine.eu/pull/377)).
  Das zeigt, dass das Paket intakt ist und seine Prüfungen noch fehlschlagen
  können, nicht dass die Software korrekt ist.

Als Nächstes konzentrieren wir uns auf Verifikationswerkzeuge, die so gebaut sind, dass ihre
Qualifizierungsnachweise erzeugt und offen veröffentlicht werden können; auf
signierte, maschinenlesbare Nachweispakete, die sich auf die Normen des
Cyberresilienzgesetzes abbilden lassen, falls und sobald diese erscheinen; auf
Rückverfolgbarkeit von jedem Beweis oder Test zu der Klausel, die er abdeckt,
auch für Änderungen von KI-Agenten; und auf MC/DC-Abdeckung für Rust und
WebAssembly.

## Grenzen

Dies ist ein Argument aus einem kleinen Projekt, keine Marktstudie. Wir haben
keine verlässliche Zahl zur Größe des Marktes für Verifikationswerkzeuge in der
sicherheitskritischen Entwicklung gefunden, und bisher hat uns kein Käufer etwas
bezahlt. Die Regel, wann eine Auflage zur Stärke wird, ist unsere Lesart einiger
weniger Fälle. Die meisten Belege, die wir zur Qualität von KI-geschriebenem Code
gefunden haben, stammen noch von Anbietern.

Was unsere Meinung ändern würde: ein veröffentlichtes Nachweisformat für das
Cyberresilienzgesetz, das unsere Pakete überflüssig macht, ein Pilotprojekt, in
dem sich niemand für offene Qualifizierungsnachweise interessiert, oder eine
unabhängige Studie, die zeigt, dass KI-geschriebener sicherheitskritischer Code
weniger Prüfung braucht, nicht mehr.
