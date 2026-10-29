# Incident ledger: run report

Generated 2026-10-29T21:34Z by `scripts/incident-ledger.py run`. Window 2026-07-31 to 2026-10-29, 34 non-fork, non-archived repos. Snapshot: these numbers are from this run and drift on the next one.

Unit: a merge to the default branch. Rates are merges with at least one signal per 100 merges, Wilson 95% interval, (k/n). Never read a bare count as a trend.

## Headline

- Escape rate (post-merge: main-red, revert, hotfix-ref, merge-guard, or a ledger entry of kind escape): **9.6 [8.5, 10.8] (246/2572)** per 100 merges
- Strict escape rate, the same without hotfix-ref (a heuristic; see Method): **5.8 [5.0, 6.8] (149/2572)**
- Incident rate, owner definition (escape or merge-queue ejection): **9.8 [8.7, 11.0] (251/2572)**
- Caught before merge (red PR commit later fixed, or queue ejection on failed checks): **18.5 [17.1, 20.1] (476/2572)**
- Catch share, caught / (caught + escaped): **65.9 [62.4, 69.3] (476/722)** percent

Signal counts (a unit can carry several): hotfix-ref 118, ledger 3, main-red 155, merge-guard 2, mq-ejected 5, pr-red 472.
Net flags: merged-before-ci 355, merged-red-head 508, no-pr 85, pr-not-found 2.

### By authoring class

| class | merges | escape /100 [95% CI] | strict escape /100 | incident /100 (owner def.) | caught /100 | catch share % |
|---|---:|---|---|---|---|---|
| bot | 528 | 5.5 [3.9, 7.8] (29/528) | 4.7 [3.2, 6.9] (25/528) | 5.5 [3.9, 7.8] (29/528) | 5.3 [3.7, 7.6] (28/528) | 49.1 [36.6, 61.7] (28/57) |
| claude-fable-5 | 54 | 3.7 [1.0, 12.5] (2/54) | 1.9 [0.3, 9.8] (1/54) | 3.7 [1.0, 12.5] (2/54) | 18.5 [10.4, 30.8] (10/54) | 83.3 [55.2, 95.3] (10/12) |
| claude-fable-5.1 | 14 | 0.0 [0.0, 21.5] (0/14) | 0.0 [0.0, 21.5] (0/14) | 0.0 [0.0, 21.5] (0/14) | 7.1 [1.3, 31.5] (1/14) | 100.0 [20.7, 100.0] (1/1) |
| claude-haiku-4.5 | 2 | 0.0 [0.0, 65.8] (0/2) | 0.0 [0.0, 65.8] (0/2) | 0.0 [0.0, 65.8] (0/2) | 0.0 [0.0, 65.8] (0/2) | n/a (n=0) |
| claude-opus-4.7 | 13 | 0.0 [0.0, 22.8] (0/13) | 0.0 [0.0, 22.8] (0/13) | 0.0 [0.0, 22.8] (0/13) | 7.7 [1.4, 33.3] (1/13) | 100.0 [20.7, 100.0] (1/1) |
| claude-opus-4.8 | 193 | 9.3 [6.0, 14.3] (18/193) | 4.1 [2.1, 8.0] (8/193) | 9.3 [6.0, 14.3] (18/193) | 16.6 [12.0, 22.5] (32/193) | 64.0 [50.1, 75.9] (32/50) |
| claude-opus-5 | 895 | 13.4 [11.3, 15.8] (120/895) | 7.7 [6.1, 9.6] (69/895) | 13.4 [11.3, 15.8] (120/895) | 26.9 [24.1, 29.9] (241/895) | 66.8 [61.7, 71.4] (241/361) |
| claude-opus-5.5 | 478 | 8.8 [6.6, 11.7] (42/478) | 5.9 [4.1, 8.3] (28/478) | 9.6 [7.3, 12.6] (46/478) | 15.5 [12.5, 19.0] (74/478) | 63.8 [54.7, 72.0] (74/116) |
| claude-sonnet-5 | 9 | 11.1 [2.0, 43.5] (1/9) | 0.0 [0.0, 29.9] (0/9) | 11.1 [2.0, 43.5] (1/9) | 11.1 [2.0, 43.5] (1/9) | 50.0 [9.5, 90.5] (1/2) |
| claude-sonnet-5.5 | 10 | 0.0 [0.0, 27.8] (0/10) | 0.0 [0.0, 27.8] (0/10) | 0.0 [0.0, 27.8] (0/10) | 10.0 [1.8, 40.4] (1/10) | 100.0 [20.7, 100.0] (1/1) |
| claude-unnamed | 48 | 14.6 [7.2, 27.2] (7/48) | 6.2 [2.1, 16.8] (3/48) | 14.6 [7.2, 27.2] (7/48) | 25.0 [14.9, 38.8] (12/48) | 63.2 [41.0, 80.9] (12/19) |
| human-only | 273 | 8.4 [5.7, 12.3] (23/273) | 4.4 [2.5, 7.5] (12/273) | 8.4 [5.7, 12.3] (23/273) | 17.6 [13.5, 22.5] (48/273) | 67.6 [56.1, 77.3] (48/71) |
| mixed | 55 | 7.3 [2.9, 17.3] (4/55) | 5.5 [1.9, 14.9] (3/55) | 9.1 [3.9, 19.6] (5/55) | 49.1 [36.4, 61.9] (27/55) | 87.1 [71.1, 94.9] (27/31) |

`human-only` means no agent marker, not proven human: agents commit under the owner's account.

### By change type

| type | merges | escape /100 [95% CI] | strict escape /100 | incident /100 (owner def.) | caught /100 | catch share % |
|---|---:|---|---|---|---|---|
| build | 49 | 6.1 [2.1, 16.5] (3/49) | 6.1 [2.1, 16.5] (3/49) | 6.1 [2.1, 16.5] (3/49) | 18.4 [10.0, 31.4] (9/49) | 75.0 [46.8, 91.1] (9/12) |
| chore | 490 | 7.6 [5.5, 10.2] (37/490) | 5.7 [4.0, 8.1] (28/490) | 7.6 [5.5, 10.2] (37/490) | 7.1 [5.2, 9.8] (35/490) | 48.6 [37.4, 59.9] (35/72) |
| ci | 102 | 13.7 [8.4, 21.7] (14/102) | 7.8 [4.0, 14.7] (8/102) | 13.7 [8.4, 21.7] (14/102) | 13.7 [8.4, 21.7] (14/102) | 50.0 [32.6, 67.4] (14/28) |
| docs | 84 | 6.0 [2.6, 13.2] (5/84) | 4.8 [1.9, 11.6] (4/84) | 6.0 [2.6, 13.2] (5/84) | 11.9 [6.6, 20.5] (10/84) | 66.7 [41.7, 84.8] (10/15) |
| feat | 289 | 16.6 [12.8, 21.3] (48/289) | 8.7 [5.9, 12.5] (25/289) | 17.6 [13.7, 22.5] (51/289) | 28.0 [23.2, 33.5] (81/289) | 62.8 [54.2, 70.6] (81/129) |
| fix | 437 | 14.2 [11.2, 17.8] (62/437) | 5.0 [3.3, 7.5] (22/437) | 14.6 [11.6, 18.3] (64/437) | 24.3 [20.5, 28.5] (106/437) | 63.1 [55.6, 70.0] (106/168) |
| non-conventional | 766 | 6.3 [4.8, 8.2] (48/766) | 5.2 [3.9, 7.0] (40/766) | 6.3 [4.8, 8.2] (48/766) | 18.7 [16.1, 21.6] (143/766) | 74.9 [68.3, 80.5] (143/191) |
| other | 318 | 8.8 [6.2, 12.4] (28/318) | 5.7 [3.6, 8.8] (18/318) | 8.8 [6.2, 12.4] (28/318) | 20.1 [16.1, 24.9] (64/318) | 69.6 [59.5, 78.0] (64/92) |
| perf | 6 | 0.0 [0.0, 39.0] (0/6) | 0.0 [0.0, 39.0] (0/6) | 0.0 [0.0, 39.0] (0/6) | 33.3 [9.7, 70.0] (2/6) | 100.0 [34.2, 100.0] (2/2) |
| refactor | 4 | 0.0 [0.0, 49.0] (0/4) | 0.0 [0.0, 49.0] (0/4) | 0.0 [0.0, 49.0] (0/4) | 0.0 [0.0, 49.0] (0/4) | n/a (n=0) |
| style | 1 | 0.0 [0.0, 79.3] (0/1) | 0.0 [0.0, 79.3] (0/1) | 0.0 [0.0, 79.3] (0/1) | 0.0 [0.0, 79.3] (0/1) | n/a (n=0) |
| test | 26 | 3.8 [0.7, 18.9] (1/26) | 3.8 [0.7, 18.9] (1/26) | 3.8 [0.7, 18.9] (1/26) | 46.2 [28.8, 64.5] (12/26) | 92.3 [66.7, 98.6] (12/13) |

### By month

| month | merges | escape /100 [95% CI] | strict escape /100 | incident /100 (owner def.) | caught /100 | catch share % |
|---|---:|---|---|---|---|---|
| 2026-08 | 667 | 8.7 [6.8, 11.1] (58/667) | 5.4 [3.9, 7.4] (36/667) | 8.7 [6.8, 11.1] (58/667) | 16.0 [13.5, 19.0] (107/667) | 64.8 [57.3, 71.7] (107/165) |
| 2026-09 | 867 | 10.7 [8.8, 13.0] (93/867) | 6.2 [4.8, 8.0] (54/867) | 10.7 [8.8, 13.0] (93/867) | 21.0 [18.4, 23.8] (182/867) | 66.2 [60.4, 71.5] (182/275) |
| 2026-10 | 1038 | 9.2 [7.5, 11.1] (95/1038) | 5.7 [4.4, 7.3] (59/1038) | 9.6 [8.0, 11.6] (100/1038) | 18.0 [15.8, 20.5] (187/1038) | 66.3 [60.6, 71.6] (187/282) |

### By repo

