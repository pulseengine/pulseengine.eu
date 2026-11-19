An owner who checks a phone early should see one line: either "All quiet, N decisions wait for the next window", or a short list of only what cannot wait. This view must not become a back door for routine questions.

## Plan (v1.6.34, after v1.6.33)

`GET /api/glance` (JSON) and `/glance` (one phone-sized page). Both are signed-in only, because they read notices. No new login: the existing session or provider token works.

Verdict `needs-you` lists one item per source below. Otherwise it is `quiet`, with counts only: open routine decisions, and agents silent for more than 30 min.

| Source | Item when |
|---|---|
| factory-notice | an open `needs-decision` notice whose `kind` or `tags` hit the always-open kinds (default `security`, `red-main`; `[glance] always_open` mirrors the notice client's `always_open_kinds`) |
| CI | the latest run on `main` of a watched repository failed |
| releases | a release run (tag push) failed and no later run for that tag succeeded |
| disk | a host's pressure verdict is `critical` |

Rules:
- Agent silence is a count, never an item, in v1. A session that ended normally, or one idle at the prompt waiting for the owner, is silent too; listing silence would fire every night and teach the owner to ignore the line. Silence becomes an item only once warte can tell "working and stopped" from "ended" or "idle" (a `status: ended` body on the session-end heartbeat, or lane data). An agent that never sent a heartbeat is counted as `unknown`, separately.
- A routine decision is never listed, only counted. Windows and off periods stay with the notice client's attention schedule. warte shows no time for "the next window" unless one is configured.
- Item text: kind, repository or host, and the decision title cut to 80 characters. No paths, pids or log lines.
- Read-only. It answers nothing and triggers nothing.

## Acceptance tests (planted)
- An urgent notice turns `quiet` into `needs-you`. A routine decision only raises the count (negative control).
- A red main, a failed release later rerun green (not listed), a failed release not rerun (listed), a critical disk.
- An agent whose last beat was 2 h ago (a session end) leaves the verdict `quiet` and appears only in the silent count. An agent that never heartbeated is counted as unknown.
- Without a login: 401.

## Not in v1
Silence as a `needs-you` item. It needs an ended or idle marker: the heartbeat route could take an optional body `{"status": "ended"}` from the hook-end beat, or lane and PR data.

Kill criterion: wrong if a routine decision ever appears as an item, or if an urgent notice, red main, failed release or critical disk leaves the line `quiet`.


## Seam: heartbeat status

```seam
format: 1
seam: warte-plugin/heartbeat-status
kind: wire
status: decided
provider:
  repo: pulseengine/warte
  promise: "POST /api/agents/{id}/heartbeat accepts an optional JSON body {\"status\": \"ended\" | \"idle\" | \"working\"}, stores it with last_heartbeat, and treats a bodyless beat as before; accepted since warte v1.6.34"
consumers:
  - repo: pulseengine/pulseengine.eu
    binding: "the factory-notice heartbeat sends status ended at hook-end and idle at the Stop hook, only once the deployed warte is v1.6.34 or later"
interface:
  - kind: file
    path: docs/topics/api-reference.md
    symbols: ["POST /api/agents/{id}/heartbeat"]
decisions:
  - summary: "optional status body with ended, idle, working; bodyless beat unchanged; the glance counts silence and never lists it in v1"
    decided_by: "warte and pulseengine.eu sessions, on the owner's night-glance request"
    date: "2026-11-18"
    ref: "warte#179"
open_questions:
  - {q: "which warte version is deployed, so the plugin may start sending status?", owner: pulseengine/warte}
```
