# Operating model

Type: Explanation/reference

Purpose / authority: Ownership and evidence semantics

Applies to: All Hub users and agents

Not a source of truth for: current Git, CI, runtime or project task state

Status: current
Last reviewed: 2026-10-17

## Who owns what

| Owner | Owns |
|---|---|
| **Git repository** | project source, history, task state, decisions |
| **CI / deterministic tools** | machine-verifiable quality gates |
| **DSH** | the remote UI and sessions you talk to |
| **Codex / OpenCode** | code exploration, editing, reasoning, verification |
| **Hub** (`~/AEH`) | navigation, registry, templates, aggregate reporting |
| **Harness instructions** (owner-controlled user configuration; project guidance remains in each repository) | short, non-project-specific rules |

## Boundaries

- The Hub is **not** a parent Git repository of project source. Project repos are
  siblings under `~/Projects/`, not children of the Hub tree.
- `hub.py doctor` enforces that a registered project path never resolves inside
  the Hub repository.
- The Hub holds no secrets, no credentials, no machine-specific personal data,
  and no duplicated project architecture or history.

## Lifecycle states

`idea` → `active` → `paused` → `done` / `archived`.

The state lives in `projects/registry.json` and is a *label* only. Derived
reality (git state, verification result) always comes from `hub.py status`, which
reads Git and recorded verification without executing project code. Only the
explicit `hub.py verify` command executes the configured gate. A registry label is never accepted as
evidence of progress.

## Single source of truth rule

If a fact exists both in the project repository and in the Hub, the repository
wins and the Hub entry is a pointer. This prevents drift, which is the main way a
control workspace turns into a stale lie.

## Roles vs. commands

- **Deterministic** (must be a script, not a judgement call): path validation,
  slug collision checks, registry read/write, git status, usage aggregation.
- **Judgement** (belongs to the agent): architecture choice, whether a test
  meaningfully covers a user journey, whether work is release-ready, how to turn
  a vague idea into scoped acceptance criteria.
- **Skill** (a repeatable judgement procedure with a clear trigger): onboarding,
  stewardship, debugging, security review. Skills should not contain anything a
  script could do deterministically or that global rules already say.
