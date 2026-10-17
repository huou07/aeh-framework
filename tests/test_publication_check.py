"""The publication gate must fail on host-specific material, and pass on a clean tree.

AEH is a private control workspace that legitimately holds private addresses,
VPN port maps, absolute home paths and operations scripts. The guard for that is
`scripts/publication-check.sh`: it must refuse to call such a tree publishable,
and it must not become a permanently red check inside the normal self gate (a
gate that always fails trains people to ignore red).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parent.parent
CHECK = HUB_ROOT / "scripts" / "publication-check.sh"


def run_check(target: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    # Keep the result independent of whether gitleaks happens to be installed.
    env["PATH"] = "/usr/bin:/bin"
    return subprocess.run(["bash", str(CHECK), str(target)], capture_output=True,
                          text=True, env=env, timeout=120)


class PublicationCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aeh-pubcheck-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_clean_tree_is_publishable(self):
        (self.tmp / "README.md").write_text("# A tool\n\nNothing host-specific here.\n")
        (self.tmp / "docs").mkdir()
        (self.tmp / "docs" / "design.md").write_text("Uses a public host: example.com\n")
        proc = run_check(self.tmp)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("PUBLICATION CHECK PASSED", proc.stdout)

    def test_private_address_fails(self):
        (self.tmp / "notes.md").write_text("Playground: http://10.8.0.1:8765/\n")
        proc = run_check(self.tmp)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("private-ipv4", proc.stdout)
        self.assertIn("NOT PUBLISHABLE", proc.stdout)

    def test_absolute_home_path_fails(self):
        (self.tmp / "conf.json").write_text('{"workspace_root": "/home/huou07/Projects"}\n')
        proc = run_check(self.tmp)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("absolute-home-path", proc.stdout)

    def test_vpn_port_map_fails(self):
        (self.tmp / "runtime.md").write_text("DSH: open its Playground card; VPN port 3080.\n")
        proc = run_check(self.tmp)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("vpn-port-map", proc.stdout)

    def test_findings_never_print_the_matched_value(self):
        secret_host = "10.9.9.9"
        (self.tmp / "leak.md").write_text(f"host={secret_host}\n")
        proc = run_check(self.tmp)
        self.assertEqual(proc.returncode, 1)
        self.assertNotIn(secret_host, proc.stdout,
                         "the gate must name the file and rule, not echo the value")

    def test_untracked_files_are_scanned_in_a_git_tree(self):
        (self.tmp / "README.md").write_text("clean\n")
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(self.tmp), check=True,
                       capture_output=True)
        subprocess.run(["git", "add", "-A"], cwd=str(self.tmp), check=True, capture_output=True)
        # Present on disk but never committed: `git add -A` would publish it later.
        (self.tmp / "untracked-notes.md").write_text("wireguard wg0 is up\n")
        proc = run_check(self.tmp)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("untracked-notes.md", proc.stdout)

    def test_self_gate_does_not_run_the_publication_check(self):
        selfcheck = (HUB_ROOT / "scripts" / "selfcheck.sh").read_text(encoding="utf-8")
        self.assertNotIn("publication-check", selfcheck,
                         "the publication gate fails by design on this tree and must not be "
                         "part of the always-on self gate")

    def test_agents_md_states_the_publication_rule(self):
        agents = (HUB_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("publication-check.sh", agents)
        self.assertIn("private", agents.lower())


if __name__ == "__main__":
    unittest.main()
