---
name: ui-ux-review
description: Design or review user-visible interfaces for usability, consistency and accessibility. Use when adding a new screen or flow, changing navigation or interaction, or when asked to review UX. Do NOT use for backend-only work, single-value CSS tweaks, or to re-check a passing build.
---

# UI/UX review

A build pass establishes no UX acceptance. Read the project's design, UX and
testing authorities first; keep its components, terminology and platform rules.
Resolve source SHA, dirty changes, user outcome, target runtime and input device.
Implement fixes only within the task's authorization.

## Select evidence for the claim

Choose the cheapest existing tool capable of answering the actual question.
Escalate when its evidence class cannot answer it; do not run every layer.

| Claim | Adequate observation | Limitation |
|---|---|---|
| Source/markup preflight | Compiler, lint, static rendered-markup checks | No JavaScript, browser accessibility, focus or layout proof |
| Semantic | Actual browser ARIA/role assertions or Flutter semantics tree; native accessibility/instrumentation where needed | Names/roles/states/actions do not establish appearance or journey completion |
| Behavioral | Real interaction plus resulting application/backend state | A component fake proves only its component contract |
| Visual | Screenshot/device observation and layout/style measurements at the target viewport/theme | An image alone proves no working journey |
| Native/package | Actual app in the named OS/runtime/package, using its supported driver | Browser frontend evidence cannot substitute; debug app is not installed-package evidence |
| Performance | Bounded workload and target runtime traces/measurements | Screenshot judgement and hosted timing cannot establish device latency |

Use Playwright for Web runtime claims, Flutter semantics/widget/integration
tooling for Flutter, supported Tauri/WebDriver mechanisms for desktop, and
Android-native accessibility/instrumentation for native Android. Commands,
fixtures and adapters belong in the project, never this shared skill.
Standard controls may already provide semantics: inspect their actual tree
before adding wrappers. Decorative paint needs no semantic node; interactive
paint needs meaningful objects/actions and an operable alternative.

## Exercise the outcome

1. Define the representative journey: entry, actions, observable result and
   undo/cancel/recovery. Cover relevant loading, empty, partial, success and
   failure states. Reuse existing tests before adding a harness.
2. Inspect roles, names, state, actions, keyboard reachability and focus entry/
   restoration where relevant. Assert async status feedback. Avoid DOM indexes,
   forced clicks or injected state changes as evidence of user interaction.
3. Run the real journey on authorized targets. Assert the resulting product
   state, not just that a click returned. Web coverage includes the project's
   required narrow width (typically 360px) and desktop; never silently substitute.
4. For visual claims retain a small representative set: viewport/window, theme,
   state and screenshot/measurement. Inspect hierarchy, clipping, overflow,
   contrast and visible focus. Use vision/human judgement where structured
   evidence cannot answer; do not require cross-platform pixel identity.
5. For native/package claims run the actual target. Keep gameplay, media
   correctness, OS enforcement and performance evidence distinct from UI semantics.
6. After a confirmed defect, pin a deterministic regression at the cheapest
   adequate layer. Preserve assertions and security boundaries. After two failed
   guesses, record observed/expected/evidence/attempts/hypotheses and make the
   next check discriminate causes before another repair.

## Evidence and stopping contract

Report only the classes actually established: IMPLEMENTED, VERIFIED_SOURCE,
VERIFIED_SEMANTIC, VERIFIED_BEHAVIORAL, VERIFIED_VISUAL, VERIFIED_NATIVE, ACCEPTED.
These are claim types, not automatic cumulative promotions. Keep project
vocabulary and map it to these classes without rewriting historical records.
ACCEPTED requires the project's authoritative CI/owner gate for the exact source
and target. Existing CI configuration, a skip or a historical pass is insufficient.

For each result name source identity (including WIP), target/tool version,
journey/state, command and observed output, artifacts, limitations and
BLOCKED/UNVERIFIED items. Separate heuristic findings from observed defects;
give reproduction, severity and the smallest remedy. Stop when the scoped
outcome has adequate evidence or a concrete capability/authority boundary is
reached. Respect resource budgets; never launch forbidden targets to fill a gap.
No new design system, orchestration service or blanket screenshot suite.
