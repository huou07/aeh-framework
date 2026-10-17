"""`hub.py` accepts hosted evidence only for the exact revision it names.

A hosted run is proof about one commit's environment. Merging it into a record
for a different commit would be a false green, so the reader is strict: wrong
revision, missing revision, malformed file or a non-hosted runner all refuse, and
each refusal says why.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import hub


def write_evidence(project: Path, payload: object) -> None:
    path = project / ".hub" / "hosted-evidence.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) if not isinstance(payload, str) else payload)


def evidence(head: str = "a" * 40, kind: str = "hosted") -> dict:
    return {"head": head, "repo": "owner/repo", "branch": "main", "workflow": "ci.yml",
            "conclusion": "success", "recorded_at": "2026-10-18T00:00:00+00:00",
            "runner": {"kind": kind, "os": "github-actions", "run_id": "1",
                       "run_url": "https://example.invalid/run/1", "label": "ci.yml"}}


class HostedEvidenceMerge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_absent_file_is_not_an_error(self):
        self.assertEqual(hub.read_hosted_evidence(self.project, "a" * 40), (None, None))

    def test_matching_revision_and_hosted_runner_is_accepted(self):
        write_evidence(self.project, evidence())
        data, note = hub.read_hosted_evidence(self.project, "a" * 40)
        self.assertIsNone(note)
        self.assertEqual(data["runner"]["kind"], "hosted")

    def test_another_revision_is_refused_with_a_reason(self):
        write_evidence(self.project, evidence(head="b" * 40))
        data, note = hub.read_hosted_evidence(self.project, "a" * 40)
        self.assertIsNone(data)
        self.assertIn("another revision", note)

    def test_unknown_current_revision_is_refused(self):
        write_evidence(self.project, evidence())
        data, note = hub.read_hosted_evidence(self.project, None)
        self.assertIsNone(data)
        self.assertIn("cannot be bound", note)

    def test_missing_revision_field_is_refused(self):
        payload = evidence()
        payload.pop("head")
        write_evidence(self.project, payload)
        data, note = hub.read_hosted_evidence(self.project, "a" * 40)
        self.assertIsNone(data)
        self.assertIn("names no revision", note)

    def test_non_hosted_runner_is_refused(self):
        write_evidence(self.project, evidence(kind="local"))
        data, note = hub.read_hosted_evidence(self.project, "a" * 40)
        self.assertIsNone(data)
        self.assertIn("hosted runner", note)

    def test_malformed_file_is_refused_not_ignored(self):
        write_evidence(self.project, "{not json\n")
        data, note = hub.read_hosted_evidence(self.project, "a" * 40)
        self.assertIsNone(data)
        self.assertIn("unreadable", note)

    def test_non_object_file_is_refused(self):
        write_evidence(self.project, ["not", "an", "object"])
        data, note = hub.read_hosted_evidence(self.project, "a" * 40)
        self.assertIsNone(data)
        self.assertIn("not a JSON object", note)


if __name__ == "__main__":
    unittest.main()
