# Cost and evaluation

Type: Reference

Purpose / authority: Measurement definitions

Applies to: Task usage and evaluations

Not a source of truth for: current Git, CI, runtime or project task state

Status: current
Last reviewed: 2026-10-13

The primary metric is **accepted useful work relative to total cost and human
rework** — not tokens generated, not agent actions, not activity.

## What is recorded

Per task, at `<project>/.hub/usage.jsonl` (one JSON object per line):

| Field | Notes |
|---|---|
| `task_id` | stable identifier |
| `project` | slug |
| `started_at`, `ended_at` | ISO-8601, wall time |
| `model`, `provider` | if known |
| `input_tokens`, `output_tokens`, `reasoning_tokens` | if the provider exposes them |
| `cost_usd`, `cost_source`, `pricing_date` | reported, or calculated with a stated price table |
| `tool_calls`, `repeated_attempts` | where measurable |
| `verification` | result of the project's real checks |
| `rework_events` | human corrections / re-dos |
| `skill_activated` | if observable |
| `status`, `accepted` | final outcome |

Every quantity is tagged **measured**, **estimated**, or **unavailable**.
Never fabricate a number. `unavailable` is a legitimate, useful value.

## Rules

- A free or bundled model is **not** automatically zero opportunity cost; record
  it as measured-zero-currency but note the opportunity cost.
- Do not read private auth stores, raw prompts, or unrelated user data to gather
  usage. Prefer documented usage output and existing lawful logs.
- Provider logs have a source and a date. Record both; prices change.

## Reporting

```bash
python3 scripts/hub.py usage --slug <slug>     # one project, per task
python3 scripts/hub.py report                  # Hub aggregate
```

The report separates measured totals from estimated totals from unavailable
fields, and shows rework and repeated attempts. No daemon, database, or
dashboard server.

## Evaluation suite

`evidence/` and the Hub self-test keep a small representative baseline so a later
change to prompts, skills, models or tools can be compared against it rather than
debated. A suite that costs paid inference is run only with owner authorization;
deterministic structural checks run for free and are the default.

## Outcome evidence

Optional task fields: first_pass_accepted, verification_retries, escaped_defects,
policy_violations, ux_findings_reopened, time_to_verified_outcome_s. Define the
observation window and source in the project. Missing acceptance and rework are
unknown, not rejected or zero. Unlabelled quantities are unavailable; numeric
booleans are invalid. JSON totals remain null when no measurement exists.
Keep measured and estimated totals separate; do not invent an aggregate agent
score. Structural fixtures validate contracts, not actual model routing or task
quality. Candidate promotion requires observed outputs and comparison to baseline.

## Interpreting rework

High tokens with low accepted work means rework or thrash, not productivity.
Repeated identical failures and long non-converging loops are the signal to look
at — not the raw token total.
