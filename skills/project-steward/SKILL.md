---
name: project-steward
description: Report evidence-based status, choose a next task, prepare a brief or handoff, review release readiness, or analyze outcome and cost for an existing registered project. Do not use for onboarding, implementing ordinary changes, diagnosing a failing check or a standalone prompt-editing request.
---

# Project steward

Status: current. Last reviewed: 2026-10-17.

## Read current state

Resolve the project with the Hub. Use `where`, `status`, `assess`,
`release-check`, `report` and `usage --slug <slug>`; use their --json interface
when the installed Hub supports it. These commands do not execute project gates.
`assess <slug>` grades source integrity, gates, contract, release readiness and
cost; `release-check <slug>` composes the release verdict. Then read the project's
existing tracker, relevant docs and Git history. A registry label is metadata,
and an `assess`/`release-check` verdict is only as current as the ledger record
and HEAD it cites.

Grade every claim with the five verdicts rather than a binary pass/fail:
`VERIFIED` (valid evidence bound to the current exact source), `FAILED` (a check
failed or data is invalid), `BLOCKED` (a required check could not run),
`NOT_VERIFIED` (insufficient evidence: no record, no contract, a claim without a
log) and `STALE` (evidence belongs to another revision, command, contract or
dirty state). A skip is never PASS. Cite the source identity, date and freshness
of existing evidence. Do not silently rerun project code for a status request.
Run checks only within existing authorization.

## Choose work or shape a brief

Name the most useful incomplete user outcome and observable completion. Prefer
work that unblocks that outcome. If comparable tasks need a tie-break, state it.
Use existing product authority and preserve architecture, scope and owner
decisions; do not create a second roadmap or reactivate historical cursors.

A brief states users/journey, desired behaviour and motivation, scope/non-goals,
constraints, acceptance, conditional UX/security evidence and authority. Reuse
an existing brief instead of duplicating it.

## Prompts and handoffs

When a prompt is part of stewardship, include only grounded pointers, scope,
invariants, acceptance and stopping criteria. A small task needs a short prompt.
Standalone requests to write, review or compress a prompt belong to prompt-assist
when the current session exposes that shared skill.

For substantial handoffs, record goal, repository/branch/HEAD, relevant changes,
command/results, unverified items, open issues, next action and authority in the
project's existing tracker or handoff. Do not copy the conversation history.

## Outcome and cost

Use observed usage records. Separate measured, estimated and unavailable values;
missing is not zero. Report acceptance, rework, retries and time to verified
outcome where measured. Do not read protected auth stores or invent an agent score.

## Readiness and stopping

Read `assess <slug>` area by area and `release-check <slug>` as the release
verdict. Review the relevant project gate, the real journey, conditional
UX/security, artifact hashes and rollback evidence. A green build or scanner is
not complete product acceptance.

Report the release readiness with the five verdicts, not Ready/Not ready:
`VERIFIED` only when a valid quality contract exists and both `verify` and
`acceptance` are `VERIFIED` at the current HEAD (with a hosted runner and
artifact hashes when the contract requires them); `STALE` when the evidence
belongs to another revision or command; `BLOCKED` when a required check could not
run; `NOT_VERIFIED` when the contract or evidence is absent; `FAILED` when a gate
failed or data is invalid. Combine areas by severity, and name every unmet
condition. Readiness does not authorize release, public publication or
production deployment.

Stop when the requested report, next action or artifact is supported. Do not
implement the next task, execute deployment or orchestrate workers merely because
a plan exists.
