"""Read-only loader and validator for a project's AEH quality contract.

The quality contract is the project-owned, machine-readable declaration of what
"verified" means for that project: which gates exist, which of them are required
or release gates, which platforms are supported, how much hosted CI is expected,
where the gate report is written, which artifacts must be hashed and how missing
or stale evidence is treated.  The authority for its shape is
``contracts/quality.schema.json`` plus the frozen interface spec; this module is
the authoritative validator.

Guarantees provided by this module:

* **Read-only.**  Nothing here writes to a project, to the Hub or to a ledger.
  ``load_contract`` and ``contract_sha256`` only read bytes; ``validate_contract``
  is a pure function over already-parsed data.
* **No execution.**  No project code, gate, shell or subprocess is ever started,
  no network is used and no daemon is created.  **The Hub never runs a command
  taken from the contract**: a repository metadata file must not be able to
  become an execution vector.  Object keys named ``command``, ``cmd``, ``run``,
  ``exec``, ``shell`` or ``script`` (case-insensitive, at any depth) are rejected
  as command injection, and the rejection names the offending JSON path.  AEH
  executes only the owner-approved command from the project's registry entry.
* **Fail closed.**  A missing contract is not an error: it is reported as
  insufficient evidence through the problem string
  ``no quality contract at <path1> or <path2>``.  An unreadable, non-UTF-8,
  unparseable or invalid contract is invalid data: ``load_contract`` returns
  ``contract=None`` with one exact problem string per violation, and never
  guesses or applies undocumented defaults.  Malformed input never raises.

Lookup order, first existing path wins (relative to the project root):

1. ``<project>/.aeh/quality.json``
2. ``<project>/docs/quality.json``

Both paths are absolute in the problem strings and in the returned ``path_str``
so a caller can use the result directly with ``contract_sha256(Path(path_str))``
regardless of the current working directory.

Python standard library only.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath

__all__ = [
    "CONTRACT_PATHS",
    "contract_sha256",
    "load_contract",
    "validate_contract",
]

#: Lookup order for a project's quality contract.  The first existing path wins.
CONTRACT_PATHS = (".aeh/quality.json", "docs/quality.json")

_ALLOWED_TOP_LEVEL_KEYS = frozenset({
    "schema",
    "project",
    "product_type",
    "supported_platforms",
    "required_gates",
    "release_gates",
    "external_requirements",
    "hosted_ci",
    "gates",
    "report",
    "artifacts",
    "policies",
})

_REQUIRED_TOP_LEVEL_KEYS = (
    "schema",
    "project",
    "product_type",
    "hosted_ci",
    "required_gates",
    "release_gates",
    "gates",
)

_ARRAY_TOP_LEVEL_KEYS = (
    "supported_platforms",
    "required_gates",
    "release_gates",
    "external_requirements",
)

#: Array fields that must be present and non-empty, not merely well-typed.
_NON_EMPTY_ARRAY_KEYS = ("required_gates", "release_gates")

_HOSTED_CI_VALUES = ("required", "optional", "none")

_GATE_KINDS = ("verify", "acceptance", "release")

#: Allowed policy values per policy key.  ``production_changes`` is narrower on
#: purpose: the spec allows only ``require_approval``/``warn`` there and has no
#: ``block`` value, so a production change is gated by approval, not refused.
_POLICY_VALUES = {
    "missing_evidence": ("block", "warn"),
    "stale_evidence": ("block", "warn"),
    "skipped_required_gate": ("block", "warn"),
    "production_changes": ("require_approval", "warn"),
}

#: Object keys that would smuggle an execution vector into repository metadata.
#: Matched case-insensitively at any depth, and never executed.
_FORBIDDEN_COMMAND_KEYS = frozenset({
    "command", "cmd", "run", "exec", "shell", "script",
})


def contract_sha256(path: Path) -> str | None:
    """Return the sha256 hex digest of the contract file's raw bytes.

    Returns ``None`` when the file cannot be read (missing, unreadable or not a
    regular file).  The digest is over the exact bytes on disk, so any edit to
    the contract invalidates records bound to the previous digest.
    """
    try:
        with open(os.fspath(path), "rb") as handle:
            raw = handle.read()
    except (OSError, TypeError, ValueError):
        return None
    return hashlib.sha256(raw).hexdigest()


def load_contract(project_path: Path) -> tuple[dict | None, str | None, list[str]]:
    """Read the first existing quality contract for a project.

    Returns ``(contract, path_str, problems)``:

    * absent: ``(None, None, ["no quality contract at <abs path 1> or <abs path 2>"])``
    * present but unreadable, not UTF-8, unparseable or invalid:
      ``(None, <abs path> , problems)`` with one exact problem string per violation
    * present and valid: ``(parsed contract, <abs path>, [])``

    ``path_str`` is always an absolute path string so it can be read, hashed or
    displayed without depending on the current working directory.  This function
    never executes anything and never raises on malformed input.
    """
    base = os.path.abspath(os.fspath(project_path))
    for relative in CONTRACT_PATHS:
        candidate = os.path.join(base, relative)
        if not os.path.exists(candidate):
            continue
        path_str = candidate
        try:
            with open(candidate, "rb") as handle:
                raw = handle.read()
        except OSError as error:
            return None, path_str, [
                f"quality contract {path_str} is unreadable: {error}"
            ]
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            return None, path_str, [
                f"quality contract {path_str} is not valid UTF-8: {error}"
            ]
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            return None, path_str, [
                f"quality contract {path_str} is not valid JSON: {error}"
            ]
        problems = validate_contract(data)
        if problems:
            return None, path_str, problems
        return data, path_str, []
    return None, None, [
        "no quality contract at "
        + " or ".join(os.path.join(base, relative) for relative in CONTRACT_PATHS)
    ]


def validate_contract(data: object) -> list[str]:
    """Return the list of problems in a parsed quality contract; [] means valid.

    Pure and total: it inspects already-parsed data, never reads files, never
    executes anything and never raises on malformed input.  One string is
    returned per violation, each naming the offending field or JSON path.

    Documented defaults are *not* applied here.  A contract may omit optional
    fields (``supported_platforms``, ``external_requirements``, ``report``,
    ``artifacts``, ``policies`` and individual ``policies`` keys); the consumer
    decides what an omitted field means.  Objects nested under allowed fields
    (for example an ``artifacts`` entry) may carry extra descriptive keys, except
    that the command-injection ban applies to every key at every depth.
    """
    problems: list[str] = []

    if not isinstance(data, dict):
        problems.append(
            f"quality contract must be a JSON object, got {_json_type(data)}"
        )
    else:
        problems.extend(_validate_top_level(data))

    # A repository metadata file must never be an execution vector.  The scan is
    # global: unknown top-level keys are already an error, but the injection
    # message must still name the exact JSON path of every offending key.
    problems.extend(_command_key_problems(data))
    return problems


def _validate_top_level(data: dict) -> list[str]:
    problems: list[str] = []

    unknown = (key for key in data if not _is_allowed_top_level_key(key))
    for key in sorted(unknown, key=str):
        problems.append(f"unknown top-level key {key!r}")

    for key in _REQUIRED_TOP_LEVEL_KEYS:
        if key not in data:
            problems.append(f"missing required key '{key}'")

    if "schema" in data:
        value = data["schema"]
        # bool is a subclass of int: `True == 1` must not pass as schema 1.
        if isinstance(value, bool) or not isinstance(value, int) or value != 1:
            problems.append(f"schema must be 1, got {_describe(value)}")

    for key in ("project", "product_type"):
        if key in data and not _is_nonempty_string(data[key]):
            problems.append(f"{key} must be a non-empty string")

    if "hosted_ci" in data:
        value = data["hosted_ci"]
        if not isinstance(value, str) or value not in _HOSTED_CI_VALUES:
            problems.append(
                "hosted_ci must be one of "
                + ", ".join(_HOSTED_CI_VALUES)
                + f", got {_describe(value)}"
            )

    problems.extend(_validate_string_arrays(data))
    problems.extend(_validate_gates(data))
    problems.extend(_validate_report(data))
    problems.extend(_validate_artifacts(data))
    problems.extend(_validate_policies(data))
    return problems


def _validate_string_arrays(data: dict) -> list[str]:
    problems: list[str] = []
    for key in _ARRAY_TOP_LEVEL_KEYS:
        if key not in data:
            continue
        value = data[key]
        if not isinstance(value, list):
            problems.append(
                f"{key} must be an array of non-empty strings, got {_json_type(value)}"
            )
            continue
        seen: set[str] = set()
        for index, entry in enumerate(value):
            if not _is_nonempty_string(entry):
                problems.append(f"{key}[{index}] must be a non-empty string")
                continue
            if entry in seen:
                problems.append(f"{key}[{index}] is a duplicate entry {entry!r}")
                continue
            seen.add(entry)
        if key in _NON_EMPTY_ARRAY_KEYS and not value:
            problems.append(f"{key} must not be empty")
    return problems


def _validate_gates(data: dict) -> list[str]:
    problems: list[str] = []
    gates = data.get("gates")
    if not isinstance(gates, dict):
        # A missing 'gates' is already reported as a missing required key; a
        # wrong type is reported here.  Either way the reference check below
        # would only repeat the same defect once per declared gate name.
        if "gates" in data:
            problems.append(f"gates must be an object, got {_json_type(gates)}")
        return problems

    for name, entry in gates.items():
        path = _child_path("gates", name)
        if not isinstance(entry, dict):
            problems.append(f"{path} must be an object, got {_json_type(entry)}")
            continue
        for key in sorted((k for k in entry if k != "gate"), key=str):
            problems.append(f"unknown key {key!r} in {path}")
        if "gate" not in entry:
            problems.append(f"{path} must declare 'gate'")
            continue
        kind = entry["gate"]
        if not isinstance(kind, str) or kind not in _GATE_KINDS:
            problems.append(
                f"{path}.gate must be one of "
                + ", ".join(_GATE_KINDS)
                + f", got {_describe(kind)}"
            )

    # Every gate named by required_gates/release_gates must be declared in gates,
    # otherwise a mandatory gate would silently not exist.
    for key in ("required_gates", "release_gates"):
        value = data.get(key)
        if not isinstance(value, list):
            continue
        for index, name in enumerate(value):
            if _is_nonempty_string(name) and name not in gates:
                problems.append(
                    f"{key}[{index}] gate {name!r} is not defined in gates"
                )
    return problems


def _validate_report(data: dict) -> list[str]:
    if "report" not in data:
        return []
    value = data["report"]
    if not isinstance(value, str):
        return [f"report must be a relative path string, got {_json_type(value)}"]
    if not _is_nonempty_string(value):
        return ["report must be a non-empty relative path string"]
    if _is_absolute_path(value):
        return [
            f"report must be a relative path contained in the project, got {value!r}"
        ]
    if ".." in _path_parts(value):
        return [f"report must not contain '..', got {value!r}"]
    return []


def _validate_artifacts(data: dict) -> list[str]:
    if "artifacts" not in data:
        return []
    value = data["artifacts"]
    if not isinstance(value, list):
        return [f"artifacts must be an array, got {_json_type(value)}"]
    problems: list[str] = []
    for index, entry in enumerate(value):
        path = f"artifacts[{index}]"
        if not isinstance(entry, dict):
            problems.append(f"{path} must be an object, got {_json_type(entry)}")
            continue
        if "name" not in entry:
            problems.append(f"{path} must declare a non-empty 'name'")
        elif not _is_nonempty_string(entry["name"]):
            problems.append(f"{path}.name must be a non-empty string")
        if "platform" in entry and not _is_nonempty_string(entry["platform"]):
            problems.append(f"{path}.platform must be a non-empty string")
        if "hash_required" in entry and not isinstance(entry["hash_required"], bool):
            problems.append(f"{path}.hash_required must be a boolean")
    return problems


def _validate_policies(data: dict) -> list[str]:
    if "policies" not in data:
        return []
    value = data["policies"]
    if not isinstance(value, dict):
        return [f"policies must be an object, got {_json_type(value)}"]
    problems: list[str] = []
    for key in sorted(value, key=str):
        path = _child_path("policies", key)
        if not isinstance(key, str) or key not in _POLICY_VALUES:
            problems.append(f"unknown policy {key!r}")
            continue
        allowed = _POLICY_VALUES[key]
        entry = value[key]
        if not isinstance(entry, str) or entry not in allowed:
            problems.append(
                f"{path} must be one of "
                + ", ".join(allowed)
                + f", got {_describe(entry)}"
            )
    return problems


def _command_key_problems(document: object) -> list[str]:
    """Report every object key that could smuggle a command into the contract.

    Iterative on purpose: a deeply nested document must produce problems rather
    than a RecursionError.  Paths use dotted access for object keys and ``[i]``
    for array elements, so the message names the exact location.
    """
    problems: list[str] = []
    stack: list[tuple[object, str]] = [(document, "")]
    while stack:
        value, path = stack.pop()
        if isinstance(value, dict):
            children: list[tuple[object, str]] = []
            for key, entry in value.items():
                child = _child_path(path, key)
                if isinstance(key, str) and key.lower() in _FORBIDDEN_COMMAND_KEYS:
                    problems.append(
                        f"command injection: key {key!r} is forbidden at JSON path "
                        f"{child}"
                    )
                children.append((entry, child))
            stack.extend(reversed(children))
        elif isinstance(value, list):
            stack.extend(
                (entry, f"{path}[{index}]")
                for index, entry in reversed(list(enumerate(value)))
            )
    return problems


def _is_allowed_top_level_key(key: object) -> bool:
    return isinstance(key, str) and key in _ALLOWED_TOP_LEVEL_KEYS


def _is_nonempty_string(value: object) -> bool:
    # Whitespace-only names are not usable identities: fail closed.
    return isinstance(value, str) and value.strip() != ""


def _child_path(path: str, key: object) -> str:
    text = key if isinstance(key, str) else repr(key)
    return text if not path else f"{path}.{text}"


def _path_parts(value: str) -> list[str]:
    return [part for part in value.replace("\\", "/").split("/") if part]


def _is_absolute_path(value: str) -> bool:
    if PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute():
        return True
    # A Windows drive-relative path ("C:foo") is not contained in the project
    # even though PureWindowsPath does not call it absolute.
    return bool(PureWindowsPath(value).drive)


def _json_type(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _describe(value: object, limit: int = 200) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        text = repr(value)
    return text if len(text) <= limit else text[: limit - 1] + "\u2026"
