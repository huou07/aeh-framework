---
name: sustained-repair
description: Sustain one authorized outcome across many turns, repeated failures, or context and quota pressure without abandoning it or retrying blindly. Use when work is already grounded and failing repeatedly, spans a handoff or session boundary, or when stopping would leave an authorized outcome unfinished. Do not use for a single failing check (use verify-debug), for status, readiness or next-task reporting (use project-steward), or as licence to retry without new discriminating evidence.
---

# Sustained repair

Persistence means finishing the authorized outcome with better evidence and
better methods. It is not infinite retries, wider scope, or ignoring a real
boundary.

Division of labour: `verify-debug` owns diagnosis and repair mechanics for one
failing check. This skill owns effort allocation, handoff and stopping across
turns. When a clause below restates host policy or another shared skill, that
source governs and this skill only names when it applies.

## Preconditions

Establish branch, HEAD, working tree, the authorized objective and its
acceptance threshold. Confirm the work is already grounded in real code or
evidence: this skill extends a diagnosed task and does not start discovery.
Keep the original requirement and threshold fixed. Persistence never redefines
success, and never authorizes more scope than the request already allowed.

## Sustain the repair loop

1. Each attempt names a falsifiable hypothesis and the check that discriminates
   it from neighbouring causes, recorded where a later session can read it.
   Host policy already caps speculative repairs at two attempts per failure:
   after that, change the hypothesis or the reproduction method rather than
   increasing the attempt count. If no discriminating check can be formed, that
   is the finding to report, not a reason to keep trying.
2. Re-run the check that proves the changed claim. A green lower layer is not
   evidence that a packaged or user-facing journey works; prove that journey
   separately or report it as unverified.
3. Parallelize only when the measured coordination benefit clearly exceeds its
   cost. Fan-out without a discriminator usually multiplies unverified results
   instead of evidence.
4. Commit verified progress atomically at safe handoff points so an interrupted
   run never leaves a half-applied change indistinguishable from intended work.

## Handoff and resume

Leave a durable handoff before context or quota becomes unsafe, and on any
interruption: objective, branch and exact HEAD, completed and current work,
decisions and invariants, checks and evidence, known limitations, next action.
Prefer the project's existing handoff or tracker; do not start a second one, and
do not spend the remaining context on unfinished speculative work instead.

On resume, read that durable state and the exact Git identity first. Do not
rediscover completed work or re-run checks whose evidence is already recorded.

## Stop only at a real boundary

Stop and ask the operator only when the next action exceeds existing
authorization, requires a credential or capability that cannot be safely
obtained or substituted, or contradicts an authoritative requirement. Do not
stop because the work is long, difficult, temporarily failing, or needs another
diagnosis.

Authority stays fail-closed: an approval that cannot be answered ends the
request rather than granting it, and protected owner credentials are never
substituted, bypassed or guessed. Persistence never weakens an acceptance
threshold, test, security, accessibility, performance target or invariant to
manufacture progress.

Where the harness tracks a goal, only a concrete external condition that
persists across consecutive rounds may close it as blocked. Difficulty,
uncertainty, or useful remaining work is not a block.

## Stop and report

Stop when the outcome has evidence at its acceptance threshold, or when a real
boundary blocks it. Report implemented, tested, accepted, blocked and unverified
items separately, with source identity and the exact checks run. Elapsed effort,
retry count or confidence is never a result.
