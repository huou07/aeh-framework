# AEH documentation

Purpose: find the smallest document needed for the task.

Authority: navigation only. This index defines no policy, proves no product state
and is not evidence of completion; the linked document and the project repository
own their claims.

Status: current

Last reviewed: 2026-10-17

## Standards and policy

What "good" means, and the rules that apply across projects.

| Document | Type | Use it for |
|---|---|---|
| [Quality standard](quality-standard.md) | Standard | The twelve product-quality criteria, the three maturity levels, priority order, release blockers and the three release questions |
| [Quality system](quality-system.md) | How-to/reference | Gates, verdicts, evidence ledger, quality contract, conformance suite, self gate, skills liveness, incident ledger, deletion policy |
| [Quality and security](quality-and-security.md) | Reference | Evidence classes, UI quality, trust boundaries and escalation |
| [Operating model](operating-model.md) | Explanation/reference | Ownership, lifecycle and the single-source-of-truth rule |
| [Engineering guide](engineering-guide.md) | How-to | Apply the framework to one engineering task |
| [Cost and evaluation](cost-and-evaluation.md) | Reference | Measure outcomes without inventing numbers |
| [AEH capabilities](aeh-capabilities.md) | Reference | Which AEH mechanism exists for each capability, plus the definition of done and AEH's own acceptance checklist |

## Operate

Procedures for doing the work.

| Document | Type | Use it for |
|---|---|---|
| [Onboarding](project-onboarding.md) | How-to | Start, organize or migrate a repository |
| [Delivery](project-delivery.md) | How-to | Complete and hand off a change |
| [Prompting](prompting.md) | How-to/reference | Task, corrective and handoff prompts |
| [Session handoff](session-handoff.md) | How-to | Deliver a prepared prompt into a project workspace and watch it run in the GUI |
| [Skills](skills.md) | Reference | Shared/project skill routing, promotion and maintenance |

## Reference

Command contracts, runtime facts and profiles.

| Document | Type | Use it for |
|---|---|---|
| [Hub CLI](hub-cli.md) | Reference | Command effects, JSON interface, verdicts, ledger fields and provenance |
| [Publication](publication.md) | How-to | Produce and publish the sanitised public snapshot without publishing the owner's machine |
| [Quality interface](quality-interface.md) | Reference | Frozen verdict, ledger, gate-report, contract and command-interface fields |
| [Shared skills catalog](writing-agents-md/shared-skills-catalog.md) | Reference | Route to one shared skill |

## Archive

Superseded or preserved material. Read for history, never as current authority.

| Document | Type | Use it for |
|---|---|---|
| [Research archive](research/README.md) | Research/explanation | Original rationale and source limitations |
| [Writing AGENTS.md](writing-agents-md/README.md) | Preserved example | Historical shared policy and skill catalogs |
| ops/ and evidence/ | Not published | Host administration and dated host evidence stay in the private Hub |
| [Legacy AEH guide](writing-agents-md/legacy-AEH-AGENTS.md) | Archival | The former hub guide |
| [Legacy skills guide](writing-agents-md/legacy-skills-guide.md) | Archival | The former skill routing guide |
| [Shared AGENTS.md](writing-agents-md/shared-AGENTS.md) | Archival | The exact former `/srv/agent-workbench/AGENTS.md` |
| [Legacy owner-global skills](writing-agents-md/legacy-owner-agents/) | Archival | Older owner skill copies |

Read on demand. Templates in [templates](../templates/) are copyable artifacts,
not mandatory paperwork. [evidence](../evidence/README.md) holds dated, curated proof indexed by its own
README. Current truth comes from Git, CI and observed runtime behaviour. A
project registry label is not evidence of completion.

## Also in this repository

Not documents to read, but part of the layout: index them so nobody has to
guess whether they are live.

| Path | Purpose |
|---|---|
| [../ops/](../ops/README.md) | Owner-run host administration. Never an agent entrypoint |
| [../evals/](../evals/README.md) | Skill routing regression corpus and its structural check |
| [../tests/](../tests/) | Hub's own tests: `python3 -m unittest discover -s tests -q` |
| [../skills/](../skills/) | Canonical shared skill bodies |
