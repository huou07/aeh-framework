# Shared skills catalog

Purpose: route to one relevant workflow without preloading the library.
Authority: navigation; host policy and session tool permissions govern execution.
Status: current
Last reviewed: 2026-10-17.

| Skill | Trigger | Neighbor / exclusion |
|---|---|---|
| code-investigate | Code location, callers, impact, bug investigation | Ordinary listing or already grounded edit |
| project-bootstrap | New project, onboarding, selective migration | Routine coding or status |
| project-steward | Existing project status, next task, brief, handoff, readiness, cost | Bootstrap, failing check diagnosis, standalone prompt edits |
| prompt-assist | Explicit write/improve/compress/handoff prompt artifact | Ordinary coding, status, actual diagnosis (verify-debug) |
| task-planning | Plan, split, sequence or parallelise work; scope, dependencies, acceptance and stop conditions | Status/readiness (project-steward), the prompt artifact itself (prompt-assist), executing the work |
| verify-debug | Failed check or requested implementation verification | Status-only or prose-only work |
| sustained-repair | Grounded work failing repeatedly, spanning a handoff or session, or facing context/quota pressure | One failing check (verify-debug), status reporting (project-steward), retry without new evidence |
| security-review | Scoped security/trust-boundary, commit, release or import review | Trivial wording or correctness debugging |
| skill-maintainer | Instruction/skill maintenance, import or misfire | Product implementation |
| ui-ux-review | New screen or flow, navigation or interaction change, or an explicit usability/accessibility review | Backend-only change, single-value style tweak, or a build/pass question (verify-debug) |

Canonical bodies are in [skills](../../skills/). Compatibility aliases point to the
same source. Load through the current harness only when the trigger applies.
Disk presence, historical catalog entries and a passed structural check do not
establish current discovery, permissions or successful model behaviour.

`ui-ux-review` was promoted to this library on 2026-10-14, `prompt-assist` on
2026-10-17 and `task-planning` on 2026-10-18 (the Hub had no Plan responsibility
with an executable procedure before it) (see instruction-history/2026-10-14-ui-ux-review-promotion and the
2026-10-17 quality pass). Both are canonical bodies under `skills/`; the
Hub-local `.opencode/skills/` and `.agents/skills/` paths are symlinks to them.
Project-specific skills retain their own scope and authority.
Project skills that duplicate shared procedures are retired in favour of the
shared body and archived as project history, not copied in parallel.
Provider skills are versioned packages; preserve their tools/assets and make only
justified, documented patches. All authored framework artifacts use English;
user-facing conversation follows the user's preferred language.
