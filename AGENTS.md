# Hub guide

AEH is a control and knowledge workspace. Product source, architecture, task
state and acceptance live in each independent repository outside this tree.
Resolve projects through `python3 scripts/hub.py where <slug>`; the configured
workspace root is in `hub.config.json`. Preserve existing Git work.

## Find the authority

| Need | Reference |
|---|---|
| Documentation navigation | [docs/README.md](docs/README.md) |
| Product-quality standard | [docs/quality-standard.md](docs/quality-standard.md) |
| Capability map, DoD, AEH acceptance checklist | [docs/aeh-capabilities.md](docs/aeh-capabilities.md) |
| Quality gates, ledger, contract, incidents | [docs/quality-system.md](docs/quality-system.md) |
| Evidence classes, UX, trust boundaries | [docs/quality-and-security.md](docs/quality-and-security.md) |
| Engineering task guidance | [docs/engineering-guide.md](docs/engineering-guide.md) |
| Prompt artifact | [docs/prompting.md](docs/prompting.md) |
| Workflow selection | [docs/skills.md](docs/skills.md); load only matching session skills |
| CLI schema and side effects | [docs/hub-cli.md](docs/hub-cli.md) |
| Project index | `projects/registry.json`, maintained by `scripts/hub.py` |
| Copyable starting points | `templates/`; copy rather than edit for a project |
| Dated proof / runtime records | `evidence/` / ignored `.hub/`; never current acceptance by themselves |

## Commands

Run from the Hub root: `python3 scripts/hub.py <command>`.

Read-only, never executing project code and never writing into a project:
`list`, `where`, `status`, `assess`, `release-check`, `report`, `usage`,
`doctor`. They accept `--json`.

`assess <slug>` grades source integrity, gates, contract, readiness and cost.
`release-check <slug>` composes the release verdict (valid contract, both gates
at the current HEAD, hosted runner, artifact hashes). Both use the verdicts below.

Mutating: `add` updates registry metadata; `remove` drops only its entry; `new`
creates an empty project directory. `verify <slug> [--gate verify|acceptance|release]`
explicitly executes the configured gate: 300 s default, 1800 s maximum, bounded
output, process-group termination, and one run at a time via `.hub/verify.lock`.
Task authorization is required; asking for status does not authorize execution.

## Verdicts

Every claim is graded `VERIFIED`, `FAILED`, `BLOCKED`, `NOT_VERIFIED` or
`STALE`; combine areas by severity, never by average.

- A skip is never PASS: a required skipped/not-run check is `BLOCKED`; an unrun lane is at best `NOT_VERIFIED`.
- CI green at a SHA other than the current HEAD is `STALE`.
- An owner or agent claim with no log is `NOT_VERIFIED`.
- Absence of a project quality contract is `NOT_VERIFIED`, never `VERIFIED`.

## Verify the Hub itself

AEH has no registry entry, so its own gate is `bash scripts/selfcheck.sh`: the
test suite, the conformance suite, the structural check and `doctor`, ending in
one `AEH_SELFCHECK=PASS|FAIL` line. Also useful:
`python3 -m unittest discover -s tests -q` and `bash evals/structural-check.sh`.

## Boundaries

- **This is the public framework snapshot of the Hub.** The private half — the
  project registry with real paths, `ops/` host administration, and the dated
  evidence that carries host paths, session ids and run ids — stays in the private
  repository. `scripts/publication-check.sh` is the gate that keeps it that way; run
  it before publishing anything from this tree.
- **AEH is not a software product and needs no remote and no CI.** It is a control
  and knowledge workspace: `scripts/hub.py` reads Git and local evidence, makes no
  network call, and its gate is `bash scripts/selfcheck.sh` run locally. This
  repository has no git remote on purpose, so nothing here is pushed anywhere by
  accident. The public repository `huou07/aeh-framework` exists only to share the
  framework; it is built by `scripts/build-public-snapshot.sh`, which proves the
  snapshot locally before anything is published ([publication](docs/publication.md)).
- One writer per repository at a time, **including AEH**: two sessions in one
  tree fight over the same files. Stop or pause the previous writer and record
  the pause before starting another.
- The registry is an index. Do not copy product roadmaps, source or architecture
  here. A registered source path inside the Hub fails `doctor`, even untracked.
- No daemon, scheduler, database, routing layer or orchestration service.
- Keep verification commands in registry entries. Per-task usage belongs in
  `<project>/.hub/usage.jsonl`: measured, estimated or unavailable, never invented.
- Shared workflow skills live in `skills/`; project-specific skills stay in
  their own repositories. Historical policy is in
  [writing AGENTS.md](docs/writing-agents-md/README.md).
- Author framework docs and skills in English; preserve original attachments as
  labelled archival data. Communicate in the owner's preferred language.
- Git commits use configured identity or explicit
  `git -c user.name=... -c user.email=... commit`. Never discard unrelated work.
- DSH, OpenCode and Codex run normally as `huou07`. Privileged host changes
  (networking, systemd, credentials, routing, publication) stay owner-gated. The
  retired worker services, `aehctl` broker and `/srv/agent-workbench` are history.
