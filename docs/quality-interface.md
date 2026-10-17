# Quality interface

Type: Reference (frozen interface).

Authority: the field names, verdict vocabulary and command contracts implemented
by `scripts/hub.py`, `scripts/quality_contract.py` and `scripts/conformance.py`,
and described in [quality system](quality-system.md). The code and the tests in
`tests/` are the executable authority; where this document and the code
disagree, one of them is a defect.

Applies to: Hub tooling and every project quality contract.

Not a source of truth for: current Git, CI, runtime or project task state.

Status: current

Last reviewed: 2026-10-17

Frozen for the 2026-10-17 quality pass. Every name below is implemented and
covered by tests; renaming one is a breaking interface change. A project adopts
the contract by copying [the template](../templates/quality-contract.json) to
`<project>/.aeh/quality.json`.

## 1. Principle

Outcome-first, evidence-first, reuse-first. AEH reports what evidence proves and
never promotes an unproven claim. `assess`, `release-check`, `status`, `report`,
`list`, `where`, `usage`, `doctor` are READ-ONLY: they must never execute project
code, never write into a project directory, never install anything.

## 2. Verdict vocabulary (five states, used everywhere)

| Verdict | Meaning |
|---|---|
| `VERIFIED` | Valid evidence bound to the current exact source identity; every required check actually ran and passed. |
| `FAILED` | A check ran and failed, or evidence/artifact data is invalid or mismatched. |
| `BLOCKED` | A required check could not run for a named environmental, platform, authority or resource reason. |
| `NOT_VERIFIED` | Insufficient evidence: no record, no contract, a claim without a log, no acceptance record. |
| `STALE` | Evidence exists but belongs to a different revision, command, contract or dirty state than the current one. |

Rules, all enforced by tests:

1. `skipped`, `neutral` and `not_run` never count as PASS.
2. Absence of a quality contract is `NOT_VERIFIED`, never `VERIFIED`.
3. A malformed ledger line is invalid data, never a pass.
4. Severity order used to combine area verdicts:
   `FAILED` > `BLOCKED` > `STALE` > `NOT_VERIFIED` > `VERIFIED`.
   Averaging, scoring or "95/100" is forbidden; a single severe area is not
   diluted by good areas.
5. Every non-`VERIFIED` verdict carries at least one human reason string.

## 3. Ledger record — `.hub/verification.jsonl` (v2, backward compatible)

Existing fields stay: `timestamp`, `slug`, `gate`, `result`, `exit_code`,
`duration_s`, `source_before`, `verify_sha256`, `branch`, `head`, `dirty`,
`dirty_files`. `result ∈ {PASS, FAIL, TIMEOUT, UNVERIFIED, BLOCKED, ERROR}`.

New fields written by `hub.py verify`:

| Field | Type | Meaning |
|---|---|---|
| `command` | string | The gate command text, plaintext (not only its hash). |
| `source_after` | object\|null | Git identity after the run; must equal `source_before` for the record to be current. |
| `contract_sha256` | string\|null | sha256 of the project's quality contract file at run time; null when no contract. |
| `commit_sha256` | string | sha256 of the recorded `command` + `gate` + `contract_sha256`, so a changed gate invalidates its record. |
| `report` | object\|null | Parsed gate report (§4) when the contract declares `report` and the file exists after the run. |
| `hub` | string | `hub.py` schema marker, e.g. `"schema=1"`. |

Never rewrite or delete old records. Readers ignore unknown fields and tolerate
records missing the new ones.

## 4. Gate report — optional, written by the project gate

Location: the contract's `report` field, relative to the project root (default
`.hub/gate-report.json`). Written by the project's own gate, read (never
executed) by `hub.py`. Shape:

