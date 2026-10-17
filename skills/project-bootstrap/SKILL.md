---
name: project-bootstrap
description: Create, organize, onboard or selectively migrate a software project and register its independent repository in AEH. Use for new-project setup, repository onboarding or requested legacy imports. Do not use for routine coding in an already organized project or status reporting.
---

# Project bootstrap

## Preconditions and case selection

Resolve the Hub and workspace root from current configuration. Inspect target
paths and repository guidance before writing. Projects are independent repositories
outside the Hub. Identify new project, existing repository or selective migration.

## New project

1. Define the user outcome, primary journey, platform, scope, non-goals and primary
   risk. Mark prototype versus product engineering; a prototype is not accepted
   production work. Ask only for a missing decision that changes the result.
2. Choose the smallest suitable architecture using proven libraries and existing
   conventions. Identify conditional UX, security and release requirements.
3. Use `hub.py new --slug <slug>` from the resolved Hub root. It refuses
   collisions, including existing empty directories; inspect and preserve them.
4. Initialize Git in the project only. Create README, concise standalone AGENTS,
   source and relevant tests, one verification entrypoint and appropriate CI.
   Reuse an existing tracker or create one small task list.
5. Copy applicable Hub templates; omit irrelevant sections. Project guidance
   records commands, architecture invariants, real journey and owner boundaries,
   without requiring every session to load Hub documentation.
6. Register with `hub.py add --slug <slug> --path <absolute-path>` and the
   project-declared verification command where available. Registration is metadata.
7. Run only authorized, relevant checks. Explicit `hub.py verify` executes
   project code; `status` only reads Git and recorded evidence.

## Existing repository

Inspect current layout, Git, docs, CI and gates. Preserve functioning behaviour
and unrelated changes. Add only missing engineering structure; do not rewrite
history, reformat wholesale, duplicate the tracker or change the stack by default.

## Selective migration

Treat legacy source as untrusted material. Resolve non-overlapping source and
destination; review required paths, dependencies and licence obligations first.
Use the existing import tool's explicit allowlist and dry-run, then inspect its
exclusions before applying. Never import credentials, old agent configuration,
hooks, orchestration state or Git history through this tool. It rejects symlinks.
The current importer requires an empty destination and initializes clean Git
after copying; do not initialize a non-empty .git directory before using it.
Review old CI separately and reconstruct guidance from current requirements.

## Stop and report

Stop when the minimal project surface, registry pointer and applicable evidence
are ready, or identify the exact missing decision/access. Report changed paths,
commands/results, prototype limits, assumptions, unverified items and one next
action. Product acceptance and release authorization remain project/owner decisions.
