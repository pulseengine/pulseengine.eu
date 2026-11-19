Seam block for temper-triage, the consumer side of the triage routes. temper reads only `ready[].repo` and `ready[].number`, reads the issue from GitHub itself, and marks done only after its GitHub writes succeeded. Design: pulseengine/temper `docs/triage.md` (branch `feat/triage-first-reply`).

```seam
format: 1
seam: warte-temper/triage-queue
kind: wire
status: decided
provider:
  repo: pulseengine/warte
  promise: "no silent change to these routes or fields; a change is announced on warte#185 first. GET /api/triage returns {ready: [Item], waiting, ...} with Item {repo (bare name in [triage].org), number, title (untrusted, 120 chars), author, url, action, queued_at}; POST /api/triage/done takes exactly {repo, number, outcome} with outcome replied, asked or skipped (201, or 422 when not queued); both need the triage:write right; an item not marked done is offered again"
consumers:
  - repo: pulseengine/temper
    binding: "temper-triage (triage/) reads only ready[].repo and ready[].number, reads the issue from GitHub itself, and marks done only after its GitHub writes succeeded; a 422 on done is logged and not retried"
interface:
  - kind: file
    path: src/triage/mod.rs
    symbols:
      - "pub struct Item {"
      - "pub repo: String,"
      - "pub number: u64,"
      - "pub ready: Vec<Item>,"
      - "[\"replied\", \"asked\", \"skipped\"]"
  - kind: file
    path: src/server/api.rs
    symbols:
      - ".route(\"/triage\", get(api_triage))"
      - ".route(\"/triage/done\", post(api_triage_done))"
      - "struct TriageDone {"
  - kind: file
    path: src/login/mod.rs
    symbols:
      - "(\"/api/triage\", \"triage:write\")"
decisions:
  - summary: "temper takes first-reply triage over from warte; warte notices, temper replies through GET /api/triage and POST /api/triage/done"
    decided_by: "owner"
    date: "2026-11-19"
    ref: "warte#185"
  - summary: "v1 sends only the outcome word; TriageDone stays deny_unknown_fields. Reply kinds in warte's view would be a new optional field, announced on warte#185 before a warte release accepts it"
    decided_by: "warte maintainer session"
    date: "2026-11-19"
    ref: "warte#185"
```
