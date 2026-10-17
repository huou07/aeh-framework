# Quality system

Type: How-to/reference. Authority: operating procedure for the Hub and its
projects; project repositories remain the authority for their own behaviour and
acceptance.

Applies to: AEH and every registered product repository.
Not a source of truth for: current Git, CI, runtime or project task state.

Status: current

Last reviewed: 2026-10-17.

Purpose: close the gap between a good knowledge workspace and products that are
actually good. The 2026-10-17 audit found the same shape in all four workspaces:
clear authority maps, honest evidence vocabulary, real gates — and then a broken
feedback loop. Gates were registered that could not fail on the product, skills
existed as documents that no session could load, verification records were empty
or stale, no usage or defect data was ever recorded, and several "current"
documents contradicted the source. This document is the operating answer.

The definitions live in [the quality standard](quality-standard.md); the command
contract lives in [the Hub CLI](hub-cli.md). This document is the procedure.

## 1. Three gates, and say which one a result proves

Every project states three commands. They are different claims, not a sequence.

| Gate | Claim it supports | Typical cost | Registry field / command |
|---|---|---|---|
| `verify` | Source hygiene and cheap correctness: format, lint, type, unit tests, doc links | seconds–minutes | `verify`; `hub.py verify <slug> --gate verify` |
| `acceptance` | The product admission gate: build, workspace tests, real journey, package where applicable | minutes–tens of minutes | `acceptance`; `hub.py verify <slug> --gate acceptance` |
| `release` | Hosted CI, artifact identity, install/upgrade/rollback on the real target | hosted only | `release`; `hub.py verify <slug> --gate release`; `hub.py release-check <slug>` |

Rules:

- The registered `verify` command must not be the only gate a project has. If a
  project can compile or test more than that, register `acceptance` too.
- A gate that cannot fail on the product is not a gate. H07P's `make check` ran
  only Python while the shipped product is a Rust crate: a passing run proved
  nothing about the crate. The 2026-10-17 work widened these gates to their
  product lanes (OR's media/UI lanes, VCE's throughput budget, H07P's Rust,
  browser and package lanes), and each recorded result now names its gate.
- **Skip honesty:** a `skipped`, `neutral` or `not_run` check is never PASS. A
  required check named in the gate report becomes `BLOCKED` with its reason; an
  unrun lane is at best `NOT_VERIFIED`. Silent degradation is worse than a red
  check.
- OR and H07P now have an aggregate `release-gate` job whose `needs:` covers
  every platform job and which fails when any dependency is not `success`; it is
  a required status check on `main` for OR (ruleset `23891411`) and H07P
  (ruleset `25306518`). VCE's `verify.yml` has no aggregate job yet, and its
  protection still names its own check. Merge queue could not be enabled through
  the API (`422 Invalid rule 'merge_queue'`) and remains an owner action.
- Never weaken a gate, an assertion or a scanner to obtain PASS.
- `status` prints both gates and what each recorded result proves; `assess` adds
  the contract, release readiness and cost areas, and `release-check` composes
  the release verdict.

## 2. Verdict vocabulary (five states, used everywhere)

`VERIFIED` (valid evidence bound to the current exact source identity; every
required check ran and passed); `FAILED` (a check failed, or data is invalid or
mismatched); `BLOCKED` (a required check could not run for a named reason);
`NOT_VERIFIED` (insufficient evidence: no record, no contract, a claim without a
log, no acceptance record); `STALE` (evidence belongs to a different revision,
command, contract or dirty state).

