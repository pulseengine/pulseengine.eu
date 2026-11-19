Each person's attention schedule (decision windows, available hours, focus blocks, off periods) should be a per-user setting, edited in warte's app. The notice client already asks `GET <warte>/api/attention` first, then its cached copy, then the local `~/.config/pulseengine/attention.json`, then defaults. Today warte doesn't serve it, so the local file wins.

## The contract
The shape is pulseengine.eu's `attention.schema.json` (schema_version 1): `windows`, `available`, `focus`, `off`, `timezone`, `max_asking_flows`, `always_open_kinds`, `updated_at`. warte serves exactly that and validates it against the same rules before storing: HH:MM spans, from different from to, at most 100 flows, a known timezone, `off.to` after `off.from`. This gets a seam block once the consumer side confirms it.

## Plan
- **Storage:** one schedule per warte login, keyed by the provider's subject, in warte's database. With no schedule set, `GET` answers 404 and the client keeps its local file and defaults, as today.
- **Reading:** `GET /api/attention`.
  - A signed-in user gets their own schedule.
  - An agent token gets the schedule of the person its agent works for. A token minted with `--owner <login>` names that person. A token without an owner gets 404, so the client falls back as today.
  - Readable with `agents:read` (v1.6.30), bound to the token's owner. Never anyone else's schedule.
- **Editing:** a "My hours" panel in the app, signed-in only.
  - Windows, available hours (the night window is the time outside them), focus blocks, off periods and timezone, each validated as above.
  - Saved with `PUT /api/attention`, for the signed-in user's own schedule only.
  - This is warte's first write made with a login rather than a token. It needs CSRF protection: same-site cookie plus an origin check plus a per-session token. It is logged as who changed what, without the values.
- **Night glance (#179) and dark window:** they use the same per-user schedule.
- **Focus helper (#180):** it writes `available` through this API for its user, rather than the local file. The local file stays the fallback when warte is unreachable.

## Acceptance (planted)
- Two users each read only their own schedule. An agent token reads only its owner's. A token without `--owner` gets 404. Without a login, 401.
- Each schema rule refuses a bad value on PUT, nothing is stored, and the field is named, never the value.
- A PUT without the CSRF token, or from a foreign origin, is refused.
- A schedule served by warte round-trips through the notice client's validator unchanged (the cross-repo check).

## Open
- How a person maps to the agents working for them: `--owner` at mint time, or a mapping in the app. v1 proposes `--owner`, which fleet-config sets when re-minting.

Kill criterion: wrong if any token or login can read or change another person's schedule, or if warte serves a schedule the notice client's validator refuses.

## Seam: attention schedule

```seam
format: 1
seam: notice-warte/attention-schedule
kind: wire
status: decided
provider:
  repo: pulseengine/pulseengine.eu
  promise: "attention.schema.json schema_version 1 is the one shape of the attention schedule; a change is a new schema_version, announced here first"
consumers:
  - repo: pulseengine/warte
    binding: "GET /api/attention serves one person's schedule in exactly that shape, validated by the same rules before it is stored; 404 when none is set; a signed-in user reads their own, an agent token reads its owner's"
interface:
  - kind: file
    path: claude-tooling/plugins/pulseengine-claude/skills/factory-notice/attention.schema.json
    symbols: ["\"schema_version\"", "\"available\"", "\"windows\"", "\"off\"", "\"always_open_kinds\""]
decisions:
  - summary: "warte stores the schedule per login and serves it at GET /api/attention; notice.py keeps its resolve order (warte, cache, local file, defaults) unchanged"
    decided_by: "owner request; warte and pulseengine.eu sessions"
    date: "2026-11-18"
    ref: "warte#181"
open_questions:
  - {q: "how a person maps to their agents (--owner at mint time, or a mapping in the app)", owner: pulseengine/warte}
```
