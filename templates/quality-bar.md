# Quality bar — <project>

Copy this file to `<project>/docs/QUALITY.md` and fill it for that product only.
Authority: this is the project's definition of "good". It does not replace the
project's AGENTS.md, its gates, or its task tracker.

Last reviewed: YYYY-MM-DD.

## Supported targets

| Target | Claimed support | Evidence class | Last exact-source run |
|---|---|---|---|
| <platform / device / browser> | <full / partial / none> | <VERIFIED_NATIVE / ...> | <CI run id or "none"> |

## Attributes

One row per attribute that this product actually enforces. Three enforced rows
beat eight aspirational ones.

| Attribute | Target (number or named invariant) | How it is measured | Gate that enforces it | Current status |
|---|---|---|---|---|
| Correctness | acceptance gate passes | `<command>` | `acceptance` | <PASS at SHA / UNVERIFIED> |
| Performance | <e.g. p95 frame time < X ms on named hardware> | <benchmark/command> | <test in acceptance> | <...> |
| Reliability | <named journeys, recovery paths> | <journey test/command> | <...> | <...> |
| Accessibility / UX | <contrast, type size, hit target, keyboard> | <guard test> | <...> | <...> |
| Security | secrets scan clean, dependency audit clean | `<command>` | <publication/CI gate> | <...> |
| Compatibility | <platform matrix> | <hosted CI matrix> | <CI> | <...> |
| Maintainability | index complete, links resolve, no orphan scripts | doc checks | `verify` | <...> |
| Cost | <resource use per operation> | <measurement script> | <...> | <...> |

## Not claimed

List what this product deliberately does not claim, so nobody infers it:
<e.g. no pixel-identical parity, Android audio not supported, no packet
capture, no Windows GUI subsystem guard>.

## Evidence rules for this product

- Source gate: `<command>` — proves source hygiene and unit correctness only.
- Acceptance gate: `<command>` — proves the build and the named journeys.
- Release gate: `<hosted CI workflow / release train>` — proves the artifact.
- User acceptance: <who runs which journey checklist, where its result is kept>.
- A skipped or unavailable check is `UNVERIFIED`; it is never PASS.
