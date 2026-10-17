# Hub CLI reference

Type: Reference

Purpose / authority: local deterministic command contract, schema version 1.

Applies to: Hub consumers.

Not a source of truth for: acceptance or release permission.

Status: current

Last reviewed: 2026-10-17

Run `python3 scripts/hub.py <command>` from the Hub root.

| Commands | Effects | JSON |
|---|---|---|
| list, where, status, assess, release-check, report, usage, doctor | Read metadata, Git and stored evidence; no project gate execution | Append --json |
| add | Update registry | No |
| new | Create empty project directory | No |
| remove | Drop a registry entry; never touches the project directory | No |
| verify | Execute configured project code under time/output bounds; append local evidence tagged with its gate (`verify`, `acceptance` or `release`) | No |

Existing text output remains default; usage now shows unknown counts explicitly.
JSON emits one stdout object with `schema_version`, `ok`, `command`, `data`.
Errors exit nonzero; diagnostics use stderr, with `data.kind` and `data.message`
in JSON. Categories include missing_project, invalid_input, invalid_config,
invalid_registry, invalid_data. Doctor failure returns structured problems.
Consumers should ignore unknown fields and reject unsupported schema versions.

Examples:

```bash
python3 scripts/hub.py status vce --json
python3 scripts/hub.py usage --slug vce --json
python3 scripts/hub.py doctor --json
```

List entries are registry metadata. Status/report include Git observations,
verification command, recorded result, freshness and evidence-read diagnostics.
Status also prints a `stale:` line: a human-readable prompt to re-check an entry
that has not been touched in over 60 days, whose repository has not committed in
over 180 days, or that has no verification command. It is a signal, not a
judgement, it never blocks, and it never executes project code.
Usage separates measured/estimated totals (null when absent) and unknown counts;
missing files have availability unavailable. Acceptance unknown is counted
separately from explicitly rejected tasks.

New verification records go to ignored `.hub/verification.jsonl`. Existing
`evidence/verification.jsonl` remains a read fallback per project; it is neither
rewritten nor deleted. **Precedence is by file, not by timestamp:** records in
`.hub/` win outright over records in `evidence/` for the same slug, regardless of
which is newer. Do not merge the two files by hand — move the historical file out
of the tree in one dated step, or the older records will silently shadow the
newer ones. `evidence/verification.jsonl` is gitignored, so it is local data and
cannot be shared or reviewed. Records carry command hash, duration, source
identity before and after execution, timestamp and result. Source changes during
verification, dirty trees, changed HEAD and changed commands invalidate current
PASS claims. Hashing the command text does not prove unchanged external tools or
ignored inputs. Runtime evidence is local data, not CI or owner acceptance.

## Verdict vocabulary

`assess` and `release-check` grade evidence with exactly one of five verdicts
(the [quality interface](quality-interface.md) §2):

| Verdict | Meaning |
|---|---|
| `VERIFIED` | Valid evidence bound to the current exact source identity; every required check ran and passed. |
| `FAILED` | A check ran and failed, or evidence/artifact data is invalid or mismatched. |
| `BLOCKED` | A required check could not run for a named environmental, platform, authority or resource reason. |
| `NOT_VERIFIED` | Insufficient evidence: no record, no contract, a claim without a log, no acceptance record. |
| `STALE` | Evidence exists but belongs to a different revision, command, contract or dirty state. |

Rules: a skip is never PASS; absence of a quality contract is `NOT_VERIFIED`;
malformed ledger data is `FAILED`; severity order is
`FAILED > BLOCKED > STALE > NOT_VERIFIED > VERIFIED`. Averaging or scoring is
forbidden — one severe area is not diluted by good ones. Every non-`VERIFIED`
verdict carries a reason string. A CI run green at another SHA is `STALE`; an
owner claim with no log is `NOT_VERIFIED`.

## assess — quality-evidence assessment (read-only)

```bash
python3 scripts/hub.py assess <slug> [--json]
```

Read-only: it never executes project code, never writes into a project
directory and never installs anything. Text or JSON; the JSON envelope is the
existing `emit_json` (`schema_version`, `ok`, `command`, `data`).

`data` ([quality interface](quality-interface.md) §6):

