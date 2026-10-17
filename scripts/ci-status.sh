#!/usr/bin/env bash
# Read-only: did the required hosted check actually RUN for this revision?
#
# A job that never started is not a pass, and it is not a product failure either.
# GitHub reports it as a failed check whose annotation explains why — on a private
# repository the common cause is an Actions spending limit or a missing payment
# method. Without this distinction "CI is red" hides "CI never ran", and the Hub
# would treat an unverified revision as a verified failure.
#
#   bash scripts/ci-status.sh <owner/repo> [sha] [required-check]
#
# Exit: 0 the required check ran and succeeded (VERIFIED)
#       1 it ran and failed (FAILED, annotation printed)
#       3 it did not run, could not be read, or the runner never started (BLOCKED)
set -uo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "ci-status: gh is not installed" >&2
  exit 3
fi

REPO="${1:?usage: ci-status.sh <owner/repo> [sha] [required-check]}"
SHA="${2:-}"
REQUIRED="${3:-release-gate}"

if [[ -z "$SHA" ]]; then
  SHA="$(gh api "repos/$REPO/commits/HEAD" --jq '.sha' 2>/dev/null || true)"
fi
if [[ -z "$SHA" ]]; then
  echo "RESULT: BLOCKED — could not resolve a revision for $REPO"
  exit 3
fi

payload="$(gh api "repos/$REPO/commits/$SHA/check-runs" 2>/dev/null || true)"
if [[ -z "$payload" ]]; then
  echo "RESULT: BLOCKED — no check runs readable for $REPO@${SHA:0:12} (not a pass)"
  exit 3
fi

# The table goes to stderr so it cannot contaminate the machine line on stdout:
#   <VERIFIED|UNKNOWN|BLOCKED>|<run_id>|<detail>
selection="$(REQUIRED="$REQUIRED" PAYLOAD="$payload" python3 - <<'PY'
import json, os, sys

required = os.environ["REQUIRED"]
runs = (json.loads(os.environ["PAYLOAD"]).get("check_runs")) or []

for run in runs:
    name = run.get("name") or "<unnamed>"
    conclusion = run.get("conclusion") or run.get("status") or "unknown"
    print(f"  {name:<24} {conclusion}", file=sys.stderr)

if not runs:
    print("BLOCKED||no check run exists for this revision")
    raise SystemExit(0)

match = [r for r in runs if (r.get("name") or "") == required]
if not match:
    print(f"BLOCKED||required check '{required}' did not run for this revision")
    raise SystemExit(0)

run = match[0]
conclusion = run.get("conclusion") or run.get("status") or "unknown"
# Whether a non-success is a real failure or a job that never started is only
# visible in the annotation, which the list endpoint does not carry.
verdict = "VERIFIED" if conclusion == "success" else "UNKNOWN"
print(f"{verdict}|{run.get('id') or ''}|{conclusion}")
PY
)"

echo "repo     : $REPO"
echo "revision : $SHA"
echo "required : $REQUIRED"
echo

status="${selection%%|*}"
rest="${selection#*|}"
run_id="${rest%%|*}"
detail="${rest#*|}"

if [[ "$status" == "VERIFIED" ]]; then
  echo "RESULT: VERIFIED — $REQUIRED ran and succeeded at ${SHA:0:12}"
  exit 0
fi

if [[ "$status" == "BLOCKED" ]]; then
  echo "RESULT: BLOCKED — $detail"
  echo "        A check that did not run is not a pass and not a product defect."
  exit 3
fi

annotation=""
if [[ -n "$run_id" ]]; then
  annotation="$(gh api "repos/$REPO/check-runs/$run_id/annotations" \
    --jq '[.[] | select(.annotation_level=="failure")][0].message // empty' 2>/dev/null || true)"
fi

case "$annotation" in
  *"was not started"*|*"spending limit"*|*"payments have failed"*)
    echo "RESULT: BLOCKED — $REQUIRED did not start (conclusion $detail)"
    [[ -n "$annotation" ]] && echo "        $annotation"
    echo "        The runner never ran; this revision is NOT VERIFIED."
    exit 3
    ;;
esac

echo "RESULT: FAILED — $REQUIRED concluded $detail"
[[ -n "$annotation" ]] && echo "        $annotation"
exit 1
