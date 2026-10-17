# Hub guide

AEH is a control and knowledge workspace. Product source, architecture, task
state and acceptance live in each independent repository outside this tree.
Resolve projects through `python3 scripts/hub.py where <slug>`; the configured
workspace root is in `hub.config.json`. Preserve existing Git work.

## Find the authority

| Need | Reference |
|---|---|
| Documentation navigation | [docs/README.md](docs/README.md) |
| Engineering task and concise project guidance | [Engineering guide](docs/engineering-guide.md) |
| Evidence classes, UX and trust boundaries | [Quality and security](docs/quality-and-security.md) |
| Task, corrective or handoff prompt | [Prompting](docs/prompting.md) |
| Available workflow selection | [Skills](docs/skills.md); load only matching session skills |
| CLI schema and side effects | [Hub CLI](docs/hub-cli.md) |
| Project index | `projects/registry.json`, maintained by `scripts/hub.py` |
| Copyable starting points | `templates/`; copy rather than edit for a project |
| Dated proof / local runtime records | `evidence/` / ignored `.hub/`; never current acceptance by themselves |
| Owner host administration | [ops/README.md](ops/README.md), [worker state](ops/README.md) |

## Operate

Run from the Hub root: `python3 scripts/hub.py <command>`.

- `list`, `where`, `status`, `report`, `usage`, `doctor` read evidence; they
  never execute project code. Read-only commands accept `--json`.
- `add` updates registry metadata; `remove` removes only its entry.
  `new` creates an empty project directory. These are explicit mutations.
- `verify <slug> [--timeout N]` explicitly executes the configured project gate:
  300s default, 1800s maximum, bounded output, process-group termination.
  Task authorization is required; asking for status does not authorize execution.
- Hub checks: `python3 -m unittest discover -s tests -q`; instruction contract
  checks and their limitations are in [evals/README.md](evals/README.md).

## Boundaries

- The registry is an index. Do not copy product roadmaps, source or architecture
  here. Registered source inside the Hub fails doctor, even when untracked.
- No daemon, scheduler, database, routing layer or orchestration service.
- Keep verification commands in registry entries. Per-task usage belongs in
  `<project>/.hub/usage.jsonl`: measured, estimated or unavailable, never invented.
- Shared instructions/skills have one canonical source under
  `/srv/agent-workbench`; project skills stay in their repository. See
  [skill ownership](docs/skills.md). Do not rewrite provider caches for style.
- Author framework docs and skills in English; preserve original attachments as
  labelled archival data. Communicate in the owner's preferred language.
- Git commits use configured identity or explicit `git -c user.name=...
  -c user.email=... commit`. Never discard unrelated work.
- Workers have no general sudo. Host setup under `ops/` is owner-run; the
  installed `/usr/local/bin/aehctl` is the fixed agent capability entrypoint after
  owner installation. See [capabilities](ops/README.md).
  Never execute the source installer or guest launcher through agent tools.
  Check live systemd state
  before relying on `agent-workbench-dsh@3080.service`; recorded deployment
  summaries are historical evidence.