| repo | merges | escape /100 [95% CI] | strict escape /100 | incident /100 (owner def.) | caught /100 | catch share % |
|---|---:|---|---|---|---|---|
| .github | 5 | 0.0 [0.0, 43.4] (0/5) | 0.0 [0.0, 43.4] (0/5) | 0.0 [0.0, 43.4] (0/5) | 0.0 [0.0, 43.4] (0/5) | n/a (n=0) |
| covalent-layers | 34 | 2.9 [0.5, 14.9] (1/34) | 2.9 [0.5, 14.9] (1/34) | 2.9 [0.5, 14.9] (1/34) | 0.0 [0.0, 10.2] (0/34) | 0.0 [0.0, 79.3] (0/1) |
| gale | 166 | 16.3 [11.4, 22.6] (27/166) | 6.0 [3.3, 10.7] (10/166) | 16.3 [11.4, 22.6] (27/166) | 25.3 [19.3, 32.4] (42/166) | 60.9 [49.1, 71.5] (42/69) |
| jess | 118 | 4.2 [1.8, 9.5] (5/118) | 1.7 [0.5, 6.0] (2/118) | 4.2 [1.8, 9.5] (5/118) | 21.2 [14.8, 29.4] (25/118) | 83.3 [66.4, 92.7] (25/30) |
| kiln | 80 | 6.2 [2.7, 13.8] (5/80) | 5.0 [2.0, 12.2] (4/80) | 6.2 [2.7, 13.8] (5/80) | 5.0 [2.0, 12.2] (4/80) | 44.4 [18.9, 73.3] (4/9) |
| loom | 93 | 9.7 [5.2, 17.4] (9/93) | 7.5 [3.7, 14.7] (7/93) | 9.7 [5.2, 17.4] (9/93) | 10.8 [5.9, 18.7] (10/93) | 52.6 [31.7, 72.7] (10/19) |
| mcp | 34 | 5.9 [1.6, 19.1] (2/34) | 5.9 [1.6, 19.1] (2/34) | 5.9 [1.6, 19.1] (2/34) | 0.0 [0.0, 10.2] (0/34) | 0.0 [0.0, 65.8] (0/2) |
| meld | 90 | 5.6 [2.4, 12.4] (5/90) | 2.2 [0.6, 7.7] (2/90) | 5.6 [2.4, 12.4] (5/90) | 38.9 [29.5, 49.2] (35/90) | 87.5 [73.9, 94.5] (35/40) |
| ordeal | 100 | 5.0 [2.2, 11.2] (5/100) | 2.0 [0.6, 7.0] (2/100) | 5.0 [2.2, 11.2] (5/100) | 9.0 [4.8, 16.2] (9/100) | 64.3 [38.8, 83.7] (9/14) |
| pulseengine-layers | 111 | 0.0 [0.0, 3.3] (0/111) | 0.0 [0.0, 3.3] (0/111) | 0.0 [0.0, 3.3] (0/111) | 1.8 [0.5, 6.3] (2/111) | 100.0 [34.2, 100.0] (2/2) |
| pulseengine.eu | 138 | 7.2 [4.0, 12.8] (10/138) | 3.6 [1.6, 8.2] (5/138) | 8.0 [4.5, 13.7] (11/138) | 8.0 [4.5, 13.7] (11/138) | 52.4 [32.4, 71.7] (11/21) |
| relay | 197 | 24.9 [19.4, 31.4] (49/197) | 12.7 [8.7, 18.1] (25/197) | 26.4 [20.7, 33.0] (52/197) | 38.6 [32.1, 45.5] (76/197) | 60.8 [52.0, 68.9] (76/125) |
| rivet | 218 | 10.1 [6.8, 14.8] (22/218) | 6.4 [3.9, 10.5] (14/218) | 10.1 [6.8, 14.8] (22/218) | 19.3 [14.6, 25.0] (42/218) | 65.6 [53.4, 76.1] (42/64) |
| rules_lean | 1 | 0.0 [0.0, 79.3] (0/1) | 0.0 [0.0, 79.3] (0/1) | 0.0 [0.0, 79.3] (0/1) | 0.0 [0.0, 79.3] (0/1) | n/a (n=0) |
| rules_ordeal | 19 | 5.3 [0.9, 24.6] (1/19) | 5.3 [0.9, 24.6] (1/19) | 5.3 [0.9, 24.6] (1/19) | 0.0 [0.0, 16.8] (0/19) | 0.0 [0.0, 79.3] (0/1) |
| rules_rocq_rust | 4 | 0.0 [0.0, 49.0] (0/4) | 0.0 [0.0, 49.0] (0/4) | 0.0 [0.0, 49.0] (0/4) | 0.0 [0.0, 49.0] (0/4) | n/a (n=0) |
| rules_verus | 2 | 0.0 [0.0, 65.8] (0/2) | 0.0 [0.0, 65.8] (0/2) | 0.0 [0.0, 65.8] (0/2) | 0.0 [0.0, 65.8] (0/2) | n/a (n=0) |
| rules_wasm_component | 73 | 8.2 [3.8, 16.8] (6/73) | 5.5 [2.2, 13.3] (4/73) | 8.2 [3.8, 16.8] (6/73) | 4.1 [1.4, 11.4] (3/73) | 33.3 [12.1, 64.6] (3/9) |
| scry | 70 | 2.9 [0.8, 9.8] (2/70) | 2.9 [0.8, 9.8] (2/70) | 2.9 [0.8, 9.8] (2/70) | 15.7 [9.0, 26.0] (11/70) | 84.6 [57.8, 95.7] (11/13) |
| sigil | 77 | 16.9 [10.1, 26.8] (13/77) | 15.6 [9.1, 25.3] (12/77) | 16.9 [10.1, 26.8] (13/77) | 9.1 [4.5, 17.6] (7/77) | 35.0 [18.1, 56.7] (7/20) |
| smithy | 34 | 11.8 [4.7, 26.6] (4/34) | 8.8 [3.0, 23.0] (3/34) | 11.8 [4.7, 26.6] (4/34) | 11.8 [4.7, 26.6] (4/34) | 50.0 [21.5, 78.5] (4/8) |
| spar | 105 | 16.2 [10.4, 24.4] (17/105) | 4.8 [2.1, 10.7] (5/105) | 17.1 [11.1, 25.5] (18/105) | 16.2 [10.4, 24.4] (17/105) | 50.0 [34.1, 65.9] (17/34) |
| synth | 471 | 10.0 [7.6, 13.0] (47/471) | 7.0 [5.0, 9.7] (33/471) | 10.0 [7.6, 13.0] (47/471) | 23.1 [19.6, 27.2] (109/471) | 69.9 [62.3, 76.5] (109/156) |
| temper | 13 | 0.0 [0.0, 22.8] (0/13) | 0.0 [0.0, 22.8] (0/13) | 0.0 [0.0, 22.8] (0/13) | 7.7 [1.4, 33.3] (1/13) | 100.0 [20.7, 100.0] (1/1) |
| varve | 167 | 5.4 [2.9, 9.9] (9/167) | 5.4 [2.9, 9.9] (9/167) | 5.4 [2.9, 9.9] (9/167) | 19.8 [14.4, 26.4] (33/167) | 78.6 [64.1, 88.3] (33/42) |
| warte | 36 | 2.8 [0.5, 14.2] (1/36) | 2.8 [0.5, 14.2] (1/36) | 2.8 [0.5, 14.2] (1/36) | 19.4 [9.8, 35.0] (7/36) | 87.5 [52.9, 97.8] (7/8) |
| wasm-component-examples | 1 | 100.0 [20.7, 100.0] (1/1) | 100.0 [20.7, 100.0] (1/1) | 100.0 [20.7, 100.0] (1/1) | 0.0 [0.0, 79.3] (0/1) | 0.0 [0.0, 79.3] (0/1) |
| wasm-layers | 29 | 0.0 [0.0, 11.7] (0/29) | 0.0 [0.0, 11.7] (0/29) | 0.0 [0.0, 11.7] (0/29) | 3.4 [0.6, 17.2] (1/29) | 100.0 [20.7, 100.0] (1/1) |
| witness | 84 | 4.8 [1.9, 11.6] (4/84) | 3.6 [1.2, 10.0] (3/84) | 4.8 [1.9, 11.6] (4/84) | 31.0 [22.1, 41.5] (26/84) | 86.7 [70.3, 94.7] (26/30) |
| wohl | 2 | 50.0 [9.5, 90.5] (1/2) | 50.0 [9.5, 90.5] (1/2) | 50.0 [9.5, 90.5] (1/2) | 50.0 [9.5, 90.5] (1/2) | 50.0 [9.5, 90.5] (1/2) |

## Baseline (weak)

Weak baseline. Pre-agent = first-parent merges before the repo's first agent marker. Spans: rules_wasm_component 2025-07-06 to 2025-11-14 (230 merges); mcp 2025-07-01 to 2026-02-20 (44 merges); rules_rocq_rust 2026-01-11 to 2026-02-20 (44 merges). Confounders: a different project phase (early, small changes), fewer repos, often no PRs and no merge queue, CI that may not have existed yet (no CI means no main-red signal, so the pre-agent escape rate is biased low), and no marker does not mean no AI. Signals limited to main-red, revert, hotfix-ref, pr-red in both eras.

### Pre-agent window vs agent era, same repos, same signals

| era | merges | escape /100 [95% CI] | strict escape /100 | incident /100 (owner def.) | caught /100 | catch share % |
|---|---:|---|---|---|---|---|
| agent era (window) | 111 | 7.2 [3.7, 13.6] (8/111) | 5.4 [2.5, 11.3] (6/111) | 7.2 [3.7, 13.6] (8/111) | 2.7 [0.9, 7.6] (3/111) | 27.3 [9.7, 56.6] (3/11) |
| pre-agent | 318 | 3.5 [1.9, 6.1] (11/318) | 3.5 [1.9, 6.1] (11/318) | 3.5 [1.9, 6.1] (11/318) | 3.8 [2.2, 6.5] (12/318) | 52.2 [33.0, 70.8] (12/23) |

Excluded from the baseline: synth: only 1 pre-agent merges; loom: only 20 pre-agent merges; sigil: pre-agent history is the imported upstream project (another author), not this org's process; meld: only 11 pre-agent merges

## Seeded and triaged entries

| id | kind | status | change | net | why | countermeasure |
|---|---|---|---|---|---|---|
| INC-2026-10-001 | escape | closed | pulseengine.eu#303, claude-opus-5.5 | no-test (manual) | checker saw one translation unit, so MISRA 8.7 fired on every public function (manual) | fxm check-tasks: fixed caller TU per C task, caller drift check, 8.7 negative control |
| INC-2026-10-002 | escape | closed | pulseengine.eu#303, claude-opus-5.5 | no-test (manual) | reference passed on an include the shipped header did not give (manual) | fxm check-tasks: the reference with every include but the task header removed must pass; a potency probe must fail to compile |
| INC-2026-10-003 | near-miss | closed | pulseengine.eu#216, claude-opus-5 | vacuous-gate (manual) | gate could not fail: shallow clone (manual) | check-plugin-version-current.py refuses a shallow history (exit 2); CI fetches full history; claim PLUGIN-VERSION-GATE-FULL-HISTORY |
| INC-2026-10-004 | escape | open | smithy#45, claude-opus-5.5 (sweep found it) | merged-without-ci (manual) | merge path bypassed the required checks (--auto instead of the automerge label) (manual) | automerge label + merge-guard (smithy#36, #37). Detective, not preventive: it predates #45, raised the alarm, and did not stop the merge |
| INC-2026-10-005 | catch | closed | pulseengine.eu#298, claude-opus-5.5 (sweep found it) | wrong-system (manual) | ran on wrong system: PATH lookup found a stale tool (manual) | zola installed by path and sha256 into $RUNNER_TEMP, called only as "$ZOLA"; claim CI-ZOLA-PINNED-BY-PATH |
| INC-2026-10-006 | near-miss | open | synth, mixed | wrong-object (manual) | gate checks the wrong object: signing is enforced on main's squash commit, not on what was authored (manual) | none yet. Candidates: a PR check that every commit is verified and authored by an expected identity; fix the worktree identity at the source |

Seed recall (mechanically detectable seeds found by the sweep): 2/2

## Net-failure classes

Ledger entries of every kind (escape, near-miss, catch) by `net.class`, plus every untriaged mechanical escape as `unclassified (manual)` until someone fills fields 2 to 4. With this few triaged entries, the order among the triaged classes says nothing yet.

- unclassified (manual): 244
- no-test: 2
- vacuous-gate: 1
- merged-without-ci: 1
- wrong-system: 1
- wrong-object: 1

## Mechanical incidents

Fields 2 to 4 (net, why, countermeasure) are manual for every row without a ledger id. PR titles are not published here; follow the repo and PR number.

