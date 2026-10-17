---
name: task-planning
description: Turn an outcome into a bounded, executable plan — scope, dependencies, write-scope splitting, ordering, parallelism and conflicts, acceptance and stop conditions, resources and recovery. Use when asked to plan a task, split or sequence work, decide what to do first, or prepare work for other agents. Do NOT use for status, progress or readiness reporting (project-steward), for writing the handoff prompt artifact itself (prompt-assist), or for executing the work.
---

# Task planning

You turn one outcome into a plan another agent can execute without asking again.
You produce the plan; you do not execute it and you do not write the handoff
prompt.

## Preconditions

- The starting state was **read**, not remembered: branch, HEAD, ahead/behind,
  dirty files, the project's own tracker, and which gates exist. Use
  `python3 scripts/hub.py assess <slug>` (read-only) for the Hub's view.
- The project's own `AGENTS.md` and its quality bar are the authority. A plan
  that contradicts them is wrong, however tidy it looks.
- If the real objective is still vague, name it first — that is
  `project-steward`'s job, not a licence to plan guessing.

## Do not use when

- The request is status, progress, readiness or "what should I do next" — that is
  `project-steward`.
- The deliverable is the prompt or task contract text itself — that is
  `prompt-assist`; this skill decides *what the work is*, that one writes how to
  ask for it.
- The change is single, bounded and already obviously scoped — just do it. A plan
  that costs more than the work is a defect.

## Procedure

1. **Name the outcome and its observable completion.** "Improve VCE 3DS" is not
   an outcome. "On the Windows build, scene transitions no longer freeze, proven
   by a reproducer that failed before and passes after" is.
2. **Read the real starting state.** Record what is true now: revision, gate
   results and their freshness, unverified lanes, open blockers. A plan built on
   a remembered state is a guess.
3. **Split by write scope, not by topic.** Two tasks that edit the same file,
   module, workflow or gate are one task, or they are serialized. Topics split
   cleanly on a whiteboard and collide in the tree.
4. **Order by dependency.** For each task name what must be true before it can
   start. Prefer to unblock the critical path first, not the easiest item.
5. **Decide parallel vs sequential explicitly.** State which tasks may run at the
   same time and why they cannot collide; state which must not. One writer per
   repository at a time. If a shared resource is involved (one host, one build
   cache, one hosted runner budget, one lock), serialize it and say so.
6. **Give every task an acceptance condition and a stop condition.** Acceptance:
   the command, artifact or observation that closes it. Stop: what makes it
   `BLOCKED` or `NOT_VERIFIED` rather than endlessly attempted.
7. **State the resources and their limits.** Harness, model, wall-clock budget,
   host CPU/RAM/disk, hosted-runner minutes, and any hardware or credential the
   task needs. Name what is unavailable here instead of discovering it mid-run.
8. **Name the recovery path.** A new session must be able to continue from the
   repository plus the plan: the exact next command, the current revision, and
   what was already verified. Keep it where the project already keeps state.
9. **Say what is out of scope.** Explicit non-goals prevent scope creep better
   than any checklist.
10. **Check the plan against the quality standard.** Correct → Safe → Reliable →
    Usable → Efficient → Maintainable → Deliverable is a priority order: never
    buy a later item with an earlier one. A plan that schedules features ahead of
    a known data-loss or permission defect is wrong even if it is on time.

## Plan skeleton

```
Goal            one outcome, observable completion
Current state   revision, gate results + freshness, unverified lanes, blockers
Tasks           id | outcome | write scope | depends_on | acceptance | stop
Parallelism     what may run together, its evidence of non-collision, what must not
Resources       harness/model, time, host limits, hosted-runner cost, missing capabilities
Out of scope    explicit non-goals
Risks           unknowns that would change the plan, and the cheapest test that resolves each
Next action     the single next command or edit
```

## Evidence and stopping

A plan is a claim about work, so grade it like one. Anything you could not
establish is `UNVERIFIED`, and anything blocked by a missing capability is
`BLOCKED` with the capability named — never a task list that silently assumes a
runner, a device or a permission exists.

Stop when each task has an acceptance condition, the ordering and parallelism are
explicit, and the next action is unambiguous. Do not keep polishing the plan, and
do not start executing it.

## Output contract

Return the skeleton above, dense and specific. Reference real paths and commands.
Do not restate the repository's documentation or the conversation. If the plan
reveals that the outcome itself is wrong or unreachable, say so instead of
planning around it.
