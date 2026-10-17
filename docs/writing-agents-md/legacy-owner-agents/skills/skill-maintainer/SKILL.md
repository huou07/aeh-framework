---
name: skill-maintainer
description: Maintain the shared skill library at ~/.agents/skills. Use when adding, editing, auditing or importing a skill, or when a skill mis-fires. Do NOT use for ordinary coding tasks or for debugging a project's own tests.

---

# Skill maintainer

Author in place at `~/.agents/skills/<name>/SKILL.md`. Do **not** create
symlinks under `~/.codex/skills/` or `~/.config/opencode/skills/` — that
duplicates discovery and risks name shadowing.

**Discovery status on this host — verified, do not overstate:** OpenCode
(`opencode debug skill`) and Codex (`codex app-server` → `skills/list`) both
list these skills natively. DSH/ACP has **not** been shown to discover them
directly; under ACP the underlying coding agent supplies them. Do not claim
native DSH discovery without re-testing it.

The global `~/.config/agent-workbench/AGENTS.md` carried the same
"discovered natively by all agents" overstatement; it was corrected on
2026-10-11 to name the two verified surfaces. Keep it that way if you edit it.

## Adding a local skill

1. Create `~/.agents/skills/<name>/SKILL.md`. Frontmatter needs `name` (matches
   the directory, `^[a-z0-9]+(-[a-z0-9]+)*$`) and `description` (what it does +
   when to use it, specific enough that the agent routes correctly).
2. Keep the body short and non-generic. Skip advice the model already follows.
3. Verify discovery:
   - Codex: `codex app-server` -> `skills/list`
   - OpenCode: `opencode debug skill`

## Importing an external skill

1. Record upstream URL, license and revision.
2. Download to `/tmp/skill-quarantine/<name>/` — never straight into a skill root.
3. Load the **`security-review`** skill for the trust-boundary scan (credential
   access, exfiltration, obfuscation, shell hooks) and for severity reporting.
   Do not restate that procedure here — one skill owns it.
4. Run the deterministic gate if present:
   `~/.config/agent-workbench/bin/skill-gate.sh` (clones to quarantine, records
   provenance, runs `gitleaks` + `osv-scanner` + regex, never executes candidate
   code). Prefer it over re-deriving the steps by hand.
5. Copy only the approved files; record provenance.
6. Reject skills that must auto-execute on every prompt or call a paid model.

## Updating

Edit the single file in `~/.agents/skills/`. Nothing to relink; start a new
Codex/OpenCode session to pick it up.
