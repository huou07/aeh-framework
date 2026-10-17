"""Schema guard for the Hub incident ledger.

The ledger is evidence: every entry records a failure that actually happened, its
root cause and the guard that keeps it from recurring. This test keeps the ledger
machine-checkable so it cannot decay into prose.
"""

import json
import re
import unittest
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parent.parent
LEDGER = HUB_ROOT / "evidence" / "incidents.jsonl"

REQUIRED = ("id", "date", "class", "where", "symptom", "root_cause",
            "evidence", "disposition", "guard", "related")
CLASSES = {"harness", "process", "host", "product"}
DISPOSITIONS = {"fixed", "guarded", "open", "superseded", "delegated"}
ID_PATTERN = re.compile(r"^AEH-D\d{3}$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_records():
    records = []
    for number, line in enumerate(LEDGER.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append((number, json.loads(line)))
        except json.JSONDecodeError as error:
            raise AssertionError(f"line {number} is not valid JSON: {error}") from error
    return records


class IncidentLedgerTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(LEDGER.is_file(), f"missing incident ledger: {LEDGER}")
        self.records = load_records()
        self.assertTrue(self.records, "the incident ledger is empty")

    def test_every_record_has_the_required_fields(self):
        for number, record in self.records:
            missing = [key for key in REQUIRED if key not in record]
            self.assertEqual(missing, [], f"line {number} is missing {missing}")

    def test_no_extra_fields(self):
        for number, record in self.records:
            extra = sorted(set(record) - set(REQUIRED))
            self.assertEqual(extra, [], f"line {number} has unexpected fields {extra}")

    def test_class_and_disposition_are_known(self):
        for number, record in self.records:
            self.assertIn(record["class"], CLASSES, f"line {number}: bad class")
            self.assertIn(record["disposition"], DISPOSITIONS, f"line {number}: bad disposition")

    def test_ids_are_unique_and_well_formed(self):
        seen = set()
        for number, record in self.records:
            self.assertRegex(record["id"], ID_PATTERN, f"line {number}: bad id")
            self.assertNotIn(record["id"], seen, f"duplicate id {record['id']}")
            seen.add(record["id"])

    def test_dates_are_iso_days(self):
        for number, record in self.records:
            self.assertRegex(record["date"], DATE_PATTERN, f"line {number}: bad date")

    def test_every_record_names_a_guard(self):
        """A failure without a guard is a story, not a fixed defect."""
        for number, record in self.records:
            self.assertTrue(str(record["guard"]).strip(),
                            f"line {number} ({record['id']}) has no guard")

    def test_open_items_point_somewhere(self):
        for number, record in self.records:
            if record["disposition"] == "open":
                self.assertTrue(str(record["related"]).strip(),
                                f"line {number} ({record['id']}) is open without a pointer")

    def test_records_are_long_enough_to_be_useful(self):
        for number, record in self.records:
            for key in ("symptom", "root_cause", "evidence"):
                self.assertGreaterEqual(len(str(record[key])), 20,
                                        f"line {number}: {key} is too short to be evidence")


if __name__ == "__main__":
    unittest.main()
