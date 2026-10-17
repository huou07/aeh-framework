# AEH capabilities

Type: Reference (capability map).

Authority: what AEH actually does today, named mechanism by mechanism. Product
repositories remain the authority for their own behaviour; a capability that is
`DOCUMENTED` or `NOT IMPLEMENTED` here must not be described as enforced.

Applies to: anyone deciding whether AEH can do a job, and anyone extending it.

Not a source of truth for: current Git, CI, runtime or project task state.

Status: current

Last reviewed: 2026-10-17

Purpose: map the owner's requested capabilities and the six core
responsibilities to the concrete AEH mechanism that exists today, so a claim
about AEH can be checked instead of assumed. The grading vocabulary is the five
verdicts in [the quality standard](quality-standard.md).

## 1. The fourteen capabilities

`IMPLEMENTED` = a mechanism exists and is exercised; `PARTIAL` = the mechanism
exists but does not cover the whole claim; `DOCUMENTED` = the procedure is
written but nothing enforces it; `NOT IMPLEMENTED` = no mechanism exists.

| # | Capability | Concrete mechanism today | Status |
|---|---|---|---|
| 1 | **Understand projects** | `hub.py list/where/status/report/assess`; project `AGENTS.md`/`README.md`/`docs/`; `code-investigate` skill; CodeGraph index when present. `assess` composes source integrity, gates, contract and cost into one verdict. | `IMPLEMENTED` |
| 2 | **Analyse and plan** | `task-planning` skill (outcome, write-scope splitting, dependency order, explicit parallelism, acceptance and stop per task, resources, recovery); [engineering guide](engineering-guide.md), [operating model](operating-model.md), [delivery](project-delivery.md); `project-steward` for the brief; `templates/project-brief.md`. | `IMPLEMENTED` |
| 3 | **Coordinate agents** | One-writer-per-repository rule; [session handoff](session-handoff.md) via `scripts/dsh_gui_session.cjs` (delivery proven from the session transcript); pause/steer via `dsh_gui_pause.cjs`/`dsh_gui_steer.cjs`. No daemon, scheduler or orchestrator, by design. | `IMPLEMENTED` |
| 4 | **Manage knowledge** | `docs/` with a navigation index and `Status:`/`Last reviewed:` discipline; `evidence/` curated ledger with its own index; `templates/`; the incident ledger. | `IMPLEMENTED` |
| 5 | **Architecture** | Architecture is owned by each repository; AEH keeps the pointers, `templates/decision-record.md` and the review checklist. AEH does not author product architecture. | `PARTIAL` |
| 6 | **Environment** | the owner's normal-user runtime notes (applications, private-network detail, model route; not published); shared toolchains (Flutter, Rust, Playwright, Node, Python); `hub.py doctor`; the readiness matrix's "runs now / missing" tables. | `IMPLEMENTED` |
| 7 | **Test automation** | Registry `verify`/`acceptance` commands executed by `hub.py verify --gate verify\|acceptance`; project gates wired into each project's CI; AEH's own conformance suite (`scripts/conformance.py`, 16 negative fixtures) grades the Hub. | `IMPLEMENTED` |
| 8 | **Quality assessment** | Frozen interface: `hub.py assess <slug>`, `hub.py release-check <slug>`, the five verdicts, the project-owned quality contract, and the optional gate report. Defined by [the quality standard](quality-standard.md); enforced by `release-check`'s six conditions. | `IMPLEMENTED` |
| 9 | **Security** | [Quality and security](quality-and-security.md) boundaries; `security-review` skill; per-project secret/dependency scans in CI; host privilege stays owner-gated. AEH has no central scanner. | `PARTIAL` |
| 10 | **Evidence verification** | `.hub/verification.jsonl` (append-only runtime ledger); freshness computed against the current HEAD; `source_before`/`source_after`; `command`, `contract_sha256` and `commit_sha256` invalidate a record when the gate or contract changes. `evidence/` holds curated, dated proof. | `IMPLEMENTED` |
| 11 | **Resource and cost** | `hub.py usage --slug <slug>` and `hub.py report`, reading `<project>/.hub/usage.jsonl`; measured/estimated/unavailable never invented. `.hub/verify.lock` serialises heavy gates so two builds cannot run at once. No usage file exists in any project yet, so the honest reading is `unavailable`. | `IMPLEMENTED` (measurement not started) |
| 12 | **Product readiness** | `hub.py assess` (areas + blockers + next actions) and `hub.py release-check` (six conditions); project `docs/QUALITY.md`; the `project-steward` readiness procedure. | `IMPLEMENTED` |
| 13 | **Release management** | `hub.py verify --gate release`; `release-check` requiring artifact `sha256` and `result == PASS`; hosted CI with an aggregate required `release-gate` (OR, H07P); per-project publication gates. Build attestation/signing is owner-gated and not implemented. | `PARTIAL` |
| 14 | **Continuous improvement** | The incident ledger `evidence/incidents.jsonl` with a mandatory guard per entry (`tests/test_incidents.py`); the conformance suite for AEH's own verdicts; `skill-maintainer` for instruction fixes; the deletion policy. | `IMPLEMENTED` |

## 2. The six core responsibilities