```json
{
  "skipped": [{"check": "vce-gpu-3ds", "reason": "no physical GPU on this runner"}],
  "not_run": [{"check": "flutter-widget-lane", "reason": "Flutter SDK absent"}],
  "covered_gates": ["source-integrity", "native-build"],
  "artifacts": [{"name": "h07p_0.3.11_amd64.deb", "path": "dist/...", "sha256": "…",
                 "platform": "linux-x64", "result": "PASS"}],
  "runner": {"kind": "local|hosted", "os": "linux", "arch": "x86_64",
             "label": "debian-optiplex", "run_url": null, "run_id": null, "job": null},
  "evidence_class": "VERIFIED_SOURCE",
  "limitations": ["guest security suite not executed"]
}
```

Hub validation is loose but fail-closed: the report must be a JSON object; every
entry of `skipped`/`not_run` must be an object with non-empty `check` and
`reason`; `artifacts` entries must be objects; a non-object or malformed report
makes the record's gate verdict `FAILED` (invalid data), never PASS.

### Hosted evidence

AEH is offline: it reads Git and local evidence and never calls GitHub. A contract
that declares `hosted_ci: "required"` can therefore only be satisfied if the
project records the hosted result locally. It goes in **its own file**,
`<project>/.hub/hosted-evidence.json`, because the project's gate rewrites
`.hub/gate-report.json` on every run and would otherwise erase the proof:

```json
{"head": "<full sha>", "repo": "owner/repo", "branch": "main",
 "workflow": "ci.yml", "conclusion": "success", "recorded_at": "...",
 "runner": {"kind": "hosted", "os": "github-actions", "run_id": "4242",
            "run_url": "...", "label": "ci.yml", "job": "..."}}
```

`hub.py verify` merges it into the record's `report` — and only when `head` equals
the revision being verified. Hosted evidence for another commit is refused with
`hosted evidence is for another revision …`, never silently merged. Copy
[the template](../templates/hosted-evidence.sh) into the project and run it after
a hosted run exists for the current commit:

```bash
bash tools/record-hosted-evidence.sh ci.yml 'Package lifecycle'
```

It records only a `success` conclusion for the exact current commit; when no
successful run exists it exits 3 and changes nothing, so the Hub reports
`BLOCKED` — which is the truthful answer, and the reason a permanently blocked
`release-check` means "bring the hosted evidence home", not "the gate is broken".
Recording a run proves the environment and the run id; it never replaces the
project's own acceptance record for behaviour.

## 5. Quality contract — machine-readable, owned by the project

Lookup order, first existing file wins:

1. `<project>/.aeh/quality.json`
2. `<project>/docs/quality.json`

JSON Schema: `contracts/quality.schema.json`. Required shape:

```json
{
  "schema": 1,
  "project": "VCE",
  "product_type": "emulator",
  "supported_platforms": ["windows-x64", "linux-x64"],
  "required_gates": ["source-integrity", "native-build"],
  "release_gates": ["product-acceptance", "artifact-integrity"],
  "external_requirements": ["windows-3ds-physical-gpu"],
  "hosted_ci": "required",
  "gates": {
    "source-integrity": {"gate": "verify"},
    "native-build": {"gate": "acceptance"}
  },
  "report": ".hub/gate-report.json",
  "artifacts": [{"name": "app.deb", "platform": "linux-x64", "hash_required": true}],
  "policies": {
    "missing_evidence": "block",
    "stale_evidence": "block",
    "skipped_required_gate": "block",
    "production_changes": "require_approval"
  }
}
```

Validation rules (fail closed):

- `schema` must be `1`; unknown top-level keys are an error.
- `required_gates` and `release_gates` are non-empty arrays of unique non-empty
  strings; `release_gates ⊇` nothing (independent lists).
- Every name in `required_gates`/`release_gates` must exist as a key in `gates`.
- Each `gates[x].gate` must be one of `verify`, `acceptance`, `release`.
- **No contract field may contain a shell command** (keys such as `command`,
  `cmd`, `run`, `exec`, `shell`, `script`). A contract that tries to inject one
  is rejected, and the contract verdict is `FAILED`. AEH executes only the
  owner-approved command in the registry entry, never metadata.
- `hosted_ci ∈ {required, optional, none}`; policy values ∈
  `{block, warn, require_approval}` (for `production_changes` only
  `require_approval`/`warn` are valid).