| repo | PR | sha | date | class | type | signals | ledger |
|---|---|---|---|---|---|---|---|
| covalent-layers | - | 7a8db83fb947 | 2026-09-24 | claude-opus-5 | non-conventional | main-red | untriaged |
| gale | #251 | 3d68c7d7f1dc | 2026-08-04 | claude-opus-5 | docs | pr-red | untriaged |
| gale | #250 | a9bbfbfb41c6 | 2026-08-05 | claude-unnamed | feat | hotfix-ref | untriaged |
| gale | #254 | 878a2ed272d4 | 2026-08-06 | claude-opus-5 | fix | main-red, hotfix-ref | untriaged |
| gale | #257 | 7609bba3dc43 | 2026-08-07 | claude-opus-5 | feat | pr-red | untriaged |
| gale | #258 | 8c05e55a805f | 2026-08-07 | claude-opus-5 | fix | pr-red | untriaged |
| gale | #259 | 90e5c4c23930 | 2026-08-08 | claude-opus-5 | other | pr-red | untriaged |
| gale | #263 | 45bfbc36dac4 | 2026-08-11 | claude-opus-5 | feat | main-red, main-red | untriaged |
| gale | #265 | 8df7e8ae87be | 2026-08-12 | claude-opus-5 | fix | pr-red | untriaged |
| gale | #268 | 22af8d5f69ce | 2026-08-12 | claude-opus-5 | chore | main-red | untriaged |
| gale | #274 | 54ff9ff6421e | 2026-08-13 | claude-opus-5 | docs | pr-red | untriaged |
| gale | #276 | e2d7595a3e96 | 2026-08-13 | claude-opus-5 | feat | pr-red | untriaged |
| gale | #281 | 3d1f3313a9c7 | 2026-08-26 | claude-opus-5 | docs | main-red | untriaged |
| gale | #283 | 52d00eb7da7c | 2026-08-26 | claude-opus-5 | feat | pr-red | untriaged |
| gale | #284 | fc224b6c986c | 2026-08-26 | claude-opus-5 | docs | pr-red | untriaged |
| gale | #292 | 828b22f83248 | 2026-08-26 | claude-opus-5 | other | pr-red | untriaged |
| gale | #295 | 51b9768edc04 | 2026-08-26 | claude-opus-5 | other | pr-red | untriaged |
| gale | #297 | f47046fd69bd | 2026-08-27 | claude-opus-5 | non-conventional | pr-red | untriaged |
| gale | #308 | 398cc3577a99 | 2026-08-27 | claude-opus-5 | fix | pr-red | untriaged |
| gale | #310 | 7ff6e7515a01 | 2026-08-28 | claude-opus-5 | fix | pr-red, hotfix-ref | untriaged |
| gale | #314 | e9d5b2ec5b0b | 2026-08-28 | claude-opus-5 | fix | main-red | untriaged |
| gale | #316 | e7b61d070be8 | 2026-09-01 | claude-opus-5 | fix | pr-red | untriaged |
| gale | #315 | 6bfd4cc0e4b7 | 2026-09-01 | claude-opus-5 | docs | pr-red | untriaged |
| gale | #321 | b88f69f059ef | 2026-09-02 | claude-opus-5 | ci | pr-red | untriaged |
| gale | #331 | 8a94210cb17b | 2026-09-03 | claude-opus-5 | chore | pr-red, hotfix-ref | untriaged |
| gale | #332 | 072a5a56c0c2 | 2026-09-03 | bot | chore | hotfix-ref | untriaged |
| gale | #338 | c4d908ead777 | 2026-09-04 | claude-opus-5 | ci | hotfix-ref | untriaged |
| gale | #339 | 0aa980abfc54 | 2026-09-04 | claude-opus-5 | other | hotfix-ref | untriaged |
| gale | #343 | 681c0dc0ce56 | 2026-09-04 | claude-opus-5 | ci | main-red | untriaged |
| gale | #349 | 6664df95ff22 | 2026-09-04 | claude-opus-5 | feat | pr-red | untriaged |
| gale | #352 | 6e44fa48177f | 2026-09-04 | claude-opus-5 | other | pr-red | untriaged |
| gale | #353 | 9919d5ae16fa | 2026-09-04 | claude-opus-5 | feat | pr-red | untriaged |
| gale | #363 | 1ce4a702093c | 2026-09-09 | claude-opus-5 | fix | hotfix-ref | untriaged |
| gale | #366 | fc90e49a41a8 | 2026-09-09 | claude-opus-5 | fix | hotfix-ref | untriaged |
| gale | #369 | 87b51353777c | 2026-09-09 | claude-opus-5 | fix | hotfix-ref | untriaged |
| gale | #370 | 26e30cfc02cc | 2026-09-10 | claude-opus-5 | fix | hotfix-ref | untriaged |
| gale | #367 | 6073115cf8f2 | 2026-09-10 | claude-opus-5 | fix | pr-red | untriaged |
| gale | #379 | eb6f1d69d233 | 2026-09-11 | claude-opus-5 | feat | main-red, main-red | untriaged |
| gale | #381 | 44abdf436e7d | 2026-09-11 | claude-opus-5 | feat | main-red | untriaged |
| gale | #385 | 4cf9a5af808d | 2026-09-16 | claude-opus-5 | fix | pr-red | untriaged |
| gale | #394 | 48fefa65ecb2 | 2026-09-17 | claude-opus-5 | fix | pr-red | untriaged |
| gale | #396 | 2a5c42d55c75 | 2026-09-17 | claude-opus-5 | feat | hotfix-ref | untriaged |
| gale | #404 | a643a98a2a9d | 2026-09-18 | claude-opus-5 | fix | pr-red | untriaged |
| gale | #405 | eb524371b6b6 | 2026-09-18 | claude-opus-5 | fix | pr-red | untriaged |
| gale | #406 | bd5e62692676 | 2026-09-18 | claude-opus-5 | feat | pr-red | untriaged |
| gale | #415 | aa488607c36d | 2026-09-23 | claude-opus-5 | feat | hotfix-ref | untriaged |
| gale | #416 | 2883219287f0 | 2026-09-23 | claude-opus-5 | feat | pr-red | untriaged |
| gale | #418 | 3e38783e0bc0 | 2026-09-30 | claude-opus-5 | ci | pr-red, hotfix-ref | untriaged |
| gale | #424 | 556b08cbfac0 | 2026-09-30 | claude-opus-5 | fix | pr-red | untriaged |
| gale | #423 | 44b739b4fa3c | 2026-09-30 | claude-opus-5 | other | pr-red | untriaged |
| gale | #425 | 0c4f089ba9d4 | 2026-09-30 | claude-opus-5 | docs | main-red | untriaged |
| gale | #426 | d2d9d81fc183 | 2026-10-01 | claude-opus-5 | feat | hotfix-ref | untriaged |
| gale | #432 | 0451acb36efb | 2026-10-02 | claude-opus-5 | feat | pr-red | untriaged |
| gale | #436 | 98e48ac71675 | 2026-10-06 | claude-opus-5 | fix | pr-red, hotfix-ref | untriaged |
| gale | #431 | 9fb8f5284ba5 | 2026-10-07 | claude-opus-5 | feat | pr-red | untriaged |
| gale | #443 | abe3dd256c26 | 2026-10-07 | claude-opus-5 | feat | pr-red, hotfix-ref | untriaged |
| gale | #445 | 0cc634b56526 | 2026-10-08 | claude-opus-5 | fix | pr-red | untriaged |
| gale | #446 | cb584fa2b3dd | 2026-10-08 | human-only | ci | main-red | untriaged |
| gale | #450 | 722fe6710f86 | 2026-10-22 | bot | chore | pr-red, hotfix-ref | untriaged |
| gale | #447 | 8de14ce846ab | 2026-10-22 | bot | chore | pr-red | untriaged |
| gale | #457 | 751d2adfc3e9 | 2026-10-22 | claude-opus-5.5 | fix | pr-red | untriaged |
| gale | #458 | f1d701ff06bf | 2026-10-22 | claude-opus-5.5 | feat | pr-red | untriaged |
| gale | #460 | 6687ea11ea6f | 2026-10-25 | claude-opus-5.5 | fix | pr-red | untriaged |
| gale | #455 | a097ff6899bd | 2026-10-28 | bot | chore | pr-red | untriaged |
| jess | #191 | 1777461e4f87 | 2026-08-28 | claude-opus-4.8 | other | pr-red | untriaged |
| jess | #197 | f55c0f03dfe3 | 2026-09-02 | claude-opus-4.8 | fix | hotfix-ref | untriaged |
| jess | #199 | 3cbfb8d3fc7e | 2026-09-02 | claude-opus-4.8 | other | pr-red | untriaged |
| jess | #200 | 4e513c228bf1 | 2026-09-02 | claude-opus-4.8 | other | hotfix-ref | untriaged |
| jess | #203 | a9a33b180d30 | 2026-09-02 | claude-opus-4.8 | other | pr-red | untriaged |
| jess | #218 | 91df1a40e68b | 2026-09-04 | claude-opus-4.8 | other | pr-red | untriaged |
| jess | #220 | 93be4d8f361e | 2026-09-04 | claude-opus-4.8 | other | pr-red | untriaged |
| jess | #227 | e9136a1932eb | 2026-09-05 | claude-opus-4.8 | fix | pr-red | untriaged |
| jess | #228 | 0312ec38c3cb | 2026-09-05 | claude-opus-4.8 | other | pr-red, hotfix-ref | untriaged |
| jess | #230 | 337b200b2894 | 2026-09-05 | claude-opus-4.8 | fix | pr-red | untriaged |
| jess | #231 | e9555c2cf3ff | 2026-09-05 | claude-opus-4.8 | other | pr-red | untriaged |
| jess | #240 | e0ad76563089 | 2026-09-05 | claude-opus-4.8 | fix | pr-red | untriaged |
| jess | #248 | e06dbf0a017f | 2026-09-06 | claude-opus-4.8 | other | pr-red | untriaged |
| jess | #255 | 6c15153ef46e | 2026-09-07 | claude-opus-4.8 | other | pr-red | untriaged |
| jess | #258 | 69636215d8e9 | 2026-09-08 | claude-opus-4.8 | fix | pr-red | untriaged |
| jess | #268 | 454229d03f47 | 2026-09-29 | claude-unnamed | non-conventional | pr-red | untriaged |
| jess | #270 | 3f9bc1305e8d | 2026-09-30 | claude-unnamed | non-conventional | pr-red | untriaged |
| jess | #271 | ae209eac4bed | 2026-09-30 | claude-unnamed | non-conventional | pr-red | untriaged |
| jess | #276 | e92aa992806e | 2026-10-01 | claude-unnamed | non-conventional | main-red | untriaged |
| jess | #281 | fc9a3a9fec08 | 2026-10-01 | claude-unnamed | non-conventional | pr-red | untriaged |
| jess | #282 | f2a6365a0240 | 2026-10-02 | claude-opus-5 | non-conventional | pr-red | untriaged |
| jess | #283 | 02230569daae | 2026-10-02 | claude-opus-5 | non-conventional | pr-red | untriaged |
| jess | #284 | ac704daac19a | 2026-10-02 | claude-opus-5 | non-conventional | pr-red | untriaged |
| jess | #289 | 84620d08950c | 2026-10-15 | claude-opus-5 | non-conventional | pr-red | untriaged |
| jess | #292 | d65a23957ffb | 2026-10-21 | human-only | non-conventional | pr-red | untriaged |
| jess | #293 | 9a2bcd50b387 | 2026-10-21 | human-only | non-conventional | pr-red | untriaged |
| jess | #294 | 816f2307445d | 2026-10-22 | human-only | non-conventional | pr-red | untriaged |
| jess | #303 | 1e30b94ee76a | 2026-10-28 | human-only | non-conventional | pr-red | untriaged |
| jess | #304 | b8104666ceb3 | 2026-10-28 | claude-opus-5.5 | non-conventional | main-red | untriaged |
| kiln | #525 | d846a313fe2e | 2026-10-14 | claude-opus-5.5 | feat | main-red | untriaged |
| kiln | #546 | d55ed87af6b9 | 2026-10-16 | claude-opus-5.5 | chore | pr-red, hotfix-ref | untriaged |
| kiln | #558 | d501ef91474a | 2026-10-21 | mixed | ci | pr-red | untriaged |
| kiln | #586 | 8cc4db65f6a5 | 2026-10-22 | mixed | fix | pr-red | untriaged |
| kiln | #595 | 65fe5ff693f1 | 2026-10-26 | mixed | ci | main-red, pr-red | untriaged |
| kiln | #606 | da174d718488 | 2026-10-29 | claude-opus-5.5 | chore | main-red | untriaged |
| kiln | #608 | 24d422298723 | 2026-10-29 | claude-opus-5.5 | fix | main-red | untriaged |
| loom | #310 | 65d72f98116f | 2026-08-05 | bot | chore | main-red | untriaged |
| loom | #318 | b71fd09d5630 | 2026-08-11 | bot | chore | main-red, hotfix-ref | untriaged |
| loom | #322 | e3a24d53deb7 | 2026-08-13 | human-only | feat | hotfix-ref | untriaged |
| loom | #349 | d628ef987db1 | 2026-08-25 | claude-opus-5 | fix | pr-red | untriaged |
| loom | #390 | b55357e44a36 | 2026-09-23 | bot | chore | main-red, main-red, hotfix-ref | untriaged |
| loom | #411 | 54406d76acec | 2026-10-08 | claude-opus-5 | fix | pr-red | untriaged |
| loom | #413 | b698037e201e | 2026-10-09 | claude-opus-5 | chore | pr-red | untriaged |
| loom | #364 | 60f6b75fd82b | 2026-10-09 | claude-opus-5 | feat | main-red | untriaged |
| loom | #414 | 8268c8feaf7e | 2026-10-14 | claude-opus-5 | feat | pr-red | untriaged |
| loom | #415 | 00287d1054da | 2026-10-15 | claude-opus-5 | feat | pr-red | untriaged |
| loom | #423 | c82e451a621c | 2026-10-15 | claude-opus-5 | fix | main-red | untriaged |
| loom | #424 | 9c2350d00461 | 2026-10-15 | claude-opus-5 | feat | main-red, pr-red | untriaged |
| loom | #425 | 3e8ebb8dc07a | 2026-10-15 | claude-opus-5 | feat | pr-red | untriaged |
| loom | #428 | 32b8f82433d8 | 2026-10-16 | human-only | ci | hotfix-ref | untriaged |
| loom | #430 | 5aa11b479d8c | 2026-10-22 | claude-opus-5.5 | chore | pr-red | untriaged |
| loom | #435 | 598a4f9efd76 | 2026-10-22 | claude-opus-5.5 | feat | pr-red | untriaged |
| loom | #431 | 63b7c71ed316 | 2026-10-23 | claude-opus-5.5 | fix | pr-red | untriaged |
| loom | #434 | 83850b6fe4c2 | 2026-10-23 | claude-opus-5.5 | feat | main-red | untriaged |
| mcp | #117 | 2cdf04ee25a7 | 2026-08-07 | bot | chore | main-red | untriaged |
| mcp | #142 | 431a1ff7172b | 2026-10-04 | bot | chore | main-red | untriaged |
| meld | #372 | 8cd6254a20f1 | 2026-08-12 | claude-opus-4.8 | feat | pr-red | untriaged |
| meld | #381 | f0eaf3e9b567 | 2026-08-14 | claude-opus-4.8 | feat | pr-red | untriaged |
| meld | #384 | 4ed2f9a826db | 2026-08-14 | claude-opus-4.8 | feat | pr-red | untriaged |
| meld | #387 | 4a63a55844b8 | 2026-08-19 | claude-opus-4.8 | feat | pr-red | untriaged |
| meld | #389 | c6e51a3ac02a | 2026-08-20 | claude-opus-4.8 | feat | pr-red | untriaged |
| meld | #392 | 5e4593b9cacb | 2026-09-02 | human-only | fix | pr-red | untriaged |
| meld | #394 | 7dc538c532e8 | 2026-09-03 | human-only | ci | pr-red | untriaged |
| meld | #396 | 56df80b452bd | 2026-09-05 | human-only | fix | pr-red | untriaged |
| meld | #403 | 65c9eae94aed | 2026-09-09 | human-only | test | pr-red | untriaged |
| meld | #416 | 2b8a11453347 | 2026-09-16 | human-only | fix | pr-red | untriaged |
| meld | #424 | f97fc40a2278 | 2026-09-18 | claude-opus-5 | feat | pr-red | untriaged |
| meld | #434 | 31053ea2c5b7 | 2026-09-23 | claude-opus-5 | feat | pr-red | untriaged |
| meld | #437 | a76aea3c82ae | 2026-09-24 | claude-opus-5 | fix | pr-red | untriaged |
| meld | #439 | a219cb1cfb20 | 2026-09-30 | claude-opus-5 | feat | pr-red | untriaged |
| meld | #448 | 289c4a610f1c | 2026-10-07 | human-only | feat | pr-red | untriaged |
| meld | #453 | da4af5239416 | 2026-10-07 | claude-unnamed | fix | hotfix-ref | untriaged |
| meld | #452 | cb3f3d02449c | 2026-10-07 | claude-unnamed | feat | pr-red, hotfix-ref | untriaged |
| meld | #456 | 19fc1eefb785 | 2026-10-08 | claude-unnamed | feat | pr-red | untriaged |
| meld | #460 | 291a123980d0 | 2026-10-08 | claude-unnamed | fix | pr-red | untriaged |
| meld | #464 | c4f17c6215bb | 2026-10-13 | claude-unnamed | fix | main-red, pr-red, hotfix-ref | untriaged |
| meld | #466 | c5f703e12bc3 | 2026-10-13 | claude-opus-5 | fix | pr-red, hotfix-ref | untriaged |
| meld | #471 | c3955eef9f6e | 2026-10-14 | claude-opus-5.5 | feat | pr-red | untriaged |
| meld | #468 | 2221f19902e2 | 2026-10-14 | claude-opus-5.5 | fix | main-red, pr-red | untriaged |
| meld | #480 | 9926d478c3ff | 2026-10-15 | claude-opus-5.5 | test | pr-red | untriaged |
| meld | #477 | 27b04fa59d08 | 2026-10-15 | mixed | fix | pr-red | untriaged |
| meld | #487 | 5eb152bea56c | 2026-10-15 | mixed | fix | pr-red | untriaged |
| meld | #490 | 21ace1612273 | 2026-10-15 | mixed | fix | pr-red | untriaged |
| meld | #498 | e2759bee733e | 2026-10-21 | mixed | feat | pr-red | untriaged |
| meld | #502 | 234343ce627f | 2026-10-21 | claude-opus-5.5 | chore | pr-red | untriaged |
| meld | #503 | 02fdab097517 | 2026-10-21 | mixed | fix | pr-red | untriaged |
| meld | #505 | 98f8e90d4348 | 2026-10-21 | mixed | test | pr-red | untriaged |
| meld | #507 | b26f1c80ae6e | 2026-10-21 | claude-opus-5.5 | other | pr-red | untriaged |
| meld | #510 | 30545b3ed6ab | 2026-10-22 | mixed | fix | pr-red | untriaged |
| meld | #518 | 45ff59d47546 | 2026-10-22 | mixed | feat | pr-red | untriaged |
| meld | #524 | 4843198e9f95 | 2026-10-22 | claude-opus-5.5 | fix | pr-red | untriaged |
| meld | #532 | 3def63b0ba21 | 2026-10-28 | claude-opus-5.5 | feat | pr-red | untriaged |
| ordeal | #125 | 8f25fd639725 | 2026-08-20 | claude-opus-4.8 | chore | hotfix-ref | untriaged |
| ordeal | #126 | d4248fcff2df | 2026-08-20 | claude-opus-4.8 | fix | hotfix-ref | untriaged |
| ordeal | #134 | a57beba4e300 | 2026-09-03 | claude-opus-4.8 | feat | main-red | untriaged |
| ordeal | #145 | e295b11b988e | 2026-09-23 | claude-fable-5 | feat | pr-red | untriaged |
| ordeal | #155 | 4e5dfc2f2920 | 2026-09-23 | claude-fable-5 | docs | pr-red | untriaged |
| ordeal | #156 | 410662086166 | 2026-09-23 | claude-fable-5 | feat | pr-red | untriaged |
| ordeal | #157 | cd012ccabed2 | 2026-09-23 | claude-opus-5.5 | chore | pr-red | untriaged |
| ordeal | #164 | 7b17dd433265 | 2026-09-24 | claude-fable-5.1 | feat | pr-red | untriaged |
| ordeal | #183 | 981f6a6ba771 | 2026-09-30 | claude-opus-5.5 | fix | hotfix-ref | untriaged |
| ordeal | #206 | 33a06cee999a | 2026-09-30 | claude-opus-5.5 | chore | main-red | untriaged |
| ordeal | #233 | 9a75d8e24d36 | 2026-10-14 | claude-opus-5.5 | feat | pr-red | untriaged |
| ordeal | #237 | 01d7335fa045 | 2026-10-15 | bot | chore | pr-red | untriaged |
| ordeal | #242 | c197a66b1fe1 | 2026-10-15 | mixed | other | pr-red | untriaged |
| ordeal | #251 | d65493fbbb10 | 2026-10-21 | mixed | feat | pr-red | untriaged |
| pulseengine-layers | #17 | 733371b876b9 | 2026-09-18 | claude-opus-5 | non-conventional | pr-red | untriaged |
| pulseengine-layers | #36 | e8db88217707 | 2026-10-29 | claude-opus-5.5 | ci | pr-red | untriaged |
| pulseengine.eu | #142 | d6035c108585 | 2026-08-06 | bot | non-conventional | pr-red | untriaged |
| pulseengine.eu | #152 | ba1d08025f98 | 2026-08-06 | claude-opus-4.8 | fix | hotfix-ref | untriaged |
| pulseengine.eu | #166 | 8e28ca60cbb9 | 2026-08-26 | claude-opus-5 | other | pr-red | untriaged |
| pulseengine.eu | #169 | 679a18503307 | 2026-08-26 | claude-opus-5 | chore | hotfix-ref | untriaged |
| pulseengine.eu | #192 | 8b1ff6c146ee | 2026-09-06 | claude-opus-5 | feat | hotfix-ref | untriaged |
| pulseengine.eu | #207 | 0927d06ce290 | 2026-09-30 | claude-opus-5 | non-conventional | hotfix-ref | untriaged |
| pulseengine.eu | #216 | 5baf97a255e8 | 2026-10-02 | claude-opus-5 | non-conventional | pr-red | INC-2026-10-003 |
| pulseengine.eu | #218 | 0fbb3e1b9ca9 | 2026-10-02 | human-only | feat | main-red | untriaged |
| pulseengine.eu | #223 | b25f3b2b1e42 | 2026-10-14 | claude-opus-5 | non-conventional | pr-red | untriaged |
| pulseengine.eu | #235 | 5443e13598f9 | 2026-10-21 | claude-opus-5.5 | other | main-red | untriaged |
| pulseengine.eu | #239 | de665ee4d650 | 2026-10-21 | claude-opus-5.5 | fix | main-red | untriaged |
| pulseengine.eu | #241 | 691e2a182554 | 2026-10-21 | claude-opus-5.5 | chore | main-red | untriaged |
| pulseengine.eu | #248 | 5ecefb6825b4 | 2026-10-25 | human-only | non-conventional | pr-red | untriaged |
| pulseengine.eu | #267 | 4d29b8209689 | 2026-10-28 | claude-opus-5.5 | fix | hotfix-ref | untriaged |
| pulseengine.eu | #277 | 8ca783dac5bb | 2026-10-28 | claude-opus-5.5 | feat | pr-red | untriaged |
| pulseengine.eu | #299 | c07fa5dcfb72 | 2026-10-29 | claude-opus-5.5 | ci | pr-red | untriaged |
| pulseengine.eu | #303 | 730ae22b14f4 | 2026-10-29 | claude-opus-5.5 | feat | ledger, ledger | INC-2026-10-001, INC-2026-10-002 |
| pulseengine.eu | #298 | bb4fc555b67d | 2026-10-29 | claude-opus-5.5 | feat | mq-ejected | INC-2026-10-005 |
| pulseengine.eu | #309 | 3c533074a890 | 2026-10-29 | claude-opus-5.5 | feat | pr-red | untriaged |
| pulseengine.eu | #310 | 9928716074c6 | 2026-10-29 | claude-opus-5.5 | ci | pr-red | untriaged |
| pulseengine.eu | #318 | 09b2e18181c0 | 2026-10-29 | claude-opus-5.5 | docs | pr-red | untriaged |
| relay | #329 | 0cd285a20608 | 2026-08-05 | claude-fable-5 | feat | hotfix-ref | untriaged |
| relay | #331 | feb89f436dca | 2026-08-05 | claude-fable-5 | other | main-red, pr-red | untriaged |
| relay | #338 | 57895007bea6 | 2026-08-07 | mixed | feat | pr-red | untriaged |
| relay | #337 | 41fb72ff707e | 2026-08-07 | mixed | feat | pr-red | untriaged |
| relay | #317 | 49fed82c3ee0 | 2026-08-07 | bot | build | main-red | untriaged |
| relay | #344 | 14dde184953d | 2026-08-11 | claude-opus-5 | feat | pr-red | untriaged |
| relay | #347 | 0a60d689d2d0 | 2026-08-11 | claude-opus-5 | other | pr-red | untriaged |
| relay | #366 | b777ba98d27e | 2026-08-26 | claude-opus-5 | feat | main-red, pr-red, hotfix-ref | untriaged |
| relay | #342 | cf19c79f467e | 2026-09-02 | claude-opus-5 | fix | main-red, pr-red, hotfix-ref | untriaged |
| relay | #375 | 34cc0fd6daf4 | 2026-09-02 | claude-opus-5 | feat | main-red, pr-red, hotfix-ref | untriaged |
| relay | #386 | ab2e7bbedd18 | 2026-09-10 | claude-opus-5 | feat | pr-red | untriaged |
| relay | #381 | 99f65d057e67 | 2026-09-10 | claude-opus-5 | feat | main-red, pr-red | untriaged |
| relay | #377 | 0bd85c2c8702 | 2026-09-10 | claude-opus-5 | fix | pr-red | untriaged |
| relay | #387 | 2e7d4d1f9412 | 2026-09-11 | claude-opus-5 | feat | pr-red | untriaged |
| relay | #391 | b66588e7689d | 2026-09-11 | claude-opus-5 | feat | pr-red | untriaged |
| relay | #365 | 519d531af7bf | 2026-09-11 | claude-opus-5 | other | pr-red | untriaged |
| relay | #390 | 8ed126a7c533 | 2026-09-11 | claude-opus-5 | feat | pr-red | untriaged |
| relay | #343 | d6b17af85521 | 2026-09-11 | claude-opus-5 | perf | pr-red | untriaged |
| relay | #393 | f03514f58779 | 2026-09-11 | claude-opus-5 | feat | main-red, main-red, hotfix-ref | untriaged |
| relay | #392 | 69ed42ccd1cd | 2026-09-11 | claude-opus-5 | feat | pr-red | untriaged |
| relay | #394 | 39f802cd3cd6 | 2026-09-13 | claude-opus-5 | other | pr-red | untriaged |
| relay | #404 | 283224d86e10 | 2026-09-15 | claude-opus-5 | fix | pr-red, hotfix-ref | untriaged |
| relay | #406 | 131cd6f2e267 | 2026-09-16 | claude-opus-5 | other | main-red, hotfix-ref | untriaged |
| relay | #420 | b727d93901da | 2026-09-16 | claude-opus-5 | other | pr-red | untriaged |
| relay | #408 | 31cbb2abd455 | 2026-09-16 | claude-opus-5 | fix | pr-red | untriaged |
| relay | #423 | 1dfe4cf1d8fc | 2026-09-16 | claude-opus-5 | feat | hotfix-ref | untriaged |
| relay | #421 | 8d53dd266ea5 | 2026-09-16 | claude-opus-5 | other | pr-red | untriaged |
| relay | #426 | 6f032e44459c | 2026-09-16 | claude-opus-5 | fix | hotfix-ref | untriaged |
| relay | #431 | 3ec4a2f243fd | 2026-09-16 | claude-opus-5 | other | hotfix-ref | untriaged |
| relay | #430 | a1b0e17412c6 | 2026-09-16 | claude-opus-5 | fix | pr-red, hotfix-ref | untriaged |
| relay | #424 | 4c5feda222b1 | 2026-09-17 | claude-opus-5 | fix | hotfix-ref | untriaged |
| relay | #432 | 7daf818daa4f | 2026-09-17 | claude-opus-5 | fix | pr-red, hotfix-ref | untriaged |
| relay | #433 | 572ae38d665a | 2026-09-17 | claude-opus-5 | fix | hotfix-ref | untriaged |
| relay | #438 | 9eacd4aa0082 | 2026-09-17 | claude-opus-5 | other | pr-red | untriaged |
| relay | #441 | 3df545c01a5e | 2026-09-17 | claude-opus-5 | fix | main-red, hotfix-ref | untriaged |
| relay | #442 | 16a0d70d2ffb | 2026-09-17 | claude-opus-5 | fix | hotfix-ref | untriaged |
| relay | #444 | 3ba320d37828 | 2026-09-17 | claude-opus-5 | fix | pr-red | untriaged |
| relay | #446 | 18642cbca20c | 2026-09-17 | claude-opus-5 | docs | pr-red | untriaged |
| relay | #402 | a8f6cf77f02e | 2026-09-17 | bot | build | pr-red | untriaged |
| relay | #368 | c56e88bf6d4d | 2026-09-17 | bot | build | pr-red | untriaged |
| relay | #454 | bf70948fa24d | 2026-09-17 | claude-opus-5 | docs | pr-red | untriaged |
| relay | #399 | 9f1df806f823 | 2026-09-17 | bot | build | pr-red | untriaged |
| relay | #460 | f9ea4469d05e | 2026-09-18 | claude-opus-5 | fix | hotfix-ref | untriaged |
| relay | #461 | 5b365f78d07f | 2026-09-18 | claude-opus-5 | other | pr-red, hotfix-ref | untriaged |
| relay | #463 | 0c69dd216bd0 | 2026-09-18 | claude-opus-5 | fix | main-red | untriaged |
| relay | #456 | 0185e8a06558 | 2026-09-18 | claude-opus-5 | fix | main-red, pr-red | untriaged |
| relay | #468 | 0fbebc947fe0 | 2026-09-18 | claude-opus-5 | other | pr-red | untriaged |
| relay | #471 | 68e19e814f01 | 2026-09-22 | bot | build | pr-red | untriaged |
| relay | #473 | b6584a815820 | 2026-09-22 | claude-opus-5 | docs | pr-red | untriaged |
| relay | #474 | eb7ef210ec77 | 2026-09-23 | claude-opus-5 | fix | main-red | untriaged |
| relay | #478 | 0bfd5f2aa02a | 2026-09-23 | claude-opus-5 | other | pr-red | untriaged |
| relay | #480 | bf270717860b | 2026-09-24 | claude-opus-5 | non-conventional | main-red, main-red, pr-red, hotfix-ref | untriaged |
| relay | #488 | c709a72b3300 | 2026-09-25 | claude-opus-5 | fix | pr-red | untriaged |
| relay | #487 | 279b0c5ad961 | 2026-09-25 | claude-opus-5 | fix | main-red, pr-red, hotfix-ref | untriaged |
| relay | #489 | b33d17489006 | 2026-09-25 | claude-opus-5 | other | pr-red | untriaged |
| relay | #493 | f8a743653504 | 2026-09-30 | claude-opus-5 | feat | pr-red | untriaged |
| relay | #495 | 1c782b243e92 | 2026-10-01 | claude-opus-5 | other | hotfix-ref | untriaged |
| relay | #496 | 83e53e8326ac | 2026-10-01 | claude-opus-5 | other | main-red, pr-red | untriaged |
| relay | #498 | 3fcfb6495979 | 2026-10-01 | claude-opus-5 | other | main-red, hotfix-ref | untriaged |
| relay | #500 | 17c92c3cb00b | 2026-10-01 | claude-opus-5 | other | pr-red | untriaged |
| relay | #502 | 6a375326e422 | 2026-10-01 | claude-opus-5 | test | pr-red | untriaged |
| relay | #506 | ccef50cf96b3 | 2026-10-01 | claude-opus-5 | other | main-red, pr-red | untriaged |
| relay | #504 | 5e07c9d79bef | 2026-10-01 | claude-opus-5 | feat | pr-red | untriaged |
| relay | #510 | c7472e41f8a0 | 2026-10-01 | claude-opus-5 | other | pr-red | untriaged |
| relay | #511 | d967046048a4 | 2026-10-01 | claude-opus-5 | feat | hotfix-ref | untriaged |
| relay | #512 | c45a4d70bc18 | 2026-10-01 | claude-opus-5 | fix | main-red | untriaged |
| relay | #507 | d2913eb82072 | 2026-10-02 | claude-opus-5 | fix | main-red, pr-red, hotfix-ref | untriaged |
| relay | #513 | 65cdbf958aa0 | 2026-10-02 | claude-opus-5 | test | pr-red | untriaged |
| relay | #518 | 5b9d244612db | 2026-10-06 | claude-opus-5 | feat | hotfix-ref | untriaged |
| relay | #501 | 30dae4a8ffa4 | 2026-10-07 | claude-opus-5 | test | pr-red | untriaged |
| relay | #515 | 1bab54f5b72b | 2026-10-07 | claude-opus-5 | feat | pr-red | untriaged |
| relay | #517 | 27d0fa9876c1 | 2026-10-07 | claude-opus-5 | feat | pr-red | untriaged |
| relay | #522 | c9f75799bf42 | 2026-10-07 | claude-opus-5 | feat | hotfix-ref | untriaged |
| relay | #524 | 119733aaf525 | 2026-10-07 | claude-opus-5 | feat | main-red, pr-red | untriaged |
| relay | #525 | 21e9b864221e | 2026-10-07 | claude-opus-5 | feat | pr-red | untriaged |
| relay | #528 | 1b4dc1b34088 | 2026-10-07 | claude-opus-5 | other | hotfix-ref | untriaged |
| relay | #526 | 3cce080195bc | 2026-10-08 | claude-opus-5 | other | pr-red | untriaged |
| relay | #532 | 49ee0a5262ff | 2026-10-08 | claude-opus-5 | other | main-red | untriaged |
| relay | #534 | 9e1c50680f7d | 2026-10-08 | claude-opus-5 | other | pr-red | untriaged |
| relay | #536 | f6f45b140cbe | 2026-10-08 | claude-opus-5 | other | pr-red | untriaged |
| relay | #540 | 2df2b5359f0b | 2026-10-09 | claude-opus-5 | fix | pr-red | untriaged |
| relay | #538 | 409afe549aae | 2026-10-09 | claude-opus-5 | other | pr-red | untriaged |
| relay | #539 | cdf3b74e7bfa | 2026-10-09 | claude-opus-5 | fix | pr-red | untriaged |
| relay | #541 | 81fb954b83a7 | 2026-10-09 | claude-opus-5 | feat | pr-red | untriaged |
| relay | #543 | 63bdbde3fb68 | 2026-10-09 | claude-opus-5 | other | pr-red, hotfix-ref | untriaged |
| relay | #547 | efc0dbf0ff04 | 2026-10-09 | claude-opus-5 | docs | hotfix-ref | untriaged |
| relay | #550 | b1acf3efe21f | 2026-10-09 | claude-opus-5 | other | pr-red | untriaged |
| relay | #551 | c2ed8bf60f63 | 2026-10-09 | claude-opus-5 | fix | pr-red | untriaged |
| relay | #557 | 2797e7b7035d | 2026-10-10 | claude-opus-5 | feat | hotfix-ref | untriaged |
| relay | #559 | 7f96f70163d8 | 2026-10-13 | claude-opus-5 | fix | hotfix-ref | untriaged |
| relay | #560 | d756c96ec48c | 2026-10-13 | claude-opus-5 | fix | main-red | untriaged |
| relay | #563 | 8179ffebc98e | 2026-10-14 | claude-opus-5 | fix | main-red | untriaged |
| relay | #568 | 89f83087f382 | 2026-10-14 | bot | build | main-red | untriaged |
| relay | #565 | 6367cd728091 | 2026-10-15 | claude-opus-5 | fix | pr-red, hotfix-ref | untriaged |
| relay | #567 | 985114b7a315 | 2026-10-21 | bot | build | main-red, pr-red | untriaged |
| relay | #577 | b1928a7cfc59 | 2026-10-21 | bot | build | pr-red | untriaged |
| relay | #581 | 7c3b283fb86e | 2026-10-21 | claude-opus-5.5 | other | pr-red | untriaged |
| relay | #588 | 588f68004192 | 2026-10-22 | claude-opus-5.5 | ci | pr-red | untriaged |
| relay | #578 | 9be9b579c3a7 | 2026-10-22 | bot | build | pr-red | untriaged |
| relay | #595 | 86239acd831a | 2026-10-22 | claude-opus-5.5 | fix | mq-ejected | untriaged |
| relay | #600 | 0a7e0cdbf795 | 2026-10-22 | claude-opus-5.5 | ci | pr-red | untriaged |
| relay | #571 | 090cfaf91326 | 2026-10-22 | mixed | feat | pr-red, mq-ejected | untriaged |
| relay | #612 | c4672cc91de2 | 2026-10-28 | claude-opus-5.5 | fix | hotfix-ref | untriaged |
| relay | #614 | fe817078cc01 | 2026-10-28 | claude-opus-5.5 | feat | hotfix-ref | untriaged |
| relay | #611 | 34819cf10b62 | 2026-10-29 | claude-opus-5.5 | fix | mq-ejected | untriaged |
| relay | #620 | 8cb289500d32 | 2026-10-29 | claude-opus-5.5 | ci | pr-red | untriaged |
| rivet | #757 | 71c7a848c40a | 2026-08-04 | human-only | fix | main-red | untriaged |
| rivet | #772 | f5592c6fba83 | 2026-08-05 | human-only | other | main-red | untriaged |
| rivet | #776 | 0d42ce1cf802 | 2026-08-06 | claude-unnamed | ci | hotfix-ref | untriaged |
| rivet | #773 | ebf08dbb045c | 2026-08-06 | human-only | ci | hotfix-ref | untriaged |
| rivet | #779 | bcee66720450 | 2026-08-07 | human-only | fix | hotfix-ref | untriaged |
| rivet | #795 | e74e6d58ef48 | 2026-08-18 | human-only | fix | pr-red | untriaged |
| rivet | #814 | 8bdae7d40663 | 2026-08-19 | claude-unnamed | chore | pr-red | untriaged |
| rivet | #830 | ebd253ad5540 | 2026-08-20 | human-only | fix | pr-red | untriaged |
| rivet | #759 | 562a3eb293ca | 2026-08-20 | human-only | fix | pr-red | untriaged |
| rivet | #813 | 3e77beae8db8 | 2026-08-20 | human-only | feat | main-red | untriaged |
| rivet | #843 | 36f2cd76edaf | 2026-08-26 | human-only | feat | pr-red | untriaged |
| rivet | #850 | b2b155cb1ef9 | 2026-08-26 | human-only | fix | hotfix-ref | untriaged |
| rivet | #855 | 9d1a87fb905c | 2026-08-26 | human-only | ci | hotfix-ref | untriaged |
| rivet | #859 | 99f3b8bda987 | 2026-08-27 | human-only | fix | pr-red | untriaged |
| rivet | #861 | 83c7d9199782 | 2026-08-27 | human-only | feat | pr-red | untriaged |
| rivet | #865 | fa387cc6fc79 | 2026-08-27 | human-only | fix | pr-red | untriaged |
| rivet | #864 | 679d61229c92 | 2026-08-27 | human-only | fix | pr-red | untriaged |
| rivet | #866 | fe18f29d8c8d | 2026-08-27 | human-only | other | pr-red | untriaged |
| rivet | #868 | 4ff980e07986 | 2026-08-28 | human-only | chore | pr-red | untriaged |
| rivet | #872 | 6254d59e7996 | 2026-09-01 | human-only | fix | main-red, pr-red | untriaged |
| rivet | #877 | 0111085d26b2 | 2026-09-02 | human-only | fix | pr-red | untriaged |
| rivet | #888 | aab7cd34fe16 | 2026-09-04 | human-only | feat | hotfix-ref | untriaged |
| rivet | #889 | 16bff52cf26e | 2026-09-05 | human-only | fix | pr-red | untriaged |
| rivet | #893 | 6778c545b26f | 2026-09-05 | human-only | feat | hotfix-ref | untriaged |
| rivet | #899 | d61b58042df0 | 2026-09-07 | human-only | feat | hotfix-ref | untriaged |
| rivet | #900 | a80ca3a3948b | 2026-09-08 | human-only | other | main-red | untriaged |
| rivet | #903 | e162eeae78d2 | 2026-09-08 | human-only | fix | pr-red | untriaged |
| rivet | #936 | 7e1aae992385 | 2026-09-11 | human-only | fix | pr-red | untriaged |
| rivet | #938 | 29cc3d26ebfe | 2026-09-11 | human-only | test | pr-red | untriaged |
| rivet | #941 | f8aa6c7fe1af | 2026-09-11 | human-only | fix | pr-red | untriaged |
| rivet | #943 | 8e4cbf406913 | 2026-09-15 | human-only | feat | main-red | untriaged |
| rivet | #970 | 218a95086474 | 2026-09-17 | claude-opus-5 | fix | pr-red | untriaged |
| rivet | #974 | bf9d15b9373e | 2026-09-23 | claude-opus-5 | fix | pr-red | untriaged |
| rivet | #987 | 29302a917204 | 2026-09-23 | claude-opus-5 | other | pr-red | untriaged |
| rivet | #993 | a910146115cb | 2026-09-24 | claude-opus-5 | feat | pr-red | untriaged |
| rivet | #991 | 4de6e01897fc | 2026-09-24 | human-only | feat | pr-red | untriaged |
| rivet | #994 | ce820fb64d47 | 2026-09-24 | human-only | non-conventional | pr-red | untriaged |
| rivet | #996 | 20db2158ab3b | 2026-09-24 | human-only | non-conventional | pr-red | untriaged |
| rivet | #997 | 1344ca1c3193 | 2026-09-25 | human-only | non-conventional | pr-red | untriaged |
| rivet | #998 | 240235ac03ed | 2026-09-25 | human-only | other | pr-red | untriaged |
| rivet | #999 | 83231d58dad9 | 2026-09-25 | human-only | feat | pr-red | untriaged |
| rivet | #1000 | 32fc25d53bf2 | 2026-09-25 | human-only | other | pr-red | untriaged |
| rivet | #1005 | da945d30f319 | 2026-09-29 | claude-opus-5.5 | feat | main-red | untriaged |
| rivet | #1007 | 369a31c00029 | 2026-09-29 | claude-opus-5.5 | chore | pr-red | untriaged |
| rivet | #1011 | a7c58cd52560 | 2026-09-30 | claude-opus-5.5 | fix | pr-red | untriaged |
| rivet | #1013 | 21242f8f44ff | 2026-09-30 | claude-opus-5.5 | test | pr-red | untriaged |
| rivet | #1014 | 5716232227a0 | 2026-09-30 | claude-opus-5.5 | fix | pr-red | untriaged |
| rivet | #1016 | d2c7c372274c | 2026-09-30 | claude-opus-5.5 | fix | pr-red | untriaged |
| rivet | #1020 | f9d35da8bb2b | 2026-09-30 | claude-opus-5.5 | non-conventional | main-red, pr-red | untriaged |
| rivet | #1019 | e5bfb90bac85 | 2026-10-01 | claude-opus-5.5 | fix | pr-red | untriaged |
| rivet | #1024 | 6e72dd7866cd | 2026-10-01 | claude-opus-5.5 | feat | main-red | untriaged |
| rivet | #1041 | 5737b85e1e01 | 2026-10-07 | claude-opus-5.5 | ci | main-red | untriaged |
| rivet | #1060 | 223f66c361b6 | 2026-10-09 | claude-opus-5.5 | fix | pr-red | untriaged |
| rivet | #1079 | 94931878c4dc | 2026-10-10 | claude-opus-5.5 | ci | main-red | untriaged |
| rivet | #1080 | 81dfc308e31a | 2026-10-10 | claude-opus-5.5 | fix | pr-red | untriaged |
| rivet | #1085 | 734cad014bea | 2026-10-14 | claude-opus-5.5 | feat | main-red, pr-red | untriaged |
| rivet | #1082 | 27c8c334e177 | 2026-10-15 | claude-opus-5.5 | test | main-red | untriaged |
| rivet | #1108 | cc3b8075446c | 2026-10-21 | claude-opus-5.5 | chore | main-red, pr-red | untriaged |
| rivet | #1111 | 9e6fb60bc0b3 | 2026-10-22 | claude-opus-5.5 | fix | pr-red | untriaged |
| rivet | #1123 | b0a75147693b | 2026-10-25 | claude-sonnet-5.5 | feat | pr-red | untriaged |
| rules_ordeal | #16 | 9b9766b90b2e | 2026-10-02 | claude-opus-5.5 | chore | main-red | untriaged |
| rules_wasm_component | #654 | 1725deb20aad | 2026-09-16 | bot | docs | main-red, main-red, hotfix-ref | untriaged |
| rules_wasm_component | #659 | 7fb790a085b5 | 2026-09-21 | bot | non-conventional | main-red | untriaged |
| rules_wasm_component | #635 | 530ea2d4861c | 2026-09-29 | mixed | feat | pr-red, hotfix-ref | untriaged |
| rules_wasm_component | #670 | 2271c9d4143d | 2026-10-08 | bot | ci | main-red | untriaged |
| rules_wasm_component | #678 | f20a23df8204 | 2026-10-14 | claude-sonnet-5 | fix | pr-red, hotfix-ref | untriaged |
| rules_wasm_component | #627 | d130fc9d9723 | 2026-10-25 | claude-opus-4.8 | feat | main-red | untriaged |
| rules_wasm_component | #703 | 54ed0635de7b | 2026-10-29 | claude-opus-5.5 | ci | pr-red | untriaged |
| scry | #115 | 524b3e0b5d8d | 2026-08-07 | claude-opus-4.8 | non-conventional | pr-red | untriaged |
| scry | #124 | dbb6892453d9 | 2026-08-21 | claude-opus-5 | non-conventional | pr-red | untriaged |
| scry | #127 | 25694bb165a2 | 2026-08-21 | claude-opus-5 | non-conventional | pr-red | untriaged |
| scry | #129 | 9e8783da0b61 | 2026-08-21 | claude-opus-5 | non-conventional | pr-red | untriaged |
| scry | #162 | 265725edf6ac | 2026-08-27 | claude-opus-5 | non-conventional | pr-red | untriaged |
| scry | #167 | b877f45537ec | 2026-08-27 | claude-opus-5 | non-conventional | main-red, pr-red | untriaged |
| scry | #170 | 8b53ec213838 | 2026-08-27 | claude-opus-5 | non-conventional | pr-red | untriaged |
| scry | #194 | 35cf3167ce5e | 2026-08-28 | claude-opus-5 | non-conventional | pr-red | untriaged |
| scry | #196 | d0a9b83076c1 | 2026-09-01 | claude-opus-5 | non-conventional | pr-red | untriaged |
| scry | #199 | 9de06694ea76 | 2026-09-01 | claude-opus-5 | non-conventional | pr-red | untriaged |
| scry | #222 | 7c22ab65cf60 | 2026-10-03 | claude-opus-5 | non-conventional | main-red | untriaged |
| scry | #225 | 66e75abfc218 | 2026-10-26 | mixed | non-conventional | pr-red | untriaged |
| sigil | #211 | e131fdf9ba40 | 2026-08-04 | bot | chore | main-red | untriaged |
| sigil | #213 | 2607571b3871 | 2026-08-05 | claude-opus-4.8 | fix | main-red | untriaged |
| sigil | #215 | 71d17eb73482 | 2026-08-05 | claude-opus-4.8 | other | main-red, pr-red | untriaged |
| sigil | #222 | 2e3c97a31d89 | 2026-08-07 | claude-opus-4.8 | other | pr-red | untriaged |
| sigil | #228 | 94f9b024a200 | 2026-08-07 | claude-opus-4.8 | other | main-red | untriaged |
| sigil | #232 | 2b5d3a611910 | 2026-08-11 | claude-opus-4.8 | feat | pr-red | untriaged |
| sigil | #271 | 476110c43d70 | 2026-09-01 | bot | chore | main-red | untriaged |
| sigil | #281 | c8ab9a11c8f6 | 2026-09-29 | bot | chore | hotfix-ref | untriaged |
| sigil | #273 | 2ed3344c4b4a | 2026-09-30 | mixed | fix | pr-red | untriaged |
| sigil | #199 | 1748d57cf795 | 2026-10-03 | bot | chore | main-red | untriaged |
| sigil | #306 | 58f58342e875 | 2026-10-14 | bot | chore | main-red | untriaged |
| sigil | #313 | 15bdd6ab4dca | 2026-10-21 | mixed | non-conventional | main-red, pr-red | untriaged |
| sigil | #321 | 59a6edbfff76 | 2026-10-27 | bot | chore | main-red | untriaged |
| sigil | #323 | 7cb4bad28dd1 | 2026-10-27 | bot | chore | main-red | untriaged |
| sigil | #329 | 37ff4a459c01 | 2026-10-27 | bot | chore | main-red, main-red | untriaged |
| sigil | #333 | a8082434ea73 | 2026-10-28 | claude-opus-5.5 | non-conventional | pr-red | untriaged |
| sigil | #300 | 517eed17c8d5 | 2026-10-29 | mixed | non-conventional | main-red, pr-red | untriaged |
| smithy | #20 | aeab46bebce1 | 2026-10-28 | claude-opus-5.5 | other | main-red, pr-red | untriaged |
| smithy | #36 | fc72e9405ae3 | 2026-10-28 | claude-opus-5.5 | ci | hotfix-ref, merge-guard | untriaged |
| smithy | #41 | a138abb658d0 | 2026-10-29 | claude-opus-5.5 | feat | pr-red | untriaged |
| smithy | #42 | f75a798b4388 | 2026-10-29 | claude-opus-5.5 | fix | pr-red | untriaged |
| smithy | #45 | 67ad04da5c2e | 2026-10-29 | claude-opus-5.5 | feat | main-red, merge-guard, ledger | INC-2026-10-004 |
| smithy | #47 | 8d435eeb7d74 | 2026-10-29 | claude-opus-5.5 | feat | hotfix-ref | untriaged |
| smithy | #51 | d72b2f782460 | 2026-10-29 | claude-opus-5.5 | fix | pr-red | untriaged |
| spar | #387 | 9903d1a25820 | 2026-08-05 | claude-opus-4.8 | non-conventional | pr-red | untriaged |
| spar | #364 | 232a5050a6fc | 2026-08-05 | claude-opus-4.8 | non-conventional | pr-red | untriaged |
| spar | #408 | c28c2ccdcf3e | 2026-08-07 | claude-opus-5 | non-conventional | pr-red | untriaged |
| spar | #410 | 686a23a4e1d3 | 2026-08-08 | human-only | chore | main-red | untriaged |
| spar | #415 | b6e469189348 | 2026-08-12 | claude-opus-5 | non-conventional | pr-red | untriaged |
| spar | #419 | ba569b7620ed | 2026-08-19 | claude-opus-5 | test | pr-red | untriaged |
| spar | #426 | 56948d85b24f | 2026-08-20 | claude-opus-5 | chore | pr-red | untriaged |
| spar | #441 | 7272e370eb32 | 2026-09-30 | claude-opus-5 | other | main-red, pr-red | untriaged |
| spar | #449 | 2ddbcc6ac829 | 2026-09-30 | claude-opus-5 | ci | pr-red | untriaged |
| spar | #440 | 20b204cc05ca | 2026-09-30 | claude-opus-4.8 | fix | pr-red, hotfix-ref | untriaged |
| spar | #451 | 7aeeef5e3852 | 2026-10-03 | claude-opus-5 | fix | pr-red | untriaged |
| spar | #443 | 3b409084439e | 2026-10-03 | claude-opus-5 | feat | pr-red | untriaged |
| spar | #442 | 1bd99d4cb979 | 2026-10-08 | claude-opus-5 | test | pr-red | untriaged |
| spar | #458 | 0b9b9f84f39c | 2026-10-09 | claude-opus-5 | chore | main-red, hotfix-ref | untriaged |
| spar | #459 | 07ab767f0fdb | 2026-10-09 | claude-opus-4.8 | fix | hotfix-ref | untriaged |
| spar | #468 | 857bf04b3a9b | 2026-10-10 | claude-opus-4.8 | fix | pr-red, hotfix-ref | untriaged |
| spar | #471 | 4fb01ed024b6 | 2026-10-10 | claude-opus-4.8 | fix | pr-red, hotfix-ref | untriaged |
| spar | #477 | 781153438996 | 2026-10-13 | claude-opus-5 | other | main-red | untriaged |
| spar | #479 | 91d562aa0550 | 2026-10-14 | claude-opus-5 | fix | pr-red | untriaged |
| spar | #487 | 7694c949f4b0 | 2026-10-14 | claude-opus-5.5 | fix | pr-red | untriaged |
| spar | #491 | eb09f52b01b8 | 2026-10-15 | claude-opus-5.5 | fix | main-red | untriaged |
| spar | #497 | 0975bc9c4633 | 2026-10-16 | claude-opus-5.5 | fix | hotfix-ref | untriaged |
| spar | #500 | 8a87a4cd90d7 | 2026-10-16 | claude-opus-5.5 | fix | hotfix-ref | untriaged |
| spar | #503 | 83eb59b178f0 | 2026-10-21 | claude-opus-5.5 | fix | hotfix-ref | untriaged |
| spar | #507 | b883caca4999 | 2026-10-21 | claude-opus-5.5 | fix | hotfix-ref | untriaged |
| spar | #509 | 02094f96c678 | 2026-10-22 | claude-opus-5.5 | fix | hotfix-ref | untriaged |
| spar | #528 | 3285537f0945 | 2026-10-28 | claude-opus-5.5 | fix | hotfix-ref | untriaged |
| spar | #538 | ee06804a5ef0 | 2026-10-28 | claude-opus-5.5 | fix | hotfix-ref | untriaged |
| spar | #541 | 137f91542e8d | 2026-10-28 | claude-opus-5.5 | fix | hotfix-ref | untriaged |
| spar | #530 | b78986e57a6c | 2026-10-29 | claude-opus-5.5 | feat | mq-ejected | untriaged |
| synth | #902 | c656b63a9209 | 2026-08-03 | bot | chore | main-red | untriaged |
| synth | #897 | 8a9446b2af3a | 2026-08-04 | claude-unnamed | non-conventional | pr-red | untriaged |
| synth | #899 | 3899997ef3c6 | 2026-08-05 | claude-unnamed | other | pr-red | untriaged |
| synth | #919 | d17c3acf7bba | 2026-08-06 | claude-opus-5 | fix | pr-red | untriaged |
| synth | #913 | 1c35b08477e2 | 2026-08-06 | claude-opus-5 | other | main-red, pr-red | untriaged |
| synth | #918 | 1817bb3e206f | 2026-08-06 | human-only | non-conventional | pr-red | untriaged |
| synth | #917 | 43cd2617f81e | 2026-08-06 | claude-unnamed | non-conventional | main-red, pr-red | untriaged |
| synth | #914 | d3221211a97b | 2026-08-07 | claude-opus-5 | other | pr-red | untriaged |
| synth | #922 | 6c3d62a6dc5b | 2026-08-07 | human-only | other | pr-red | untriaged |
| synth | #934 | 810cddc6a35f | 2026-08-08 | human-only | fix | pr-red | untriaged |
| synth | #939 | 3eec0d37b430 | 2026-08-10 | bot | chore | main-red | untriaged |
| synth | #942 | e9d9cb980d66 | 2026-08-12 | claude-opus-5 | non-conventional | hotfix-ref | untriaged |
| synth | #945 | 3e5c3e8eb1d6 | 2026-08-12 | claude-opus-5 | docs | pr-red | untriaged |
| synth | #950 | 0f326bbb4564 | 2026-08-12 | claude-opus-5 | chore | main-red | untriaged |
| synth | #954 | e21071e794b4 | 2026-08-13 | claude-opus-5 | other | pr-red | untriaged |
| synth | #959 | 8b4808ba3651 | 2026-08-13 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #960 | c2f9d72c827e | 2026-08-13 | claude-opus-5 | fix | pr-red | untriaged |
| synth | #971 | cb80e60c0522 | 2026-08-14 | claude-opus-5 | fix | pr-red | untriaged |
| synth | #975 | 572b10183f7c | 2026-08-14 | claude-opus-5 | fix | pr-red | untriaged |
| synth | #976 | 9b07c831e550 | 2026-08-14 | claude-opus-5 | perf | pr-red | untriaged |
| synth | #978 | 778b36475288 | 2026-08-14 | claude-opus-5 | feat | pr-red | untriaged |
| synth | #980 | 91e6be662732 | 2026-08-14 | claude-opus-5 | chore | pr-red | untriaged |
| synth | #992 | 7d05ea9cda65 | 2026-08-18 | claude-opus-5 | fix | pr-red | untriaged |
| synth | #991 | 3964ac259c8c | 2026-08-18 | claude-opus-5 | feat | main-red, pr-red | untriaged |
| synth | #993 | 4b7eb9afa111 | 2026-08-18 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #997 | 03b5c7410dc2 | 2026-08-19 | bot | chore | pr-red | untriaged |
| synth | #1002 | 4f1d4551b85d | 2026-08-19 | claude-opus-5 | feat | hotfix-ref | untriaged |
| synth | #1004 | 11a3ad5818a4 | 2026-08-20 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1016 | 0d18991c94d5 | 2026-08-21 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1029 | 16b135ba19a0 | 2026-08-21 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1035 | ca6bcdc2ac91 | 2026-08-25 | bot | chore | main-red | untriaged |
| synth | #1042 | 3672143ddefa | 2026-08-26 | human-only | other | pr-red | untriaged |
| synth | #1047 | d656fb8a392f | 2026-08-26 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1050 | 1fe1ad225cac | 2026-08-26 | claude-opus-5 | other | pr-red | untriaged |
| synth | #1060 | e0c7a0d52a81 | 2026-08-26 | claude-opus-5 | fix | pr-red | untriaged |
| synth | #1056 | 4cbb51da0eca | 2026-08-26 | human-only | other | hotfix-ref | untriaged |
| synth | #1061 | 1f05893e63e8 | 2026-08-26 | claude-opus-5 | non-conventional | hotfix-ref | untriaged |
| synth | #1058 | e1a7b57ddf89 | 2026-08-26 | claude-opus-5 | non-conventional | pr-red, hotfix-ref | untriaged |
| synth | #1051 | f1e2e7bc19e1 | 2026-08-26 | claude-opus-5 | non-conventional | pr-red, hotfix-ref | untriaged |
| synth | #1071 | f8036ec175e4 | 2026-08-26 | claude-opus-5 | non-conventional | pr-red, hotfix-ref | untriaged |
| synth | #1075 | 0ec9dc7a49f6 | 2026-08-27 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1076 | 81ef63333528 | 2026-08-27 | claude-opus-5 | non-conventional | main-red | untriaged |
| synth | #1082 | 116e3bbd75d9 | 2026-08-27 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1083 | 64aa5bd20270 | 2026-08-27 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1084 | 4ba720d8f214 | 2026-08-27 | claude-opus-5 | non-conventional | pr-red, hotfix-ref | untriaged |
| synth | #1096 | c4b463f39313 | 2026-08-28 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1101 | e7635868382a | 2026-08-28 | claude-opus-5 | non-conventional | main-red, hotfix-ref | untriaged |
| synth | #1103 | 23a0b54636c6 | 2026-08-28 | claude-opus-5 | other | hotfix-ref | untriaged |
| synth | #1104 | 1d9188b99f84 | 2026-08-28 | claude-opus-5 | non-conventional | main-red, hotfix-ref | untriaged |
| synth | #1114 | 54a32685d820 | 2026-09-01 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1115 | f9ba4d55c089 | 2026-09-01 | claude-opus-5 | non-conventional | main-red, hotfix-ref | untriaged |
| synth | #1116 | b4860e4e2bd3 | 2026-09-01 | claude-opus-5 | fix | pr-red | untriaged |
| synth | #1123 | 3bbf93621dc6 | 2026-09-02 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1134 | 50889180ef00 | 2026-09-03 | claude-opus-5 | other | main-red, pr-red | untriaged |
| synth | #1137 | b552fb4c5e03 | 2026-09-03 | claude-opus-5 | chore | pr-red | untriaged |
| synth | #1139 | 2b5f68406b7d | 2026-09-03 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1148 | 31daf6d6a2f5 | 2026-09-05 | claude-opus-5 | other | pr-red | untriaged |
| synth | #1149 | 12a01a32d9df | 2026-09-05 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1177 | 8862ee2fbb43 | 2026-09-07 | claude-opus-5 | other | pr-red | untriaged |
| synth | #1179 | 297e696d25ab | 2026-09-07 | claude-opus-5 | feat | pr-red | untriaged |
| synth | #1182 | 32098c7a780b | 2026-09-07 | claude-opus-5 | non-conventional | hotfix-ref | untriaged |
| synth | #1107 | 1b07bfcb64e4 | 2026-09-07 | bot | chore | main-red | untriaged |
| synth | #1190 | e96d23ff3e62 | 2026-09-07 | claude-opus-5 | fix | hotfix-ref | untriaged |
| synth | #1188 | 1aa3de9afb53 | 2026-09-07 | claude-opus-5 | feat | pr-red | untriaged |
| synth | #1202 | c7d945fcb4f2 | 2026-09-08 | human-only | chore | hotfix-ref | untriaged |
| synth | #1232 | 817558a95740 | 2026-09-09 | claude-opus-5 | feat | pr-red, hotfix-ref | untriaged |
| synth | #1227 | d2e26f4525c8 | 2026-09-09 | claude-opus-5 | fix | pr-red | untriaged |
| synth | #1233 | 316d38e68d56 | 2026-09-09 | claude-opus-5 | feat | pr-red | untriaged |
| synth | #1237 | 75a029538524 | 2026-09-09 | claude-opus-5 | other | main-red | untriaged |
| synth | #1242 | 499c38955ce3 | 2026-09-09 | claude-opus-5 | feat | hotfix-ref | untriaged |
| synth | #1249 | 4a3f60801e51 | 2026-09-10 | claude-opus-5 | fix | main-red, hotfix-ref | untriaged |
| synth | #1246 | 71a2c37b411d | 2026-09-10 | claude-opus-5 | test | pr-red | untriaged |
| synth | #1245 | 62d87768278f | 2026-09-10 | claude-opus-5 | test | pr-red | untriaged |
| synth | #1256 | 0cfcc1600a34 | 2026-09-10 | claude-opus-5 | fix | pr-red | untriaged |
| synth | #1258 | 2e1a82871a12 | 2026-09-10 | claude-opus-5 | fix | pr-red | untriaged |
| synth | #1271 | 31980043dec8 | 2026-09-15 | claude-opus-5 | fix | pr-red | untriaged |
| synth | #1295 | 06f3ef51f19e | 2026-09-16 | claude-opus-5 | feat | pr-red | untriaged |
| synth | #1296 | 5cee7491ebf4 | 2026-09-16 | claude-opus-5 | non-conventional | main-red | untriaged |
| synth | #1299 | 9e519fecac27 | 2026-09-16 | claude-opus-5 | other | pr-red | untriaged |
| synth | #1304 | 313780085fdd | 2026-09-17 | claude-opus-5 | non-conventional | main-red | untriaged |
| synth | #1316 | bd81bc8cb6f6 | 2026-09-17 | claude-opus-5 | other | pr-red | untriaged |
| synth | #1323 | 2d956ce9c366 | 2026-09-18 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1327 | fb9af78416ce | 2026-09-18 | claude-opus-5 | non-conventional | main-red | untriaged |
| synth | #1332 | de049f24a7e0 | 2026-09-18 | claude-opus-5 | other | pr-red | untriaged |
| synth | #1338 | 70ab1ce4f47d | 2026-09-18 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1340 | c18c185e7e0f | 2026-09-19 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1348 | 6470e1712ca3 | 2026-09-22 | claude-opus-5 | other | pr-red | untriaged |
| synth | #1351 | 2da2a190feec | 2026-09-23 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1352 | 23c6b2d2d49d | 2026-09-23 | claude-opus-5 | non-conventional | main-red | untriaged |
| synth | #1356 | 934e2bfbc135 | 2026-09-23 | human-only | feat | main-red | untriaged |
| synth | #1357 | f22a3288c59c | 2026-09-23 | human-only | non-conventional | pr-red | untriaged |
| synth | #1355 | 368293fb1e73 | 2026-09-23 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1369 | 8216fd21f97c | 2026-09-24 | claude-opus-5 | non-conventional | main-red | untriaged |
| synth | #1371 | c7da4b3ea5bc | 2026-09-24 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1375 | 4d673950a977 | 2026-09-24 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1376 | 4a76de5e54db | 2026-09-24 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1377 | ca1e889a6d8f | 2026-09-24 | claude-opus-5 | non-conventional | main-red, pr-red | untriaged |
| synth | #1379 | 03d87d05abd1 | 2026-09-24 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1380 | a5c9b6d67e86 | 2026-09-24 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1382 | f2625c576d3d | 2026-09-24 | claude-opus-5 | other | main-red | untriaged |
| synth | #1383 | 3fb02a6fface | 2026-09-24 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1384 | bd3655554b69 | 2026-09-24 | claude-opus-5 | non-conventional | main-red, pr-red | untriaged |
| synth | #1385 | 68ce06a1820e | 2026-09-24 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1386 | 52171d83584e | 2026-09-24 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1387 | d7c2f55c3088 | 2026-09-24 | claude-opus-5 | non-conventional | main-red, pr-red | untriaged |
| synth | #1388 | a1dc2fa53e50 | 2026-09-24 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1389 | 852d5f383926 | 2026-09-25 | claude-opus-5 | non-conventional | main-red | untriaged |
| synth | #1393 | 472c977b178e | 2026-09-25 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1397 | 2d562eccec05 | 2026-09-25 | claude-opus-5 | non-conventional | main-red | untriaged |
| synth | #1399 | a030db47da04 | 2026-09-25 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1408 | dbc394618f04 | 2026-09-25 | claude-opus-5 | non-conventional | main-red | untriaged |
| synth | #1413 | 562de1ea31aa | 2026-09-28 | bot | chore | main-red | untriaged |
| synth | #1420 | 7a9126e08386 | 2026-09-30 | claude-opus-5 | non-conventional | main-red | untriaged |
| synth | #1421 | 87dbe01d7ff6 | 2026-09-30 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1425 | 96f84e2075b2 | 2026-09-30 | claude-opus-5 | non-conventional | main-red | untriaged |
| synth | #1427 | 839ddbb73a6a | 2026-09-30 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1429 | d4c5eba83e73 | 2026-09-30 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1434 | 18c5c5d6417b | 2026-09-30 | claude-opus-5 | non-conventional | main-red, pr-red | untriaged |
| synth | #1438 | 5f096a470af4 | 2026-10-01 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1452 | 28196ec70d7b | 2026-10-01 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1475 | 2799b04d1ff9 | 2026-10-07 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1483 | ee9a9559e022 | 2026-10-07 | claude-opus-5 | non-conventional | main-red | untriaged |
| synth | #1492 | afa59b5d6704 | 2026-10-08 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1494 | 5d8b2ab6c5ff | 2026-10-08 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1496 | da00e699fa77 | 2026-10-08 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1497 | d011ced79381 | 2026-10-08 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1503 | 1027a50a2168 | 2026-10-09 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1510 | e1dcaf93e4e1 | 2026-10-09 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1520 | 004620316a1b | 2026-10-13 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1524 | 1977ec6bb02d | 2026-10-14 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1525 | 479982ea57cf | 2026-10-14 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1537 | 6ac98ef871d5 | 2026-10-14 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1538 | 9ce8348b4133 | 2026-10-15 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1543 | 7a4f014eabcc | 2026-10-15 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1546 | b0b7c58e3f95 | 2026-10-15 | claude-opus-5 | non-conventional | pr-red | untriaged |
| synth | #1554 | 897dbf69d123 | 2026-10-16 | claude-opus-5.5 | non-conventional | pr-red | untriaged |
| synth | #1564 | f982481f8854 | 2026-10-21 | claude-opus-5.5 | non-conventional | pr-red | untriaged |
| synth | #1569 | 85914929398e | 2026-10-21 | claude-opus-5.5 | non-conventional | pr-red | untriaged |
| synth | #1577 | ffd308cb0bf8 | 2026-10-23 | claude-opus-5.5 | non-conventional | pr-red | untriaged |
| synth | #1585 | 92c3e3778813 | 2026-10-23 | claude-opus-5.5 | non-conventional | pr-red | untriaged |
| synth | #1592 | efb0f28a027c | 2026-10-28 | claude-opus-5.5 | non-conventional | pr-red | untriaged |
| synth | #1598 | a28a09af6da3 | 2026-10-28 | claude-opus-5.5 | non-conventional | pr-red | untriaged |
| synth | #1602 | d048b52387d8 | 2026-10-28 | claude-opus-5.5 | non-conventional | pr-red | untriaged |
| temper | #56 | 9251aa443af3 | 2026-10-03 | claude-opus-4.7 | chore | pr-red | untriaged |
| varve | #30 | 16da3e7cdc2e | 2026-08-08 | claude-fable-5 | feat | pr-red | untriaged |
| varve | #31 | b71b7cef3a94 | 2026-08-08 | claude-fable-5 | fix | pr-red | untriaged |
| varve | #33 | 677352bd9a56 | 2026-08-08 | claude-fable-5 | feat | pr-red | untriaged |
| varve | #35 | c78b25f64e8e | 2026-08-08 | claude-fable-5 | fix | pr-red | untriaged |
| varve | #41 | 6c87a47de29a | 2026-08-12 | claude-opus-4.8 | feat | main-red | untriaged |
| varve | #53 | 86a0aa1f066e | 2026-08-14 | claude-opus-4.8 | non-conventional | main-red, pr-red | untriaged |
| varve | #55 | b6cf77313ec9 | 2026-08-14 | claude-opus-4.8 | non-conventional | pr-red | untriaged |
| varve | #75 | 732a8a0a0dab | 2026-08-19 | claude-opus-5 | non-conventional | main-red, pr-red | untriaged |
| varve | #83 | b7666ee6ee13 | 2026-08-19 | claude-opus-5 | non-conventional | pr-red | untriaged |
| varve | #114 | 1ea76695a87f | 2026-08-28 | claude-opus-5 | non-conventional | main-red, main-red, pr-red | untriaged |
| varve | #123 | 4376202cea81 | 2026-09-03 | human-only | non-conventional | pr-red | untriaged |
| varve | #127 | f114a15dd3b4 | 2026-09-05 | human-only | non-conventional | pr-red | untriaged |
| varve | #129 | c16fcce565d2 | 2026-09-06 | human-only | other | pr-red | untriaged |
| varve | #137 | 8994b0781c4d | 2026-09-09 | human-only | non-conventional | pr-red | untriaged |
| varve | #144 | d453fe4ee996 | 2026-09-10 | human-only | non-conventional | main-red | untriaged |
| varve | #151 | eec5a61193ce | 2026-09-16 | human-only | non-conventional | pr-red | untriaged |
| varve | #111 | dea92121cc85 | 2026-09-16 | human-only | non-conventional | pr-red | untriaged |
| varve | #150 | a1aa5900d5ce | 2026-09-16 | human-only | non-conventional | pr-red | untriaged |
| varve | #163 | e724b300695e | 2026-09-18 | claude-opus-5 | non-conventional | main-red | untriaged |
| varve | #173 | 241ab8ccd518 | 2026-09-23 | claude-opus-5 | non-conventional | pr-red | untriaged |
| varve | #182 | 37d145d7126b | 2026-09-23 | claude-opus-5 | non-conventional | pr-red | untriaged |
| varve | #199 | 985b6eb04e5e | 2026-09-25 | claude-opus-5 | non-conventional | pr-red | untriaged |
| varve | #158 | 136a29b77e39 | 2026-09-28 | bot | build | pr-red | untriaged |
| varve | #211 | 728dc1c210d2 | 2026-09-30 | claude-opus-5 | non-conventional | main-red | untriaged |
| varve | #221 | f7e9c4b5b9e2 | 2026-09-30 | claude-opus-5 | non-conventional | pr-red | untriaged |
| varve | #232 | 8be141cdb70d | 2026-10-01 | claude-opus-5 | non-conventional | pr-red | untriaged |
| varve | #239 | 20e3d3f0a4c1 | 2026-10-06 | claude-opus-5 | non-conventional | pr-red | untriaged |
| varve | #238 | 11cb9282172a | 2026-10-08 | bot | build | pr-red | untriaged |
| varve | #255 | 388decb966cd | 2026-10-15 | mixed | non-conventional | pr-red | untriaged |
| varve | #260 | a433b97fd08c | 2026-10-15 | claude-opus-5.5 | non-conventional | main-red | untriaged |
| varve | #269 | 4f2dcecccfd1 | 2026-10-15 | claude-opus-5.5 | non-conventional | main-red, pr-red | untriaged |
| varve | #264 | db9805dfe859 | 2026-10-16 | mixed | non-conventional | pr-red | untriaged |
| varve | #274 | b4b48ec3ea3d | 2026-10-21 | mixed | non-conventional | pr-red | untriaged |
| varve | #276 | 8a3c26e1f377 | 2026-10-21 | mixed | non-conventional | pr-red | untriaged |
| varve | #278 | 35592ae333c5 | 2026-10-21 | mixed | non-conventional | pr-red | untriaged |
| varve | #279 | e7019ad77789 | 2026-10-22 | claude-opus-5.5 | non-conventional | pr-red | untriaged |
| varve | #266 | f19452c050f6 | 2026-10-25 | mixed | chore | pr-red | untriaged |
| varve | #287 | 325e2a534d67 | 2026-10-28 | claude-opus-5.5 | non-conventional | pr-red | untriaged |
| warte | #21 | 1d4a74aadf83 | 2026-10-26 | human-only | non-conventional | main-red | untriaged |
| warte | #43 | fa9d844fb67b | 2026-10-28 | claude-opus-5.5 | non-conventional | pr-red | untriaged |
| warte | #54 | afa9cdafe801 | 2026-10-28 | claude-opus-5.5 | non-conventional | pr-red | untriaged |
| warte | #56 | f4cdbf618286 | 2026-10-28 | claude-opus-5.5 | other | pr-red | untriaged |
| warte | #64 | fea18053da9d | 2026-10-28 | claude-opus-5.5 | non-conventional | pr-red | untriaged |
| warte | #66 | 97978abf2835 | 2026-10-29 | claude-opus-5.5 | other | pr-red | untriaged |
| warte | #74 | d462808c81bc | 2026-10-29 | claude-opus-5.5 | non-conventional | pr-red | untriaged |
| warte | #84 | dcffced8041c | 2026-10-29 | claude-opus-5.5 | non-conventional | pr-red | untriaged |
| wasm-component-examples | #11 | aa189a31f35c | 2026-10-28 | claude-opus-5.5 | docs | main-red | untriaged |
| wasm-layers | #8 | 1dea4a0798cb | 2026-09-24 | claude-opus-5 | non-conventional | pr-red | untriaged |
| witness | #176 | 2143e5da6269 | 2026-08-05 | bot | chore | main-red | untriaged |
| witness | #181 | 6fd27d015df6 | 2026-08-11 | claude-opus-4.8 | fix | pr-red | untriaged |
| witness | #183 | 346c59b5490e | 2026-08-12 | claude-opus-4.8 | non-conventional | main-red | untriaged |
| witness | #193 | 908732b10367 | 2026-08-12 | claude-opus-4.8 | fix | pr-red | untriaged |
| witness | #190 | 29cad1a5fa97 | 2026-08-13 | bot | chore | pr-red | untriaged |
| witness | #195 | 03cc3069b617 | 2026-08-13 | claude-opus-4.8 | fix | pr-red | untriaged |
| witness | #211 | fd20a0cae635 | 2026-09-07 | bot | chore | pr-red | untriaged |
| witness | #219 | 67629fade11c | 2026-09-07 | claude-fable-5 | fix | pr-red | untriaged |
| witness | #217 | 48dbf2604d47 | 2026-09-07 | claude-opus-5 | fix | pr-red | untriaged |
| witness | #216 | 48e101407388 | 2026-09-07 | bot | chore | pr-red | untriaged |
| witness | #215 | 6bf6ad54cc91 | 2026-09-07 | bot | chore | pr-red | untriaged |
| witness | #203 | ad1f737440ca | 2026-09-07 | bot | chore | pr-red | untriaged |
| witness | #191 | 6c5fa87d1ad6 | 2026-09-07 | bot | chore | pr-red | untriaged |
| witness | #240 | 00e6a99fdff2 | 2026-09-30 | bot | chore | main-red | untriaged |
| witness | #233 | 743c5e01e9b8 | 2026-10-06 | bot | chore | pr-red | untriaged |
| witness | #230 | 7b3330a912ab | 2026-10-06 | bot | chore | pr-red | untriaged |
| witness | #244 | 5d894c226434 | 2026-10-06 | claude-fable-5 | feat | pr-red | untriaged |
| witness | #225 | e096d578f065 | 2026-10-06 | bot | chore | pr-red | untriaged |
| witness | #246 | 32f23b14f817 | 2026-10-14 | bot | chore | pr-red | untriaged |
| witness | #248 | 1becf11708c5 | 2026-10-14 | bot | chore | pr-red | untriaged |
| witness | #250 | 2785d856c40d | 2026-10-14 | bot | chore | pr-red | untriaged |
| witness | #245 | 105a8823d5d0 | 2026-10-14 | human-only | non-conventional | pr-red | untriaged |
| witness | #253 | 5303cddc5fb9 | 2026-10-14 | claude-opus-5.5 | fix | pr-red | untriaged |
| witness | #252 | 3796ad09e1f7 | 2026-10-14 | claude-opus-5.5 | chore | pr-red | untriaged |
| witness | #254 | 51135cb89aef | 2026-10-14 | claude-opus-5.5 | chore | pr-red | untriaged |
| witness | #255 | 3ef7704db13e | 2026-10-14 | claude-opus-5.5 | non-conventional | pr-red | untriaged |
| witness | #249 | 3b8bf2db985e | 2026-10-14 | bot | chore | pr-red | untriaged |
| witness | #264 | a5310ee8feaa | 2026-10-15 | claude-opus-5.5 | fix | pr-red | untriaged |
| witness | #256 | 3ba1146e05f7 | 2026-10-15 | claude-opus-5.5 | feat | pr-red | untriaged |
| witness | #270 | ca38cc42c22b | 2026-10-15 | bot | chore | hotfix-ref | untriaged |
| wohl | #66 | a02c16ec7150 | 2026-10-29 | claude-opus-5.5 | ci | main-red, pr-red | untriaged |

