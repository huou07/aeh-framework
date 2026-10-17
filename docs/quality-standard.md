# Product quality standard

Type: Standard (authoritative framework policy).

Authority: this is the canonical definition of "good product" that AEH and its
projects are measured against. A project repository remains the authority for its
own behaviour, gates and acceptance; where the two disagree, fix one.

Applies to: AEH and every registered product repository.

Not a source of truth for: current Git, CI, runtime or project task state.

Status: current

Last reviewed: 2026-10-17

Purpose: state, in one place, what product quality means, how each criterion is
proven, which AEH mechanism enforces it, and — honestly — where AEH only
documents it today. [Quality system](quality-system.md) is the operating
procedure; [quality and security](quality-and-security.md) owns the evidence
classes; [Hub CLI](hub-cli.md) owns the command contract.

## 1. Verdicts: how a claim is graded

AEH grades every claim with exactly one of five verdicts, defined in the frozen
interface ([quality interface](quality-interface.md) §2) and emitted by
`hub.py assess` and `hub.py release-check`:

| Verdict | Meaning |
|---|---|
| `VERIFIED` | Valid evidence bound to the current exact source identity; every required check actually ran and passed. |
| `FAILED` | A check ran and failed, or evidence/artifact data is invalid or mismatched. |
| `BLOCKED` | A required check could not run for a named environmental, platform, authority or resource reason. |
| `NOT_VERIFIED` | Insufficient evidence: no record, no contract, a claim without a log, no acceptance record. |
| `STALE` | Evidence exists but belongs to a different revision, command, contract or dirty state than the current one. |

Rules:

- A skip is never PASS. A required gate recorded in `report.skipped`/`report.not_run`
  is `BLOCKED`; an unrun lane is at best `NOT_VERIFIED`.
- Absence of a quality contract is `NOT_VERIFIED`, never `VERIFIED`.
- Malformed ledger or report data is `FAILED`, never a pass.
- Severity order: `FAILED` > `BLOCKED` > `STALE` > `NOT_VERIFIED` > `VERIFIED`.
  Averaging, scoring or "95/100" is forbidden. One severe area is not diluted by
  good areas.
- Every non-`VERIFIED` verdict carries at least one human reason string.
- A CI run that is green at a different SHA than the current HEAD is `STALE`.
- An owner or agent claim with no log is `NOT_VERIFIED`.

## 2. The twelve product-quality criteria

Each row states what must be true, how it is measured, the evidence class that
proves it, the AEH mechanism or gate that enforces it, and whether AEH enforces
it today or only documents it. "Enforced" means a mechanism exists that can fail
closed; it does not mean every project currently passes.

