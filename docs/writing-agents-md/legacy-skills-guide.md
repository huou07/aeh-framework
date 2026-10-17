# AEH skill routing and maintenance

Type: Reference

Authority: navigation and contract guidance; host and project rules govern execution.

Last reviewed: 2026-10-13.

The shared [catalog](/srv/agent-workbench/skills.md) holds the canonical skills.
AEH adds one local candidate:

| Candidate | Positive trigger | Negative neighbor | Evidence / stop |
|---|---|---|---|
| [prompt-assist](../.opencode/skills/prompt-assist/SKILL.md) | Explicit prompt, review, compression, corrective or handoff artifact | Ordinary implementation, status or actual diagnosis | Grounded proportional artifact; essential missing fact or complete artifact |

`ui-ux-review` was promoted to the shared library on 2026-10-14; its canonical
body is `/srv/agent-workbench/skills/ui-ux-review/SKILL.md` and its Hub copy is
retired (rollback snapshot:
`/srv/agent-workbench/instruction-history/2026-10-14-ui-ux-review-promotion/`).

Descriptions route; bodies carry procedures. Catalogs do not activate skills,
install candidates or grant tools. Use current DSH skill loading for DSH entries
and native discovery for native agent skills. A readable path is not live discovery.

Keep product-specific instructions in each project. VCE has five local skills
and its own routing catalog; OR has repository-specific policy and shared-skill
routing. Tiny CLI projects need no empty local skill hierarchy.

Maintain discriminating positive/negative triggers, real preconditions, minimal
procedure, meaningful evidence, authority, stopping and output. Preserve unique
product invariants, licences and invocation metadata. Review external imports
before execution; update a canonical source once rather than its symlink aliases.

The [regression corpus](../evals/README.md) covers prompt/UX and neighboring routes.
Schema/parser checks cannot establish live selection or accepted outcomes.
Provider package changes need a specific defect, original hash and reapplicable
patch; caches can be replaced by updates. Do not rewrite vendor content merely
for common formatting. All authored framework resources use English.