## Method and blind spots

recorded per unit and never mixed silently:
  escape (post-merge):
    main-red    a push/merge_group GitHub Actions suite on the unit's sha concluded
                FAILURE/TIMED_OUT/STARTUP_FAILURE and the previous run of the same
                workflow on first-parent main was not red (a red streak is charged
                to the commit that started it; path-filtered commits are skipped)
    revert      a later unit says "This reverts commit <sha>" or is titled
                Revert "<this unit's subject>"
    hotfix-ref  a later fix:/revert unit, within 14 days, references this unit's
                PR number (#N). Heuristic: a mention is not proof of causation
    merge-guard a "merge-guard: unchecked change on main (<sha12>)" issue
    ledger      a docs/incidents/ledger.yaml entry of kind escape names this merge
                (a manually found escape, e.g. a harness defect fixed later)
  catch (pre-merge):
    pr-red      a PR commit before the head had a FAILURE/ERROR status rollup and
                the PR still merged (the red was fixed before merge)
    mq-ejected  the PR was removed from the merge queue with reason failed_checks
  flags (nets, not incidents):
    merged-before-ci   a pull_request Actions suite on the head was still running
                       at mergedAt
    merged-red-head    the head's status rollup is FAILURE/ERROR yet it merged
    no-pr              pushed to main without a PR

Calibration, first run, 2026-10-29, by hand. hotfix-ref: of 15 randomly sampled links, 9 named a real defect in the referenced merge and 6 were mentions (a reference point, a fix credited to that PR, a list), so precision is about 60% and the strict escape rate leaves it out. merged-red-head: 4 sampled heads were red on an advisory check (2), a failing audit on a dependabot bump (1) and failing clippy and tests on a dependabot bump (1), so the flag mixes real overrides with advisory reds. merged-before-ci: 4 of 4 sampled had pull_request checks still running at mergedAt (required or not), all of which later passed or were cancelled.

