---
name: verify-debug
description: Diagnose a failing check from its output and fix it, or confirm a change is green. Use when a test, lint or build check fails, or before reporting an implementation as done.
---

# Verify debug

1. Pick the smallest checks that actually cover the change. Respect the
   project's own gates; do not invent new ones for unrelated code.
2. Run them and read the real output. Diagnose from that output, not from a
   guess about what probably broke.
3. **After two speculative attempts at the same failure, stop guessing.** Record
   the exact failure, form a falsifiable root-cause hypothesis, and get a
   reproduction or a test that discriminates between causes before editing
   again. A retry or a longer timeout is not a diagnosis.
4. Fix, rerun the same checks. Repeat until they pass or the blocker is real and
   stated.
5. Report the commands you ran and their results. If something could not be
   verified, say so explicitly instead of implying it passed.
