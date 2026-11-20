+++
title = "North Star"
description = "Where PulseEngine is heading, how far it is, and what is committed next. The goal has no date; objectives are measured at each monthly varve layer by scripts, never typed in."
template = "north-star.html"
draft = false
+++

The goal keeps moving further out; only the steps toward it are dated. Inside, work flows through Kanban and gates. Each monthly varve layer is a measurement point, so progress becomes a curve. Every objective names its indicator and a guard metric, because agents work on whatever a gate checks. An objective that no script measures yet says **unmeasured**, not zero. This is work in progress: most objectives are not measured yet.

A rivet feature in any repository links up to the objective it serves with `serves: O2`, or `serves: [O1, O5]` for more than one. The rivet schema fragment `schemas/north-star.yaml` in this site's repository allows exactly the objective ids below, and `rivet validate` (0.43.0 or later) rejects any other. New ideas start as issues labelled `idea`; triage either links them to an objective, parks them, or closes them with a reason.