- A missing contract is not an error; it is `NOT_VERIFIED` with the reason
  `no quality contract at <path1> or <path2>`.
- An unreadable, unparseable or invalid contract is `FAILED` with the exact
  problem strings.

Loader interface, module `scripts/quality_contract.py`:

```python
CONTRACT_PATHS = (".aeh/quality.json", "docs/quality.json")

def load_contract(project_path: Path) -> tuple[dict | None, str | None, list[str]]:
    """Return (contract, path_str_or_None, problems). contract is None with a
    reason in problems when absent. problems is non-empty when invalid."""
```

`contract_sha256(path)` returns the sha256 of the raw file bytes, or `None`.

## 6. `hub.py assess <slug> [--json]`

Read-only. Output areas, text and JSON. JSON envelope as the existing
`emit_json` (`schema_version`, `ok`, `command`, `data`).

`data`:

```json
{
  "slug": "or",
  "path": "<workspace-root>/OR",
  "generated_at": "2026-10-17T16:00:00+00:00",
  "overall": {"verdict": "NOT_VERIFIED", "blockers": ["…"], "next_actions": ["…"]},
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
  the path is not a Git repository. `notes` carries `dirty`, `ahead`,
  `behind`, missing upstream.
- `gates`: one entry per configured gate (`verify`, then `acceptance`). Verdict
  from the latest record: no record → `NOT_VERIFIED`; `FAIL`/`ERROR` → `FAILED`;
  `TIMEOUT` → `BLOCKED`; `PASS` + freshness `CURRENT…` → `VERIFIED`; freshness
  `STALE…`/`historical…` → `STALE`; malformed-only ledger → `FAILED`.
  A required gate named in the record's `report.skipped`/`not_run` is `BLOCKED`
  with that reason, even when `result` is `PASS`.
  `required` is true when the contract lists a gate name mapped to this gate
  command, else false.
- `contract`: per §5.
- `release_readiness` per §7.
- `cost`: `NOT_VERIFIED` with `availability: unavailable` when
  `<project>/<usage_file>` is missing; when records exist, `VERIFIED` if at
  least one accepted task is recorded, else `NOT_VERIFIED` (measurement started
  but nothing accepted yet). Never invent numbers. **Cost is advisory:** it is
  reported as its own area and in `overall.advisories`, but it is deliberately
  NOT combined into the product verdict — a project with no usage ledger is not
  thereby an unverified product. Every other area is combined.
- `overall.verdict` = most severe verdict among `source_integrity`, `gates`,
  `contract` and `release_readiness` (worst-of, never an average).
- `overall.blockers` = ordered unique reasons from every non-`VERIFIED` product
  area, plus source-integrity notes.
- `overall.advisories` = ordered unique process notes (currently cost).
- `overall.next_actions` = concrete commands, e.g.
  `python3 scripts/hub.py verify or --gate acceptance`.

Exit codes for `assess`: `0` when overall is `VERIFIED`; `1` when `FAILED`;
`3` for `BLOCKED`, `STALE` and `NOT_VERIFIED`. A read emergency (missing path)
exits `1` with `data.kind`.

## 7. `hub.py release-check <slug> [--json]`

Read-only composition of `assess`. `data`:

```json
{"slug": "or", "verdict": "BLOCKED", "reasons": ["…"], "missing": ["…"],
 "evidence": {"verify": {"verdict": "VERIFIED", "head": "…"},
              "acceptance": {"verdict": "VERIFIED", "head": "…"}},
 "artifacts": [{"name": "…", "sha256": "…", "result": "PASS"}]}
