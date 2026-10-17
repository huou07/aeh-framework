# Prompting for coding agents

Type: How-to/reference

Purpose / authority: Prompt artifact procedure

Applies to: Explicit prompt and handoff requests

Not a source of truth for: current Git, CI, runtime or project task state

Status: current
Last reviewed: 2026-10-15

How AEH turns vague owner requests into prompts that execute well. For the
full brief/handoff shapes, see `project-steward` and
`templates/project-brief.md` — this document does not repeat them.

## Vague idea → actionable task

Convert, in this order: outcome (what someone can do afterwards), scope and
non-goals, constraints, acceptance (observable), authority (what needs a
human). If the outcome is unclear, narrow to an MVP first; never write a big
spec for a vague goal. One missing essential decision → one focused question.
Anything else → safe defaults, stated.

## Project-aware context retrieval

Resolve the project via the Hub, then pull only what changes execution:
branch/commit, real paths, the project's own verify commands, governing
invariants. Read-only first (status, log, docs); open files only when the
task names them. Verified facts and assumptions go in separate piles, and the
prompt says which is which.

## Context budgeting and progressive disclosure

Every included line must raise the chance of correct execution. Prefer
pointers (`docs/player-layering.md`, `app.py:3931`) over pasted content;
Histories, unrelated reports, and whole conversations never belong in a
prompt. Start small; let the agent pull more.

## Proportionality

Small task → a few lines. Medium → outcome, context, scope, verification,
stop condition. Large/handoff → plus repo state, risks, authority, durable
state. A short prompt that executes beats a long prompt that hedges — see
below.

## Failure patterns

Mega-prompt for a one-line fix; invented repo state or CI results; prescribed
steps the agent would choose better; role-play and motivational filler;
repeated prohibitions; pasted history as "context"; no stopping condition, so
the agent optimizes forever; acceptance as checklist instead of outcome.

## Handoffs

Real workspace path, verified branch/commit, outcome, relevant existing work,
exact verify command, what must not be overwritten. Independently
understandable, no duplicated Git/Hub state, no claimed sessions.

## Modes and corrective prompts

One prompt-assist procedure supports brief, task, handoff, corrective, review and
compress. Brief shapes an already established product outcome; project-steward
owns prioritization and source project state. Choose the mode by artifact need,
never split into more skills without evaluation evidence.

Delivery: an artifact written for a product project belongs in that project as
`docs/prompts/<NAME>.md`. To run it in the project's workspace so the owner can
watch it in the GUI, follow [session handoff](session-handoff.md); the launcher's
exit code, not the click, decides whether the prompt arrived.

Corrective artifact:

```text
Observed: actual failure, target and source identity
Expected: observable user/product outcome
Evidence: exact command/result, reproduction or artifact
Already attempted: each change and observed result
What those attempts ruled out: supported exclusions; unknown if inconclusive
Next discriminating check: falsifiable hypothesis and smallest distinguishing check
Forbidden shortcuts: preserved invariants, assertions and security boundaries
Acceptance: required evidence class, outcome and authoritative gate
Stop condition: outcome evidenced, or concrete capability/authority blocker
```

After two speculative repairs of the same failure, stop guessing and investigate.
Do not enlarge the prompt to repeat urgency. State competing hypotheses and what
new observation will distinguish them before another edit.

Do not invent failure details. Actual diagnosis of a failing test/build belongs
to verify-debug; prompt-assist only writes the requested corrective artifact.
Evaluate outcome, grounding, proportionality, acceptance and authority using
positive, subtle, negative-neighbor and no-skill cases. Keep static contract
checks separate from live routing and accepted outcomes.

## When prompting is not enough

If agents repeatedly fail the same task despite good prompts, the fix is not
a longer prompt. Suspect, in order: missing tool, missing evidence path,
unclear invariant (make it a lint/test), bad environment, or a task not worth
automating. Fix the repository, not the prose.

## Examples

Short beats long — a one-line fix:

```text
# Good (small): everything the agent needs, nothing else
Fix the off-by-one in `upload_specs` (`app.py:4141`) that rejects 0-byte
cover art. Keep chunked-upload behavior unchanged.
Done when the reported case passes, `bash tools/verify-project.sh` passes,
and the diff touches only the size check. Do not weaken tests.
```

```text
# Bad (same task): zero additional task information, all decoration
YOU ARE A WORLD-CLASS PRINCIPAL ENGINEER. THINK VERY DEEPLY. NEVER GIVE UP.
Read the ENTIRE repository first. Rewrite whatever looks unclean. ...
```

Medium — vague improvement, grounded before writing:

```text
# Example request: "make the game page less cluttered"
Outcome: the VCE game-detail page shows one primary action and no
duplicated metadata on desktop and 360px widths.
Context: `app.py:game_page` (verified branch `feature/...`, commit
`9624423`); design authority `docs/design-system.md`.
Non-goals: player internals, backend routes.
Done when the representative journey (library → detail → Play) completes
in the real UI and `bash tools/verify-project.sh` passes.
Assumed: no new artwork. Unverified: narrow-viewport rendering (no browser
on this host) — state the result as static review.
```
