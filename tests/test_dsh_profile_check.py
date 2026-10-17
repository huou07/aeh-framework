"""Unit tests for scripts/dsh_profile_check.py.

The compose step needs a live DSH install, but the risky-configuration scanner is
pure and is the part that guards AEH-D019.
"""

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HUB_ROOT = Path(__file__).resolve().parent.parent


def load_module():
    spec = importlib.util.spec_from_file_location(
        "dsh_profile_check", HUB_ROOT / "scripts" / "dsh_profile_check.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["dsh_profile_check"] = module
    spec.loader.exec_module(module)
    return module


PATCH = """\
- id: ui-settings-general
  name: "@deepseek-ai/dsh-client-ui-settings-general"
  config:
    welcomeNoticeVersion: 2026-09-28.1
- id: llm-pi-ai
  name: "@deepseek-ai/dsh-llm-pi-ai"
  config:
    providers:
      opencode-go:
        baseURL: http://127.0.0.1:4000/v1
        models:
          - id: declared-model
            name: Declared
            reasoningEfforts: false
          - id: undeclared-model
            name: Undeclared
        apiKeyEnv: OPENCODE_GO_API_KEY
"""


class ReasoningDeclarationTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def scan(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            patch = Path(tmp) / "cordis.patch.yml"
            patch.write_text(text)
            return self.module.undeclared_reasoning_models(patch)

    def test_flags_only_models_without_a_declaration(self):
        self.assertEqual(self.scan(PATCH), ["undeclared-model"])

    def test_plugin_entries_are_not_models(self):
        # ui-settings-general and llm-pi-ai are top-level plugin ids.
        flagged = self.scan(PATCH)
        self.assertNotIn("ui-settings-general", flagged)
        self.assertNotIn("llm-pi-ai", flagged)

    def test_missing_patch_file_is_not_a_failure(self):
        module = self.module
        self.assertEqual(module.undeclared_reasoning_models(Path("/nonexistent/cordis.patch.yml")), [])

    def test_a_fully_declared_profile_is_clean(self):
        text = PATCH.replace("          - id: undeclared-model\n            name: Undeclared\n", "")
        self.assertEqual(self.scan(text), [])


class ComposeSandboxFallbackTests(unittest.TestCase):
    """AEH-D021: a sandboxed session cannot let `--dump-config` rewrite the profile."""

    def setUp(self):
        self.module = load_module()
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name) / "profiles"
        (root / "web").mkdir(parents=True)
        (root / "web" / "cordis.yml").write_text("[]\n")
        (root / "web" / "cordis.patch.yml").write_text("- id: x\n")
        (root / "web" / "node_modules").mkdir()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.object(self.module, "PROFILE_DIR", root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.root = root

    def test_a_denied_write_retries_in_a_temporary_home(self):
        seen = []

        def fake_run(cmd, **kwargs):
            seen.append(kwargs.get("env"))
            if "env" not in kwargs:
                return subprocess.CompletedProcess(
                    cmd, 1, "", "Error: EACCES: permission denied, open 'cordis.yml'")
            return subprocess.CompletedProcess(cmd, 0, "- id: tool\n", "")

        with mock.patch.object(self.module.subprocess, "run", fake_run):
            with mock.patch.object(self.module.shutil, "which", return_value="/bin/dsh"):
                code, output = self.module.compose("web")

        self.assertEqual(code, 0)
        self.assertEqual(len(seen), 2, "the real compose must be tried before the copy")
        self.assertIsNone(seen[0])
        self.assertIn("DSH_HOME", seen[1])
        self.assertTrue(seen[1]["DSH_HOME"].startswith("/tmp"))
        self.assertIn("- id: tool", output)
        self.assertIn("not writable here", output)

    def test_a_writable_profile_is_composed_in_place(self):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(kwargs)
            return subprocess.CompletedProcess(cmd, 0, "- id: tool\n", "")

        self.module.os.chmod(self.root / "web", 0o700)
        with mock.patch.object(self.module.subprocess, "run", fake_run):
            with mock.patch.object(self.module.shutil, "which", return_value="/bin/dsh"):
                code, output = self.module.compose("web")

        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 1)
        self.assertIn("- id: tool", output)
        self.assertNotIn("not writable here", output)


if __name__ == "__main__":
    unittest.main()
