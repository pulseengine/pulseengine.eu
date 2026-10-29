---
name: seam-contract
description: "This skill should be used at a seam between two repos, in either direction: BEFORE building against another repo's interface (a WIT package, a wire format, a published component, a trait crate); when asked to change something another repo binds to; when an issue in another repo addresses us or asks how we will consume something; and at release-execution step 4c, before a tag. It writes the contract as a ```seam block (strict YAML) in the owning issue, with an owner repo on each side, options and a recommendation before building, the decision with who and when, and an owner for every open question. seam-check.py then checks every block mechanically: required fields, owners, dated decisions, the interface file and WIT version on the provider's default branch, and the consumer's guard script. Exit 1 on a violation, 2 when GitHub cannot be read. Owner decisions go through factory-notice. Composes with release-execution (4c), issue-hunt and factory-notice."
metadata:
  author: pulseengine.eu
  version: "0.1.0"
---

# Seam contract: write the interface between repos down, then check it

A **seam** is the agreed interface between two repos: a WIT package, a wire
frame, a trait crate, a published component's identity. One side, the
**provider**, owns the promise not to change it silently. The other side, the
**consumer**, owns its binding. In the drone stack four seams were written down
by hand in issues (jess#62, jess#167, relay#572, relay#589). The only mechanical
check among them was jess's pin-identity guard. The blocks were prose, so
nothing went red when a contract drifted from the code. This skill turns each
contract into a block that a script checks.

## The block

Put one fenced `seam` block in the issue that owns the seam: the body, or a
comment when you may not edit the body. The body is canonical. When the body
has no block, the newest comment that carries one counts. It is strict YAML:
unknown keys, duplicate keys, unquoted versions and missing fields are
violations.

````markdown
```seam
format: 1
seam: relay-jess/estimator-identity      # unique across the org
kind: identity                           # hal | consumption | wire | identity | other
status: implemented                      # proposed | options | decided | implemented | broken
provider:
  repo: pulseengine/relay
  promise: "one published exporter per interface"
  guard: scripts/build-components.sh     # optional, must exist in the provider repo
consumers:
  - repo: pulseengine/jess
    binding: "the ekf-stage pin names falcon-iekf"
    guard: tools/deps/check-estimator-identity.sh   # optional, a path or a list; each must exist
interface:                               # one entry or a list
  - kind: wit                            # the file's `package` line must equal package@version
    path: wit/falcon-cascade/cascade.wit
    package: "pulseengine:falcon-cascade"
    version: "0.12.0"
    interfaces: [ekf]                    # each must be declared in the file
  - kind: file                           # each symbol is literal text that must appear
    path: crates/falcon-hitl/src/wire.rs
    symbols: ["pub const VERSION: u8 = 2;"]
options:                                 # status options: two or more, plus a recommendation
  - {id: stop-publishing, summary: "stop publishing falcon-ekf"}
  - {id: annotate, summary: "keep it and annotate"}
recommendation: stop-publishing
decisions:                               # status decided or implemented: one or more
  - summary: "stop publishing falcon-ekf"
    option: stop-publishing
    decided_by: "relay maintainer"
    date: "2026-10-21"
    ref: "relay#589"
implemented_by: "relay#590"              # required for status implemented
open_questions:                          # each owner must be a side of this seam
  - {q: "who applies per-IMU calibration?", owner: pulseengine/relay}
```
````

`implemented` means merged on the provider's default branch. It does not mean
released. Say in `implemented_by` whether a tag carries it.

## Procedure

**Outbound: we are about to build against, or change, another repo's
interface.** Do not build first. Open, or find, the issue in the repo that owns
the decision, which is the layer that owns it. Post a block with `status:
options`, two or more options and your recommendation. Then run `seam-check.py
--block draft.md` before posting, and build only once the block says `decided`.
Building on a guess turns the owner's decision into a cleanup of your code.

**Inbound: an issue addresses us, or another repo asks how we will consume
something.** Confirm the consumption shape before building anything: which
interface, which version, sync or stream, who owns the types. Record the answer
as a decision in the block, with `decided_by` and the date. A question you
cannot answer gets an `open_questions` entry with an owner. A question with no
owner never gets answered.

**On change: we are changing something a consumer binds to.** Update the block
in the same change: a new version, a new symbol, or `status: broken` while the
two sides settle it. Then comment on the issue to notify every consumer
**before** a tag carries the change. `seam-check` goes red when the interface
file no longer matches the block. That is the point: the provider cannot move
the interface without the contract saying so.

**Owner decisions** (choosing between options, `broken`, anything
irreversible) go to the owner as a `needs-decision` notice through
[`factory-notice`], with the block's options as the notice's options. The agent
does not pick. It records the answer in the block once it arrives.

## The check

```sh
S=<this skill's base directory>/seam-check.py   # it sits next to this SKILL.md
python3 $S                                  # every open issue labelled `seam` in the org
python3 $S --party pulseengine/relay        # the seams this repo provides or consumes
python3 $S --issue pulseengine/jess#167     # one issue
python3 $S --block draft.md                 # a draft, before posting it
python3 $S --format json                    # schema seam-check.v1, for warte or a loop
python3 $S --self-test                      # every rule's negative control
```

The rules are: the block parses; required fields are present; `kind` and
`status` are valid; both sides name an owner repo; every open question has an
owner who is a side of the seam; a decided status has a dated decision; an
options status has two or more options and a recommendation; an implemented
status names what landed it; the interface file exists at the provider's
default branch; a WIT `package` line matches the block's package and version;
every named interface or symbol is present; every named guard file exists. A
`broken` status, a duplicate seam id and a labelled issue without a block are
also violations. A decided seam whose latest decision is older than
`--stale-days` (default 30) is a warning, and `--strict` makes it fail.

**Exit 0** means every seam passed. **Exit 1** means a violation, or that no
seam was found at all: zero seams checked is not a pass. **Exit 2** means
GitHub could not be read: an API failure, a rate limit, a repo the token cannot
see, or incomplete search results. Treat exit 2 as unknown, never as green.

GitHub access is REST over curl, not `gh`, because the self-hosted runners have
no `gh`. The token is `GITHUB_TOKEN` or `GH_TOKEN`, else `gh auth token` when gh
is installed. It is sent only to the GitHub API host.

**Blind spots.** An issue that carries a block but not the `seam` label is not
discovered, so label it. A private repo the token cannot read is exit 2. Only
open issues are discovered. The check proves that the contract matches the
provider's files. It does not prove that the consumer's code honours the
contract; the consumer's `guard` script is what does that.

**The transport is swappable.** Issues are the transport today. The script
reads them through one class with four methods (discover, issue,
default_branch, read_file). A later agora channel is another class with the
same methods, and the block format stays the same.

## Where it plugs in

- [`release-execution`] step 4c runs `seam-check.py --party <this repo>`
  before a tag, and treats exit 1 or 2 as blocking.
- [`issue-hunt`] treats an issue with a `seam` block as one to watch in
  **every** repo that is a party to it, not only the repo the loop watermarks.
  On jess#167, relay's loop polled only relay, and jess's answer sat unread for
  11.5 hours.
- [`factory-notice`] carries the owner's decisions.
- `.github/workflows/seam-check.yml` in pulseengine.eu runs the live check
  weekly and on demand. It is deliberately not a required PR check, because
  live data can go red for reasons outside the PR. The self-test runs in every
  PR's CI.

## Anti-patterns

- **The contract only in prose.** Every one of the four drone seams was written
  down, and none went red when the code moved. relay#589's text still says
  `ekf@0.11.0` while relay main is at `@0.12.0`, and the block check catches
  that.
- **Building, then asking.** The design question goes to the owning repo as
  options before the first line is written.
- **An open question with no owner.** Nobody answers it.
- **Announcing one breaking change and not the other.** In the v1.133 release,
  the namespace rename was announced and the path move was not, and only the
  path move caused harm. List every published surface the change touches, and
  update every block that names one.
- **Reading exit 2 as green.** An API failure is unknown, never a pass.
