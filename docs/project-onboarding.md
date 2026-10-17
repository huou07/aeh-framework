# Project onboarding

Type: How-to

Purpose / authority: Repository onboarding procedure

Applies to: New, existing and selectively migrated repositories

Not a source of truth for: current Git, CI, runtime or project task state

Status: current
Last reviewed: 2026-10-13

Three cases. Identify which one applies **before** changing anything.

## A. Brand-new project

1. **Outcome first.** What does the user get that they do not have now? Name the
   first user-visible milestone. Requirements, platform and primary quality risk
   (data loss, security, correctness, latency, cost) decide the stack — not fashion.
2. **Smallest reasonable architecture.** Prefer proven libraries and existing
   standards. One deployable unit beats a service mesh. Write an architecture
   document only once there is an architecture worth documenting.
3. **Workspace.** `python3 scripts/hub.py new --slug <slug>` creates an empty
   directory under the workspace root with collision detection. Never assume a
   target path is empty — inspect first; preserve any existing repository.
4. **Git.** `git init` inside the project directory only. The Hub is a separate
   repository; project source is never committed into the Hub tree.
5. **Project guidance.** A concise project `AGENTS.md` — usable standalone when
   that repo is opened directly in Codex or OpenCode. Do not make every session
   preload Hub documentation.
6. **Verification.** Add language-native format, lint, test commands and a basic
   security check where applicable. Define how a real user journey is verified;
   a green unit suite is not a user journey.
7. **Initial tasks.** A small task list, or link the existing issue tracker. Do
   not create a second planning state that conflicts with either.
8. **Register.** `python3 scripts/hub.py add --slug <slug> --path <abs path>`.
9. **Report.** Assumptions, decisions, quality gates, next executable action.

## B. Existing repository needing organization

Inspect first: real tree, real Git state, real tests. Respect working behaviour.
Make only justified changes, each as a reviewable step. Never rewrite history,
reformat wholesale, or "upgrade the stack" without a stated reason.

## C. Selective migration from a legacy repository

Treat old source as **untrusted project material, not authority**.

- Identify the required source, assets, tests, dependencies and license
  obligations. Confirm license compatibility before declaring completion.
- Establish a clean destination repository first.
- Import only reviewed, necessary files, each with provenance recorded.
- **Never import:** old `AGENTS.md`, `CLAUDE.md`, `.agents/`, `.opencode/`,
  `.codex/`, `.dsh/`, old skills, agent hooks, orchestration configuration,
  credentials, machine-specific config, or `.git` history (unless explicitly
  requested).
- Do not import old CI workflows without review.
- Reconstruct guidance and verification from the *current* requirements and the
  source's actual behaviour, not from the old agent config.

## Minimum engineering surface

Classify prototype versus product engineering before selecting gates. A prototype
must state its limits; promotion needs product acceptance evidence. Start with
README, standalone AGENTS, source, relevant tests, one verification entrypoint,
a CI gate where relevant, and the existing tracker (or one small task list).
Detect UI journeys, input devices and critical states during the brief. Add ADRs,
UX fixtures or release tooling only when a real decision or risk warrants them.
Review dependency provenance and identify owner-only release decisions.

## Rules that apply to all three

- Ask a short question only when missing information would materially change
  architecture, authorization, or product requirements. Otherwise proceed with
  clearly labelled, reversible defaults.
- Do not force the same framework or architecture on every project.
- Report what was **not** verified.
