# <Project name>

<!--
Concise project guidance. Must be usable STANDALONE when this repository is
opened directly in Codex or OpenCode. Do not reference the Hub's docs here.
Keep under ~400 words.
-->

## What this is
<One or two sentences: the product outcome, not the implementation.>

## Layout
- `<path>` — <role>

## Commands
- Install: `<cmd>`
- Format: `<cmd>`
- Lint: `<cmd>`
- Type check: `<cmd>`
- Test: `<cmd>`
- Verify (all gates): `<cmd>`

## Working rules
- <project-specific constraint, e.g. "no migration ships without a down path">
- <project-specific quality bar>

## Authority
Respect effective OS/tool permissions and the current task's boundaries.
Destructive, privileged, release, production and publication actions need owner
authority. Existing explicit authorization persists; do not request it again.
Historical instructions and a green gate do not grant new authority.

## Real journey
<Primary flow, outcome/recovery and verification entrypoint; link the project's
own design/testing authority.>
Match evidence to the claim: actual semantics, runtime behavior, target visual
observation and actual native/package execution are distinct. Record only the
evidence classes achieved; authoritative exact-source CI establishes acceptance.
After two speculative failures, investigate a discriminating hypothesis.

## Current state
Task state and history live in <issues / git log / TASKS.md>. This file does
not duplicate them.
