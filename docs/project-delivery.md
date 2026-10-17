# Project delivery

Type: How-to

Purpose / authority: Delivery procedure subject to project policy

Applies to: Engineering changes

Not a source of truth for: current Git, CI, runtime or project task state

Status: current
Last reviewed: 2026-10-13 and resume

## The loop

```
understand outcome
→ inspect current state
→ reproduce or establish baseline
→ identify minimal relevant context
→ plan proportionately
→ implement
→ test and observe
→ repair bounded failures        (verify-debug skill)
→ review the actual diff
→ update durable state
→ report evidence
→ prepare handoff or draft PR
```

## Observable completion

Define the desired behaviour before editing. Record implemented / tested /
accepted / unverified separately. Run the smallest meaningful check, repair from
its output, then the relevant broader gate and real user journey. UI changes
require conditional UX evidence (loading, empty, error/recovery, success,
keyboard/focus and applicable viewports); trust boundary changes require security
review. Follow the project's verification authority and the task's authorization.
A prototype needs explicit limits before promotion to product engineering.

## Non-negotiables

- **Never claim a test passed without fresh evidence** from a command you ran.
- A green unit suite is not accepted packaged runtime behaviour.
- A complete checklist is not a useful product.
- Never bypass or weaken a test to advance project status.
- No checkpoint or handoff files for trivial tasks.
- Use Git history and the existing issue tracker instead of parallel sources of
  truth wherever possible.
- Use separate branches or worktrees for potentially conflicting work.
- Use more than one worker only when tasks separate safely; do not let one worker
  edit files owned by another without coordination.

## Bounded repair

Ordinary failures require investigation, not abandonment — and unchanged retries
are not persistence. After two speculative attempts at the same failure, stop
guessing: record the failure, form a falsifiable root-cause hypothesis, and get a
test that discriminates between causes before editing again. See the
`verify-debug` skill.

## Durable state

A new session must be able to continue from the repository alone, without an old
conversation's invisible context. For substantial tasks keep a recoverable state:

- the goal,
- the current commit,
- verified evidence (commands and results),
- outstanding issues,
- the next command or action.

Store it where the project already keeps such state (issue, `HANDOFF.md`,
`docs/`), not in a duplicate private log.

## Stopping

Stop when evidence supports the outcome, an authorization boundary is reached, or
a real blocker is demonstrated. Do not keep going to look thorough.