```

`VERIFIED` requires ALL of:

1. A valid contract that declares at least one `release_gates` entry.
2. Latest `verify` record verdict `VERIFIED` at the current HEAD.
3. Latest `acceptance` record verdict `VERIFIED` at the current HEAD.
4. No `required_gates` entry appears in `report.skipped`/`report.not_run` of
   those records.
5. Contract `hosted_ci == "required"` ⇒ `source_integrity.ahead == 0`
   (HEAD pushed, so hosted CI can cover it) and the acceptance record's
   `report.runner.kind == "hosted"`.
6. Every artifact declared in the contract appears in a record's
   `report.artifacts` with a 64-hex `sha256` and `result == "PASS"`.

Otherwise: `FAILED` when a gate failed, an artifact hash is missing/mismatched,
or contract/report data is invalid; `BLOCKED` when a required check could not
run (skipped/not_run, unpushed HEAD, no hosted runner) or a gate record is
`TIMEOUT`; `STALE` when a record is stale; `NOT_VERIFIED` when evidence or the
contract is simply absent. Reasons name each unmet condition.

Exit codes: `0` only for `VERIFIED`; `1` for `FAILED`; `3` otherwise.

## 8. `hub.py verify` additions

- Ingest the contract's `report` file after the run (§4) and record it.
- Record `command`, `source_after`, `contract_sha256`, `commit_sha256`, `hub`.
- Acquire a non-blocking exclusive `flock` on `.hub/verify.lock` before running
  and release it after. When the lock is held, print
  `result  : BLOCKED (another verification is already running)` and exit `3`
  without executing anything. This is the resource guard: heavy builds must not
  run concurrently by accident.
- `--gate` gains `release` as an accepted value, using `entry["release"]` when
  the registry entry defines it; an absent command is `UNVERIFIED`, exit `3`.

## 9. `hub.py doctor` additions

Report (fail) when: `contracts/quality.schema.json` is missing or unparseable;
`tests/fixtures/conformance/` is missing or has no fixture directories; the
`.hub/` directory is not writable for the ledger; `scripts/conformance.py`
missing. Existing checks stay.

## 10. Conformance suite (who tests AEH)

- Runner: `scripts/conformance.py` — builds a disposable Hub copy under a
  temporary directory (its own `hub.config.json`, `projects/registry.json`,
  fake Git project, crafted `.hub/verification.jsonl`), runs the real
  `scripts/hub.py` from that copy via subprocess, and asserts the verdict.
- Fixtures: `tests/fixtures/conformance/<id>/` with `scenario.json`
  (`{"id", "title", "expect": {"assess_overall": "...", "release_check": "..."},
  "required": ["fixture.json"]}`).
- Wired into `python3 -m unittest discover -s tests` by `tests/test_conformance.py`,
  which fails when any fixture produces a wrong or missing verdict, and when a
  fixture is present but not exercised. Zero false-green on the designed set is
  the acceptance criterion; it is not a claim that AEH can never be wrong.
- Mandatory fixture ids (at minimum): `verified-clean-head`, `unpushed-head`,
  `stale-old-sha`, `skipped-required-gate`, `no-acceptance-record`,
  `artifact-hash-mismatch`, `missing-required-runner`, `agent-claim-no-log`,
  `malformed-ledger`, `contract-invalid-unknown-gate`, `contract-command-injection`,
  `status-is-read-only`, `verify-timeout-blocked`, `dirty-tree-stale`.

## 11. AEH self gate

`scripts/selfcheck.sh` runs, in order, and prints one final
`AEH_SELFCHECK=PASS|FAIL` line:

1. `python3 -m unittest discover -s tests -q`
2. `python3 scripts/conformance.py`
3. `bash evals/structural-check.sh`
4. `python3 scripts/hub.py doctor`

It is AEH's own acceptance gate. The Hub has no registry entry (a registered
path inside the Hub must fail doctor), so the self gate is a script, not a
registry entry.

## 12. Frozen names (do not rename)

`VERIFIED`, `FAILED`, `BLOCKED`, `NOT_VERIFIED`, `STALE`;
`hub.py assess`, `hub.py release-check`, `hub.py verify --gate release`;
`.hub/verification.jsonl`, `.hub/verify.lock`, `.hub/usage.jsonl`,
`.hub/gate-report.json`; `.aeh/quality.json`, `docs/quality.json`;
`contracts/quality.schema.json`; `scripts/quality_contract.py`,
`scripts/conformance.py`, `scripts/selfcheck.sh`;
`tests/fixtures/conformance/`, `tests/test_conformance.py`.
