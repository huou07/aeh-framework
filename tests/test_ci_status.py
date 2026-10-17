"""A check that never started is BLOCKED, not FAILED and never PASS.

The Hub's CI on a private repository was blocked by the account's Actions
spending limit: GitHub reported the job as failed with zero steps and an
annotation explaining that the job was not started. `scripts/ci-status.sh` must
tell those states apart, because "CI is red" otherwise hides "CI never ran".
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = HUB_ROOT / "scripts" / "ci-status.sh"

FAKE_GH = """#!/usr/bin/env bash
if [[ "$1 $2" == "api repos/fixture/repo/commits/HEAD" ]]; then
  echo '{"sha":"deadbeef"}'; exit 0
fi
if [[ "$1 $2" == "api repos/fixture/repo/commits/deadbeef/check-runs" ]]; then
  cat "${FAKE_CHECKS}"; exit 0
fi
case "$2" in
  repos/fixture/repo/check-runs/*/annotations) cat "${FAKE_ANNOTATIONS:-/dev/null}"; exit 0 ;;
esac
echo "fake gh: unhandled $*" >&2
exit 2
"""


def check_run(name: str, conclusion: str | None, run_id: int = 1) -> dict:
    return {"id": run_id, "name": name, "conclusion": conclusion, "status": "completed",
            "details_url": "https://example.invalid/run/1", "output": {}}


def run_status(checks: list[dict], annotations: list[dict] | None = None,
               required: str = "release-gate") -> subprocess.CompletedProcess:
    tmp = Path(tempfile.mkdtemp(prefix="aeh-cistatus-"))
    bin_dir = tmp / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(0o755)
    (tmp / "checks.json").write_text(json.dumps({"check_runs": checks}))
    (tmp / "annotations.json").write_text(json.dumps(annotations or []))
    env = dict(os.environ)
    env.update({"PATH": f"{bin_dir}:{env['PATH']}",
                "FAKE_CHECKS": str(tmp / "checks.json"),
                "FAKE_ANNOTATIONS": str(tmp / "annotations.json")})
    return subprocess.run(["bash", str(SCRIPT), "fixture/repo", "deadbeef", required],
                          capture_output=True, text=True, env=env, timeout=60)


class CiStatus(unittest.TestCase):
    def test_successful_required_check_is_verified(self):
        proc = run_status([check_run("release-gate", "success"), check_run("self gate", "success")])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("VERIFIED", proc.stdout)

    def test_not_started_job_is_blocked_and_prints_the_reason(self):
        message = ("The job was not started because recent account payments have failed or "
                   "your spending limit needs to be increased.")
        proc = run_status([check_run("release-gate", "failure")],
                          annotations=[{"annotation_level": "failure", "message": message}])
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertIn("BLOCKED", proc.stdout)
        self.assertIn("spending limit", proc.stdout)

    def test_required_check_absent_is_blocked_not_verified(self):
        proc = run_status([check_run("self gate", "success")])
        self.assertEqual(proc.returncode, 3, proc.stdout)
        self.assertIn("did not run", proc.stdout)

    def test_real_failure_is_failed(self):
        proc = run_status([check_run("release-gate", "failure")],
                          annotations=[{"annotation_level": "failure", "message": "step 4 failed"}])
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("FAILED", proc.stdout)
        self.assertIn("step 4 failed", proc.stdout)

    def test_no_check_runs_is_blocked(self):
        proc = run_status([])
        self.assertEqual(proc.returncode, 3, proc.stdout)
        self.assertIn("BLOCKED", proc.stdout)

    def test_table_never_contaminates_the_machine_line(self):
        """The table goes to stderr, so a multi-line listing cannot corrupt parsing."""
        proc = run_status([check_run("self gate", "success"), check_run("release-gate", "success")])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("self gate", proc.stderr)
        self.assertNotIn("self gate", proc.stdout)

    def test_script_is_not_part_of_the_self_gate(self):
        selfcheck = (HUB_ROOT / "scripts" / "selfcheck.sh").read_text(encoding="utf-8")
        self.assertNotIn("ci-status", selfcheck,
                         "reading GitHub needs the network and must stay an explicit command")


if __name__ == "__main__":
    unittest.main()
