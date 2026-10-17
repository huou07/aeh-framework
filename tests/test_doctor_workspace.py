"""`doctor` must be honest about an environment it cannot verify.

The Hub's registry indexes paths on the owner's host. A CI runner and a fresh
clone have neither the workspace root nor those paths, and the Hub's own gate
must still be able to run there — but without ever claiming those projects were
verified. These tests pin both directions: absent environment is an explicit
note, present environment with a missing path is a failure.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import hub


class Args:
    json = False


class JsonArgs:
    json = True


def run_doctor(cfg: dict, reg: dict, args=None) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = hub.cmd_doctor(args or Args(), cfg, reg)
    return code, out.getvalue(), err.getvalue()


def registry(entries: dict) -> dict:
    return {"version": 1, "projects": entries}


def entry(slug: str, path: Path) -> dict:
    return {"slug": slug, "path": str(path), "verify": "true", "acceptance": None,
            "release": None, "state": "active", "remote": None}


class DoctorWorkspace(unittest.TestCase):
    def test_absent_workspace_is_a_note_not_a_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing_ws = Path(tmp) / "no-such-workspace"
            cfg = {"workspace_root": str(missing_ws),
                   "registry": "projects/registry.json",
                   "usage_file": ".hub/usage.jsonl"}
            reg = registry({"ghost": entry("ghost", missing_ws / "ghost")})
            code, out, _ = run_doctor(cfg, reg)
            self.assertEqual(code, 0, out)
            self.assertIn("NOTE", out)
            self.assertIn("NOT VERIFIED", out)
            self.assertIn("environment note", out)

    def test_present_workspace_with_missing_project_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            ws.mkdir()
            cfg = {"workspace_root": str(ws), "registry": "projects/registry.json",
                   "usage_file": ".hub/usage.jsonl"}
            reg = registry({"ghost": entry("ghost", ws / "ghost")})
            code, out, _ = run_doctor(cfg, reg)
            self.assertEqual(code, 1)
            self.assertIn("path missing", out)
            self.assertIn("FAILURES PRESENT", out)

    def test_absent_workspace_result_line_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {"workspace_root": str(Path(tmp) / "gone"),
                   "registry": "projects/registry.json",
                   "usage_file": ".hub/usage.jsonl"}
            code, out, _ = run_doctor(cfg, registry({}))
            self.assertEqual(code, 0, out)
            self.assertIn("ALL PASS", out)
            self.assertIn("environment note", out)

    def test_json_reports_notes_and_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {"workspace_root": str(Path(tmp) / "gone"),
                   "registry": "projects/registry.json",
                   "usage_file": ".hub/usage.jsonl"}
            reg = registry({"ghost": entry("ghost", Path(tmp) / "gone" / "ghost")})
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = hub.cmd_doctor(JsonArgs(), cfg, reg)
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue())
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["data"]["problems"], [])
            self.assertTrue(payload["data"]["notes"])

    def test_project_inside_hub_still_fails_whatever_the_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            inside = hub.HUB_ROOT / "docs"
            cfg = {"workspace_root": str(ws), "registry": "projects/registry.json",
                   "usage_file": ".hub/usage.jsonl"}
            # Build the workspace so only the containment failure remains.
            ws.mkdir()
            reg = registry({"sneaky": entry("sneaky", inside)})
            code, out, _ = run_doctor(cfg, reg)
            self.assertEqual(code, 1)
            self.assertIn("inside the Hub repo", out)


if __name__ == "__main__":
    unittest.main()
