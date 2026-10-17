"""Hosted evidence must be recorded without erasing the gate's own report.

AEH is offline, so a contract with `hosted_ci: "required"` is only satisfied when
the project records the hosted run itself. The recorder writes
`.hub/hosted-evidence.json` — a separate file, because the project's gate rewrites
`.hub/gate-report.json` on every run and would otherwise erase the proof.
`hub.py verify` merges the two, and only for the exact revision.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = HUB_ROOT / "templates" / "hosted-evidence.sh"

FAKE_GH = """#!/usr/bin/env bash
case "$1 $2" in
  "repo view") echo "${FAKE_REPO}" ;;
  "run list") cat "${FAKE_RUN_JSON}" ;;
  *) echo "fake gh: unhandled $*" >&2; exit 2 ;;
esac
"""

RUN = [{
    "databaseId": 4242,
    "headSha": "HEAD",
    "url": "https://example.invalid/run/4242",
    "conclusion": "success",
    "workflowName": "ci.yml",
    "event": "push",
}]


def git(args: list[str], cwd: Path) -> None:
    env = dict(os.environ)
    env.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
                "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
                "GIT_CONFIG_COUNT": "0"})
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True,
                   text=True, env=env)


class HostedEvidenceTemplate(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aeh-hosted-"))
        self.project = self.tmp / "project"
        self.project.mkdir()
        git(["init", "-q", "-b", "main"], self.project)
        (self.project / "README.md").write_text("fixture\n")
        git(["add", "-A"], self.project)
        git(["commit", "-q", "-m", "fixture"], self.project)
        shutil.copy2(TEMPLATE, self.project / "hosted-evidence.sh")

        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text(FAKE_GH)
        gh.chmod(0o755)
        self.run_json = self.tmp / "run.json"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_script(self) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env.update({
            "PATH": f"{self.bin}:{env['PATH']}",
            "FAKE_REPO": "huou07/fixture",
            "FAKE_RUN_JSON": str(self.run_json),
        })
        return subprocess.run(["bash", "hosted-evidence.sh", "ci.yml"],
                              cwd=str(self.project), capture_output=True, text=True,
                              env=env, timeout=60)

    def test_no_successful_run_is_blocked_and_writes_nothing(self):
        self.run_json.write_text("[]\n")
        proc = self.run_script()
        self.assertEqual(proc.returncode, 3, proc.stdout + proc.stderr)
        self.assertIn("BLOCKED", proc.stderr)
        self.assertFalse((self.project / ".hub" / "hosted-evidence.json").exists())

    def test_successful_run_records_hosted_runner_for_this_revision(self):
        self.run_json.write_text(json.dumps(RUN) + "\n")
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(self.project),
                              capture_output=True, text=True, check=True).stdout.strip()
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        evidence = json.loads((self.project / ".hub" / "hosted-evidence.json").read_text())
        self.assertEqual(evidence["head"], head)
        self.assertEqual(evidence["runner"]["kind"], "hosted")
        self.assertEqual(evidence["runner"]["run_id"], "4242")
        self.assertEqual(evidence["conclusion"], "success")

    def test_it_never_touches_the_gate_report(self):
        """The gate rewrites its own report; the recorder must not compete with it."""
        self.run_json.write_text(json.dumps(RUN) + "\n")
        report = self.project / ".hub" / "gate-report.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps({"skipped": [{"check": "gpu", "reason": "none"}]}))
        before = report.read_text()
        self.assertEqual(self.run_script().returncode, 0)
        self.assertEqual(report.read_text(), before)

    def test_template_is_referenced_by_the_interface(self):
        interface = (HUB_ROOT / "docs" / "quality-interface.md").read_text(encoding="utf-8")
        self.assertIn("hosted-evidence.sh", interface)
        self.assertIn("hosted-evidence.json", interface)


if __name__ == "__main__":
    unittest.main()
