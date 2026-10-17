---
name: code-investigate
description: Locate relevant code fast with rg, fd, ast-grep and CodeGraph before reading files. Use for bug hunts, impact analysis, and codebase orientation.
---

# Code investigate

1. Scope: `git status`, `git log --oneline -10`, repo root.
2. Static search first: `rg -n "pattern"`, `fd <name>`, `ast-grep run --pattern '<ast>' --lang <lang> <path>` (NOTE: never bare `sg` — that is util-linux set-group on Debian). Prefer structural search over full-file reads.
3. If `.codegraph/` exists: `codegraph explore "<symbol or question>"` (or `codegraph_explore` MCP) for symbols, callers, call paths.
4. Inspect callers/dependencies + recent changes (`git log -p -- <file>`), then load only relevant files.
5. Report: matched files:symbols, call paths, what was NOT found.

Rules: never dump whole repos; never index `/`, `/etc`, secrets stores.
