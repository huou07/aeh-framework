# Agentic Engineering Hub

> **This is the public framework snapshot.** [PUBLICATION.md](PUBLICATION.md) says
> exactly what it contains and what deliberately stays in the private Hub: the
> project registry with real paths, `ops/` host administration, and dated evidence.

A small, version-controlled **control and knowledge workspace** for software
projects. Open this directory in DSH (or Codex / OpenCode through ACP) and
drive it in natural language.

This repository contains **no project source code**. Every project is an
independent Git repository under the workspace root (`~/Projects/`). The Hub
holds only navigation, registry, templates and aggregate reporting.

## Quick start

```bash
cd ~/AEH                 # this directory
python3 scripts/hub.py doctor        # self-check
python3 scripts/hub.py list          # registered projects
python3 scripts/hub.py new --slug my-tool   # create isolated workspace
python3 scripts/hub.py add --slug my-tool --path ~/Projects/my-tool  # writes registry
python3 scripts/hub.py status my-tool       # read-only: Git/evidence, no project code
python3 scripts/hub.py verify my-tool       # explicitly executes the bounded project gate
python3 scripts/hub.py report              # aggregate view
```

## Natural-language entry points

| You say | What happens |
|---|---|
| "Organize project ABC" | `project-bootstrap` skill → workspace, Git repo, project AGENTS.md, verification, registry entry |
| "Show progress of ABC" | `project-steward` → real Git + test evidence, honest implemented/tested/blocked split |
| "Write me a prompt for ABC" | `project-steward` → grounded, task-proportional implementation brief |
| "Write/shorten a prompt for task X" | `prompt-assist` (Hub-local skill) → concise prompt artifact; see `docs/prompting.md` |
| "Continue the top task in ABC" | `project-steward` → next high-value task with measurable completion |
| "Is ABC ready for release?" | `project-steward` → evidence-based review, not a checklist |
| "How efficient was ABC?" | `project-steward` + `hub.py usage` → measured/estimated/unavailable split |
| "Import files from old project" | `project-bootstrap` → selective, reviewed, provenance-tracked migration |

## Design rules

- Deterministic tooling (Python stdlib, Git) owns path validation, registry and
  reporting. Agents own judgement. No daemon, scheduler, database or router.
- Git history, tests and CI are the sources of truth; the Hub is an index.
- Harness-specific instructions stay small and non-project-specific; project knowledge
  lives in each project's own `AGENTS.md`.
- Shared skill source lives once in `~/AEH/skills`. Worker
  harness profiles expose it through native discovery paths; individual skills
  are loaded on demand. Do not copy the library into a project or user HOME.

See [AGENTS.md](AGENTS.md) for the operating rules and
[documentation index](docs/README.md) for the workflow reference and
[engineering guide](docs/engineering-guide.md) for practical guidance extracted
from the retained deep research.

## Layout

```
AGENTS.md            navigation map for agents
README.md            this file
hub.config.json      workspace root + registry location
docs/                operating model, onboarding, delivery, quality, cost, prompting
templates/           project AGENTS.md, brief, handoff, ADR, review checklist
projects/registry.json   project index (machine-owned)
scripts/hub.py       deterministic CLI
evidence/            hub self-test evidence
```

## Command effects

`list`, `where`, `status`, `report`, `usage`, and `doctor` inspect existing
metadata/evidence. `new` creates a directory; `add` writes registry metadata;
`verify` runs the registered command with a timeout and output limit. Registry
metadata is not proof that a project's current code passes verification.

## Adding a project

1. Describe the outcome and constraints to the agent (no long questionnaire —
   labelled reversible defaults are fine).
2. The agent creates the workspace, Git repo, project guidance and verification.
3. The agent registers it: `python3 scripts/hub.py add --slug <slug> --path <abs path>`.
4. From then on the project repo is authoritative; the registry just points at it.
