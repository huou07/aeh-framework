---
name: skill-maintainer
description: Audit, add, update or import shared and project-local skills, their routing catalogs and instruction contracts. Use for demonstrated skill misfires or requested instruction maintenance. Do not use for ordinary product coding, project debugging or unrelated skill discovery.
---

# Skill maintainer

## Ownership and preconditions

The canonical shared library is `skills/` under the AEH workspace root; the
preserved shared policy is `docs/writing-agents-md/shared-AGENTS.md`, and the
preserved routing catalog is `docs/writing-agents-md/shared-skills-catalog.md`.
The retired `/srv/agent-workbench` paths are history: resolve the current Hub
root before editing rather than trusting an inherited path.
Project skills stay in the project repository. Resolve real paths and read current
content before editing; update one canonical file, never discovery aliases.

Inventory only authorized instruction roots. Inspect readable files without
activating every workflow. Separate custom skills, project candidates, installed
provider packages and disk-only skills absent from the current session catalog.
A catalog or readable file does not grant tools or prove live discovery.

## Audit and update

1. Identify a concrete reason: misrouting, missing procedure, wrong path/claim,
   duplicated knowledge, unclear evidence or stopping/authority rule.
2. Preserve the user's intent, invocation policy, unique product invariants,
   supported metadata, licences and provider tool contracts.
3. Keep a discriminating name/description with positive and neighboring negative
   triggers. The body supplies preconditions, procedure, evidence, stopping and
   output contract only where needed.
4. Prefer references to project authorities over embedded task/history dumps.
   Write authored instruction resources in English.
5. Save a versioned backup or Git diff and original hash. Preserve unrelated work.
   Prepare changes before requesting any missing approval; operate only with the
   current identity and effective filesystem/tool permissions.
6. Validate syntax, reference existence and representative positive/subtle/
   negative/no-skill contracts. Structural checks do not prove live routing,
   accepted outcomes or discovery.
7. Modify vendor files only for a demonstrated defect within the requested scope;
   record package/version and a minimal patch for reapplication after updates.
   Do not rewrite caches just for stylistic uniformity.

## External imports

Record upstream URL, licence and immutable revision. Quarantine first, invoke
security-review for instruction/executable risk, and use a verified existing
import gate when available. Never assume an obsolete helper path exists. Do not
execute candidate scripts or expose credentials during review. Install only
reviewed, authorized content into the selected canonical root.

## Discovery and promotion

Use the actual session's discovery/loader. DSH catalog entries use the current
DSH skill tool and exact exposed name; native Codex/OpenCode skills use their
documented mechanisms. Do not copy DSH skills into a private native directory.
Preserve each session's connection and caller identity.

Candidate promotion needs observed routing/output results against baseline and
verified discovery on the target harness. Do not claim it from a schema check or
an earlier session. Existing Codex/OpenCode observations are dated evidence;
DSH discovery remains unverified until observed for the current connection.

## Stop and report

Stop when justified edits and available checks are complete. Report changed and
retained files, provenance/rollback location, coverage, verification, discovery
limits and exact permission blockers. A maintenance task grants no authority to
change production, credentials, protected services or public publication.
