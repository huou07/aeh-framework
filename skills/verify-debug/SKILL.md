---
name: verify-debug
description: Diagnose and repair a failing test, lint, build or runtime check, or verify a requested implementation against its existing gates. Do not use for status-only requests, ordinary questions or prose-only edits with no meaningful executable check.
---

# Verify debug

## Establish evidence

Resolve the repository, scope, source identity and canonical gate. Use existing
authorization; a check that executes project code is distinct from reading status.
Select the smallest check that covers the changed behaviour or observed failure.
Do not invent product tests for a wording-only change.

## Diagnose and repair

1. Run the relevant authorized check and read its actual output, including exit
   status. Distinguish PASS, FAIL, TIMEOUT, NOT RUN and unavailable tooling.
2. Identify the failing path and state a falsifiable hypothesis. Use a minimal
   reproduction or check that distinguishes likely causes.
3. Make the smallest justified correction; preserve acceptance and unrelated work.
   Never weaken an assertion, scanner or environment boundary to obtain PASS.
4. Rerun the failing check. After two speculative attempts at the same failure,
   require new discriminating evidence before another edit.
5. Run the relevant broader project gate when justified. Once checks pass, repeat
   or expand testing only for new changes, failures or unresolved risks.

## Stop and output

Stop when the requested behaviour has relevant evidence, or a concrete missing
capability/authority prevents further work. Report commands, results, source
identity, actual repair, remaining risks and unverified runtime/platform items.
Skipped or synthetic checks do not establish real user or packaged acceptance.
