"""The snapshot builder must refuse to run outside its contract.

A full build takes about a minute (it runs the snapshot's own gate), so the slow
end-to-end path is exercised by hand and recorded in evidence. These tests pin
the cheap invariants that make the build trustworthy: it refuses a target inside
the Hub, it names the private material it excludes, and it runs both gates on the
result before declaring success.
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parent.parent
BUILDER = HUB_ROOT / "scripts" / "build-public-snapshot.sh"


class BuildPublicSnapshot(unittest.TestCase):
    def test_refuses_a_target_inside_the_hub(self):
        proc = subprocess.run(["bash", str(BUILDER), str(HUB_ROOT / "tmp-public")],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("must not be inside the Hub", proc.stderr)
        self.assertFalse((HUB_ROOT / "tmp-public").exists(),
                         "a refused build must not create the target")

    def test_requires_a_target(self):
        proc = subprocess.run(["bash", str(BUILDER)], capture_output=True, text=True,
                              timeout=60)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("usage", (proc.stdout + proc.stderr).lower())

    def test_script_names_the_private_material_it_excludes(self):
        text = BUILDER.read_text(encoding="utf-8")
        for expected in ("ops", "evidence", "REPORT.md", "normal-user-runtime.md",
                         "readiness-2026-10-17.md"):
            with self.subTest(excluded=expected):
                self.assertIn(expected, text)

    def test_script_runs_both_gates_before_succeeding(self):
        text = BUILDER.read_text(encoding="utf-8")
        self.assertIn("publication-check.sh", text)
        self.assertIn("selfcheck.sh", text)
        self.assertIn("SNAPSHOT=PASS", text)
        self.assertIn("SNAPSHOT=FAIL", text)

    def test_script_redacts_the_incident_ledger(self):
        text = BUILDER.read_text(encoding="utf-8")
        self.assertIn("incidents.jsonl", text)
        self.assertIn("<private-ip>", text)
        self.assertIn("<session>", text)

    def test_publication_gate_does_not_scan_its_own_rule_tables(self):
        """The builder carries redaction rules; the gate must exclude it."""
        gate = (HUB_ROOT / "scripts" / "publication-check.sh").read_text(encoding="utf-8")
        self.assertIn("scripts/build-public-snapshot.sh", gate)


if __name__ == "__main__":
    unittest.main()
