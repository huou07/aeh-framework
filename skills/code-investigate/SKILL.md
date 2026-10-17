---
name: code-investigate
description: Locate relevant code and explain callers, dependencies or change impact. Use for bug investigation and codebase orientation. Do not use for ordinary file listing, simple prose edits or a task already grounded in the necessary code.
---

# Code investigate

## Preconditions

Resolve the repository and applicable guidance. Inspect Git status and relevant
recent history; preserve work in progress. Discovery is read-only.

## Procedure

1. Define the symbol, behaviour or impact question. In an indexed repository,
   explore its CodeGraph index before broad search; verify index results against
   source because the index may be stale.
2. Use the session's native search and read tools. Where shell search is allowed,
   use rg, fd and ast-grep for the smallest relevant path. Never use bare sg
   (the Unix command changes groups); use ast-grep explicitly.
3. Read matched definitions, callers and relevant tests. Inspect recent changes
   only where they explain the behaviour. Do not dump the entire repository.
4. Trace the actual input, state and output path. Separate demonstrated code
   relationships from hypotheses that need runtime evidence.
5. Stop when the question is answered or a specific missing source/index/runtime
   prevents it. Do not build a new index outside the authorized repository.

## Output

Report files and symbols, relevant callers/dependencies, the supported conclusion
and its limits. For a bug, name the next discriminating check. Do not claim a
runtime fix, edit code or run a project gate from this investigation alone.