| Criterion | What must be true | How it is measured | Evidence class | AEH mechanism / gate | Status |
|---|---|---|---|---|---|
| **1. Value** | A named user can reach an outcome they care about; the completion condition is observable. | Owner-run user-acceptance checklist per journey on the real target; escaped-defect record. | `ACCEPTED` | `docs/QUALITY.md` user-acceptance row; `release-check` requires an acceptance record, but cannot observe value. | `DOCUMENTED` |
| **2. Core-function completeness** | Every stated core function exists and is reachable in the packaged product, not only in source or in tests. | Packaged end-to-end journey over each core function; covered-gate list in the gate report. | `VERIFIED_NATIVE` / `ACCEPTED` | `acceptance` gate; `release-check` condition 1 and 6 (declared `release_gates` and artifacts); a skipped core lane is `BLOCKED`. | `ENFORCED` |
| **3. Correctness** | Outputs match the stated contract on representative and adversarial inputs; invariants hold. | Unit, integration, property and negative tests; golden files, checksums and invariant checks. | `VERIFIED_SOURCE` → `VERIFIED_BEHAVIORAL` | `verify` (cheap) and `acceptance` (real); ledger binds the result to the exact HEAD and command. | `ENFORCED` |
| **4. UX** | Everyday journeys are discoverable, efficient, recoverable and consistent; loading/empty/error/success states are covered. | Journey tests; visual regression; accessibility scan; observed user testing. | `VERIFIED_VISUAL` / `VERIFIED_BEHAVIORAL` + user test | Project `docs/QUALITY.md` UX row and UI guard tests; `release-check` sees only that a gate ran. | `DOCUMENTED` |
| **5. Performance** | Latency, throughput, memory and CPU/GPU stay inside a named-machine budget under bounded load. | Benchmarks reporting p50/p95/p99, memory and CPU/GPU against a threshold in the default gate. | `VERIFIED_BEHAVIORAL` with measured traces | Budget check inside `acceptance`; contract `artifacts`/report carry the result. | `DOCUMENTED` |
| **6. Reliability / recovery** | No crash or data loss in the named journeys; recovery, retry and graceful-degradation paths are exercised. | Soak and stress runs, fault injection, recovery-path tests, crash reports. | `VERIFIED_BEHAVIORAL` / `VERIFIED_NATIVE` | Acceptance journey tests; an unrun recovery lane must be named in `report.not_run` (→ `BLOCKED`/`NOT_VERIFIED`). | `DOCUMENTED` |
| **7. Security / privacy** | No secrets or credentials in the tree; dependencies and trust boundaries reviewed; least privilege; negative permission tests pass. | Secrets scan and dependency audit in CI; threat model; negative permission tests; `security-review` skill. | `ACCEPTED` for the scanned scope | `verify`/`acceptance` publication or CI gate; `release-check` fails a failed release gate. A clean scan is evidence, never proof. | `ENFORCED` |
| **8. Compatibility / accessibility** | Each claimed platform has an exact-source run on that platform; accessibility invariants (contrast, type, focus, hit area, keyboard) hold. | Hosted CI matrix per platform; accessibility guard tests. | `VERIFIED_NATIVE` per platform / `ACCEPTED` | GitHub CI matrix plus the required aggregate `release-gate` (OR, H07P); `release-check` condition 5 (`hosted_ci`). Accessibility is not centrally gated. | `ENFORCED` (compatibility) / `DOCUMENTED` (accessibility) |
| **9. Install / update** | Clean install, upgrade, uninstall and rollback work from the real artifact on the supported target; version identity is single-sourced. | Package-lifecycle test on the target OS; install time; rollback run. | `VERIFIED_NATIVE` | `verify --gate release`; `release-check` condition 6 (artifact `sha256` and `result == PASS`). | `ENFORCED` where a project declares artifacts; `MISSING` for source-only or unsigned releases |
| **10. Verified quality** | The released revision is the tested revision; evidence is bound to exact SHA, command and contract. | Ledger `head`, `source_after`, `contract_sha256`, `commit_sha256`; freshness computed against the current HEAD. | `ACCEPTED` (exact-source) | `hub.py verify` records; `hub.py assess` computes freshness; `hub.py release-check` composes the release verdict. | `ENFORCED` |
| **11. Maintainability** | Indexed documents, one truth per fact, no orphan scripts, tests where defects were found. | Structural and link/index checks; conformance fixtures; incident guards. | `VERIFIED_SOURCE` | `evals/structural-check.sh`, `scripts/conformance.py`, `scripts/selfcheck.sh`, `tests/`, the incident-ledger schema check. | `ENFORCED` |
| **12. Sustainability / trust** | Licence, provenance, reproducible build and honest reporting; a broken release can be withdrawn and rebuilt. | SBOM, licence and checksum in the release; build attestation; incident records with guards. | `ACCEPTED` | Release provenance (attestation/signing is owner-gated), incident ledger schema, [deletion policy](quality-system.md#13-delete-what-lies). | `DOCUMENTED` |

Honesty notes, measured on 2026-10-17 and superseding older claims:

- No registered project has a machine-readable quality contract
  (`<project>/.aeh/quality.json` or `<project>/docs/quality.json`) yet, so
  `release-check` returns `NOT_VERIFIED` even where both gates are green. See
  [AEH capabilities](aeh-capabilities.md).
- The ledger holds records from both schema generations. Records written since
  2026-10-18 carry `command`, `source_after`, `contract_sha256`, `commit_sha256`
  and the parsed gate report, so a changed gate, contract or revision invalidates
  them; older records carry only the command hash and are read tolerantly. The
  distinction is visible per record, and `assess` computes freshness from
  whatever each record actually contains.
- VCE enforces one real throughput budget both ways; OR and H07P have no
  named-machine performance budget. No project has a golden/screenshot baseline
  or observed user testing.

## 3. Maturity levels: the release-claim ladder

A release claim is a claim about maturity. Never claim a higher rung than the
evidence supports; each rung names the evidence it requires.

| Level | Claim | Required evidence |
|---|---|---|
| **Works** | It runs and does the core job on at least one supported target. | `verify` + `acceptance` `VERIFIED` at a clean, identified revision; core journeys run. |
| **Usable** | A person who is not the developer can install it, do the job, recover from a plausible failure and uninstall it on the supported target. | The "works" evidence **plus** install/upgrade/uninstall/rollback, a passing UX/accessibility check and one measured performance number. |
| **Truly good** | It is trustworthy under stress and adversarial conditions, within budgets, and the release process can prove exactly what shipped. | The "usable" evidence **plus** `release-check` `VERIFIED`, security review and negative tests, compatibility matrix green at the released SHA, artifact hashes, and an owner acceptance record. |

The three levels are cumulative, not alternatives. A "works" claim on one
platform says nothing about another platform; state the platform with the claim.

## 4. Priority order

When two criteria compete, the earlier one wins:

```
Correct → Safe → Reliable → Usable → Efficient → Maintainable → Deliverable
```

This is a **priority order, not a linear process**. Work may proceed on later
items at any time, but never at the cost of an earlier one. A correctness,
safety or reliability defect is a release blocker no matter how good the later
columns look; efficiency or cost work never justifies shipping a wrong or unsafe
result. "Deliverable" is last because a release that is wrong, unsafe, unreliable
or unusable is not a delivery.

## 5. Measurable criteria

Every criterion below must name an observable and a threshold. A number without
a measurement is prose, not a budget. Prefer three enforced rows over twelve
aspirational ones.

| Area | Observable / metric | How it is measured | Gate |
|---|---|---|---|
| Functional | Each core job completes end to end in the packaged artifact | Packaged E2E journey per core function | `acceptance` |
| Correctness | Output equals the specified result; invariants hold | Golden files, checksums, invariant and negative tests | `verify` + `acceptance` |
| Performance | p50 / p95 / p99 latency, throughput, peak and steady memory, CPU/GPU use | Bounded workload on named hardware, percentile report vs threshold | budget test in `acceptance` |
| Smoothness | Frame pacing and stutter, dropped frames, input-to-pixel latency | Frame-time trace; p99 and long-frame count vs budget | UI/player budget in `acceptance` |
| Stability | No crash, leak or data loss over time and under fault | Soak, stress, recovery and fault-injection runs | `acceptance` (named lane) |
| Security | Denial holds where access is denied; audit and secret scans are clean | Negative permission tests plus a reviewed threat model; secrets/dependency scan | security/publication gate in `verify`/`acceptance` |
| UI/UX | Journeys complete; states covered; a11y invariants hold | Visual regression, accessibility scan, observed user test | UI guard in `acceptance` |
| Install | Clean install, upgrade, uninstall and rollback succeed | Package lifecycle on the target OS | `verify --gate release` |
| Release quality | The artifact hash, CI evidence and acceptance record all match the shipped SHA | artifact `sha256` + CI run + owner acceptance record | `release-check` |

## 6. Release blockers vs continuous improvements

**Release blockers** (any one stops a release claim):

- Any severe area is `FAILED`, or invalid/mismatched evidence data exists.
- A required check is `BLOCKED` (missing platform, tool, authority or resource)
  or a required lane is skipped/not run.
- Evidence is `STALE` — gates, artifacts or acceptance belong to another revision,
  command, contract or dirty state than the released one.
- No quality contract, no acceptance record, or a claimed artifact without a
  64-hex `sha256` and `result == PASS`.
- A supported target is claimed without an exact-source run on that target.
- A secret or credential is present in the tree, or the release has no rollback.
- A core function, recovery path or security boundary is unproven at the
  released SHA.

**Continuous improvements** (do not block; record and schedule):

- A metric without a budget, or a budget with no baseline yet.
- Coverage, accessibility or UX observation gaps.
- Documentation staleness and missing cost/usage measurement.
- Maintainability debt, orphan scripts and duplicate truth.

The hard rule: **no average score can offset a severe defect.** Verdicts combine
by severity, not by mean. A release is not "mostly ready" if one core journey
fails, one supported platform is untested, one artifact hash is unknown, or one
security boundary is unproven.

## 7. The three release questions

Before any release claim, answer all three, with evidence:

1. **Can a user do the job?** Name the user, the job and the observable
   completion, and show the packaged product doing it on the supported target.
2. **Is it trustworthy and safe?** Show correctness, reliability and recovery
   under load and fault, plus the security/privacy review and negative tests.
3. **Is the released version the tested version?** Show the artifact hash, the CI
   run and the acceptance record all bound to the same revision.

### The stranger-with-no-dev-environment test

The decisive test for "usable": hand the shipped artifact and its README to
someone who has never seen the repository, on a supported target, with **no
development environment, no source checkout and no agent**. They must install it,
complete the core job, recover from a plausible failure using only the shipped
documentation, and uninstall it. If they cannot, the release is at most "works",
whatever the gates say. Record the result, including what was not attempted.

## 8. Value versus cost

Value is the outcome a user can reach — not activity, tokens, commits, coverage
percentage or the number of checks. Cost is the runway and effort spent reaching
it. The standard is accepted useful work relative to total cost and human rework
(see [cost and evaluation](cost-and-evaluation.md)).

- Spend verification where failure is likely and expensive: on the critical path,
  on irreversible or trust-boundary operations, on the platforms users actually
  hold.
- A cheap check on the critical path beats an expensive check off it. A gate that
  is always red, or that cannot fail on the product, is worse than no gate — it
  removes signal.
- The gates must cost less than the defect class they catch. The 2026-10-17 OR
  Windows failure is the worked example: local green missed a property of the
  hosted runner, and only the hosted matrix could see it.
- `unavailable`, `NOT_VERIFIED` and `BLOCKED` are honest, useful results. An
  invented number is never one.