```json
{
  "slug": "or",
  "path": "<workspace-root>/OR",
  "generated_at": "2026-10-17T16:00:00+00:00",
  "overall": {"verdict": "NOT_VERIFIED", "blockers": ["…"],
              "advisories": ["cost: …"], "next_actions": ["…"]},
  "areas": {
    "source_integrity": {"verdict": "VERIFIED", "head": "…", "branch": "…",
      "upstream": "origin/main", "ahead": 0, "behind": 0, "dirty": false,
      "dirty_files": 0, "notes": []},
    "gates": [
      {"gate": "verify", "command": "…", "required": true, "verdict": "VERIFIED",
       "recorded_result": "PASS", "head": "…", "recorded_at": "…",
       "duration_s": 33.8, "freshness": "CURRENT for clean HEAD …",
       "skipped": [], "not_run": [], "reason": null}
    ],
    "contract": {"verdict": "FAILED", "path": null, "schema_version": null,
      "required_gates": [], "release_gates": [], "problems": ["…"]},
    "release_readiness": {"verdict": "NOT_VERIFIED", "reasons": ["…"], "missing": ["…"]},
    "cost": {"verdict": "NOT_VERIFIED", "availability": "unavailable",
      "records": null, "reason": "no .hub/usage.jsonl"}
  }
}
```

Deterministic rules:

- `source_integrity`: `VERIFIED` when Git identity and sync state are readable;
  `BLOCKED` when Git is present but identity is unreadable; `NOT_VERIFIED` when
  the path is not a Git repository. `notes` carries dirty, ahead, behind and a
  missing upstream.
- `gates`: one entry per configured gate (`verify`, then `acceptance`). No
  record → `NOT_VERIFIED`; `FAIL`/`ERROR` → `FAILED`; `TIMEOUT` → `BLOCKED`;
  `PASS` with freshness `CURRENT…` → `VERIFIED`; `STALE…`/`historical…` →
  `STALE`; malformed-only ledger → `FAILED`. A required gate named in the
  record's `report.skipped`/`not_run` is `BLOCKED` with that reason **even when
  `result` is `PASS`**. `required` is true when the contract maps a gate name to
  this gate command.
- `cost`: `NOT_VERIFIED` with `availability: unavailable` when the usage file is
  missing; with records, `VERIFIED` only when at least one accepted task is
  recorded. Never invented numbers.
- `overall.verdict` is the most severe area verdict; `blockers` are the ordered
  unique reasons from every non-`VERIFIED` area; `next_actions` are concrete
  commands.

Exit codes: `0` when overall is `VERIFIED`; `1` when `FAILED` (including a read
emergency such as a missing path, which also sets `data.kind`); `3` for
`BLOCKED`, `STALE` and `NOT_VERIFIED`.

## release-check — release verdict (read-only)

```bash
python3 scripts/hub.py release-check <slug> [--json]
```

Read-only composition of `assess`. `data` ([quality interface](quality-interface.md) §7):

```json
{"slug": "or", "verdict": "BLOCKED", "reasons": ["…"], "missing": ["…"],
 "evidence": {"verify": {"verdict": "VERIFIED", "head": "…"},
              "acceptance": {"verdict": "VERIFIED", "head": "…"}},
 "artifacts": [{"name": "…", "sha256": "…", "result": "PASS"}]}
```

`VERIFIED` requires **all** of:

1. a valid quality contract declaring at least one `release_gates` entry;
2. the latest `verify` record `VERIFIED` at the current HEAD;
3. the latest `acceptance` record `VERIFIED` at the current HEAD;
4. no `required_gates` entry appearing in those records'
   `report.skipped`/`report.not_run`;
5. when the contract sets `hosted_ci == "required"`, the HEAD is pushed
   (`ahead == 0`) and the acceptance report's `runner.kind == "hosted"`;
6. every artifact declared in the contract appears in a record's
   `report.artifacts` with a 64-hex `sha256` and `result == "PASS"`.

Otherwise: `FAILED` when a gate failed, an artifact hash is missing or
mismatched, or contract/report data is invalid; `BLOCKED` when a required check
could not run (skipped/not-run lane, unpushed HEAD, no hosted runner, `TIMEOUT`
record); `STALE` when a record is stale; `NOT_VERIFIED` when the contract or the
evidence is simply absent. Reasons name each unmet condition.

Exit codes: `0` only for `VERIFIED`; `1` for `FAILED`; `3` otherwise.

## verify additions

`python3 scripts/hub.py verify <slug> --gate verify|acceptance|release`.

- `--gate release` uses the registry entry's `release` command; an absent
  command records `UNVERIFIED` and exits `3`.
