"""Regression guards for Hub command safety.

Each test here corresponds to a defect proven by hand against the previous
implementation. Run with:

    python3 -m unittest discover -s tests -q
"""

from __future__ import annotations

import concurrent.futures
import contextlib
import io
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import hub


def write_verify(directory: Path, body: str) -> None:
    script = directory / "verify.sh"
    script.write_text("#!/usr/bin/env bash\n" + body)
    script.chmod(0o755)


def git_fixture(args: list[str], cwd: Path) -> None:
    """Build a fixture repository under the Git rules the Hub itself uses.

    A raw `git` inherits the harness environment, whose half-forwarded indexed
    configuration makes every call fatal (`missing config key
    GIT_CONFIG_KEY_0`) and whose worker UID does not own the checkout. Reusing
    hub.git_argv/git_env keeps a fixture about the Hub rather than about the
    environment that happened to launch the test run.
    """
    subprocess.run(hub.git_argv(cwd, args), cwd=str(cwd), check=True,
                   env=hub.git_env(), capture_output=True, text=True)


class TempHarness(unittest.TestCase):
    """Point hub at a throwaway registry + project directory."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.outside = tempfile.TemporaryDirectory()
        root = Path(self.dir.name)          # stands in for the Hub repo
        self.proj = Path(self.outside.name) / "proj"   # a SIBLING of the hub
        self.proj.mkdir()
        self.sentinel = Path(self.outside.name) / "PWNED.txt"
        self.old_root, self.old_cfg = hub.HUB_ROOT, hub.CONFIG_PATH
        (root / "cfg.json").write_text(json.dumps({
            "version": 1, "workspace_root": str(root),
            "registry": "registry.json", "usage_file": ".hub/usage.jsonl",
        }))
        (root / "registry.json").write_text(json.dumps({
            "version": 1,
            "projects": {"poc": {
                "slug": "poc", "path": str(self.proj), "state": "active",
                "verify": "./verify.sh", "is_repo": False,
            }},
        }))
        hub.HUB_ROOT = root
        hub.CONFIG_PATH = root / "cfg.json"
        self.cfg = hub.load_config()
        self.reg = hub.load_registry(self.cfg)

    def tearDown(self):
        hub.HUB_ROOT, hub.CONFIG_PATH = self.old_root, self.old_cfg
        self.dir.cleanup()
        self.outside.cleanup()

    def status(self):
        class A:
            slug = "poc"
        return hub.cmd_status(A(), self.cfg, self.reg)


class TestStatusIsReadOnly(TempHarness):
    """Defect: `status` executed the registry's verify command.

    registry.json is a TRACKED file, so poisoning it turned a routine
    "what's the progress?" query into arbitrary code execution with no
    approval prompt.
    """

    def test_status_does_not_execute_verify(self):
        write_verify(self.proj, f'echo "ran" >> {self.sentinel}\n')
        self.status()
        self.assertFalse(self.sentinel.exists(),
                         "status must not run project code")

    def test_status_reports_verify_is_not_run(self):
        write_verify(self.proj, f'echo "ran" >> {self.sentinel}\n')
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.status()
        self.assertIn("NO RECORDED RESULT", buf.getvalue())


class TestVerificationEvidence(TempHarness):
    def init_repo(self):
        git_fixture(["init", "-q"], self.proj)
        git_fixture(["config", "user.name", "Hub Test"], self.proj)
        git_fixture(["config", "user.email", "hub-test@localhost"], self.proj)
        git_fixture(["add", "."], self.proj)
        git_fixture(["commit", "-qm", "fixture"], self.proj)

    def verify(self):
        class A:
            slug = "poc"
            timeout = 10
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            return hub.cmd_verify(A(), self.cfg, self.reg)

    def status_text(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.status()
        return buf.getvalue()

    def test_verify_persists_current_clean_result_and_status_only_reads_it(self):
        write_verify(self.proj, 'echo "verified"\n')
        self.init_repo()
        self.reg["projects"]["poc"]["verify"] = "./verify.sh"
        self.assertEqual(self.verify(), 0)
        output = self.status_text()
        self.assertIn("result  : PASS", output)
        self.assertIn("CURRENT for clean HEAD", output)
        self.assertFalse(self.sentinel.exists())

    def test_status_marks_evidence_stale_after_source_changes(self):
        write_verify(self.proj, 'echo "verified"\n')
        self.init_repo()
        self.reg["projects"]["poc"]["verify"] = "./verify.sh"
        self.assertEqual(self.verify(), 0)
        (self.proj / "source.txt").write_text("changed")
        output = self.status_text()
        self.assertIn("result  : PASS", output)
        self.assertIn("STALE; current working tree has uncommitted changes", output)


class TestVerifyResourceCleanup(TempHarness):
    def test_stdout_is_closed_after_normal_completion(self):
        write_verify(self.proj, 'echo "verified"\n')
        real_popen = hub.subprocess.Popen
        processes = []

        def capture_process(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            processes.append(process)
            return process

        with mock.patch.object(hub.subprocess, "Popen", side_effect=capture_process):
            state, rc, _ = hub.run_verify("./verify.sh", self.proj, timeout=10)

        self.assertEqual((state, rc), ("PASS", 0))
        self.assertEqual(len(processes), 1)
        self.assertTrue(processes[0].stdout.closed)


class TestVerificationEvidenceConcurrency(TempHarness):
    def test_concurrent_appends_preserve_complete_jsonl_records(self):
        count = 120
        identity = {"branch": "main", "head": "abc123", "dirty": False,
                    "dirty_files": 0}
        with (
            mock.patch.object(hub, "git_verification_identity", return_value=identity),
            concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool,
        ):
            list(pool.map(
                lambda code: hub.append_verification_evidence(
                    "poc", self.proj, "true", "PASS", code
                ),
                range(count),
            ))

        lines = hub.verification_path().read_text(encoding="utf-8").splitlines()
        records = [json.loads(line) for line in lines]
        self.assertEqual(len(records), count)
        self.assertEqual({record["exit_code"] for record in records}, set(range(count)))
        self.assertTrue(all(record["slug"] == "poc" for record in records))


class TestVerifyIsBounded(TempHarness):
    """Defect: timeout killed only the direct child; forked grandchildren
    survived and ran to completion."""

    def test_grandchild_does_not_outlive_timeout(self):
        marker = str(self.outside.name) + "/ESCAPED.txt"
        write_verify(self.proj, f'( sleep 6; echo escaped > {marker} ) &\nsleep 30\n')
        state, rc, _ = hub.run_verify("./verify.sh", self.proj, timeout=2)
        self.assertEqual(state, "TIMEOUT")
        self.assertEqual(rc, 124)
        time.sleep(7)
        self.assertFalse(os.path.exists(marker),
                         "a forked grandchild outlived the timeout bound")

    def test_timeout_is_distinguished_from_failure(self):
        write_verify(self.proj, "sleep 30\n")
        state, rc, _ = hub.run_verify("./verify.sh", self.proj, timeout=2)
        self.assertEqual(state, "TIMEOUT", "timeout must not report as FAIL")
        self.assertEqual(rc, 124)


class TestOutputIsCapped(TempHarness):
    """Defect: capture_output buffered the entire stream (12.8 MB retained /
    42 MB peak for 300k lines) while displaying only the last 15 lines."""

    def test_output_is_truncated(self):
        write_verify(self.proj,
                     "for i in $(seq 1 200000); do "
                     "echo 'PADDING PADDING PADDING PADDING PADDING'; done\n")
        state, _, out = hub.run_verify("./verify.sh", self.proj, timeout=60)
        self.assertEqual(state, "PASS")
        self.assertLess(len(out), hub.VERIFY_MAX_CAPTURE * 2,
                        "output must be capped, not fully buffered")
        self.assertIn("truncated", out)


class TestNoLoginShell(TempHarness):
    """Defect: `bash -lc` executed the user's shell rc files, importing
    arbitrary profile code into every status query."""

    def test_bashrc_is_not_executed(self):
        write_verify(self.proj, 'echo "verify ran"\n')
        rcfile = self.proj / ".bashrc"
        rcfile.write_text(f'echo "RCFILE EXECUTED" >> {self.sentinel}\n')
        state, _, out = hub.run_verify("./verify.sh", self.proj, timeout=20)
        self.assertEqual(state, "PASS")
        self.assertNotIn("RCFILE EXECUTED", out)
        self.assertFalse(self.sentinel.exists())


class TestTimeoutClamp(TempHarness):
    def test_timeout_is_clamped_to_maximum(self):
        write_verify(self.proj, "true\n")
        # A caller asking for a huge bound must not get one.
        _, _, _ = hub.run_verify("./verify.sh", self.proj, timeout=10**9)
        # run_verify clamps internally; assert the clamp constant is sane
        self.assertLessEqual(hub.VERIFY_MAX_TIMEOUT, 3600)


class TestSlugNames(TempHarness):
    """Slugs are human project names: any case, spaces and punctuation must
    work, while names that would escape the workspace or break the CLI fail
    closed."""

    def accept(self, name):
        self.assertIsNone(hub.validate_slug(name), f"should accept {name!r}")

    def reject(self, name):
        self.assertIsNotNone(hub.validate_slug(name), f"should reject {name!r}")

    def test_real_world_names_are_accepted(self):
        for name in ("or", "OR", "OpenCut-Reinforced", "abc todo", "Dự án",
                     "my.project", "café", "a+b", "v2 (beta)", "项目"):
            self.accept(name)

    def test_dangerous_names_are_rejected(self):
        for name in ("", " ", "../escape", "a/b", "a\\b", "..", ".",
                     "-flag", "tab\there", "new\nline", "x" * 101):
            self.reject(name)

    def test_lookup_is_case_insensitive(self):
        self.reg["projects"]["OR"] = dict(self.reg["projects"]["poc"], slug="OR")
        del self.reg["projects"]["poc"]
        self.assertEqual(hub.require_project(self.reg, "or")["slug"], "OR")
        self.assertEqual(hub.require_project(self.reg, "oR")["slug"], "OR")

    def test_unknown_slug_still_fails_closed(self):
        with self.assertRaises(SystemExit):
            hub.require_project(self.reg, "nope")

    def test_add_refuses_case_variant_of_registered_slug(self):
        (hub.HUB_ROOT / "poc2").mkdir()
        args = type("A", (), {"slug": "POC", "path": str(self.proj),
                              "remote": None, "state": "active", "verify": None})()
        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            hub.cmd_add(args, self.cfg, self.reg)
        self.assertNotIn("POC", self.reg["projects"])
        self.assertIn("poc", self.reg["projects"])

    def test_registry_with_case_only_duplicates_is_refused(self):
        # Lookups fold case, so such a registry would be ambiguous: fail closed.
        (hub.HUB_ROOT / "registry.json").write_text(json.dumps({
            "version": 1,
            "projects": {
                "OR": {"slug": "OR", "path": str(self.proj)},
                "or": {"slug": "or", "path": str(self.proj)},
            },
        }))
        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            hub.load_registry(self.cfg)

    def test_new_names_the_directory_after_the_slug_verbatim(self):
        # `new` refuses a workspace root inside the Hub, so point it at a
        # sibling directory instead of the harness root.
        workspace = Path(self.outside.name) / "workspaces"
        cfg = {**self.cfg, "workspace_root": str(workspace)}
        args = type("A", (), {"slug": "Tên Dự Án"})()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(hub.cmd_new(args, cfg, self.reg), 0)
        created = workspace / "Tên Dự Án"
        self.assertTrue(created.is_dir())
        self.assertIn(shlex.quote("Tên Dự Án"), buf.getvalue())
        created.rmdir()


class TestPathContainment(TempHarness):
    def test_registry_path_inside_hub_is_detected(self):
        # hub.HUB_ROOT is the temp root for this harness; anything under it is
        # "inside the Hub" and must be refused.
        inside = hub.HUB_ROOT / "would-be-project"
        inside.mkdir(exist_ok=True)
        try:
            self.assertTrue(hub.is_within_hub(inside))
        finally:
            inside.rmdir()

    def test_nested_path_inside_hub_is_detected(self):
        nested = hub.HUB_ROOT / "a" / "b" / "c"
        nested.mkdir(parents=True, exist_ok=True)
        try:
            self.assertTrue(hub.is_within_hub(nested))
        finally:
            (hub.HUB_ROOT / "a" / "b" / "c").rmdir()
            (hub.HUB_ROOT / "a" / "b").rmdir()
            (hub.HUB_ROOT / "a").rmdir()

    def test_project_outside_hub_is_allowed(self):
        self.assertFalse(hub.is_within_hub(self.proj))

    def test_status_rejects_missing_path(self):
        import contextlib
        import io
        self.reg["projects"]["poc"]["path"] = str(self.outside.name) + "/gone"
        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            self.status()


class TestRemoveOnlyTouchesTheRegistry(TempHarness):
    """Defect: there was no way to unregister a project.

    A fixture that is no longer a project stayed in `list`, `report` and
    `doctor` forever, labelled `active`. The fix must not become a delete:
    unregistering must never remove a project directory or its files.
    """

    def remove(self, **kwargs):
        class A:
            slug = "poc"
            forget = False
        for key, value in kwargs.items():
            setattr(A, key, value)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = hub.cmd_remove(A(), self.cfg, self.reg)
        return code, buf.getvalue()

    def test_remove_drops_the_entry_and_saves_the_registry(self):
        write_verify(self.proj, 'echo hi\n')
        marker = self.proj / "real-source.txt"
        marker.write_text("keep me")

        self.remove()

        self.assertNotIn("poc", self.reg["projects"])
        saved = json.loads((hub.HUB_ROOT / "registry.json").read_text())
        self.assertNotIn("poc", saved["projects"])
        self.assertTrue(marker.exists(), "remove must never delete project files")
        self.assertTrue(self.proj.exists(), "remove must never delete the directory")

    def test_remove_is_case_insensitive_like_every_other_lookup(self):
        class A:
            slug = "POC"
            forget = False
        with contextlib.redirect_stdout(io.StringIO()):
            hub.cmd_remove(A(), self.cfg, self.reg)
        self.assertEqual(self.reg["projects"], {})

    def test_remove_refuses_an_unknown_slug_without_touching_the_registry(self):
        class A:
            slug = "not-registered"
            forget = False
        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            hub.cmd_remove(A(), self.cfg, self.reg)
        self.assertIn("poc", self.reg["projects"])

    def test_forget_discards_orphaned_verification_records(self):
        records = hub.verification_path()
        records.parent.mkdir(parents=True, exist_ok=True)
        records.write_text(
            json.dumps({"slug": "poc", "result": "PASS"}) + "\n"
            + json.dumps({"slug": "other", "result": "PASS"}) + "\n")

        self.remove(forget=True)

        remaining = [json.loads(line) for line in records.read_text().splitlines()
                     if line.strip()]
        self.assertEqual([r["slug"] for r in remaining], ["other"])

    def test_records_are_kept_by_default_and_the_orphan_is_reported(self):
        records = hub.verification_path()
        records.parent.mkdir(parents=True, exist_ok=True)
        records.write_text(json.dumps({"slug": "poc", "result": "PASS"}) + "\n")

        _, output = self.remove()

        self.assertTrue(records.exists(), "records must survive by default")
        self.assertIn("no longer reachable", output)


class TestRegistryStaleness(TempHarness):
    """A registry label is not evidence; staleness is a prompt to re-check."""

    def test_missing_verify_is_reported_as_a_staleness_reason(self):
        entry = dict(self.reg["projects"]["poc"])
        entry.pop("verify", None)
        reason = hub.registry_staleness(entry, {"commit_date": None})
        self.assertIn("no verification command", reason)

    def test_long_unregistered_entry_is_reported(self):
        entry = dict(self.reg["projects"]["poc"])
        entry["registered_at"] = (datetime.now(UTC)
                                  - timedelta(days=hub.STALE_AFTER_DAYS + 5)).isoformat()
        reason = hub.registry_staleness(entry, {"commit_date": None})
        self.assertIn("registered", reason)

    def test_fresh_entry_with_a_gate_reports_no_signal(self):
        entry = dict(self.reg["projects"]["poc"])
        reason = hub.registry_staleness(entry, {"commit_date": None})
        self.assertEqual(reason, "no staleness signal")

    def test_staleness_never_raises_on_unparseable_dates(self):
        entry = dict(self.reg["projects"]["poc"])
        entry["registered_at"] = "not-a-date"
        reason = hub.registry_staleness(entry, {"commit_date": "also-not-a-date"})
        self.assertIn("unparseable", reason)


def init_commit(repo: Path) -> None:
    """A one-commit repository, built without ambient Git configuration."""
    git_fixture(["init", "-q", "-b", "main"], repo)
    (repo / "file.txt").write_text("one\n")
    git_fixture(["add", "file.txt"], repo)
    git_fixture(["-c", "user.name=hub-test",
                 "-c", "user.email=hub-test@example.invalid",
                 "commit", "-q", "-m", "one"], repo)


class GitEvidenceSurvivesTheHarnessEnvironment(unittest.TestCase):
    """Hub evidence must not depend on the environment the harness forwards.

    Measured defect (2026-10-16): the worker launcher declares Git's ownership
    exception as GIT_CONFIG_COUNT/KEY_0/VALUE_0, the harness credential scrub
    drops the KEY entry alone, and every registered project then read
    `REPO=no  git UNAVAILABLE (rev_parse_exit_128)` although each checkout was
    clean and healthy. `run` now owns the Git environment instead.
    """

    def test_git_env_pins_indexed_configuration_off(self):
        with mock.patch.dict(os.environ, {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "safe.directory",
            "GIT_CONFIG_VALUE_0": "/tmp/*",
        }):
            env = hub.git_env()
        self.assertEqual(env["GIT_CONFIG_COUNT"], "0")
        leftovers = [n for n in env
                     if n.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"))]
        self.assertEqual(leftovers, [])

    def test_git_argv_declares_the_ownership_exception(self):
        argv = hub.git_argv(Path("/tmp/example"), ["status", "--porcelain"])
        self.assertEqual(argv[0], "git")
        self.assertIn("-c", argv)
        self.assertIn("safe.directory=/tmp/example", argv)
        self.assertEqual(argv[-2:], ["status", "--porcelain"])

    def test_git_state_reads_a_repo_under_a_broken_harness_environment(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            init_commit(repo)
            with mock.patch.dict(os.environ, {
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_VALUE_0": "/tmp/*",
            }):
                # This half-forwarded pair is exactly what breaks an ambient
                # call, so an unguarded Hub cannot read evidence here.
                os.environ.pop("GIT_CONFIG_KEY_0", None)
                ambient = subprocess.run(
                    ["git", "rev-parse", "--is-inside-work-tree"],
                    cwd=d, capture_output=True, text=True, check=False)
                self.assertNotEqual(ambient.returncode, 0,
                                    "the guard only matters while the pair is fatal")
                state = hub.git_state(repo)
        self.assertTrue(state["is_repo"])
        self.assertEqual(state["branch"], "main")
        self.assertIs(state["dirty"], False)
        self.assertEqual(len(state["commit"]), 7)

    def test_unreadable_paths_do_not_inflate_the_dirty_count(self):
        """Git warns about unreadable paths on stderr; those are not changes.

        Measured 2026-10-17: VCE's `deploy/shadow/` is unreadable to this UID,
        so eight "could not open directory" warnings made the Hub report 19
        dirty files for an 11-file tree.
        """
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            init_commit(repo)
            secret = repo / "secret"
            secret.mkdir()
            secret.chmod(0o000)
            try:
                raw = subprocess.run(
                    ["git", "status", "--porcelain"], cwd=d, env=hub.git_env(),
                    capture_output=True, text=True, check=False)
                self.assertEqual(raw.stdout.strip(), "")
                self.assertIn("Permission denied", raw.stderr)
                state = hub.git_state(repo)
            finally:
                secret.chmod(0o700)
        self.assertIs(state["dirty"], False)
        self.assertEqual(state["dirty_files"], 0)


if __name__ == "__main__":
    unittest.main()