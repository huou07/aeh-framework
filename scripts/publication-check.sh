#!/usr/bin/env bash
# Publication gate for the Hub repository.
#
# The Hub is a control workspace: it legitimately holds host-specific material
# (private addresses, VPN port maps, absolute home paths, operations scripts,
# session and incident records). That is fine while the repository is private and
# it is exactly what must not be world-readable.
#
# Run this BEFORE publishing the repository, pushing it to a public mirror, or
# making a public remote the default. It is deliberately NOT part of
# scripts/selfcheck.sh: it fails by design on today's tree, and a gate that is
# always red trains people to ignore red.
#
#   bash scripts/publication-check.sh            # scan the Hub tree
#   bash scripts/publication-check.sh <dir>      # scan any directory
#
# Read-only, deterministic, no network. Exit 0 only when the scanned tree carries
# no host-specific or secret material. It prints file:line and the rule name, and
# never prints the matched value.
set -uo pipefail

TARGET="${1:-}"
if [[ -z "$TARGET" ]]; then
  TARGET="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
fi

if [[ ! -d "$TARGET" ]]; then
  echo "publication-check: not a directory: $TARGET" >&2
  exit 2
fi

# Rules are (name|extended regex). Keep them host-specific, not style rules.
RULES=(
  'private-ipv4|(^|[^0-9])10\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}([^0-9]|$)'
  'private-ipv4|(^|[^0-9])192\.168\.[0-9]{1,3}\.[0-9]{1,3}([^0-9]|$)'
  'private-ipv4|(^|[^0-9])172\.(1[6-9]|2[0-9]|3[01])\.[0-9]{1,3}\.[0-9]{1,3}([^0-9]|$)'
  'absolute-home-path|(^|[^A-Za-z0-9_])/home/[a-z][a-z0-9_.-]*'
  'vpn-or-tunnel|(utun[0-9]+|wireguard|wg[0-9]+|WG_ENDPOINT)'
  'private-model-route|(litellm|omniroute|omni-route)'
  'vpn-port-map|([Vv][Pp][Nn])[^.]{0,24}(port|PORT)'
  'private-key-material|BEGIN [A-Z ]*PRIVATE KEY'
  'credential-assignment|(password|passwd|secret|token|api[_-]?key)["'"'"']?[[:space:]]*[:=][[:space:]]*["'"'"'][^"'"'"']{8,}'
)

if git -C "$TARGET" rev-parse --git-dir >/dev/null 2>&1; then
  mapfile -t FILES < <(git -C "$TARGET" ls-files)
  SCOPE="tracked files"
  # Untracked-but-present material is the same leak once someone runs `git add -A`.
  while IFS= read -r extra; do
    [[ -n "$extra" ]] && FILES+=("$extra")
  done < <(git -C "$TARGET" ls-files --others --exclude-standard)
else
  mapfile -t FILES < <(cd "$TARGET" && find . -type f -not -path './.git/*' -printf '%P\n' | sort)
  SCOPE="files on disk"
fi

echo "publication-check — $TARGET ($SCOPE)"
findings=0

# The checker and its test contain the rule table itself, so they would always
# match their own patterns. Excluded explicitly rather than by weakening a rule.
EXCLUDE=('scripts/publication-check.sh' 'tests/test_publication_check.py'
         'scripts/build-public-snapshot.sh' 'tests/test_build_public_snapshot.py')

for rule in "${RULES[@]}"; do
  name="${rule%%|*}"
  pattern="${rule#*|}"
  for rel in "${FILES[@]:-}"; do
    [[ -z "$rel" ]] && continue
    skip=0
    for excluded in "${EXCLUDE[@]}"; do
      [[ "$rel" == "$excluded" ]] && skip=1
    done
    ((skip)) && continue
    file="$TARGET/$rel"
    [[ -f "$file" ]] || continue
    # Skip binary-looking files: a match there is noise, not evidence.
    if ! grep -Iq . "$file" 2>/dev/null; then continue; fi
    if grep -nEI -- "$pattern" "$file" >/dev/null 2>&1; then
      while IFS=: read -r line _rest; do
        echo "  FAIL  $name  $rel:$line"
        findings=$((findings + 1))
      done < <(grep -nEI -- "$pattern" "$file" | cut -d: -f1-2 | head -3)
    fi
  done
done

# Secrets get a real scanner when one is available, not a regex of ours.
#
# Two gitleaks builds exist on this host: ~/.local/bin/gitleaks is 8.30.1 (the
# version the product repositories pin in CI) and /usr/bin/gitleaks is an older
# build whose `detect` exits 1 on a non-git directory while reporting "no leaks
# found". So: prefer the pinned install, pass --no-git when the target is not a
# repository, and judge the JSON report rather than the exit code. A scanner that
# cannot complete is NOT PASS (incident AEH-D025).
GITLEAKS=""
for candidate in "${HOME:-/root}/.local/bin/gitleaks" "$(command -v gitleaks 2>/dev/null || true)"; do
  if [[ -n "$candidate" && -x "$candidate" ]]; then GITLEAKS="$candidate"; break; fi
done

if [[ -n "$GITLEAKS" ]]; then
  gl_version="$("$GITLEAKS" version 2>/dev/null | head -n 1 || true)"
  [[ -n "$gl_version" ]] || gl_version="version-unknown"
  gl_report="$(mktemp)"
  gl_args=(detect --source "$TARGET" --no-banner --redact
           --report-format json --report-path "$gl_report")
  git -C "$TARGET" rev-parse --git-dir >/dev/null 2>&1 || gl_args+=(--no-git)
  "$GITLEAKS" "${gl_args[@]}" >/dev/null 2>&1 || true
  gl_count="$(python3 - "$gl_report" <<'PY' 2>/dev/null || true
import json, sys
try:
    data = json.load(open(sys.argv[1]))
except Exception:
    raise SystemExit(0)
print(len(data) if isinstance(data, list) else 0)
PY
)"
  rm -f "$gl_report"
  if [[ "$gl_count" =~ ^[0-9]+$ ]]; then
    if ((gl_count > 0)); then
      echo "  FAIL  gitleaks $gl_version: $gl_count secret finding(s)"
      findings=$((findings + 1))
    else
      echo "  PASS  gitleaks $gl_version: no secret material found"
    fi
  else
    echo "  NOTE  gitleaks $gl_version could not complete: secret scanning was skipped, not passed"
  fi
else
  echo "  NOTE  gitleaks not installed: secret scanning was skipped, not passed"
fi

echo
if ((findings)); then
  echo "RESULT: NOT PUBLISHABLE ($findings host-specific or secret finding(s))"
  echo "        Publish a sanitised snapshot, or keep the repository private."
  echo "        The Hub is private by decision (evidence/incidents.jsonl AEH-D024)."
  exit 1
fi
echo "RESULT: PUBLICATION CHECK PASSED"
