# AEH skill routing and maintenance

> Runtime update, 2026-10-15: the former shared worker installation is retired.
> Preserved shared skill bodies now live in `../skills/`; historical AGENTS.md
> and older skill versions are in `writing-agents-md/`. References below to
> `/srv/agent-workbench` describe the historical setup. See
> normal user runtime (not published) for the installed applications.

Type: Reference

Authority: navigation and contract guidance; host and project rules govern execution.

Status: current

Last reviewed: 2026-10-17.

The shared [catalog](writing-agents-md/shared-skills-catalog.md) routes to ten
canonical skill bodies in `../skills/`:

| Shared skill | Positive trigger | Negative neighbor | Evidence / stop |
|---|---|---|---|
| [code-investigate](../skills/code-investigate/SKILL.md) | Code location, callers, impact or bug investigation | Ordinary listing or an already grounded edit | Locate and explain; stop when the surface is known |
| [project-bootstrap](../skills/project-bootstrap/SKILL.md) | New project, onboarding, selective migration | Routine coding or status | Registered, organized repository |
| [project-steward](../skills/project-steward/SKILL.md) | Existing project status, next task, brief, handoff, readiness, cost | Bootstrap, failing-check diagnosis, standalone prompt edits | Evidence-based report or artifact |
| [prompt-assist](../skills/prompt-assist/SKILL.md) | Explicit prompt, review, compression, corrective or handoff artifact | Ordinary implementation, status or actual diagnosis | Grounded proportional artifact |
| [verify-debug](../skills/verify-debug/SKILL.md) | Failed check or requested implementation verification | Status-only or prose-only work | Failing check repaired from evidence |
| [sustained-repair](../skills/sustained-repair/SKILL.md) | Work failing repeatedly, across a handoff, or under context/quota pressure | A single failing check, status reporting, retry without new evidence | One authorized outcome sustained |
| [security-review](../skills/security-review/SKILL.md) | Scoped security/trust-boundary, commit, release or import review | Trivial wording or correctness debugging | Boundary and severity report |
| [skill-maintainer](../skills/skill-maintainer/SKILL.md) | Instruction/skill maintenance, import or misfire | Product implementation | Validated, documented skill change |
| [ui-ux-review](../skills/ui-ux-review/SKILL.md) | New screen or flow, navigation or interaction change, explicit usability review | Backend-only change, single-value style tweak, build/pass question | Journey-based UX evidence |
| [task-planning](../skills/task-planning/SKILL.md) | Plan, split, sequence or parallelise work; dependencies, acceptance and stop conditions | Status or readiness reporting, the prompt artifact itself, executing the work | Executable plan with acceptance and stop per task |

`ui-ux-review` was promoted to the shared library on 2026-10-14, `prompt-assist`
on 2026-10-17, and `task-planning` on 2026-10-18 — the Hub previously had no
Plan responsibility backed by an executable procedure. `prompt-assist`'s
canonical body moved from `.opencode/skills/prompt-assist/SKILL.md` to
`../skills/prompt-assist/SKILL.md`; the Hub-local paths are symlinks to it.
Historical promotion receipts remain in the archived evidence tree.

Descriptions route; bodies carry procedures. Catalogs do not activate skills,
install candidates or grant tools. Use current DSH skill loading for DSH entries
and native discovery for native agent skills. A readable path is not live discovery.

Keep product-specific instructions in each project. VCE keeps seven local skills
(`an3-build`, `an3-control-plane`, `an3-player-regression`, `an3-staging-deploy`,
`public-release-security`, `vce-gameplay-performance`, `vce-product-journeys`)
and its own routing catalog; H07P keeps three (`h07p-isolation`, `h07p-files`,
`h07p-efficiency-ci`); OR has repository-specific policy and shared-skill
routing only. Tiny CLI projects need no empty local skill hierarchy.

## Where the shared library is exposed

Measured 2026-10-17: the shared bodies were reachable on disk but on no discovery
root, so no session could load them, and OR's sessions received no catalog at all.
They are now exposed once, at the user root `~/.dsh/skills/`, as symlinks to the
ten canonical bodies in `../skills/` (including the promoted `prompt-assist` and
`task-planning`).
Project-local skills stay in `<project>/.agents/skills/` and are discovered from
the repository. One source, one discovery path per name.

Verify what sessions can actually load, rather than what exists on disk:

```bash
python3 scripts/skill_liveness.py          # table, exit 1 on any gap
python3 scripts/skill_liveness.py --json
```

It reads the newest `skill-catalog` event in each workspace's own session
transcript, so a missing entry is a discovery gap. It does not start an agent and
does not prove that a model selected or applied a skill.

Maintain discriminating positive/negative triggers, real preconditions, minimal
procedure, meaningful evidence, authority, stopping and output. Preserve unique
product invariants, licences and invocation metadata. Review external imports
before execution; update a canonical source once rather than its symlink aliases.

The [regression corpus](../evals/README.md) covers prompt/UX and neighboring routes.
Schema/parser checks cannot establish live selection or accepted outcomes.Provider package changes need a specific defect, original hash and reapplicable
patch; caches can be replaced by updates. Do not rewrite vendor content merely
for common formatting. All authored framework resources use English.
