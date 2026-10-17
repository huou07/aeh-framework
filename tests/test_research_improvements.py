"""Behaviour guards for structured evidence and selective migration."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import hub
import skill_eval
from test_hub_safety import TempHarness, write_verify

REPO = Path(__file__).resolve().parent.parent


class TestStructuredCommands(TempHarness):
    def call(self, *argv):
        out = io.StringIO()
        with mock.patch.object(sys, "argv", ["hub.py", *argv]), contextlib.redirect_stdout(out):
            rc = hub.main()
        return rc, json.loads(out.getvalue())

    def test_read_commands_never_execute_project_gate(self):
        write_verify(self.proj, f'echo ran > "{self.sentinel}"\n')
        (hub.HUB_ROOT / "evidence").mkdir()
        for command in (["list"], ["where", "poc"], ["status", "poc"],
                        ["report"], ["usage", "--slug", "poc"], ["doctor"]):
            rc, result = self.call(*command, "--json")
            # This fixture deliberately has workspace_root inside Hub.
            self.assertEqual(rc, 1 if command[0] == "doctor" else 0)
            self.assertEqual(result["schema_version"], 1)
            self.assertFalse(self.sentinel.exists())

    def test_unknown_project_returns_structured_error(self):
        rc, result = self.call("status", "missing", "--json")
        self.assertEqual(rc, 1)
        self.assertFalse(result["ok"])
        self.assertEqual(result["data"]["kind"], "missing_project")

    def test_git_permission_failure_is_unavailable_not_non_repository(self):
        (self.proj / ".git").mkdir()
        with mock.patch.object(hub, "run", return_value=(128, "dubious ownership")):
            rc, result = self.call("status", "poc", "--json")
        self.assertEqual(rc, 0)
        self.assertIsNone(result["data"]["git"]["is_repo"])
        self.assertEqual(result["data"]["git"]["git_error"], "rev_parse_exit_128")

    def test_invalid_registry_fails_closed(self):
        for value in ([], {"version": 2, "projects": {}},
                      {"version": 1, "projects": {"poc": {"slug": "poc", "path": "../x"}}}):
            (hub.HUB_ROOT / "registry.json").write_text(json.dumps(value))
            rc, result = self.call("list", "--json")
            self.assertEqual(rc, 1)
            self.assertFalse(result["ok"])


class TestEvidenceSemantics(TempHarness):
    def test_new_writes_only_use_runtime_directory(self):
        identity = {"branch": "main", "head": "abc", "dirty": False, "dirty_files": 0}
        legacy = hub.HUB_ROOT / "evidence/verification.jsonl"
        legacy.parent.mkdir()
        legacy.write_text('{"slug":"poc","result":"OLD"}\n')
        with mock.patch.object(hub, "git_verification_identity", return_value=identity):
            target = hub.append_verification_evidence(
                "poc", self.proj, "true", "PASS", 0, before=identity, duration_s=0.1)
        self.assertEqual(target.parent.name, ".hub")
        self.assertEqual(json.loads(legacy.read_text())["result"], "OLD")
        self.assertEqual(hub.latest_verification("poc")[0]["duration_s"], 0.1)

    def test_legacy_evidence_remains_readable(self):
        legacy = hub.HUB_ROOT / "evidence/verification.jsonl"
        legacy.parent.mkdir()
        legacy.write_text('{"slug":"poc","result":"PASS"}\n')
        self.assertEqual(hub.latest_verification("poc")[0]["result"], "PASS")

    def test_changed_command_is_stale(self):
        identity = {"branch": "main", "head": "abc", "dirty": False, "dirty_files": 0}
        record = {**identity, "verify_sha256": hashlib.sha256(b"true").hexdigest()}
        with mock.patch.object(hub, "git_verification_identity", return_value=identity):
            self.assertIn("command changed", hub.verification_freshness(record, self.proj, "false"))

    def test_legacy_project_survives_other_projects_new_runtime_records(self):
        legacy = hub.HUB_ROOT / "evidence/verification.jsonl"
        legacy.parent.mkdir()
        legacy.write_text('{"slug":"poc","result":"PASS"}\n')
        runtime = hub.verification_path()
        runtime.parent.mkdir()
        runtime.write_text('{"slug":"other","result":"FAIL"}\n')
        self.assertEqual(hub.latest_verification("poc")[0]["result"], "PASS")

    def test_unknown_cleanliness_does_not_claim_current(self):
        identity = {"branch": "main", "head": "abc", "dirty": None, "dirty_files": None}
        with mock.patch.object(hub, "git_verification_identity", return_value=identity):
            self.assertIn("unavailable", hub.verification_freshness(identity, self.proj))

    def test_source_changed_during_verification_is_historical(self):
        after = {"branch": "main", "head": "new", "dirty": False, "dirty_files": 0}
        record = {**after, "source_before": {**after, "head": "old"}}
        with mock.patch.object(hub, "git_verification_identity", return_value=after):
            self.assertIn("changed during verification", hub.verification_freshness(record, self.proj))

    def test_missing_usage_is_unavailable(self):
        self.assertEqual(hub.usage_summary(self.proj / "missing")["availability"], "unavailable")

    def test_unknown_metrics_are_not_zero_or_measured(self):
        path = self.proj / "usage.jsonl"
        path.write_text('\n'.join(json.dumps(row) for row in [
            {"cost_usd": 99}, {"measurement": "measured", "cost_usd": 2},
            {"measurement": "estimated", "cost_usd": 3, "accepted": False},
            {"measurement": "measured", "rework_events": True}, [], {"measurement": "other", "cost_usd": 5},
            {"measurement": "measured", "cost_usd": float("inf")}
        ]))
        result = hub.usage_summary(path)
        self.assertEqual(result["malformed_lines"], 1)
        self.assertEqual(result["metrics"]["cost_usd"]["measured"], 2)
        self.assertEqual(result["metrics"]["cost_usd"]["estimated"], 3)
        self.assertIsNone(result["metrics"]["rework_events"]["measured"])
        self.assertEqual(result["acceptance_unknown"], 5)


class TestImportBoundary(unittest.TestCase):
    def test_allowlist_dry_run_and_symlinks(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            src, dst = root / "src", root / "dst"
            src.mkdir()
            (src / "code").mkdir()
            (src / "code-extra").mkdir()
            (src / "code/main.py").write_text("print('ok')\n")
            (src / "code-extra/unreviewed.py").write_text("bad")
            (src / "code/link").symlink_to(root / "outside")
            (root / "outside").write_text("external")
            cmd = [sys.executable, str(REPO / "scripts/legacy_import.py"),
                   "--src", str(src), "--dst", str(dst)]
            self.assertNotEqual(subprocess.run(cmd, capture_output=True, check=False).returncode, 0)
            dry = subprocess.run([*cmd, "--include", "code", "--dry-run"],
                                 capture_output=True, text=True, check=False)
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertFalse(dst.exists())
            apply = subprocess.run([*cmd, "--include", "code"], capture_output=True,
                                   text=True, check=False)
            self.assertEqual(apply.returncode, 0, apply.stderr)
            self.assertTrue((dst / "code/main.py").exists())
            self.assertFalse((dst / "code-extra").exists())
            self.assertFalse((dst / "code/link").exists())
            manifest = json.loads((dst / "IMPORT-PROVENANCE.json").read_text())
            self.assertEqual(len(manifest["copied"]), 1)
            self.assertEqual(len(manifest["copied"][0]["sha256"]), 64)

    def test_overlapping_destination_is_rejected_before_mutation(self):
        with tempfile.TemporaryDirectory() as name:
            src = Path(name)
            dst = src / "nested"
            result = subprocess.run([sys.executable, str(REPO / "scripts/legacy_import.py"),
                                     "--src", str(src), "--dst", str(dst), "--include", "code"],
                                    capture_output=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(dst.exists())


class TestCorpus(unittest.TestCase):
    def test_versioned_cases_cover_modes_and_neighbors(self):
        cases = skill_eval.load_cases(REPO / "evals/skill-contracts.jsonl")
        self.assertGreaterEqual(len(cases), 12)

    def test_contradictory_contract_is_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "cases.jsonl"
            path.write_text(json.dumps({
                "label": "contradiction", "input": "request", "cwd_kind": "hub",
                "expected_skills": ["x"], "must_not_select": ["x"],
                "required_behaviors": [], "forbidden_behaviors": []
            }))
            with self.assertRaises(ValueError):
                skill_eval.load_cases(path)