| Responsibility | What it means here | Mechanism |
|---|---|---|
| **Discover** | Find the project, its real revision and its recorded evidence without executing product code. | `hub.py where/list/status`, `git`, project docs; `assess` read areas. |
| **Plan** | Turn an outcome into bounded tasks with observable completion, dependency order, explicit parallelism, authority and a stop condition. | `task-planning` skill; `project-steward` for the brief; `prompt-assist` for the handoff text; `templates/project-brief.md`; engineering guide. |
| **Execute** | Run the authorized product gate, bounded in time and output, one writer per tree. | `hub.py verify --gate verify\|acceptance\|release`; project gates. |
| **Verify** | Bind results to exact source identity and grade them with the five verdicts; never promote a skip. | `.hub/verification.jsonl`; `hub.py assess`; gate reports; `scripts/conformance.py`. |
| **Deliver** | Decide release readiness against declared gates and artifacts, with the owner holding the authority. | `hub.py release-check`; hosted CI `release-gate`; `docs/QUALITY.md` acceptance record. |
| **Improve** | Convert each failure met into a recorded incident with an executable guard, and fix the procedure. | `evidence/incidents.jsonl` + `tests/test_incidents.py`; conformance fixtures; deletion policy. |

## 3. Definition of done for a change

Ten items. Each names the check that proves it; `UNPROVEN` means no automated
check exists today and the item rests on review.

| # | Done means | Proof | Proved today? |
|---|---|---|---|
| 1 | The outcome is named: who can do what, and the observable completion condition. | Prompt/issue text with a completion condition | `UNPROVEN` (review) |
| 2 | The starting state was read from Git, not from memory. | `git status --porcelain`, `hub.py where <slug>`, `hub.py status <slug>` output recorded | Proved by the commands |
| 3 | The change is the smallest justified one; unrelated files and history are untouched. | Diff review: `git diff --stat` | `UNPROVEN` (review) |
| 4 | Relevant checks ran at the changed revision and their real output was read. | The command output, not a summary | `UNPROVEN` (review) |
| 5 | The fast gate is green at a clean HEAD. | `python3 scripts/hub.py verify <slug> --gate verify` | Proved for the three registered projects |
| 6 | The admission gate is green where the product can build and test. | `python3 scripts/hub.py verify <slug> --gate acceptance` | Proved for the three registered projects |
| 7 | The affected real journey, and conditional UX/security evidence, exists. | Named journey run, or `security-review` output | `UNPROVEN` (no observed-user or golden baseline) |
| 8 | No skip is reported as a pass; unrun lanes are named. | Gate report `skipped`/`not_run`, or the gate's own output | Partly proved (report ingestion is part of the frozen interface) |
| 9 | Evidence is recorded with source identity, and docs/claims match the change. | Ledger record `head` + freshness `CURRENT`; docs review | Proved for the three projects (`assess` shows `CURRENT`); v2 fields land at the next re-recording |
| 10 | The handoff states the next action, unverified items, authority boundary and rollback. | Project tracker or handoff entry | `UNPROVEN` (review) |

## 4. AEH acceptance checklist

Requirements AEH must satisfy for its own changes and releases. Each names the
command or test that would prove it; `UNPROVEN` means the guard does not exist
yet at the time of this review.

| # | Requirement | Proof | Status |
|---|---|---|---|
| 1 | The Hub's own suite passes. | `python3 -m unittest discover -s tests -q` | Proved |
| 2 | Verdict behaviour is pinned by fixtures (false-green is caught). | `python3 scripts/conformance.py` | Proved: 16 fixtures, `RESULT: NO FALSE-GREEN` (2026-10-17) |
| 3 | The instruction and skill surface is structurally valid. | `bash evals/structural-check.sh` | Proved |
| 4 | Config, registry and containment are healthy. | `python3 scripts/hub.py doctor` | Proved: `RESULT: ALL PASS` (2026-10-17) |
| 5 | One command runs the whole self gate and prints the verdict. | `bash scripts/selfcheck.sh` → `AEH_SELFCHECK=PASS` | Proved: `AEH_SELFCHECK=PASS` (2026-10-17) |
| 6 | Read-only commands never execute project code or write into a project. | Conformance fixture `status-is-read-only` | Proved |
| 7 | The quality-contract schema exists and rejects command injection. | `contracts/quality.schema.json`; fixtures `contract-invalid-unknown-gate`, `contract-command-injection` | Proved |
| 8 | The runtime ledger is append-only and never rewrites a record. | Ledger tests; every record written since 2026-10-18 carries `command`, `source_after`, `contract_sha256`, `commit_sha256` and the parsed gate report, so a changed gate, contract or revision invalidates it | Proved: 29 records, the newest carry all v2 fields |
| 9 | Skills that sessions cannot load are reported as gaps. | `python3 scripts/skill_liveness.py` | Proved |
| 10 | Every incident has an executable guard. | `python3 -m unittest tests.test_incidents` | Proved |
| 11 | Every current framework document carries `Status:` and `Last reviewed:`, is reachable from the docs index, and its relative links and anchors resolve (preserved history is exempt by an explicit list). | `python3 -m unittest tests.test_docs_contract` | Proved: 4 tests (2026-10-17) |
| 12 | AEH verifies itself locally and can share the framework. | `bash scripts/selfcheck.sh` — no network, no daemon, no remote, no CI; `scripts/build-public-snapshot.sh` proves the shareable snapshot before publishing it | Proved locally on every change; the snapshot is proved at build time (publication gate + self gate) before it is published |

## 5. What AEH deliberately does not do

- No daemon, scheduler, database, routing layer or orchestration service.
- No project source inside the Hub; `hub.py doctor` fails a registered path that
  resolves inside the Hub.
- No privilege boundary: a Git worktree or a prompt is not an OS sandbox.
- No release, publication, deployment or host privilege change without owner
  authority.
