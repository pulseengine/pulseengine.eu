This issue owns the seam between warte's triage routes (REQ-TRIAGE-001/002, landed in #153) and temper, which will write the first replies.

- warte notices new issues and lists those ready for a first reply at `GET /api/triage`. With `[auth]` on, a token with `triage:write` reads the list.
- temper replies on GitHub as the org's GitHub App, then marks each item `POST /api/triage/done` with `{repo, number, outcome}`, where outcome is `replied`, `asked` or `skipped`, and only after its GitHub writes succeeded. warte answers 422 for an item that isn't queued, and temper does not retry it.
- warte never executes anything from an issue, and its read API publishes no issue text beyond what the route already does.

The seam block comes from the temper side as a comment, checked against warte's main. Decision on reply kinds (temper's question): v1 keeps only the outcome word. `TriageDone` stays `deny_unknown_fields`, and adding a reply kind later is a new field announced here first.