- After the run it ingests the contract's `report` file (default
  `.hub/gate-report.json`), which the project's own gate writes; `hub.py` reads
  it and never executes it. The report may carry `skipped[]`, `not_run[]`,
  `covered_gates[]`, `artifacts[]`, `runner`, `evidence_class` and
  `limitations[]`. Hub validation is loose but fail-closed: a non-object or a
  malformed `skipped`/`not_run` entry makes the record's gate verdict `FAILED`,
  never PASS.
- New ledger fields: `command` (plaintext gate command, not only its hash),
  `source_after` (must equal `source_before` for the record to be current),
  `contract_sha256` (the contract file at run time, `null` when absent),
  `commit_sha256` (sha256 of `command` + `gate` + `contract_sha256`, so a
  changed gate invalidates its record), `report` (the parsed gate report) and
  `hub` (schema marker). Old records are never rewritten or deleted; readers
  ignore unknown fields and tolerate missing ones.
- Before running, `verify` takes a non-blocking exclusive `flock` on
  `.hub/verify.lock` and releases it after. When the lock is held it prints
  `result  : BLOCKED (another verification is already running)` and exits `3`
  **without executing anything**. This is the resource guard: two heavy builds
  must not run concurrently by accident.

## Quality contract lookup

A project owns a machine-readable quality contract. Lookup order, first existing
file wins:

1. `<project>/.aeh/quality.json`
2. `<project>/docs/quality.json`

Schema: `contracts/quality.schema.json`. The contract declares
`required_gates`, `release_gates`, per-gate command mapping, `hosted_ci`,
`report` path, expected `artifacts` and `policies`. A missing contract is not an
error — it is `NOT_VERIFIED` with the reason
`no quality contract at <path1> or <path2>`. An unreadable, unparseable or
invalid contract is `FAILED` with the exact problem strings. **No contract field
may contain a shell command** (keys such as `command`, `cmd`, `run`, `exec`,
`shell`, `script`): a contract that tries to inject one is rejected with
verdict `FAILED`. AEH executes only the owner-approved command in the registry
entry, never metadata. See [the quality standard](quality-standard.md) and
[quality system](quality-system.md).

## Unregistering a project

```bash
python3 scripts/hub.py remove --slug or            # keep recorded results
python3 scripts/hub.py remove --slug or --forget   # also discard them
```

`remove` edits `projects/registry.json` and nothing else. It never deletes a
project directory, a Git repository or any project file, and it says so on every
run. It resolves slugs case-insensitively like every other command, and refuses
an unknown slug without touching the registry.

Recorded verification results are keyed by slug, so removing an entry orphans
them. By default they are kept on disk and the command reports that they are no
longer reachable from the registry; `--forget` discards only that slug's records.
Use `remove --slug <fixture> --forget` to retire a fixture project that is no
longer a project. Archiving or deleting the directory itself remains an explicit,
separate decision by the owner.

## Retiring a fixture

A fixture that has served its purpose has no exit route today, which is why
several fixtures stayed labelled `active` indefinitely. Retire one by
`remove --slug <name> --forget`, then move or delete its directory yourself. Do
not delete the directory first: `remove` reports when the registered path is
already gone, which is useful, but removing the registry entry first keeps the
sequence auditable.

## Project names (slugs)

A slug is the project's own name, so it is not restricted to lowercase
kebab-case. `add` and `new` accept any case, spaces and punctuation, including
non-ASCII (`OR`, `abc todo`, `Dự án`, `my.project`, `项目`). `new` creates the
directory with that spelling verbatim under the workspace root.

Rejected, because they would corrupt the registry, break argument parsing or
escape the workspace directory:

| Rejected | Reason |
|---|---|
| `/` and `\` | path separators; the slug becomes a directory name |
| control characters, leading/trailing whitespace | corrupt text output and CLI parsing |
| `.` and `..` | directory traversal |
| leading `-` | read as a flag; pass `--slug=<name>` |
| more than 100 characters | registry key and CLI ergonomics |

Lookup is case-insensitive: `status OR`, `status or` and `status Or` all resolve
one entry. The entry keeps the spelling it was registered with and JSON output
echoes that registered slug. Because lookup folds case, two entries differing
only by case are ambiguous — `add` refuses the second spelling and `load_registry`
/ `doctor` fail closed on a hand-edited registry containing both.
