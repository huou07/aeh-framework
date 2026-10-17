"""AEH conformance gate: the Hub must not claim VERIFIED when it should not.

The Hub grades other projects, so it is graded here adversarially. Every fixture
in `tests/fixtures/conformance/` builds a disposable Hub copy, runs the real
`scripts/hub.py`, and asserts the verdict the scenario requires. A fixture that
is present but never exercised is a failure too: the suite refuses to report
coverage it did not earn.

Zero false-green on the designed set is the acceptance criterion. It is not a
claim that the Hub can never be wrong.
"""

from __future__ import annotations

import functools
import json
import subprocess
import sys
import unittest
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parent.parent
RUNNER = HUB_ROOT / "scripts" / "conformance.py"
CONFORMANCE_DIR = HUB_ROOT / "tests" / "fixtures" / "conformance"

# The scenarios the owner named, each of which must exist and be exercised.
MANDATORY_SCENARIOS = {
    "verified-clean-head",
    "unpushed-head",
    "stale-old-sha",
    "skipped-required-gate",
    "no-acceptance-record",
    "artifact-hash-mismatch",
    "missing-required-runner",
    "agent-claim-no-log",
    "malformed-ledger",
    "contract-invalid-unknown-gate",
    "contract-command-injection",
    "status-is-read-only",
    "verify-timeout-blocked",
    "dirty-tree-stale",
    "no-contract",
}


@functools.lru_cache(maxsize=1)
def conformance_report() -> tuple[int, str, dict | None]:
    """Run the conformance suite once per test process."""
    proc = subprocess.run([sys.executable, str(RUNNER), "--json"],
                          cwd=str(HUB_ROOT), capture_output=True, text=True,
                          timeout=1800)
    try:
        payload = json.loads(proc.stdout)
    except ValueError:
        payload = None
    return proc.returncode, (proc.stdout + proc.stderr), payload


class ConformanceSuite(unittest.TestCase):
    def test_fixtures_produce_the_expected_verdicts(self):
        code, output, payload = conformance_report()
        self.assertIsNotNone(payload, f"conformance runner emitted no JSON:\n{output}")
        failures = [f"{item['id']}: {'; '.join(item['problems'])}"
                    for item in payload["fixtures"] if not item["ok"]]
        self.assertEqual(failures, [], "\n".join(failures) + "\n" + output)
        self.assertEqual(code, 0, output)

    def test_mandatory_scenarios_exist_and_run(self):
        _, output, payload = conformance_report()
        self.assertIsNotNone(payload, output)
        exercised = {item["id"] for item in payload["fixtures"]}
        self.assertEqual(MANDATORY_SCENARIOS - exercised, set(),
                         "mandatory negative scenario(s) missing from the suite")

    def test_no_undeclared_fixture_directories(self):
        on_disk = {path.parent.name for path in CONFORMANCE_DIR.glob("*/scenario.json")}
        _, output, payload = conformance_report()
        self.assertIsNotNone(payload, output)
        exercised = {item["id"] for item in payload["fixtures"]}
        self.assertEqual(on_disk - exercised, set(),
                         "fixture on disk but never exercised")

    def test_fixture_scenarios_are_valid_json_objects(self):
        paths = sorted(CONFORMANCE_DIR.glob("*/scenario.json"))
        self.assertTrue(paths, "no conformance scenario files found")
        for path in paths:
            with self.subTest(fixture=path.parent.name):
                spec = json.loads(path.read_text(encoding="utf-8"))
                self.assertIsInstance(spec, dict)
                self.assertEqual(spec.get("id"), path.parent.name)
                self.assertTrue(spec.get("expect") is not None or spec.get("probes"),
                                "a scenario must assert something")


if __name__ == "__main__":
    unittest.main()