- Severity order used to combine areas:
  `FAILED` > `BLOCKED` > `STALE` > `NOT_VERIFIED` > `VERIFIED`. Averaging,
  scoring or "95/100" is forbidden; a single severe area is not diluted by good
  areas (see [release blockers](quality-standard.md#6-release-blockers-vs-continuous-improvements)).
- A skip is never PASS. Absence of a quality contract is `NOT_VERIFIED`, never
  `VERIFIED`. Malformed ledger or report data is `FAILED`.
- A CI run green at another SHA is `STALE`; an owner or agent claim with no log
  is `NOT_VERIFIED`.
- Every non-`VERIFIED` verdict carries at least one human reason string.

## 3. One evidence ledger, exact source identity

- Runtime records live in one place: `.hub/verification.jsonl`. Curated,
  human-written records may be preserved under `evidence/`, but a project must not
  keep two competing ledgers.
- Every record carries gate, result, exit code, duration, branch, HEAD, dirty
  state, and the hash of the command that produced it. A result is meaningful only
  for that exact source state.
- New records add `command` (plaintext), `source_after` (must equal
  `source_before` for the record to be current), `contract_sha256`,
  `commit_sha256` (command + gate + contract, so a changed gate invalidates its
  record), `report` and the `hub` schema marker. Old records are never rewritten
  or deleted; readers tolerate missing fields.
- Freshness is computed against the current HEAD, not against the age of the file.
- `verify` holds a non-blocking exclusive `flock` on `.hub/verify.lock` while it
  runs, so two heavy builds cannot run concurrently by accident; a held lock is
  `BLOCKED` with `another verification is already running` and exits `3` without
  executing anything.
- Per-task usage lives in `<project>/.hub/usage.jsonl`, one JSON object per line,
  exactly as [cost and evaluation](cost-and-evaluation.md) defines. Every quantity
  is `measured`, `estimated`, or `unavailable`. A missing directory is
  `unavailable`; it is never zero and never invented.
- Acceptance and escape data (first-pass acceptance, rework, escaped defects) is
  recorded only when a real source exists. An empty ledger is an honest statement
  that measurement has not started.

## 4. The quality contract and the gate report

A project may own a machine-readable quality contract, looked up at
`<project>/.aeh/quality.json` then `<project>/docs/quality.json` (schema
`contracts/quality.schema.json`). It declares `required_gates`, `release_gates`,
the gate-command mapping, `hosted_ci`, the report path, expected `artifacts` and
`policies`. Validation is fail-closed: a missing contract is `NOT_VERIFIED` with
the reason `no quality contract at <path1> or <path2>`; an unparseable or invalid
contract is `FAILED`. **No contract field may contain a shell command** — a
contract that tries to inject one is rejected. AEH executes only the
owner-approved command in the registry entry, never metadata.

The project's own gate may write an optional report (default
`.hub/gate-report.json`) carrying `skipped[]`, `not_run[]`, `covered_gates[]`,
`artifacts[]`, `runner`, `evidence_class` and `limitations[]`. `hub.py` reads it
and never executes it. A non-object or malformed report makes the record's gate
verdict `FAILED`, never PASS.

Measured 2026-10-17: no registered project has a contract yet, so `release-check`
reports `NOT_VERIFIED` even where `verify` and `acceptance` are green. Creating
the contract is the next step for each project.

## 5. Skills must be loadable, or they are not skills

A procedure an agent cannot load is documentation, and must be labelled as such.

- A skill counts only when the running harness exposes it in that session's skill
  catalog and the agent can actually load it. Measure it with
  `python3 scripts/skill_liveness.py`, which reads the catalog each workspace's
  own session was given; a skill on disk that no session can load is a discovery
  gap, not a skill. Measured 2026-10-17: AEH 9, H07P 12, OR 9, VCE 16 — complete.
- Shared bodies live in `skills/`; project bodies live in the project. Catalogs
  route; they do not activate. `prompt-assist` is now a promoted shared body; the
  other eight canonical bodies are listed in the [shared catalog](writing-agents-md/shared-skills-catalog.md).
- If a procedure cannot be exposed to the harness, either fix discovery or move
  the text into ordinary project documentation and remove it from the catalog.
- Routing tables must not contradict current authority. A skill that forbids the
  lane the project's own guide authorises is a defect in the skill.
- Verify discovery when it matters, and report the limitation instead of claiming
  a load.

## 6. A quality bar per project

Each product repository keeps `docs/QUALITY.md`: the definition of "good" for
that product. One row per quality attribute, with a target, a measurement, the
gate that enforces it, and the current status. OR, VCE and H07P each have one
(2026-10-17).

| Attribute | Example target | Enforced by |
|---|---|---|
| Correctness | The project's acceptance gate passes at the released SHA | `acceptance` |
| Performance | Stated frame/latency/throughput budget measured on named hardware | budget test in `acceptance` |
| Reliability | No crash or data loss in the named journeys; recovery paths exercised | journey tests |
| Accessibility/UX | Named contrast/type/hit-area invariants and keyboard paths | UI guard test |
| Security | Secrets scan, dependency audit, trust-boundary review at the release candidate | publication/CI gate |
| Compatibility | The supported platform matrix, each with an exact-source hosted run | CI matrix |
| Maintainability | Indexed docs, no orphan scripts, no duplicate truth | doc checks |
| Cost | Resource use per operation, measured, not asserted | measurement script |

Use [the quality bar template](../templates/quality-bar.md). A number without a
measurement is prose, not a budget. Prefer three attributes actually enforced over
eight that are aspirational.

## 7. The conformance suite — who tests AEH

AEH grades other projects, so its own verdicts need adversarial fixtures.

- Runner: `python3 scripts/conformance.py` builds a disposable Hub copy in a
  temporary directory (its own `hub.config.json`, `projects/registry.json`, a
  fake Git project and a crafted `.hub/verification.jsonl`), runs the real
  `scripts/hub.py` from that copy, and asserts the verdict.
- Fixtures: `tests/fixtures/conformance/<id>/scenario.json` with `id`, `title`,
  `expect` (`assess_overall`, `release_check`) and `required`.
- Wired into `python3 -m unittest discover -s tests` by
  `tests/test_conformance.py`, which fails on a wrong or missing verdict and on a
  fixture that is present but not exercised. Mandatory ids include
  `verified-clean-head`, `unpushed-head`, `stale-old-sha`,
  `skipped-required-gate`, `no-acceptance-record`, `artifact-hash-mismatch`,
  `missing-required-runner`, `agent-claim-no-log`, `malformed-ledger`,
  `contract-invalid-unknown-gate`, `contract-command-injection`,
  `status-is-read-only`, `verify-timeout-blocked`, `dirty-tree-stale`.
- Zero false-green on the designed set is the acceptance criterion. It is not a
  claim that AEH can never be wrong.

## 8. The AEH self gate

The Hub has no registry entry, because a registered path inside the Hub must fail
`doctor`. Its own acceptance gate is therefore a script: `bash scripts/selfcheck.sh`
runs, in order, `python3 -m unittest discover -s tests -q`,
`python3 scripts/conformance.py`, `bash evals/structural-check.sh` and
`python3 scripts/hub.py doctor`, and prints one final line
`AEH_SELFCHECK=PASS|FAIL`. A green self gate is required for any Hub change.

There is no hosted gate, and there is no git remote: AEH is a control workspace,
not a shipped product, so a local gate is the whole gate. The public
[framework snapshot](publication.md) is proved at build time instead — the builder
refuses to finish unless the snapshot passes this self gate and the publication
gate. Two environment rules keep the local gate honest:

- `doctor` treats an absent workspace root (a CI runner, a fresh clone) as an
  explicit `NOT VERIFIED` note rather than a failure, and goes strict again as
  soon as the workspace root exists. A failing Hub gate in CI must mean the Hub
  is wrong, not that the runner is not the owner's laptop.
- The structural check measures what a session can actually load; a shared body
  on disk that no session was offered is a discovery gap, not a skill.
- Hosted CI on a private repository needs the account's Actions payment method and
  a spending limit above zero. When a job never starts, GitHub reports it as a
  failed check with zero steps; `bash scripts/ci-status.sh <owner/repo>` separates
  that from a real failure, exits 3, and prints the annotation. A job that did not
  start is `BLOCKED` and the revision is `NOT VERIFIED` — never a pass, and never a
  product defect (incident AEH-D026).

## 9. User acceptance and field feedback

A gate proves the software runs; it does not prove the product is good.

- Define release channels and what each one claims.
- Before a release, the owner runs an explicit acceptance checklist per user
  journey on the real target. Its result is recorded, including what was not run.
- After a release, captured failures (logs, crash reports, support reports) become
  defect records with a source and a date. Escaped defects are the one metric that
  says whether the process works.
- Design and UX claims need observation of the real journey; an automated scan
  covers selected regressions only (see [the quality standard](quality-standard.md#7-the-three-release-questions)).

## 10. Documentation discipline, enforced like code

- Every document carries `Status: current | superseded | archival` and
  `Last reviewed`; the index lists it. A document with no status is current by
  convention, so stale text is a bug, not a nuance.
- Checks run in the project gate: index completeness, relative links that resolve,
  freshness for current-claim documents, and claim records whose SHA exists in
  Git and is an ancestor of HEAD.
- A dated snapshot ("what runs today") is not authority. Either keep the fact in
  Git/CI, or mark the document as a snapshot in its first lines; `readiness-2026-10-17.md`
  is `superseded` for this reason.
- The repository wins over every Hub document. Where they disagree, fix one.
- One tracker per project. Dated handoffs belong in the existing handoff or
  evidence location; do not accumulate a parallel journal.

## 11. Git, release and one writer per repository

- Before starting, establish branch, HEAD, upstream and dirty state, and reconcile
  with the remote. Published but missing history is a blocker, not a detail.
- One working agent per repository at a time — **including AEH itself**. Two
  sessions in one tree fight over the same files; stop or pause the previous one
  first, and record the pause.
- Record session identity with the pause so a resume is possible: session id,
  working directory, HEAD, tree state, and the exact next action.
- Release and publication require the project's own exact-source gates plus owner
  authority. A green gate never grants publication by itself.
- The Hub is private and holds host-specific material. Publishing it, mirroring it
  publicly or changing its visibility requires `bash scripts/publication-check.sh`
  to pass; it fails by design on today's tree (incident AEH-D024). It is
  deliberately not part of `scripts/selfcheck.sh`, because a gate that is always red
  trains people to ignore red. `release-check`
  additionally requires a valid contract, both `verify` and `acceptance`
  `VERIFIED` at the current HEAD, a hosted runner when the contract demands one,
  and an artifact `sha256` for every declared artifact.

## 12. Failures are evidence

A failure that is not recorded is paid for twice. Every defect met while doing the
work — a broken script, a wrong assumption, a gate that could not fail, a host
capability that is missing — is evidence about the process, and belongs in the
ledger, not only in the chat that hit it.

Record each one in [`evidence/incidents.jsonl`](../evidence/README.md) with
its symptom, root cause, the evidence that proves it, and **the guard that keeps it
from recurring**. `tests/test_incidents.py` enforces the schema: an entry without a
guard fails the suite. `templates/incident-record.md` is the copyable form for a
project's own ledger.

The rule, in order:

1. **Record** the failure where the work happened, with the real command output,
   not a paraphrase. The observed error text is the evidence.
2. **Classify** it: `harness` (the tools used to do the work), `process` (the
   procedure or gate), `host` (a capability of the machine), `product` (the
   software under change).
3. **Guard** it. Prefer an executable guard — a test, a check, a fail-loud branch —
   over a sentence in a document. If no guard is possible yet, the disposition is
   `open` and it names the decision that would close it.
4. **Feed it back.** When a failure shows the procedure was wrong, change the
   procedure in the same pass, not later. The 2026-10-17 incidents changed
   [session handoff](session-handoff.md) (pause mechanics), [skills](skills.md)
   (discovery must be measured) and this document (gate scope, skip honesty).

A clean run that hid a skip, a gate that passed while the product failed, and a
control that looked successful but did nothing are all failures of this class: they
are worse than a red check, because they remove the signal.

## 13. Delete what lies

Keeping a false document is worse than having none. When a document, script or
ledger contradicts the source:

1. Fix it if the correct text is known and short.
2. Otherwise move it to the archive with a dated one-line reason.
3. Delete it when it is dead code, a duplicate journal, leaked host data, or an
   unmaintained pointer.

Never delete reviewable history that the project's own policy protects; archive
it instead.

## Applying this

The order that works, and the one the 2026-10-17 reorganization used:

1. Stop or pause the writing agents; verify the trees are quiet.
2. Reconcile each repository with its remote; make the tree equal a known revision.
3. Register the real `verify` and `acceptance` gates, and make the fast gate
   fail loudly on skips.
4. Fix contradictions between documentation and source; add the missing guards
   that would have caught them.
5. Add `docs/QUALITY.md` and wire one enforced budget.
6. Adopt the evidence and usage ledgers; record the first honest entries.
7. Delete or archive what lies.
8. Record every failure met along the way in the
   [incident ledger](../evidence/README.md) and give it a guard.
9. Only then hand work back to project sessions, with prompts that name the gate,
   the evidence class and the stopping condition.

Measured after that pass (2026-10-17), with fresh ledger records at each HEAD:

| Project | HEAD | verify | acceptance | Hosted CI |
|---|---|---|---|---|
| OR | `c8b627b` | `VERIFIED` | `VERIFIED` (5 named `UNVERIFIED` lanes) | Platform verification + required `release-gate` success |
| VCE | `2ff10bf` | `VERIFIED` | `VERIFIED` | `verify` workflow success |
| H07P | `095603b8` | `VERIFIED` | `VERIFIED` | CI (incl. `release-gate`) success; branch has no upstream configured |

`assess` reports `verify` and `acceptance` `VERIFIED` for all three at those
clean HEADs, and reports `contract` and `release` `NOT_VERIFIED` because no
project has a machine-readable quality contract yet: a release claim needs
`release_gates`, a hosted runner and artifact hashes that nobody has declared.
The ledger records also predate the v2 fields (`command`, `contract_sha256`,
`commit_sha256`), which matter at the next re-recording. That is the correct
reading, not a regression.
