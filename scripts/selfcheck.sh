#!/usr/bin/env bash
# AEH's own gate.
#
# The Hub grades other projects, so it must be able to grade itself. AEH has no
# registry entry (a registered source path inside the Hub fails doctor), so its
# gate is this script rather than a registry `verify` command. It is read-only
# with respect to every project repository; it runs only Hub-local checks.
#
#   python3 -m unittest discover -s tests -q   Hub safety and conformance tests
#   python3 scripts/conformance.py             negative fixtures, no false-green
#   bash evals/structural-check.sh             skill library and instruction surface
#   python3 scripts/hub.py doctor               config, registry, containment
#
# Exit 0 only when every step passes. Prints one final AEH_SELFCHECK line.
set -uo pipefail

HUB_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HUB_ROOT" || exit 1

failed=0
step() {
  local name="$1"; shift
  printf '\n=== %s ===\n' "$name"
  if "$@"; then
    printf '  -- %s: PASS\n' "$name"
  else
    printf '  -- %s: FAIL\n' "$name" >&2
    failed=1
  fi
}

step "hub unit tests" python3 -m unittest discover -s tests -q
step "conformance (no false-green)" python3 scripts/conformance.py
step "structural check" bash evals/structural-check.sh
step "doctor" python3 scripts/hub.py doctor

printf '\n'
if ((failed)); then
  printf 'AEH_SELFCHECK=FAIL\n'
  exit 1
fi
printf 'AEH_SELFCHECK=PASS\n'
