"""Hermetic tests for the read-only quality-contract module.

Everything here runs against ``tempfile.TemporaryDirectory()`` fixtures and the
Hub's own ``contracts/``/``templates/`` documents; no registered project, no
network and no subprocess is involved, and nothing is written inside the
repository.  Run with:

    python3 -m unittest tests.test_quality_contract -v
    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

HUB_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HUB_ROOT / "scripts"))

import quality_contract


def valid_contract() -> dict:
    """The smallest contract that satisfies every required rule."""
    return {
        "schema": 1,
        "project": "demo",
        "product_type": "cli",
        "hosted_ci": "none",
        "required_gates": ["source-integrity"],
        "release_gates": ["release-acceptance"],
        "gates": {
            "source-integrity": {"gate": "verify"},
            "release-acceptance": {"gate": "acceptance"},
        },
    }


class ValidateContractTests(unittest.TestCase):
    """validate_contract is pure, total and fail-closed."""

    def test_minimal_valid_contract(self):
        self.assertEqual(quality_contract.validate_contract(valid_contract()), [])

    def test_non_object_document_is_rejected(self):
        self.assertEqual(
            quality_contract.validate_contract([]),
            ["quality contract must be a JSON object, got array"],
        )
        self.assertEqual(
            quality_contract.validate_contract("{}"),
            ["quality contract must be a JSON object, got string"],
        )
        self.assertEqual(
            quality_contract.validate_contract(None),
            ["quality contract must be a JSON object, got null"],
        )

    def test_unknown_top_level_key(self):
        data = valid_contract()
        data["unexpected"] = True
        self.assertEqual(
            quality_contract.validate_contract(data),
            ["unknown top-level key 'unexpected'"],
        )

    def test_missing_required_keys(self):
        for key in ("schema", "project", "product_type", "hosted_ci", "gates"):
            with self.subTest(key=key):
                data = valid_contract()
                del data[key]
                self.assertIn(
                    f"missing required key '{key}'",
                    quality_contract.validate_contract(data),
                )

    def test_schema_must_be_the_integer_one(self):
        for value in (2, "1", None, True):
            with self.subTest(value=value):
                data = valid_contract()
                data["schema"] = value
                self.assertIn(
                    "schema must be 1, got "
                    + json.dumps(value),
                    quality_contract.validate_contract(data),
                )

    def test_empty_or_whitespace_required_key_values(self):
        for key in ("project", "product_type"):
            with self.subTest(key=key):
                data = valid_contract()
                data[key] = "   "
                self.assertEqual(
                    quality_contract.validate_contract(data),
                    [f"{key} must be a non-empty string"],
                )

    def test_empty_required_gates(self):
        data = valid_contract()
        data["required_gates"] = []
        self.assertEqual(
            quality_contract.validate_contract(data),
            ["required_gates must not be empty"],
        )

    def test_missing_required_gates(self):
        data = valid_contract()
        del data["required_gates"]
        self.assertEqual(
            quality_contract.validate_contract(data),
            ["missing required key 'required_gates'"],
        )

    def test_gate_name_referenced_but_absent_from_gates(self):
        data = valid_contract()
        data["required_gates"] = ["source-integrity", "ghost"]
        self.assertEqual(
            quality_contract.validate_contract(data),
            ["required_gates[1] gate 'ghost' is not defined in gates"],
        )

    def test_release_gate_name_referenced_but_absent_from_gates(self):
        data = valid_contract()
        data["release_gates"] = ["nowhere"]
        self.assertEqual(
            quality_contract.validate_contract(data),
            ["release_gates[0] gate 'nowhere' is not defined in gates"],
        )

    def test_non_string_gate_name(self):
        data = valid_contract()
        data["required_gates"] = ["source-integrity", 3]
        self.assertEqual(
            quality_contract.validate_contract(data),
            ["required_gates[1] must be a non-empty string"],
        )

    def test_invalid_gate_kind(self):
        data = valid_contract()
        data["gates"]["source-integrity"] = {"gate": "publish"}
        self.assertEqual(
            quality_contract.validate_contract(data),
            [(
                'gates.source-integrity.gate must be one of verify, acceptance, '
                'release, got "publish"'
            )],
        )

    def test_gate_entry_must_declare_gate(self):
        data = valid_contract()
        data["gates"]["source-integrity"] = {}
        self.assertEqual(
            quality_contract.validate_contract(data),
            ["gates.source-integrity must declare 'gate'"],
        )

    def test_gate_entry_only_allows_gate_key(self):
        data = valid_contract()
        data["gates"]["source-integrity"] = {"gate": "verify", "when": "always"}
        self.assertEqual(
            quality_contract.validate_contract(data),
            ["unknown key 'when' in gates.source-integrity"],
        )

    def test_invalid_hosted_ci(self):
        data = valid_contract()
        data["hosted_ci"] = "sometimes"
        self.assertEqual(
            quality_contract.validate_contract(data),
            ['hosted_ci must be one of required, optional, none, got "sometimes"'],
        )

    def test_invalid_policy_value(self):
        cases = (
            ({"production_changes": "block"},
             ('policies.production_changes must be one of require_approval, warn, '
              'got "block"')),
            ({"missing_evidence": "require_approval"},
             ('policies.missing_evidence must be one of block, warn, '
              'got "require_approval"')),
            ({"stale_evidence": False},
             'policies.stale_evidence must be one of block, warn, got false'),
            ({"everything": "block"}, "unknown policy 'everything'"),
        )
        for policies, expected in cases:
            with self.subTest(policies=policies):
                data = valid_contract()
                data["policies"] = policies
                self.assertEqual(
                    quality_contract.validate_contract(data), [expected]
                )

    def test_absolute_report_is_rejected(self):
        for value in ("/etc/passwd", "C:\\secrets.json", "C:secrets.json",
                      "\\\\server\\share\\report.json"):
            with self.subTest(value=value):
                data = valid_contract()
                data["report"] = value
                problems = quality_contract.validate_contract(data)
                self.assertEqual(len(problems), 1)
                self.assertIn("report must be a relative path contained in the "
                              "project", problems[0])

    def test_parent_traversal_in_report_is_rejected(self):
        for value in ("../outside.json", "reports/../../outside.json",
                      "..\\outside.json"):
            with self.subTest(value=value):
                data = valid_contract()
                data["report"] = value
                self.assertEqual(
                    quality_contract.validate_contract(data),
                    [f"report must not contain '..', got {value!r}"],
                )

    def test_empty_report_is_rejected(self):
        data = valid_contract()
        data["report"] = "   "
        self.assertEqual(
            quality_contract.validate_contract(data),
            ["report must be a non-empty relative path string"],
        )

    def test_duplicate_entry_in_required_gates(self):
        data = valid_contract()
        data["required_gates"] = ["source-integrity", "source-integrity"]
        self.assertEqual(
            quality_contract.validate_contract(data),
            ["required_gates[1] is a duplicate entry 'source-integrity'"],
        )

    def test_duplicate_entry_in_supported_platforms(self):
        data = valid_contract()
        data["supported_platforms"] = ["linux-x64", "linux-x64"]
        self.assertEqual(
            quality_contract.validate_contract(data),
            ["supported_platforms[1] is a duplicate entry 'linux-x64'"],
        )

    def test_artifacts_are_checked(self):
        data = valid_contract()
        data["artifacts"] = [
            {"name": "app.deb"},
            {"platform": "linux-x64"},
            {"name": ""},
            {"name": "x", "platform": 3},
            {"name": "y", "hash_required": "yes"},
            "not-an-object",
        ]
        self.assertEqual(
            quality_contract.validate_contract(data),
            [
                "artifacts[1] must declare a non-empty 'name'",
                "artifacts[2].name must be a non-empty string",
                "artifacts[3].platform must be a non-empty string",
                "artifacts[4].hash_required must be a boolean",
                "artifacts[5] must be an object, got string",
            ],
        )

    def test_command_key_rejected_at_top_level(self):
        data = valid_contract()
        data["command"] = "rm -rf /"
        self.assertEqual(
            quality_contract.validate_contract(data),
            [
                "unknown top-level key 'command'",
                "command injection: key 'command' is forbidden at JSON path command",
            ],
        )

    def test_command_key_rejected_inside_gates(self):
        data = valid_contract()
        data["gates"]["source-integrity"]["script"] = "./build.sh"
        problems = quality_contract.validate_contract(data)
        self.assertEqual(
            problems,
            [
                "unknown key 'script' in gates.source-integrity",
                ("command injection: key 'script' is forbidden at JSON path "
                 "gates.source-integrity.script"),
            ],
        )
        self.assertIn("gates.source-integrity.script", problems[-1])

    def test_command_key_rejected_inside_artifacts(self):
        data = valid_contract()
        data["artifacts"] = [{"name": "app.deb", "run": "make dist"}]
        problems = quality_contract.validate_contract(data)
        self.assertEqual(
            problems,
            [("command injection: key 'run' is forbidden at JSON path "
              "artifacts[0].run")],
        )
        self.assertIn("artifacts[0].run", problems[0])

    def test_command_key_is_case_insensitive(self):
        for key in ("Command", "CMD", "Exec", "SHELL", "Script", "Run"):
            with self.subTest(key=key):
                data = valid_contract()
                data["gates"]["source-integrity"] = {"gate": "verify", key: "x"}
                problems = quality_contract.validate_contract(data)
                self.assertIn(
                    f"command injection: key {key!r} is forbidden", problems[-1]
                )

    def test_valid_but_unusual_contract_still_validates(self):
        data = {
            "schema": 1,
            "project": "maximal",
            "product_type": "desktop-app",
            "supported_platforms": [
                "linux-x64", "windows-x64", "macos-arm64", "linux-arm64",
            ],
            "required_gates": ["source-integrity", "native-build"],
            "release_gates": [
                "product-acceptance", "artifact-integrity", "native-build",
            ],
            "external_requirements": ["physical-gpu", "code-signing-key"],
            "hosted_ci": "required",
            "gates": {
                "source-integrity": {"gate": "verify"},
                "native-build": {"gate": "acceptance"},
                "product-acceptance": {"gate": "acceptance"},
                "artifact-integrity": {"gate": "release"},
            },
            "report": "docs/gate-reports/latest.json",
            "artifacts": [
                {"name": "app.deb", "platform": "linux-x64",
                 "hash_required": True},
                {"name": "app.msi"},
            ],
            # A partial policies object is allowed: omitted keys keep their
            # documented defaults rather than being invented here.
            "policies": {"production_changes": "require_approval"},
        }
        self.assertEqual(quality_contract.validate_contract(data), [])

    def test_malformed_input_never_raises(self):
        documents = [
            None,
            0,
            1.5,
            True,
            "text",
            [],
            [{"command": "x"}],
            {},
            {"schema": 1, "project": 3, "product_type": [], "hosted_ci": {},
             "required_gates": {"a": 1}, "release_gates": 7, "gates": [],
             "report": 9, "artifacts": {"name": "x"}, "policies": []},
            {"gates": {"a": {"gate": None}}, "required_gates": ["a"],
             "release_gates": ["a"]},
            {"policies": {"production_changes": None, 5: "block"}},
            {1: {2: 3}},
            {"artifacts": [None, 5, "x"]},
        ]
        for document in documents:
            with self.subTest(document=document):
                problems = quality_contract.validate_contract(document)
                self.assertIsInstance(problems, list)
                self.assertTrue(all(isinstance(p, str) for p in problems))

    def test_deeply_nested_command_key_is_reported_without_recursion_error(self):
        document: dict = {}
        node = document
        for _ in range(2000):
            child: dict = {}
            node["level"] = child
            node = child
        node["command"] = "x"
        problems = quality_contract.validate_contract(document)
        self.assertTrue(
            any("command injection" in problem for problem in problems),
            problems,
        )


class LoadContractTests(unittest.TestCase):
    """load_contract only reads, uses the frozen lookup order and fails closed."""

    def write(self, root: Path, relative: str, text: str) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_absent_contract_names_both_absolute_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract, path_str, problems = quality_contract.load_contract(root)
            self.assertIsNone(contract)
            self.assertIsNone(path_str)
            expected = (
                "no quality contract at "
                + os.path.join(os.path.abspath(tmp), ".aeh", "quality.json")
                + " or "
                + os.path.join(os.path.abspath(tmp), "docs", "quality.json")
            )
            self.assertEqual(problems, [expected])
            self.assertIn(".aeh/quality.json", problems[0])
            self.assertIn("docs/quality.json", problems[0])

    def test_valid_contract_is_loaded_from_the_first_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self.write(root, ".aeh/quality.json",
                              json.dumps(valid_contract()))
            contract, path_str, problems = quality_contract.load_contract(root)
            self.assertEqual(problems, [])
            self.assertEqual(contract, valid_contract())
            self.assertEqual(path_str, str(path))
            self.assertTrue(Path(path_str).is_absolute())

    def test_docs_contract_is_found_when_aeh_is_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self.write(root, "docs/quality.json",
                              json.dumps(valid_contract()))
            contract, path_str, problems = quality_contract.load_contract(root)
            self.assertEqual(problems, [])
            self.assertEqual(contract, valid_contract())
            self.assertEqual(path_str, str(path))

    def test_first_existing_path_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = valid_contract()
            first["project"] = "first"
            second = valid_contract()
            second["project"] = "second"
            self.write(root, ".aeh/quality.json", json.dumps(first))
            aeh_path = root / ".aeh" / "quality.json"
            self.write(root, "docs/quality.json", json.dumps(second))
            contract, path_str, problems = quality_contract.load_contract(root)
            self.assertEqual(problems, [])
            self.assertEqual(contract["project"], "first")
            self.assertEqual(path_str, str(aeh_path))

    def test_invalid_contract_returns_no_contract_but_names_the_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = valid_contract()
            data["required_gates"] = ["ghost"]
            path = self.write(root, ".aeh/quality.json", json.dumps(data))
            contract, path_str, problems = quality_contract.load_contract(root)
            self.assertIsNone(contract)
            self.assertEqual(path_str, str(path))
            self.assertEqual(
                problems,
                ["required_gates[0] gate 'ghost' is not defined in gates"],
            )

    def test_unparseable_json_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self.write(root, ".aeh/quality.json", '{"schema": 1,')
            contract, path_str, problems = quality_contract.load_contract(root)
            self.assertIsNone(contract)
            self.assertEqual(path_str, str(path))
            self.assertEqual(len(problems), 1)
            self.assertTrue(problems[0].startswith(f"quality contract {path} "))
            self.assertIn("is not valid JSON", problems[0])

    def test_json_array_instead_of_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self.write(root, ".aeh/quality.json", '[{"schema": 1}]')
            contract, path_str, problems = quality_contract.load_contract(root)
            self.assertIsNone(contract)
            self.assertEqual(path_str, str(path))
            self.assertEqual(
                problems,
                ["quality contract must be a JSON object, got array"],
            )

    def test_invalid_utf8_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / ".aeh" / "quality.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'{"schema": 1, "project": "\xff\xfe"}')
            contract, path_str, problems = quality_contract.load_contract(root)
            self.assertIsNone(contract)
            self.assertEqual(path_str, str(path))
            self.assertEqual(len(problems), 1)
            self.assertIn("is not valid UTF-8", problems[0])

    def test_directory_where_the_contract_should_be_is_unreadable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".aeh" / "quality.json").mkdir(parents=True)
            contract, path_str, problems = quality_contract.load_contract(root)
            self.assertIsNone(contract)
            self.assertEqual(path_str, str(root / ".aeh" / "quality.json"))
            self.assertEqual(len(problems), 1)
            self.assertIn("is unreadable", problems[0])

    def test_unreadable_file_is_reported(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("running as root: file mode cannot deny reads")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self.write(root, ".aeh/quality.json",
                              json.dumps(valid_contract()))
            path.chmod(0o000)
            try:
                contract, path_str, problems = quality_contract.load_contract(root)
            finally:
                path.chmod(0o600)
            self.assertIsNone(contract)
            self.assertEqual(path_str, str(path))
            self.assertEqual(len(problems), 1)
            self.assertIn("is unreadable", problems[0])


class ContractSha256Tests(unittest.TestCase):
    def test_known_byte_string_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "quality.json"
            path.write_bytes(b"abc")
            self.assertEqual(
                quality_contract.contract_sha256(path),
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            )

    def test_empty_file_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "quality.json"
            path.write_bytes(b"")
            self.assertEqual(
                quality_contract.contract_sha256(path),
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            )

    def test_missing_file_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(
                quality_contract.contract_sha256(Path(tmp) / "absent.json")
            )

    def test_digest_tracks_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "quality.json"
            path.write_bytes(b"{}")
            first = quality_contract.contract_sha256(path)
            path.write_bytes(b'{"schema": 1}')
            self.assertNotEqual(first, quality_contract.contract_sha256(path))


class DeclaredSchemaTests(unittest.TestCase):
    """The declared schema and the copyable template stay consistent and valid."""

    SCHEMA_PATH = HUB_ROOT / "contracts" / "quality.schema.json"
    TEMPLATE_PATH = HUB_ROOT / "templates" / "quality-contract.json"

    def test_schema_and_template_are_valid_json(self):
        schema = json.loads(self.SCHEMA_PATH.read_text(encoding="utf-8"))
        json.loads(self.TEMPLATE_PATH.read_text(encoding="utf-8"))
        self.assertTrue(schema)

    def test_schema_documents_the_frozen_shape(self):
        schema = json.loads(self.SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"],
                         "https://json-schema.org/draft/2020-12/schema")
        self.assertTrue(schema["$id"])
        self.assertTrue(schema["title"])
        self.assertIs(schema["additionalProperties"], False)
        self.assertEqual(
            set(schema["required"]),
            {"schema", "project", "product_type", "hosted_ci",
             "required_gates", "release_gates", "gates"},
        )
        self.assertEqual(
            set(schema["properties"]),
            {"schema", "project", "product_type", "supported_platforms",
             "required_gates", "release_gates", "external_requirements",
             "hosted_ci", "gates", "report", "artifacts", "policies"},
        )
        self.assertEqual(
            set(schema["$defs"]["gateEntry"]["properties"]), {"gate"}
        )
        self.assertEqual(
            schema["$defs"]["gateEntry"]["properties"]["gate"]["enum"],
            ["verify", "acceptance", "release"],
        )
        self.assertEqual(
            schema["properties"]["hosted_ci"]["enum"],
            ["required", "optional", "none"],
        )

    def test_template_names_the_frozen_lookup_location_and_report_default(self):
        template = json.loads(self.TEMPLATE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            quality_contract.CONTRACT_PATHS,
            (".aeh/quality.json", "docs/quality.json"),
        )
        self.assertEqual(template["report"], ".hub/gate-report.json")
        self.assertTrue(
            set(template["required_gates"]) <= set(template["gates"])
        )
        self.assertTrue(
            set(template["release_gates"]) <= set(template["gates"])
        )


if __name__ == "__main__":
    unittest.main()
