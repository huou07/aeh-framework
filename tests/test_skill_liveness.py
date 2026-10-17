"""Unit tests for scripts/skill_liveness.py.

The interesting logic is the DSH session-directory encoding and the expected-skill
sets; both are pure and testable without touching the live session store.
"""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parent.parent


def load_module():
    spec = importlib.util.spec_from_file_location(
        "skill_liveness", HUB_ROOT / "scripts" / "skill_liveness.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["skill_liveness"] = module
    spec.loader.exec_module(module)
    return module


class SessionDirEncodingTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_encoding_strips_leading_slash_and_wraps(self):
        # DSH encodes /srv/example-work as --srv-example-work--.
        candidate = ("--" + "/srv/example-work".lstrip("/").replace("/", "-") + "--")
        self.assertEqual(candidate, "--srv-example-work--")

    def test_missing_directory_returns_none(self):
        module = self.module
        original = module.SESSIONS
        try:
            module.SESSIONS = Path("/nonexistent-session-store")
            self.assertIsNone(module.session_dir_for(Path("/tmp/example-work")))
        finally:
            module.SESSIONS = original


class ExpectedSkillTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_project_expected_reads_only_skill_directories(self):
        module = self.module
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / ".agents" / "skills"
            (root / "alpha").mkdir(parents=True)
            (root / "alpha" / "SKILL.md").write_text("---\nname: alpha\n---\n")
            (root / "beta").mkdir()          # no SKILL.md -> not a skill
            (root / "notes.md").write_text("flat files are not bundles\n")
            self.assertEqual(module.project_expected(Path(tmp)), {"alpha"})

    def test_project_expected_is_empty_without_a_skills_root(self):
        module = self.module
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(module.project_expected(Path(tmp)), set())


class RegistryReadTests(unittest.TestCase):
    def test_registry_entries_are_well_formed(self):
        """Mechanism, not inventory: any registry, including an empty one."""
        module = load_module()
        registry = module.read_registry()
        self.assertEqual(registry.get("version"), 1)
        projects = registry.get("projects")
        self.assertIsInstance(projects, dict)
        for slug, entry in projects.items():
            with self.subTest(slug=slug):
                self.assertEqual(entry.get("slug"), slug)
                self.assertTrue(str(entry.get("path", "")).startswith("/"),
                                "a registered project path must be absolute")


if __name__ == "__main__":
    unittest.main()
