---
name: security-review
description: Review diffs for leaked secrets, unsafe dependencies and risky changes. Use before commits, releases, or installing external code.
---

# Security review

1. `git diff --stat`, `git diff`, `gitleaks detect --source . --no-git` where available; check for keys, tokens, passwords, private URLs.
2. Review dependency/manifest changes; flag unknown external code, install hooks, network exfiltration, obfuscation.
3. Distinguish suspicion from confirmed vulnerability. Never auto-install, execute, or approve unknown code.
4. Report findings with file:line evidence + severity; clean scanner output is NOT proof of safety.
