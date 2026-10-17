#!/usr/bin/env python3
"""AEH conformance suite: does the Hub ever claim VERIFIED when it should not?

The Hub grades other projects, so the Hub itself must be graded adversarially.
This runner builds a disposable copy of the Hub in a temporary directory — its
own `hub.config.json`, its own registry, a real (tiny) Git repository, a real
`.hub/verification.jsonl` — and runs the real `scripts/hub.py` from that copy as
a subprocess. Nothing here touches the live Hub, the real registry, the real
ledger or any project repository.

A fixture is `tests/fixtures/conformance/<id>/scenario.json`:

    {
      "id": "stale-old-sha",
      "title": "evidence from a previous revision is STALE, not VERIFIED",
      "project": {"verify": "bash verify.sh", "acceptance": "bash accept.sh"},
      "files": {"verify.sh": "#!/usr/bin/env bash\\nexit 0\\n"},
      "artifacts": {"dist/app.bin": "payload"},
      "contract": "base" | null | { ...quality.json... },
      "git": {"remote": false},
      "steps":  [{"cmd": ["verify", "fx", "--gate", "verify"], "expect_exit": 0}],
      "mutate": ["commit"],
      "probes": [{"cmd": ["assess", "fx", "--json"],
                  "json_path": "data.overall.verdict", "expect": "STALE",
                  "expect_exit": 3}],
      "assert_absent": ["canary.txt"]
    }

Exit 0 only when every fixture produces exactly the expected verdict. Fixtures
that never run are a failure too: the suite refuses to report coverage it did
not exercise. Zero false-green on the designed set is the acceptance
criterion — it is not a claim that the Hub can never be wrong.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parent.parent
CONFORMANCE_DIR = HUB_ROOT / "tests" / "fixtures" / "conformance"
PROJECT_NAME = "fx"
PROJECT_SLUG = "fx"

BASE_CONTRACT = {
    "schema": 1,
    "project": "FX",
    "product_type": "fixture",
    "supported_platforms": ["linux-x64"],
    "required_gates": ["source-integrity", "product-build"],
    "release_gates": ["product-acceptance"],
    "hosted_ci": "optional",
    "gates": {
        "source-integrity": {"gate": "verify"},
        "product-build": {"gate": "acceptance"},
    },
    "policies": {
        "missing_evidence": "block",
        "stale_evidence": "block",
        "skipped_required_gate": "block",
        "production_changes": "require_approval",
    },
}

MUTATIONS = ("commit", "dirty", "break-ledger", "modify-artifact",
             "remove-contract", "truncate-ledger")


class FixtureError(RuntimeError):
    pass


def hub_git(args: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["GIT_CONFIG_COUNT"] = "0"
    env["GIT_AUTHOR_NAME"] = "conformance"
    env["GIT_AUTHOR_EMAIL"] = "conformance@example.invalid"
    env["GIT_COMMITTER_NAME"] = "conformance"
    env["GIT_COMMITTER_EMAIL"] = "conformance@example.invalid"
    proc = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                          text=True, env=env, timeout=60)
    if check and proc.returncode != 0:
        raise FixtureError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc


def write_file(path: Path, content: str, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if mode is not None:
        path.chmod(mode)


def resolve_contract(spec: dict) -> dict | None:
    contract = spec.get("contract", None)
    if contract == "base":
        return json.loads(json.dumps(BASE_CONTRACT))
    return contract


def setup_fixture(spec: dict, root: Path) -> Path:
    """Materialise the disposable Hub copy and return the project path."""
    scripts = root / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    for name in ("hub.py", "quality_contract.py"):
        source = HUB_ROOT / "scripts" / name
        if not source.is_file():
            raise FixtureError(f"required Hub script is missing: {source}")
        shutil.copy2(source, scripts / name)

    workspace = root / "ws"
    project = workspace / PROJECT_NAME
    project.mkdir(parents=True, exist_ok=True)
    (root / "projects").mkdir(parents=True, exist_ok=True)
    (root / ".hub").mkdir(parents=True, exist_ok=True)
    write_file(root / "hub.config.json", json.dumps({
        "version": 1,
        "workspace_root": str(workspace),
        "registry": "projects/registry.json",
        "usage_file": ".hub/usage.jsonl",
    }, indent=2) + "\n")

    for rel, content in (spec.get("files") or {}).items():
        write_file(project / rel, content)
    for rel, content in (spec.get("artifacts") or {}).items():
        write_file(project / rel, content)

    # The contract is committed with the project: a fresh untracked contract
    # would make every fixture read as a dirty tree. `.hub/` is runtime state
    # (gate reports, ledger) and belongs in .gitignore, exactly as a real
    # project would keep it.
    contract = resolve_contract(spec)
    if contract is not None:
        write_file(project / ".aeh" / "quality.json", json.dumps(contract, indent=2) + "\n")
    write_file(project / ".gitignore", ".hub/\n")

    git_spec = spec.get("git") or {}
    hub_git(["init", "-q", "-b", "main"], project)
    write_file(project / "TRACKED.txt", "fixture\n")
    hub_git(["add", "-A"], project)
    hub_git(["commit", "-q", "-m", "fixture: initial"], project)
    if git_spec.get("remote"):
        bare = root / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", str(bare)],
                       capture_output=True, check=True, timeout=60)
        hub_git(["remote", "add", "origin", str(bare)], project)
        hub_git(["push", "-q", "-u", "origin", "main"], project)
    for index in range(int(git_spec.get("ahead_commits") or 0)):
        write_file(project / f"ahead-{index}.txt", "not pushed\n")
        hub_git(["add", "-A"], project)
        hub_git(["commit", "-q", "-m", f"fixture: local commit {index}"], project)

    project_spec = spec.get("project") or {}
    entry = {
        "slug": PROJECT_SLUG,
        "path": str(project),
        "workspace_root": str(workspace),
        "in_workspace_root": True,
        "remote": None,
        "state": "active",
        "verify": project_spec.get("verify"),
        "acceptance": project_spec.get("acceptance"),
        "release": project_spec.get("release"),
        "is_repo": True,
        "registered_at": "2026-10-17T00:00:00+00:00",
    }
    write_file(root / "projects" / "registry.json",
               json.dumps({"version": 1, "projects": {PROJECT_SLUG: entry}},
                          indent=2, sort_keys=True) + "\n")
    return project


def run_hub(root: Path, argv: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(root / "scripts" / "hub.py"), *argv],
        cwd=str(root), capture_output=True, text=True, timeout=timeout)


def json_at(payload: object, path: str) -> object:
    current = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise FixtureError(f"json path not found: {path}")
        current = current[part]
    return current


def apply_mutation(name: str, project: Path, root: Path, spec: dict) -> None:
    if name == "commit":
        write_file(project / f"new-{len(list(project.glob('new-*')))}.txt", "moved\n")
        hub_git(["add", "-A"], project)
        hub_git(["commit", "-q", "-m", "fixture: move HEAD"], project)
    elif name == "dirty":
        write_file(project / "uncommitted-note.txt", "dirty\n")
    elif name == "break-ledger":
        ledger = root / ".hub" / "verification.jsonl"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("a", encoding="utf-8") as stream:
            stream.write("{not json at all\n")
    elif name == "truncate-ledger":
        ledger = root / ".hub" / "verification.jsonl"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text("", encoding="utf-8")
    elif name == "modify-artifact":
        for rel in (spec.get("artifacts") or {}):
            write_file(project / rel, "tampered payload\n")
    elif name == "remove-contract":
        target = project / ".aeh" / "quality.json"
        if target.exists():
            target.unlink()
    else:
        raise FixtureError(f"unknown mutation: {name}")


def run_fixture(spec: dict, *, keep: bool = False) -> dict:
    fixture_id = spec.get("id")
    if not fixture_id:
        raise FixtureError("scenario.json has no id")
    problems: list[str] = []
    observed: list[str] = []
    root = Path(tempfile.mkdtemp(prefix=f"aeh-conf-{fixture_id}-"))
    try:
        project = setup_fixture(spec, root)
        for step in spec.get("steps") or []:
            proc = run_hub(root, step["cmd"])
            observed.append(f"step {' '.join(step['cmd'])} -> exit {proc.returncode}")
            expected = step.get("expect_exit")
            if expected is not None and proc.returncode != expected:
                problems.append(
                    f"step {' '.join(step['cmd'])}: exit {proc.returncode}, expected {expected}"
                    f" | {tail(proc)}")
        for name in spec.get("mutate") or []:
            apply_mutation(name, project, root, spec)

        for probe in spec.get("probes") or []:
            proc = run_hub(root, probe["cmd"])
            observed.append(f"probe {' '.join(probe['cmd'])} -> exit {proc.returncode}")
            expected_exit = probe.get("expect_exit")
            if expected_exit is not None and proc.returncode != expected_exit:
                problems.append(
                    f"probe {' '.join(probe['cmd'])}: exit {proc.returncode}, "
                    f"expected {expected_exit} | {tail(proc)}")
            path = probe.get("json_path")
            if path:
                if not proc.stdout.strip():
                    problems.append(f"probe {' '.join(probe['cmd'])}: no stdout to parse")
                    continue
                try:
                    payload = json.loads(proc.stdout)
                except ValueError as error:
                    problems.append(f"probe {' '.join(probe['cmd'])}: stdout is not JSON "
                                    f"({type(error).__name__}) | {tail(proc)}")
                    continue
                try:
                    value = json_at(payload, path)
                except FixtureError as error:
                    problems.append(str(error))
                    continue
                expected = probe.get("expect")
                observed.append(f"  {path} = {value!r}")
                if expected is not None and value != expected:
                    problems.append(f"probe {' '.join(probe['cmd'])}: {path} = {value!r}, "
                                    f"expected {expected!r}")
            if probe.get("stdout_contains"):
                needle = probe["stdout_contains"]
                if needle not in proc.stdout and needle not in proc.stderr:
                    problems.append(
                        f"probe {' '.join(probe['cmd'])}: output does not contain {needle!r}")

        for rel in spec.get("assert_absent") or []:
            if (project / rel).exists():
                problems.append(f"{rel} exists but the read-only command must not create it")
        for rel in spec.get("assert_present") or []:
            if not (project / rel).exists():
                problems.append(f"{rel} is missing but the fixture requires it")
        return {"id": fixture_id, "title": spec.get("title", ""),
                "ok": not problems, "problems": problems, "observed": observed}
    finally:
        if keep:
            print(f"fixture kept at {root}", file=sys.stderr)
        else:
            shutil.rmtree(root, ignore_errors=True)


def tail(proc: subprocess.CompletedProcess, limit: int = 240) -> str:
    text = (proc.stdout or "") + (proc.stderr or "")
    text = " ".join(text.split())
    return text[-limit:]


def load_scenarios() -> list[dict]:
    if not CONFORMANCE_DIR.is_dir():
        raise FixtureError(f"conformance fixture directory is missing: {CONFORMANCE_DIR}")
    specs = []
    for path in sorted(CONFORMANCE_DIR.glob("*/scenario.json")):
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as error:
            raise FixtureError(f"{path} is not valid JSON ({type(error).__name__})")
        if not isinstance(spec, dict):
            raise FixtureError(f"{path} must hold a JSON object")
        spec.setdefault("_path", str(path))
        specs.append(spec)
    if not specs:
        raise FixtureError(f"no scenario.json found under {CONFORMANCE_DIR}")
    return specs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fixture", action="append", default=None,
                        help="run only this fixture id (repeatable)")
    parser.add_argument("--keep", action="store_true", help="keep temp roots for inspection")
    parser.add_argument("--json", action="store_true", help="machine-readable result")
    args = parser.parse_args(argv)

    try:
        scenarios = load_scenarios()
    except FixtureError as error:
        print(f"conformance: {error}", file=sys.stderr)
        return 2

    if args.fixture:
        wanted = set(args.fixture)
        scenarios = [s for s in scenarios if s.get("id") in wanted]
        missing = wanted - {s.get("id") for s in scenarios}
        if missing:
            print(f"conformance: unknown fixture(s): {sorted(missing)}", file=sys.stderr)
            return 2

    results, duration = [], []
    for spec in scenarios:
        try:
            results.append(run_fixture(spec, keep=args.keep))
        except (FixtureError, subprocess.TimeoutExpired, OSError) as error:
            results.append({"id": spec.get("id", "<unknown>"), "title": spec.get("title", ""),
                            "ok": False, "observed": [],
                            "problems": [f"runner error: {type(error).__name__}: {error}"]})

    failed = [r for r in results if not r["ok"]]
    if args.json:
        print(json.dumps({"schema_version": 1, "fixtures": results,
                          "passed": len(results) - len(failed), "failed": len(failed)},
                         indent=2, sort_keys=True))
    else:
        for result in results:
            mark = "PASS" if result["ok"] else "FAIL"
            print(f"  {mark}  {result['id']:<32} {result['title']}")
            for problem in result["problems"]:
                print(f"        {problem}")
        print()
        print(f"fixtures: {len(results)}  passed: {len(results) - len(failed)}  "
              f"failed: {len(failed)}")
        print(f"RESULT: {'NO FALSE-GREEN' if not failed else 'FALSE-GREEN OR UNPROVEN'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
