# PROVENANCE — `ui-ux-review` (staged candidate, not yet installed)

**Date:** 2026-10-13 (created), 2026-10-14 (revised) · **Status:** staged in the
Hub for review; NOT installed to the canonical library.

## Revision 2026-10-14 — semantic-first inspection

Revised to prefer structured inspection over screenshots, so an agent can
review a UI without a vision model or a local browser.

The method table and the per-platform commands were written against the actual
repositories, not from memory:

- **VCE web** — `tools/inspect-ui.py` (added in VCE in this change) prints the
  accessible tree of a rendered page. Verified on this host by starting
  `app.py` and inspecting `/`, `/games`, `/login`, `/register` and `/offline`.
  Stdlib only; no browser, no Playwright, no network install.
- **OR Flutter** — `tester.ensureSemantics()` + `tester.getSemantics()`, which
  `apps/or_app/test/widget_test.dart` already used. No new API introduced.
- **Android native / Tauri** — recorded as device- and CI-only, because this
  host has no `adb`, no emulator and no desktop session.

**Not verified here:** the VCE command was run against a live local server and
its output inspected. The Flutter commands were **not** executed, because no
Flutter or Dart SDK is installed on this host; they are written to match the
patterns already present and passing in `widget_test.dart`, and CI
(`flutter test` in `platform-verification.yml`) is the authority for them.

**Why no Playwright/axe integration:** this host has no browser binary, so
adding one would have meant a large install that could not have been justified
by a measured benefit here. The web surface is server-rendered, so the
accessibility tree is reachable without one. A browser remains the right tool
for layout, colour and motion, and the skill says so rather than pretending
otherwise.

## Sources reviewed (fetched 2026-10-13; principles paraphrased, nothing copied)

1. **Nielsen Norman Group, "10 Usability Heuristics for User Interface
   Design"** — fetched full article text (heuristics 1–4 with tips verbatim
   on screen; 5–10 per the article's standard list; last reviewed Jan 2024
   per the page).
   [nngroup.com/articles/ten-usability-heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/)
   — © Nielsen Norman Group; short principles paraphrased with attribution,
   no NNG prose reproduced. Taken: status visibility → feedback rule; user
   control/undo → cancel/recovery rule; consistency (incl. Jakob's Law) →
   prefer-established-patterns rule; error prevention/recovery → states rule.
2. **Vercel Web Interface Guidelines** — fetched the full living document
   (Interactions / Animations / Layout / Content sections).
   [vercel.com/design/guidelines](https://vercel.com/design/guidelines) ·
   feedback repo `vercel-labs/web-interface-guidelines` is **MIT licensed**
   (verified via GitHub API: `license.key: mit`). Paraphrased regardless; no
   text reproduced. Taken: keyboard-everywhere + visible focus; hit targets
   (≥24px, ≥44px mobile); gestures-have-alternatives; announce async updates
   (aria-live); no-dead-ends; all-states-designed; icons-have-labels.
3. **Anthropic `frontend-design` skill** (`anthropics/skills` repo) — fetched
   `skills/frontend-design/SKILL.md` (sha `a533345…`) in full plus its
   `LICENSE.txt`: **Apache License 2.0** (verified). Deliberately NOT copied:
   that skill's job is *distinctive visual identity for new UI* ("take
   aesthetic risk"), while this skill's job is *usability review of existing
   flows that defers to the project's design language* — complementary, not
   overlapping (see skill Limits). Taken: only the copy-naming rule (CTA
   names the outcome; same verb through the flow) and the anti-AI-slop
   calibration, both paraphrased.
4. **W3C WCAG 2.2** — direct fetch **blocked** (w3.org returns HTTP 403 to
   this session's fetcher, both TR and WAI pages; recorded here as a fetch
   limitation, not as content). Referenced only as requirement *names*
   (accessible names, visible focus, text contrast, keyboard reachability —
   all corroborated by the fetched Vercel page, which itself cites WCAG 2.2
   Understanding docs for dragging-movements and pause-stop-hide). No WCAG
   prose reproduced, so no license exposure regardless.
5. **Platform-native conventions (Apple HIG, Material 3)** — direct fetch
   returned JS-rendered shells with no readable content (recorded as a fetch
   limitation). General principles applied from established knowledge and
   corroborated by the fetched Vercel page (44px mobile targets, safe areas,
   reduced-motion). Paraphrased; no text reproduced.
- VCE project docs (`docs/design-system.md`, `docs/ui-page-contract.md`) —
  read as the project-specific authority the skill defers to; not duplicated.

## Security review (per `security-review` procedure)

- New files are static Markdown prose: no executable code, no shell hooks, no
  network calls, no credential access, no new dependencies.
- `git diff --stat` / `git diff` to be reviewed before commit; secret scan via
  the Hub's existing checks. Nothing here crosses a trust boundary.
- Verbatim-import risk: none — there is no imported content to quarantine, so
  `skill-gate.sh` quarantine was not applicable. If a future revision imports
  external skill text, it must go through `/tmp/skill-quarantine/` +
  `security-review` + license record first.

## Why staged here instead of installed

The canonical library (`/srv/agent-workbench/skills`, same inode as
`~/.agents/skills`) is **read-only** in this session — verified:

```
touch /srv/agent-workbench/skills/.write-test → Read-only file system
```

Shared software there is administrator-managed per host policy. This directory
(`skills/ui-ux-review/` in the Hub repo) is the reviewable candidate. An
owner/admin installs it with:

```bash
cp -r skills/ui-ux-review /srv/agent-workbench/skills/ui-ux-review
# verify discovery: `opencode debug skill`, Codex `skills/list`
```

`AGENTS.md` was deliberately NOT wired to the new skill yet: pointing global
instructions at a skill that is not discoverable would be misleading. Wire it
after installation.

## Rollback

```bash
git rm -r skills/ui-ux-review
```

No other Hub file depends on this directory.
