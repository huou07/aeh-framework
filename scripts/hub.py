#!/usr/bin/env python3
"""Agentic Engineering Hub CLI.

Deterministic operations for project discovery, registration, status and
usage aggregation. Standard library only. No daemon, no scheduler, no network.

Usage:
    python3 scripts/hub.py <command> [options]

Commands:
    add      Register a project in the registry
    list     List registered projects
    where    Resolve a slug to its verified workspace path
    status   Derived status from real Git state (READ-ONLY: runs no project code)
    assess   Quality-evidence assessment across areas (READ-ONLY, five verdicts)
    release-check  Release readiness verdict (READ-ONLY, five verdicts)
    verify   Explicitly run a project's verification command (bounded, opt-in)
    report   Aggregate Hub view
    new      Create an isolated empty project workspace (collision-checked)
    usage    Per-task efficiency/cost record for one project
    doctor   Self-check: config, registry integrity, containment, evidence

Security note: `status`, `assess`, `release-check`, `report`, `usage`, `list`,
`where` and `doctor` are read-only. They never execute project code, never write
into a project directory and never install anything. Running a project's
verification executes that project's own code, so it is a separate, explicit
command with a wall-clock bound, an output cap, whole-process-group termination
on timeout, and an exclusive `.hub/verify.lock` so two heavy builds cannot run
at once by accident.

Verdict vocabulary (see docs/quality-standard.md and docs/quality-interface.md):
VERIFIED, FAILED, BLOCKED, STALE, NOT_VERIFIED. A skipped or not-run check is
never PASS; evidence from another revision is STALE; a claim with no log is
NOT_VERIFIED.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import queue
import shlex
import signal
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# The project-owned, machine-readable quality contract. Kept in its own module
# so it can be tested without importing the CLI. A missing module is fatal on
# purpose: `doctor` reports it rather than the Hub pretending contracts work.
from quality_contract import (  # noqa: E402  (sys.path set above)
    CONTRACT_PATHS,
    contract_sha256,
    load_contract,
)

HUB_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = HUB_ROOT / "hub.config.json"
# A slug is the project's own name. Any case, spaces and punctuation are
# accepted; only characters that would corrupt the registry, break the CLI or
# escape the workspace directory are rejected (see validate_slug).
SLUG_MAX_LEN = 100
SLUG_PATH_SEPARATORS = ("/", "\\")
RUN_TIMEOUT = 300
# A verification command is project-supplied code. Its output is capped so a
# runaway build cannot exhaust memory: only the head and tail are retained.
VERIFY_MAX_CAPTURE = 64 * 1024
VERIFY_MAX_TIMEOUT = 1800


def git_env() -> dict[str, str]:
    """An environment in which `git` can start at all.

    The worker launcher declares Git's ownership exception through
    `GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0=safe.directory` and
    `GIT_CONFIG_VALUE_0=<home>/*`. The harness credential scrub drops every
    child environment name matching /KEY|PASSWORD|SECRET|TOKEN/ before it is
    handed to a shell, so the KEY entry disappears while the count and the
    value survive. Git then refuses to run — `fatal: missing config key
    GIT_CONFIG_KEY_0` — and reports the same failure for a missing repository,
    a dirty tree and a healthy one alike (measured 2026-10-16 under
    h07p-dsh.service, where every registered project read REPO=no).

    The Hub therefore stops inheriting indexed configuration rather than
    depending on it: the count is pinned to zero, so any leftover pair is
    ignored instead of fatal.
    """
    env = dict(os.environ)
    env["GIT_CONFIG_COUNT"] = "0"
    for name in [n for n in env
                 if n.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"))]:
        del env[name]
    return env


def git_argv(cwd: Path, args: list[str]) -> list[str]:
    """`git` argv that trusts the tree being read, and nothing else.

    A worker UID that does not own the checkout is refused by Git's ownership
    check, so the exception is declared per call. Every call site reads either
    the Hub root or a configured project path — both repository roots — and the
    trailing glob covers subdirectories of that same tree.
    """
    root = str(Path(cwd).resolve())
    return ["git", "-c", f"safe.directory={root}",
            "-c", f"safe.directory={root}/*", *args]


def run_verify(cmd_str: str, cwd: Path,
               timeout: int = RUN_TIMEOUT) -> tuple[str, int, str]:
    """Run a project's verification command under hard bounds.

    Returns (state, exit_code, output) where state is one of:
      PASS     exit 0
      FAIL     non-zero exit
      TIMEOUT  exceeded the wall-clock bound
      ERROR    could not start (missing shell, bad cwd, ...)

    Safety properties, each covered by tests/test_hub_safety.py:
      * no login shell — `-c`, not `-lc`, so shell rc files are not executed;
      * the whole process GROUP is killed on timeout, so a forked grandchild
        cannot outlive the bound;
      * output is capped; the middle of a huge stream is dropped, not buffered.
    """
    timeout = max(1, min(int(timeout), VERIFY_MAX_TIMEOUT))
    try:
        proc = subprocess.Popen(
            ["bash", "-c", cmd_str],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            start_new_session=True,  # own process group -> killpg reaches children
        )
    except (OSError, ValueError) as e:
        return "ERROR", 127, f"could not start verification: {e}"

    chunks: list[str] = []
    size = 0
    dropped = 0
    q: queue.Queue = queue.Queue()

    def reader() -> None:
        try:
            for line in iter(proc.stdout.readline, ""):
                q.put(line)
        except (OSError, ValueError):
            pass
        q.put(None)  # EOF sentinel

    t = threading.Thread(target=reader, daemon=True)
    t.start()

    deadline = time.monotonic() + timeout
    eof = False
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            item = q.get(timeout=min(remaining, 0.5))
        except queue.Empty:
            continue
        if item is None:
            eof = True
            break
        if size < VERIFY_MAX_CAPTURE:
            chunks.append(item)
            size += len(item)
        else:
            dropped += len(item)

    if not eof:
        # Wall-clock bound reached: tear down the ENTIRE process group so a
        # forked grandchild cannot outlive the command.
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            proc.kill()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        try:
            proc.stdout.close()
        except (OSError, ValueError):
            pass
        body = "".join(chunks)
        if dropped:
            body += f"\n... [{dropped} bytes of output truncated] ...\n"
        body += f"\nTIMEOUT: exceeded {timeout}s; whole process group killed"
        return "TIMEOUT", 124, body

    proc.wait(timeout=10)
    proc.stdout.close()
    rc = proc.returncode if proc.returncode is not None else 1
    body = "".join(chunks)
    if dropped:
        body += f"\n... [{dropped} bytes of output truncated] ...\n"
    return ("PASS" if rc == 0 else "FAIL"), rc, body


# ---------------------------------------------------------------- utilities

class HubError(SystemExit):
    def __init__(self, msg: str, code: int, kind: str):
        super().__init__(code)
        self.message, self.kind = msg, kind


def die(msg: str, code: int = 1, kind: str = "invalid_input"):
    print(f"hub: error: {msg}", file=sys.stderr)
    raise HubError(msg, code, kind)


def ok(msg: str):
    print(msg)


def validate_slug(slug: str) -> str | None:
    """Return None when the slug is usable, else the reason it is rejected.

    Project names are human input, so case, spaces and punctuation are allowed.
    Rejected: empty/overlong names, control characters, path separators (the
    slug becomes a directory name under the workspace root), `.`/`..`, and a
    leading `-` that the shell/argparse would read as a flag.
    """
    if not isinstance(slug, str) or not slug:
        return "slug must be a non-empty string"
    if len(slug) > SLUG_MAX_LEN:
        return f"slug longer than {SLUG_MAX_LEN} characters"
    if slug != slug.strip():
        return "slug must not begin or end with whitespace"
    if any(ord(c) < 0x20 or ord(c) == 0x7F for c in slug):
        return "slug must not contain control characters"
    for separator in SLUG_PATH_SEPARATORS:
        if separator in slug:
            return f"slug must not contain '{separator}' (path separator)"
    if slug in (".", ".."):
        return "slug must not be '.' or '..'"
    if slug.startswith("-"):
        return ("slug must not start with '-'; pass it as --slug=<name> so the "
                "shell and argparse do not read it as a flag")
    return None


def resolve_key(reg: dict, slug: str) -> str | None:
    """Registry key matching `slug` case-insensitively, or None if unknown.

    Slugs are stored with the spelling the owner registered. Commands accept any
    case, so `status OR` resolves the entry registered as `OR`.
    """
    wanted = slug.casefold()
    for key in reg["projects"]:
        if key.casefold() == wanted:
            return key
    return None


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        die(f"config missing: {CONFIG_PATH}")
    cfg = load_json_object(CONFIG_PATH, "invalid_config")
    for key in ("workspace_root", "registry", "usage_file"):
        if not isinstance(cfg.get(key), str) or not cfg[key]:
            die(f"config missing key: {key}")
    for key in ("registry", "usage_file"):
        if Path(cfg[key]).is_absolute() or ".." in Path(cfg[key]).parts:
            die(f"invalid_config: {key} must be a contained relative path")
    return cfg


def load_json_object(path: Path, kind: str) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        die(f"{kind}: {type(error).__name__}", kind=kind)
    if not isinstance(value, dict):
        die(f"{kind}: expected an object", kind=kind)
    return value


def registry_path(cfg: dict) -> Path:
    return HUB_ROOT / cfg["registry"]


def load_registry(cfg: dict) -> dict:
    p = registry_path(cfg)
    if not p.exists():
        return {"version": 1, "projects": {}}
    reg = load_json_object(p, "invalid_registry")
    if reg.get("version") != 1 or not isinstance(reg.get("projects"), dict):
        die("invalid_registry: expected version 1 and projects object", kind="invalid_registry")
    for slug, entry in reg["projects"].items():
        if (validate_slug(slug) is not None or not isinstance(entry, dict)
                or entry.get("slug") != slug
                or not isinstance(entry.get("path"), str)
                or not Path(entry["path"]).is_absolute()
                or any(entry.get(key) is not None and not isinstance(entry[key], str)
                       for key in ("verify", "acceptance", "release", "state", "remote"))):
            die("invalid_registry: invalid project entry", kind="invalid_registry")
    # Slugs resolve case-insensitively, so two entries differing only by case
    # would make lookups ambiguous. Fail closed instead of picking one.
    folded: dict[str, str] = {}
    for slug in reg["projects"]:
        key = slug.casefold()
        if key in folded:
            die(f"invalid_registry: '{slug}' and '{folded[key]}' differ only by case; "
                "slugs are matched case-insensitively", kind="invalid_registry")
        folded[key] = slug
    return reg


def save_registry(cfg: dict, reg: dict):
    p = registry_path(cfg)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(reg, indent=2, sort_keys=True) + "\n")


def inside(child: Path, parent: Path) -> bool:
    """True if child is parent or is contained by parent (both resolved)."""
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def is_within_hub(path: Path) -> bool:
    """True if the path lives inside the Hub repository or its .git dir."""
    p = path.resolve()
    return inside(p, HUB_ROOT) or inside(p / ".git", HUB_ROOT)


def run(cmd: list[str], cwd: Path, timeout: int = 30, *,
        combine_stderr: bool = True) -> tuple[int, str]:
    """Run a bounded read-only command and return (exit_code, output).

    Git calls never inherit the ambient environment: `run` supplies the
    ownership exception and the scrubbed indexed-config environment from
    git_argv/git_env, so Hub evidence does not depend on what the harness
    happened to forward to this process.

    `combine_stderr=False` returns stdout alone. Callers that parse structured
    stdout must use it: `git status --porcelain` writes warnings for paths this
    UID cannot read ("could not open directory ... Permission denied") to
    stderr, and counting those lines as status entries inflates the dirty
    count with paths that are not changes at all (measured 2026-10-17 against
    VCE, where 8 unreadable `deploy/shadow/` entries read as 19 dirty files
    instead of 11).
    """
    env = None
    if cmd and cmd[0] == "git":
        cmd = git_argv(cwd, cmd[1:])
        env = git_env()
    try:
        r = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout,
            check=False, env=env,
        )
        out = (r.stdout + r.stderr).strip() if combine_stderr else r.stdout.strip()
        return r.returncode, out
    except FileNotFoundError:
        return 127, f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timeout after {timeout}s"


def git_state(path: Path) -> dict:
    """Real Git state read from disk. Never from the registry label."""
    state = {
        "is_repo": False, "branch": None, "commit": None, "commit_date": None,
        "subject": None, "dirty": None, "dirty_files": None, "remotes": [],
    }
    if not (path / ".git").exists():
        return state
    rc, out = run(["git", "rev-parse", "--is-inside-work-tree"], path)
    if rc != 0:
        state["is_repo"] = None
        state["git_error"] = f"rev_parse_exit_{rc}"
        return state
    if out.strip() != "true":
        return state
    state["is_repo"] = True
    state["branch"] = (run(["git", "rev-parse", "--abbrev-ref", "HEAD"], path)[1] or None)
    state["commit"] = (run(["git", "rev-parse", "--short", "HEAD"], path)[1] or None)
    state["commit_date"] = (run(["git", "log", "-1", "--format=%cI"], path)[1] or None)
    state["subject"] = (run(["git", "log", "-1", "--format=%s"], path)[1] or None)
    status_rc, status_output = run(["git", "status", "--porcelain"], path,
                                   combine_stderr=False)
    if status_rc == 0:
        state["dirty_files"] = len([l for l in status_output.splitlines() if l.strip()])
        state["dirty"] = state["dirty_files"] > 0
    state["remotes"] = run(["git", "remote", "-v"], path)[1].splitlines()
    return state


# ------------------------------------------------------- verdict vocabulary

# The five states are a scope statement, not a score: VERIFIED means "valid
# evidence, bound to this exact source, every required check actually ran and
# passed". FAILED, BLOCKED, STALE and NOT_VERIFIED each name a different reason
# the claim is not established. Averaging them would let a severe defect hide
# behind good areas, so combining is always worst-of.
VERDICTS = ("VERIFIED", "FAILED", "BLOCKED", "STALE", "NOT_VERIFIED")
_VERDICT_SEVERITY = {"VERIFIED": 0, "NOT_VERIFIED": 1, "STALE": 2,
                     "BLOCKED": 3, "FAILED": 4}
HEX64 = set("0123456789abcdef")


def combine_verdicts(*verdicts: str) -> str:
    """Most severe verdict, never an average."""
    worst = "VERIFIED"
    for verdict in verdicts:
        if verdict not in _VERDICT_SEVERITY:
            verdict = "NOT_VERIFIED"
        if _VERDICT_SEVERITY[verdict] > _VERDICT_SEVERITY[worst]:
            worst = verdict
    return worst


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def is_sha256(value: object) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and set(value.lower()) <= HEX64)


def git_sync(path: Path) -> dict:
    """Upstream and ahead/behind for the checked-out branch, or nulls.

    A branch with no configured upstream is not automatically "unknown": H07P
    is pushed to `origin/codex/h07p-product` while `branch.<name>.merge` is
    unset, and reading that as unknown would hide whether hosted CI can cover
    the revision. The fallback is the matching remote-tracking branch, used
    only when `@{u}` is unset.
    """
    out: dict = {"upstream": None, "ahead": None, "behind": None}
    rc, upstream = run(["git", "rev-parse", "--abbrev-ref",
                        "--symbolic-full-name", "@{u}"], path)
    upstream = upstream.strip()
    if rc != 0 or not upstream:
        branch = (run(["git", "rev-parse", "--abbrev-ref", "HEAD"], path)[1] or "").strip()
        if not branch or branch == "HEAD":
            return out
        candidate = f"origin/{branch}"
        exists, _ = run(["git", "rev-parse", "--verify", "--quiet",
                         f"refs/remotes/{candidate}"], path)
        if exists != 0:
            return out
        upstream = candidate
    out["upstream"] = upstream
    rc, counts = run(["git", "rev-list", "--left-right", "--count",
                      f"HEAD...{upstream}"], path)
    if rc == 0:
        parts = counts.split()
        if len(parts) == 2 and all(p.lstrip("-").isdigit() for p in parts):
            out["ahead"], out["behind"] = int(parts[0]), int(parts[1])
    return out


def normalise_checks(value: object) -> list[dict]:
    """Gate-report skip/not-run entries as {check, reason} pairs, best effort.

    Returns [] for anything that is not a list of objects with a non-empty
    `check`. Validity is decided by `read_gate_report`; this only shapes what
    the text and JSON output shows.
    """
    if not isinstance(value, list):
        return []
    checks = []
    for item in value:
        if not isinstance(item, dict):
            continue
        check = item.get("check")
        if isinstance(check, str) and check:
            reason = item.get("reason")
            checks.append({"check": check,
                           "reason": reason if isinstance(reason, str) and reason
                           else "no reason given"})
    return checks


def read_gate_report(project_path: Path, report_rel: object) -> tuple[dict | None, str | None]:
    """Read the gate report a quality contract may declare. Never executes it.

    Returns (report, error). `error` is None when no report is declared or the
    declared report does not exist yet (absence is handled by the caller as a
    coverage gap, not as invalid data). A file that exists but is malformed is
    an error: coverage claims built on unreadable data are not evidence.
    """
    if not isinstance(report_rel, str) or not report_rel:
        return None, None
    rel = Path(report_rel)
    if rel.is_absolute() or ".." in rel.parts:
        return None, f"declared gate report path is not contained: {report_rel}"
    target = project_path / rel
    if not target.is_file():
        return None, f"declared gate report was not produced: {rel}"
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as error:
        return None, f"declared gate report is unreadable ({type(error).__name__})"
    if not isinstance(data, dict):
        return None, "declared gate report is not a JSON object"
    for key in ("skipped", "not_run"):
        value = data.get(key)
        if value is None:
            continue
        if not isinstance(value, list):
            return None, f"declared gate report field '{key}' is not a list"
        for item in value:
            if (not isinstance(item, dict) or not isinstance(item.get("check"), str)
                    or not item["check"] or not isinstance(item.get("reason"), str)
                    or not item["reason"]):
                return None, (f"declared gate report field '{key}' needs "
                              "{check, reason} objects with non-empty strings")
    for item in data.get("artifacts") or []:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            return None, "declared gate report field 'artifacts' needs objects with a name"
    return data, None


def read_hosted_evidence(project_path: Path, head: str | None) -> tuple[dict | None, str | None]:
    """Read `<project>/.hub/hosted-evidence.json`, written by the project.

    AEH never calls GitHub, so a contract that requires hosted CI can only be
    satisfied when the project records the hosted run locally (the template
    `templates/hosted-evidence.sh` does that). The evidence is kept in its own
    file so the project's gate can rewrite its coverage report without erasing
    it, and it is accepted only for the exact revision being verified: hosted
    proof for another commit is STALE, not evidence.

    Returns (evidence, note). `note` explains why a present file was not used.
    """
    path = project_path / ".hub" / "hosted-evidence.json"
    if not path.is_file():
        return None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as error:
        return None, f"hosted evidence is unreadable ({type(error).__name__})"
    if not isinstance(data, dict):
        return None, "hosted evidence is not a JSON object"
    recorded = data.get("head")
    if not isinstance(recorded, str) or not recorded:
        return None, "hosted evidence names no revision"
    if not head:
        return None, "hosted evidence cannot be bound: the current revision is unknown"
    if recorded != head:
        return None, (f"hosted evidence is for another revision "
                      f"({recorded[:12]} vs {head[:12]})")
    runner = data.get("runner")
    if not isinstance(runner, dict) or runner.get("kind") != "hosted":
        return None, "hosted evidence does not name a hosted runner"
    return data, None


def require_project(reg: dict, slug: str) -> dict:
    key = resolve_key(reg, slug)
    if key is None:
        known = ", ".join(sorted(reg["projects"])) or "(none)"
        die(f"unknown project '{slug}'. Registered: {known}", kind="missing_project")
    return reg["projects"][key]


def entry_path(entry: dict) -> Path:
    return Path(entry["path"]).expanduser()


# ----------------------------------------------------------------- commands

def cmd_add(args, cfg, reg):
    reason = validate_slug(args.slug)
    if reason:
        die(f"invalid slug '{args.slug}': {reason}")
    existing = resolve_key(reg, args.slug)
    if existing is not None and existing != args.slug:
        die(f"slug '{args.slug}' conflicts with registered project '{existing}'. "
            "Slugs are matched case-insensitively; register one spelling only.")
    path = Path(args.path).expanduser()
    if not path.is_absolute():
        die("path must be absolute")
    if not path.exists():
        die(f"path does not exist: {path}")
    if not path.is_dir():
        die(f"path is not a directory: {path}")
    if is_within_hub(path):
        die(f"refusing to register a path inside the Hub repository: {path}\n"
            "       project source repositories live under the workspace root.")

    ws = Path(cfg["workspace_root"]).expanduser()
    rel = path.relative_to(ws) if inside(path, ws) else None
    if rel is None:
        print(f"hub: warning: {path} is outside workspace root {ws}", file=sys.stderr)

    entry = {
        "slug": args.slug,
        "path": str(path),
        "workspace_root": str(ws),
        "in_workspace_root": rel is not None,
        "remote": args.remote,
        "state": args.state,
        "verify": args.verify,
        "acceptance": args.acceptance,
        "release": getattr(args, "release", None),
        "registered_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    g = git_state(path)
    entry["is_repo"] = g["is_repo"]
    reg["projects"][args.slug] = entry
    save_registry(cfg, reg)
    ok(f"registered '{args.slug}' -> {path}")
    ok(f"  git repo: {g['is_repo']}  branch: {g['branch']}  commit: {g['commit']}")
    if args.verify:
        ok(f"  verify: {args.verify}")
    if args.acceptance:
        ok(f"  acceptance: {args.acceptance}")
    if getattr(args, "release", None):
        ok(f"  release: {args.release}")
    return 0


def cmd_new(args, cfg, reg):
    reason = validate_slug(args.slug)
    if reason:
        die(f"invalid slug '{args.slug}': {reason}")
    ws = Path(cfg["workspace_root"]).expanduser()
    ws.mkdir(parents=True, exist_ok=True)
    if is_within_hub(ws):
        die(f"workspace root is inside the Hub repository: {ws}")
    target = ws / args.slug
    if target.exists():
        entries = list(target.iterdir()) if target.is_dir() else []
        if not entries:
            die(f"{target} exists and is an empty directory — refusing to claim it "
                "silently; remove it or choose another slug.")
        die(f"collision: {target} already exists and is NOT empty "
            f"({len(entries)} entries). Nothing was changed.")
    target.mkdir(parents=True)
    ok(f"created empty workspace: {target}")
    # Slugs may contain spaces and punctuation, so the suggested commands are
    # shell-quoted rather than interpolated raw.
    quoted = shlex.quote(str(target))
    ok(f"  next: git -C {quoted} init -b main")
    ok(f"  then:  python3 scripts/hub.py add --slug={shlex.quote(args.slug)} --path {quoted}")
    return 0


def cmd_remove(args, cfg, reg):
    """Drop a registry entry. Never touches the project directory.

    Unregistering is not deleting. The workspace path may hold a real
    repository, so this command only edits registry metadata and says so.
    """
    key = resolve_key(reg, args.slug)
    if key is None:
        known = ", ".join(sorted(reg["projects"])) or "(none)"
        die(f"unknown project '{args.slug}'. Registered: {known}", kind="missing_project")
    entry = reg["projects"][key]
    path = entry.get("path", "(unknown)")

    del reg["projects"][key]
    save_registry(cfg, reg)

    ok(f"unregistered '{key}' (registry entry removed)")
    ok(f"  project directory untouched and still on disk: {path}")
    if path != "(unknown)" and not Path(path).exists():
        ok(f"  note: {path} no longer exists; only the registry entry was removed")

    # Recorded verification results are indexed by slug, so dropping the entry
    # orphans them. Say what happened instead of leaving a silent gap.
    records = verification_path()
    if records.exists():
        retained = True
        try:
            retained = any(json.loads(line).get("slug") == key
                           for line in records.read_text(encoding="utf-8").splitlines()
                           if line.strip())
        except (OSError, ValueError):
            retained = None
        if retained:
            if args.forget:
                kept = [ln for ln in records.read_text(encoding="utf-8").splitlines()
                        if ln.strip()
                        and json.loads(ln).get("slug") != key]
                records.write_text(
                    ("\n".join(kept) + "\n") if kept else "", encoding="utf-8")
                ok(f"  discarded recorded verification results for '{key}' (--forget)")
            else:
                ok(f"  recorded verification results for '{key}' are kept in "
                   f"{records} but no longer reachable from the registry; "
                   f"use --forget to discard them")

    if args.forget:
        ok("  --forget removes registry metadata and verification records only. "
           "It never deletes a project directory, a Git repository or project files.")
    return 0


def cmd_list(args, cfg, reg):
    if not reg["projects"]:
        ok("no projects registered")
        return 0
    rows = [("SLUG", "STATE", "REPO", "PATH", "VERIFY")]
    for slug in sorted(reg["projects"]):
        e = reg["projects"][slug]
        rows.append((
            slug, e.get("state", "-"), "yes" if e.get("is_repo") else "no",
            e.get("path", "-"), "yes" if e.get("verify") else "no",
        ))
    w = [max(len(r[i]) for r in rows) for i in range(5)]
    for i, r in enumerate(rows):
        ok("  ".join(c.ljust(w[j]) for j, c in enumerate(r)).rstrip())
        if i == 0:
            ok("  ".join("-" * x for x in w))
    return 0


def cmd_where(args, cfg, reg):
    e = require_project(reg, args.slug)
    p = entry_path(e)
    if not p.exists():
        die(f"registered path no longer exists: {p}")
    print(p)
    return 0


def verification_path() -> Path:
    return HUB_ROOT / ".hub" / "verification.jsonl"


def git_verification_identity(path: Path) -> dict:
    g = git_state(path)
    if not g["is_repo"]:
        return {"branch": None, "head": None, "dirty": None, "dirty_files": None}
    _, head = run(["git", "rev-parse", "HEAD"], path)
    return {
        "branch": g["branch"],
        "head": head.strip() or None,
        "dirty": g["dirty"],
        "dirty_files": g["dirty_files"],
    }


def append_verification_evidence(slug: str, path: Path, command: str,
                                 state: str, exit_code: int, *,
                                 before: dict | None = None,
                                 after: dict | None = None,
                                 duration_s: float | None = None,
                                 gate: str = "verify",
                                 contract_hash: str | None = None,
                                 report: dict | None = None,
                                 report_error: str | None = None) -> Path:
    """Append one runtime record. Records are never rewritten or deleted.

    A result is meaningful only for the exact source state it names. The
    record therefore carries the command text, the source identity before AND
    after the run, the hash of the quality contract in force, and the parsed
    gate report when the project produced one.
    """
    identity = git_verification_identity(path)
    record = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "slug": slug,
        "gate": gate,
        "result": state,
        "exit_code": exit_code,
        "duration_s": duration_s,
        "command": command,
        "source_before": before,
        "source_after": after,
        "verify_sha256": sha256_text(command),
        "commit_sha256": sha256_text(
            f"{gate}\x00{command}\x00{contract_hash or ''}"),
        "contract_sha256": contract_hash,
        "report": report,
        "report_error": report_error,
        "hub": "schema=1",
        **identity,
    }
    target = verification_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
    fd = os.open(target, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o660)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            view = memoryview(payload)
            while view:
                written = os.write(fd, view)
                view = view[written:]
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
    return target


def latest_verification(slug: str, gate: str = "verify") -> tuple[dict | None, int, str | None]:
    latest = None
    malformed = 0
    read_error = None
    for target in (HUB_ROOT / "evidence" / "verification.jsonl", verification_path()):
        try:
            with target.open(encoding="utf-8") as stream:
                for line in stream:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        malformed += 1
                        continue
                    # Records written before gates existed carry no "gate" key and
                    # describe the source gate only.
                    if (isinstance(record, dict) and record.get("slug") == slug
                            and record.get("gate", "verify") == gate):
                        latest = record
        except FileNotFoundError:
            continue
        except (OSError, UnicodeError) as error:
            read_error = type(error).__name__
    return latest, malformed, read_error


def verification_freshness(record: dict, path: Path, command: str | None = None) -> str:
    current = git_verification_identity(path)
    if command is not None and record.get("verify_sha256") != sha256_text(command):
        return "STALE; verification command changed"
    before = record.get("source_before")
    after = record.get("source_after")
    if before is not None:
        # Two distinct defects: the tree moved while the gate ran (before vs
        # after), and an internally inconsistent record whose embedded
        # before-identity contradicts its own top-level identity. Both make the
        # result unbindable to a revision. Before source_after existed only the
        # second test ran, and it read the record against itself for every
        # well-formed record.
        if isinstance(after, dict) and before != after:
            return "historical; source identity changed during verification"
        if before != {k: record.get(k) for k in before}:
            return "historical; source identity changed during verification"
    recorded_head = record.get("head")
    if not current["head"] or not recorded_head:
        return "historical; Git source identity unavailable"
    if current["head"] != recorded_head:
        return f"STALE; HEAD changed to {current['head'][:12]}"
    if record.get("dirty") is True:
        if current["dirty"] is True:
            return "historical; verification ran on a dirty tree and exact tree identity is unknown"
        return "historical; verification ran on a dirty tree"
    if current["dirty"] is True:
        return "STALE; current working tree has uncommitted changes"
    if current["dirty"] is not False or record.get("dirty") is not False:
        return "historical; clean working tree identity unavailable"
    return f"CURRENT for clean HEAD {current['head'][:12]}"


STALE_AFTER_DAYS = 60

# Directories that legitimately live at the Hub root and are never project
# source. Anything else with a nested layout must be justified, not assumed.
TRACKED_FILE_CHECK_EXEMPT = frozenset()


def registry_staleness(entry: dict, git: dict) -> str:
    """Describe why a registry entry may no longer reflect reality.

    A registry label is never evidence, so this is a prompt to re-check, not a
    judgement. It never blocks and never executes project code.
    """
    reasons = []
    registered_at = entry.get("registered_at")
    if registered_at:
        try:
            days = (datetime.now(UTC) - datetime.fromisoformat(registered_at)).days
            if days > STALE_AFTER_DAYS:
                reasons.append(f"entry registered {days} day(s) ago")
        except (TypeError, ValueError):
            reasons.append("registered_at is unparseable")
    commit_date = git.get("commit_date")
    if commit_date:
        try:
            days = (datetime.now(UTC) - datetime.fromisoformat(commit_date)).days
            if days > STALE_AFTER_DAYS * 3:
                reasons.append(f"repository has not committed in {days} day(s)")
        except (TypeError, ValueError):
            pass
    if not entry.get("verify"):
        reasons.append("no verification command configured")
    return "; ".join(reasons) if reasons else "no staleness signal"


def dedupe(values: list[str]) -> list[str]:
    seen, out = set(), []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gate_entry(entry: dict, path: Path, gate: str, required_names: list[str],
               contract_hash: str | None) -> dict:
    """One registry gate as a verdict, never as a score.

    Verdict rules, in order: an unconfigured gate is NOT_VERIFIED; an unreadable
    ledger is BLOCKED; a malformed ledger with no valid record is FAILED;
    FAIL/ERROR are FAILED; TIMEOUT is BLOCKED; UNVERIFIED is NOT_VERIFIED; a
    changed contract or a moved command is STALE; a declared-but-missing gate
    report is BLOCKED (coverage unknown); a malformed report is FAILED; a
    required gate named in skipped/not_run is BLOCKED even when result is PASS;
    only then, PASS with CURRENT freshness is VERIFIED.
    """
    required = set(required_names)
    out = {
        "gate": gate, "command": entry.get(gate), "required": bool(required),
        "verdict": "NOT_VERIFIED", "reason": None, "recorded_result": None,
        "head": None, "recorded_at": None, "duration_s": None, "freshness": None,
        "skipped": [], "not_run": [], "report_error": None,
    }
    command = entry.get(gate)
    if not command:
        out["reason"] = "gate is not configured in the registry"
        return out

    record, malformed, read_error = latest_verification(entry["slug"], gate)
    if read_error:
        out["verdict"], out["reason"] = "BLOCKED", f"evidence ledgers could not be read ({read_error})"
        return out
    if record is None:
        if malformed:
            out["verdict"] = "FAILED"
            out["reason"] = f"ledger holds no valid record; ignored {malformed} malformed line(s)"
        else:
            out["reason"] = "no recorded result"
        return out

    report = record.get("report") if isinstance(record.get("report"), dict) else None
    out.update({
        "recorded_result": record.get("result"),
        "head": record.get("head"),
        "recorded_at": record.get("timestamp"),
        "duration_s": record.get("duration_s"),
        "report_error": record.get("report_error"),
        "freshness": verification_freshness(record, path, command),
    })
    if report:
        out["skipped"] = normalise_checks(report.get("skipped"))
        out["not_run"] = normalise_checks(report.get("not_run"))

    if contract_hash and record.get("contract_sha256") and record["contract_sha256"] != contract_hash:
        out["verdict"] = "STALE"
        out["reason"] = "the quality contract changed after this record was written"
        return out
    if record.get("report_error"):
        message = record["report_error"]
        if "was not produced" in message:
            out["verdict"], out["reason"] = "BLOCKED", message
        else:
            out["verdict"], out["reason"] = "FAILED", message
        return out

    result = record.get("result")
    if result != "PASS":
        verdict, reason = {
            "FAIL": ("FAILED", "the gate ran and failed"),
            "ERROR": ("FAILED", "the gate could not complete (ERROR)"),
            "TIMEOUT": ("BLOCKED", "the gate exceeded its wall-clock bound"),
            "BLOCKED": ("BLOCKED", "the gate recorded BLOCKED"),
            "UNVERIFIED": ("NOT_VERIFIED", "the gate recorded UNVERIFIED"),
        }.get(result, ("NOT_VERIFIED", f"unrecognised recorded result {result!r}"))
        out["verdict"], out["reason"] = verdict, reason
        return out

    blocked = [c for c in out["skipped"] + out["not_run"] if c["check"] in required]
    if blocked:
        named = "; ".join(f"{c['check']} ({c['reason']})" for c in blocked)
        out["verdict"] = "BLOCKED"
        out["reason"] = f"required gate(s) reported skipped or not run: {named}"
        return out
    if not str(out["freshness"]).startswith("CURRENT"):
        out["verdict"], out["reason"] = "STALE", str(out["freshness"])
        return out
    out["verdict"], out["reason"] = "VERIFIED", None
    return out


def collected_artifacts(records: dict) -> dict:
    found: dict = {}
    for record in records.values():
        report = record.get("report") if isinstance(record, dict) else None
        if not isinstance(report, dict):
            continue
        for item in report.get("artifacts") or []:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                found[item["name"]] = item
    return found


def release_readiness(slug: str, path: Path, contract: dict | None,
                      contract_verdict: str, contract_problems: list[str],
                      gate_entries: list[dict], source: dict) -> dict:
    """What would still stop this revision from shipping, as named conditions.

    VERIFIED needs all of: a valid contract that declares release gates; the
    verify and acceptance gates VERIFIED at the current HEAD; no required gate
    skipped or not run; hosted-runner evidence plus a pushed HEAD when the
    contract requires hosted CI; and every declared artifact backed by a PASS
    record with a valid sha256 (recomputed against the file when it is present
    on this host).
    """
    problems: list[tuple[str, str]] = []
    missing: list[str] = []
    records = {name: latest_verification(slug, name)[0]
               for name in ("verify", "acceptance", "release")}
    by_gate = {gate["gate"]: gate for gate in gate_entries}

    if contract_verdict == "FAILED":
        problems.append(("FAILED", "quality contract is invalid: "
                         + "; ".join(contract_problems)))
        missing.append("valid quality contract")
    elif contract is None:
        problems.append(("NOT_VERIFIED", "; ".join(contract_problems)
                         or "no quality contract"))
        missing.append("quality contract")
    elif not (contract.get("release_gates") or []):
        problems.append(("NOT_VERIFIED", "quality contract declares no release_gates"))
        missing.append("release_gates")

    for name in ("verify", "acceptance"):
        gate = by_gate.get(name)
        if gate is None or not gate["command"]:
            problems.append(("NOT_VERIFIED", f"{name} gate is not configured in the registry"))
            missing.append(f"{name} gate")
            continue
        if gate["verdict"] != "VERIFIED":
            problems.append((gate["verdict"],
                             f"{name} gate is {gate['verdict']}: {gate['reason'] or 'no reason recorded'}"))
            if gate["verdict"] == "NOT_VERIFIED":
                missing.append(f"{name} evidence at HEAD")

    if contract is not None:
        required = set(contract.get("required_gates") or [])
        for name, gate in by_gate.items():
            for item in gate["skipped"] + gate["not_run"]:
                if item["check"] in required:
                    problems.append(("BLOCKED",
                                     f"required gate {item['check']} was not run in {name}: {item['reason']}"))

        if contract.get("hosted_ci") == "required":
            if source.get("ahead"):
                problems.append(("BLOCKED",
                                 f"HEAD is {source['ahead']} commit(s) ahead of its upstream; "
                                 "hosted CI cannot cover this revision"))
            runner = None
            for name in ("acceptance", "verify"):
                record = records.get(name)
                report = record.get("report") if isinstance(record, dict) else None
                if isinstance(report, dict) and isinstance(report.get("runner"), dict):
                    runner = report["runner"]
                    break
            if runner is None or runner.get("kind") != "hosted":
                problems.append(("BLOCKED", "no hosted-runner evidence recorded for this revision"))

    collected = collected_artifacts(records)
    artifacts: list[dict] = []
    for item in (contract.get("artifacts") if contract else None) or []:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        found = collected.get(item["name"])
        row = {
            "name": item["name"], "found": found is not None,
            "sha256": found.get("sha256") if found else None,
            "result": found.get("result") if found else None,
            "platform": (found or {}).get("platform") or item.get("platform"),
            "local_check": None,
        }
        if found is None:
            problems.append(("BLOCKED", f"declared artifact has no evidence: {item['name']}"))
            missing.append(f"artifact {item['name']}")
            artifacts.append(row)
            continue
        if item.get("hash_required", True) and not is_sha256(found.get("sha256")):
            problems.append(("FAILED", f"artifact {item['name']} has no valid sha256"))
        if found.get("result") != "PASS":
            problems.append(("FAILED", f"artifact {item['name']} did not record a PASS result"))
        reported_path = found.get("path")
        if isinstance(reported_path, str) and reported_path:
            rel = Path(reported_path)
            if rel.is_absolute() or ".." in rel.parts:
                problems.append(("FAILED", f"artifact {item['name']} path escapes the project: {reported_path}"))
            elif (path / rel).is_file():
                actual = sha256_file(path / rel)
                matches = is_sha256(found.get("sha256")) and actual == found["sha256"].lower()
                row["local_check"] = {"checked": True, "matches": matches, "actual_sha256": actual}
                if not matches:
                    problems.append(("FAILED", f"artifact {item['name']} hash does not match the file on disk"))
            else:
                row["local_check"] = {"checked": False, "matches": None,
                                      "reason": "artifact file not present on this host"}
        artifacts.append(row)

    verdict = combine_verdicts(*[v for v, _ in problems]) if problems else "VERIFIED"
    return {
        "verdict": verdict,
        "reasons": [reason for _, reason in problems],
        "missing": dedupe(missing),
        "artifacts": artifacts,
        "evidence": {name: {"verdict": gate["verdict"], "head": gate["head"]}
                     for name, gate in by_gate.items()},
    }


def assess_data(entry: dict, cfg: dict) -> dict:
    """Read-only assessment across areas. Never runs project code."""
    slug, path = entry["slug"], entry_path(entry)
    data: dict = {
        "slug": slug, "path": str(path),
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "overall": {}, "areas": {},
    }

    git = git_state(path)
    sync = git_sync(path) if git["is_repo"] else {"upstream": None, "ahead": None, "behind": None}
    notes: list[str] = []
    if git["is_repo"]:
        source_verdict = "VERIFIED"
        if git["dirty"]:
            notes.append(f"{git['dirty_files']} uncommitted change(s): evidence cannot bind to a revision")
        if sync["upstream"] is None:
            notes.append("no upstream configured for this branch")
        elif sync["ahead"]:
            notes.append(f"HEAD is {sync['ahead']} commit(s) ahead of {sync['upstream']}: "
                         "hosted CI does not cover this revision")
        if sync["behind"]:
            notes.append(f"HEAD is {sync['behind']} commit(s) behind {sync['upstream']}")
        if git["dirty"]:
            source_verdict = "NOT_VERIFIED"
    elif git.get("git_error"):
        source_verdict = "BLOCKED"
        notes.append(f"Git identity unavailable ({git['git_error']})")
    else:
        source_verdict = "NOT_VERIFIED"
        notes.append("not a Git repository: no history evidence available")
    source = {
        "verdict": source_verdict, "head": git.get("commit"), "branch": git.get("branch"),
        "upstream": sync["upstream"], "ahead": sync["ahead"], "behind": sync["behind"],
        "dirty": git.get("dirty"), "dirty_files": git.get("dirty_files"), "notes": notes,
    }

    contract, contract_path, contract_problems = load_contract(path)
    contract_hash = contract_sha256(Path(contract_path)) if contract_path else None
    if contract is not None:
        contract_verdict = "VERIFIED"
    elif contract_path:
        contract_verdict = "FAILED"
    else:
        contract_verdict = "NOT_VERIFIED"

    required_by_command: dict[str, list[str]] = {}
    if contract is not None:
        for name, spec in (contract.get("gates") or {}).items():
            if name in (contract.get("required_gates") or []):
                required_by_command.setdefault(spec["gate"], []).append(name)

    gate_entries = []
    for name in ("verify", "acceptance", "release"):
        if name == "release" and not entry.get("release"):
            continue
        gate_entries.append(gate_entry(entry, path, name,
                                       required_by_command.get(name, []), contract_hash))

    data["areas"]["source_integrity"] = source
    data["areas"]["gates"] = gate_entries
    data["areas"]["contract"] = {
        "verdict": contract_verdict, "path": contract_path,
        "schema_version": (contract or {}).get("schema"),
        "required_gates": list((contract or {}).get("required_gates") or []),
        "release_gates": list((contract or {}).get("release_gates") or []),
        "hosted_ci": (contract or {}).get("hosted_ci"),
        "problems": contract_problems,
    }
    data["areas"]["release_readiness"] = release_readiness(
        slug, path, contract, contract_verdict, contract_problems, gate_entries, source)

    usage_file = path / cfg.get("usage_file", ".hub/usage.jsonl")
    if not usage_file.is_file():
        data["areas"]["cost"] = {
            "verdict": "NOT_VERIFIED", "availability": "unavailable", "records": None,
            "reason": f"no {cfg.get('usage_file', '.hub/usage.jsonl')}: measurement has not started",
        }
    else:
        summary = usage_summary(usage_file)
        accepted = summary.get("accepted") or 0
        data["areas"]["cost"] = {
            "verdict": "VERIFIED" if accepted else "NOT_VERIFIED",
            "availability": "available", "records": summary.get("records"),
            "accepted": accepted,
            "reason": None if accepted else "records exist but no accepted task is recorded yet",
        }

    areas = data["areas"]
    # `cost` is a process measurement, not a product claim: a project with no
    # usage ledger is not thereby an unverified product. It keeps its own
    # verdict, is reported as an advisory, and is deliberately not combined
    # into the overall product verdict. Everything else is.
    verdicts = [areas["source_integrity"]["verdict"], areas["contract"]["verdict"],
                areas["release_readiness"]["verdict"]]
    verdicts += [gate["verdict"] for gate in gate_entries]
    blockers: list[str] = list(areas["source_integrity"]["notes"]) \
        if areas["source_integrity"]["verdict"] != "VERIFIED" else []
    # The release-readiness reasons already name every unmet contract, gate,
    # hosted-runner and artifact condition, so they are the single source of
    # blocker text; repeating the raw area reasons here would duplicate them.
    blockers += areas["release_readiness"]["reasons"]
    advisories = [f"cost: {areas['cost']['reason']}"] if areas["cost"].get("reason") else []

    next_actions = []
    for gate in gate_entries:
        if gate["verdict"] == "NOT_VERIFIED" and gate["command"]:
            next_actions.append(f"python3 scripts/hub.py verify {slug} --gate {gate['gate']}")
    if areas["contract"]["verdict"] != "VERIFIED":
        next_actions.append(f"add {path}/.aeh/quality.json from templates/quality-contract.json")
    if areas["release_readiness"]["verdict"] != "VERIFIED":
        next_actions.append(f"python3 scripts/hub.py release-check {slug}")

    data["overall"] = {
        "verdict": combine_verdicts(*verdicts),
        "blockers": dedupe(blockers),
        "advisories": dedupe(advisories),
        "next_actions": dedupe(next_actions),
    }
    return data


def release_data(entry: dict, cfg: dict) -> dict:
    """Release-readiness view, derived from the same assessment as `assess`."""
    assessment = assess_data(entry, cfg)
    readiness = assessment["areas"]["release_readiness"]
    return {
        "slug": entry["slug"],
        "verdict": readiness["verdict"],
        "reasons": readiness["reasons"],
        "missing": readiness["missing"],
        "evidence": readiness["evidence"],
        "artifacts": readiness["artifacts"],
        "source_integrity": assessment["areas"]["source_integrity"],
        "contract": assessment["areas"]["contract"],
    }


def cmd_status(args, cfg, reg):
    e = require_project(reg, args.slug)
    p = entry_path(e)
    if not p.exists():
        die(f"registered path no longer exists: {p}")

    ok(f"project : {e['slug']}")
    ok(f"path    : {p}")
    ok(f"label   : {e.get('state')}  (registry label, not evidence)")

    g = git_state(p)
    if g["is_repo"]:
        ok(f"git     : branch={g['branch']} commit={g['commit']} "
           f"dirty={g['dirty']} ({g['dirty_files']} changed files)")
        ok(f"last    : {g['commit_date']} {g['subject']}")
    elif g.get("git_error"):
        ok(f"git     : UNAVAILABLE ({g['git_error']}; repository identity not established)")
    else:
        ok("git     : NOT a git repository (no history evidence available)")

    def report_gate(label: str, command: str | None, gate: str) -> None:
        """Print one gate's configured command and its latest recorded result."""
        if not command:
            ok(f"{label:<7} : not configured — this gate is UNVERIFIED, not assumed")
            return
        ok(f"{label:<7} : configured -> `{command}`")
        record, malformed, evidence_error = latest_verification(e["slug"], gate)
        if evidence_error:
            ok(f"{label:<7}   result  : UNAVAILABLE (evidence could not be read: {evidence_error})")
        elif record is None and malformed:
            ok(f"{label:<7}   result  : UNAVAILABLE (no valid record; ignored {malformed} malformed line(s))")
        elif record is None:
            ok(f"{label:<7}   result  : NO RECORDED RESULT (run `hub.py verify "
               f"{e['slug']} --gate {gate}` to execute and record it)")
        else:
            result = record.get("result", "UNKNOWN")
            timestamp = record.get("timestamp", "time unavailable")
            ok(f"{label:<7}   result  : {result} (verified {timestamp}; "
               f"{verification_freshness(record, p, command)})")
        if malformed:
            ok(f"{label:<7}   evidence: ignored {malformed} malformed record(s)")

    report_gate("verify", e.get("verify"), "verify")
    report_gate("accept", e.get("acceptance"), "acceptance")
    if e.get("release"):
        report_gate("release", e.get("release"), "release")

    age = "unknown"
    if g["commit_date"]:
        try:
            dt = datetime.fromisoformat(g["commit_date"])
            age = f"{(datetime.now(UTC) - dt).days} day(s) since last commit"
        except ValueError:
            pass
    ok(f"freshness: {age}")
    ok(f"registry : {registry_staleness(e, g)}")
    return 0


def verdict_exit(verdict: str) -> int:
    """0 only for VERIFIED; 1 for FAILED; 3 for everything unestablished."""
    return {"VERIFIED": 0, "FAILED": 1}.get(verdict, 3)


def print_assessment(data: dict) -> None:
    areas = data["areas"]
    ok(f"project : {data['slug']}")
    ok(f"path    : {data['path']}")
    ok(f"overall : {data['overall']['verdict']}")
    source = areas["source_integrity"]
    ok(f"  source-integrity : {source['verdict']:<12} "
       f"branch={source['branch']} head={source['head']} "
       f"ahead={source['ahead']} behind={source['behind']} dirty={source['dirty']}")
    for note in source["notes"]:
        ok(f"                     - {note}")
    for gate in areas["gates"]:
        detail = gate["reason"] or f"{gate['recorded_result']} at {gate['recorded_at']}"
        if gate["freshness"]:
            detail = f"{detail}; {gate['freshness']}"
        if gate["duration_s"] is not None:
            detail = f"{detail}; {gate['duration_s']}s"
        ok(f"  gate {gate['gate']:<12} : {gate['verdict']:<12} {detail}")
        for item in gate["skipped"]:
            ok(f"                     skipped: {item['check']} — {item['reason']}")
        for item in gate["not_run"]:
            ok(f"                     not run: {item['check']} — {item['reason']}")
    contract = areas["contract"]
    ok(f"  contract         : {contract['verdict']:<12} {contract['path'] or 'none'}")
    for problem in contract["problems"]:
        ok(f"                     - {problem}")
    readiness = areas["release_readiness"]
    ok(f"  release          : {readiness['verdict']:<12} "
       f"{len(readiness['reasons'])} unmet condition(s)")
    cost = areas["cost"]
    ok(f"  cost             : {cost['verdict']:<12} {cost.get('reason') or 'records present'}")
    if data["overall"]["blockers"]:
        ok("blockers:")
        for reason in data["overall"]["blockers"]:
            ok(f"  - {reason}")
    if data.get("overall", {}).get("advisories"):
        ok("advisories (not part of the product verdict):")
        for reason in data["overall"]["advisories"]:
            ok(f"  - {reason}")
    if data["overall"]["next_actions"]:
        ok("next actions:")
        for action in data["overall"]["next_actions"]:
            ok(f"  - {action}")


def cmd_assess(args, cfg, reg):
    """Read-only: read evidence and report verdicts. Runs no project code."""
    entry = require_project(reg, args.slug)
    path = entry_path(entry)
    if not path.is_dir():
        die(f"registered path no longer exists: {path}")
    data = assess_data(entry, cfg)
    print_assessment(data)
    ok("")
    ok("read-only: no project code was executed and nothing was written.")
    return verdict_exit(data["overall"]["verdict"])


def cmd_release_check(args, cfg, reg):
    """Read-only release readiness. A green build is not a release verdict."""
    entry = require_project(reg, args.slug)
    path = entry_path(entry)
    if not path.is_dir():
        die(f"registered path no longer exists: {path}")
    data = release_data(entry, cfg)
    ok(f"project : {data['slug']}")
    ok(f"verdict : {data['verdict']}")
    for name, evidence in data["evidence"].items():
        ok(f"  {name:<10} : {evidence['verdict']:<12} head={evidence['head']}")
    for artifact in data["artifacts"]:
        ok(f"  artifact {artifact['name']:<24} : "
           f"{artifact['result'] or 'no record'} sha256={artifact['sha256'] or 'none'}")
    if data["reasons"]:
        ok("unmet conditions:")
        for reason in data["reasons"]:
            ok(f"  - {reason}")
    if data["missing"]:
        ok("missing:")
        for item in data["missing"]:
            ok(f"  - {item}")
    ok("")
    ok("read-only: a release verdict requires the contract, this exact source "
       "and the artifact evidence; it never authorises publication by itself.")
    return verdict_exit(data["verdict"])


def acquire_verify_lock() -> tuple[int | None, str | None]:
    """Non-blocking exclusive lock: one heavy gate at a time on this host.

    Two agents building the same or different projects at once is how a
    workstation runs out of RAM and disk and how a benchmark becomes noise.
    Returns (fd, None) when acquired, (None, reason) otherwise; the caller must
    release the fd with flock(LOCK_UN) and os.close.
    """
    lock = HUB_ROOT / ".hub" / "verify.lock"
    try:
        lock.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(lock, os.O_RDWR | os.O_CREAT, 0o660)
    except OSError as error:
        return None, type(error).__name__
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None, "busy"
    return fd, None


def cmd_verify(args, cfg, reg):
    """Explicitly execute a project's verification command.

    This runs project-supplied code. It is never reached from `status`,
    `assess` or `release-check`.
    """
    e = require_project(reg, args.slug)
    p = entry_path(e)
    if not p.exists():
        die(f"registered path no longer exists: {p}")
    gate = getattr(args, "gate", "verify")
    cmd_str = e.get(gate)
    if not cmd_str:
        ok(f"{gate:<7} : not configured for '{e['slug']}' — nothing to run")
        ok("result  : UNVERIFIED, not assumed")
        return 3

    ok(f"project : {e['slug']}")
    ok(f"path    : {p}")
    ok(f"gate    : {gate}")
    ok(f"command : `{cmd_str}`")
    ok(f"bound   : {args.timeout}s wall clock, {VERIFY_MAX_CAPTURE} bytes output, "
       "whole process group killed on timeout, exclusive .hub/verify.lock")
    ok("note    : this executes code from the project repository")
    ok("")

    lock_fd, lock_reason = acquire_verify_lock()
    if lock_fd is None:
        if lock_reason == "busy":
            ok("result  : BLOCKED (another verification is already running)")
        else:
            ok(f"result  : BLOCKED (could not take the verify lock: {lock_reason})")
        ok("note    : nothing was executed; retry when the other gate finishes")
        return 3

    try:
        contract, contract_path, _ = load_contract(p)
        contract_hash = contract_sha256(Path(contract_path)) if contract_path else None
        report_rel = contract.get("report") if isinstance(contract, dict) else None
        if contract_path:
            ok(f"contract: {contract_path}")

        before = git_verification_identity(p)
        started = time.monotonic()
        state, rc, out = run_verify(cmd_str, p, timeout=args.timeout)
        duration = round(time.monotonic() - started, 3)
        after = git_verification_identity(p)
        report, report_error = read_gate_report(p, report_rel)

        # Hosted evidence lives in its own file so the project's gate can rewrite
        # its own coverage report without erasing proof of a hosted run. It is
        # merged only when it names the exact revision being verified.
        hosted, hosted_note = read_hosted_evidence(p, (before or {}).get("head"))
        if hosted:
            merged = dict(report) if isinstance(report, dict) else {}
            merged["runner"] = hosted["runner"]
            merged["hosted_evidence"] = {
                key: hosted[key] for key in ("head", "repo", "branch", "workflow",
                                             "conclusion", "recorded_at")
                if hosted.get(key) is not None
            }
            report = merged
            ok(f"hosted  : run {hosted['runner'].get('run_id')} recorded for this revision")
        elif hosted_note:
            ok(f"hosted  : {hosted_note}")

        effective = state
        if report_error:
            effective = "BLOCKED" if "was not produced" in report_error else "FAILED"
        elif state == "PASS" and isinstance(contract, dict) and isinstance(report, dict):
            required = set(contract.get("required_gates") or [])
            blocked = [c for c in normalise_checks(report.get("skipped"))
                       + normalise_checks(report.get("not_run")) if c["check"] in required]
            if blocked:
                effective = "BLOCKED"
                ok("required gate(s) reported skipped or not run:")
                for item in blocked:
                    ok(f"          {item['check']} — {item['reason']}")

        if effective == state:
            ok(f"result  : {state} (exit {rc})")
        else:
            ok(f"result  : {effective} (command exited {rc}, recorded as {state})")
        if before != after:
            ok("warning : the source identity changed during the run; the record is "
               "historical and cannot certify the current revision")
        if report_error:
            ok(f"report  : {report_error}")

        try:
            evidence = append_verification_evidence(
                e["slug"], p, cmd_str, effective, rc, before=before, after=after,
                duration_s=duration, gate=gate, contract_hash=contract_hash,
                report=report, report_error=report_error)
            ok(f"evidence: recorded in {evidence}")
        except OSError as error:
            ok(f"evidence: NOT SAVED ({type(error).__name__}); result remains in this run output")
        if out:
            for line in out.splitlines()[-15:]:
                ok(f"          {line}")
        return {"PASS": 0, "FAIL": 1, "TIMEOUT": 124, "ERROR": 2, "BLOCKED": 3}[effective]
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


def cmd_usage(args, cfg, reg):
    e = require_project(reg, args.slug)
    p = entry_path(e)
    usage_rel = cfg.get("usage_file", ".hub/usage.jsonl")
    f = p / usage_rel
    if not f.exists():
        print(f"hub: no usage record for '{args.slug}' at {f}")
        print("      this is UNAVAILABLE, not zero. Nothing was inferred.")
        return 0

    summary = usage_summary(f)
    ok(f"usage for '{args.slug}'  ({f})")
    ok(f"  tasks recorded : {summary['records']}")
    ok(f"  malformed lines : {summary['malformed_lines']}")
    for key in ("accepted", "acceptance_unknown", "first_pass_accepted", "first_pass_unknown"):
        ok(f"  {key}: {summary[key]}")
    for field, values in summary["metrics"].items():
        ok(f"  {field}:")
        for quality, value in values.items():
            ok(f"      {quality}: {value if value is not None else 'UNAVAILABLE'}")
    ok("  note: 'unavailable' = the provider/session did not expose the value.")
    ok("        No number above was invented.")
    return 0


def cmd_report(args, cfg, reg):
    ok(f"Agentic Engineering Hub — {HUB_ROOT}")
    ok(f"workspace root: {cfg['workspace_root']}")
    ok("")
    ok(f"{'SLUG':<24} {'LABEL':<10} {'REPO':<5} {'DIRTY':<6} {'COMMIT':<9} VERIFY")
    for slug in sorted(reg["projects"]):
        e = reg["projects"][slug]
        p = entry_path(e)
        if not p.exists():
            ok(f"{slug:<24} {e.get('state', '-'):<10} {'-':<5} {'-':<6} {'-':<9} MISSING PATH")
            continue
        g = git_state(p)
        ok(f"{slug:<24} {e.get('state', '-'):<10} "
           f"{('yes' if g['is_repo'] else 'no'):<5} "
           f"{g['dirty_files'] if g['is_repo'] else '-'!s:<6} "
           f"{g['commit'] or '-'!s:<9} {e.get('verify') or 'NONE (unverified)'}")
    ok("")
    ok("Labels are registry labels only. Run `hub.py status <slug>` for real evidence.")
    return 0


def cmd_doctor(args, cfg, reg):
    problems = []
    # A checkout that is not the owner's host has no workspace root and no
    # registered project paths. That is an environment fact, not a defect: the
    # Hub's own gate must run in CI and in a fresh clone without claiming to
    # have verified projects it never saw. When the workspace root IS present,
    # a missing project path is a real problem again.
    notes: list[str] = []

    ws = Path(cfg["workspace_root"]).expanduser()
    if is_within_hub(ws):
        problems.append(f"workspace root is inside the Hub repository: {ws}")
    workspace_present = ws.exists()
    if not workspace_present:
        notes.append(f"workspace root {ws} is not present in this environment: "
                     "registered project paths are NOT VERIFIED here")

    for slug, e in reg["projects"].items():
        reason = validate_slug(slug)
        if reason:
            problems.append(f"{slug}: unusable slug: {reason}")
        p = Path(e["path"]).expanduser()
        if not p.exists():
            if workspace_present:
                problems.append(f"{slug}: path missing: {p}")
            else:
                notes.append(f"{slug}: path not present here: {p}")
            continue
        if is_within_hub(p):
            problems.append(f"{slug}: project source is inside the Hub repo: {p}")
        if e.get("remote") and not e["remote"].startswith(("http", "git@", "ssh://")):
            problems.append(f"{slug}: suspicious remote URL: {e['remote']}")

    # Lookups fold case, so entries differing only by case are ambiguous.
    folded: dict[str, str] = {}
    for slug in reg["projects"]:
        key = slug.casefold()
        if key in folded:
            problems.append(f"'{slug}' and '{folded[key]}' differ only by case; "
                            "lookups would be ambiguous")
        folded[key] = slug

    ev = HUB_ROOT / "evidence"
    if not ev.is_dir():
        problems.append("evidence/ directory missing")

    # Tracked-file check: no project source may be tracked in the Hub repo.
    rc, out = run(["git", "ls-files"], HUB_ROOT)
    if rc == 0:
        tracked = out.splitlines()
        for line in tracked:
            if line.startswith(("Projects/", "workspaces/")) or "/.hub/" in line:
                problems.append(f"Hub tracks workspace content: {line}")
        # Untracked project source is the same violation with a lower paper
        # trail: `git add -A` would turn it into tracked workspace content, and
        # nothing in the tree would stop that.
        rc2, ignored = run(["git", "status", "--porcelain", "--untracked-files=normal"],
                           HUB_ROOT)
        if rc2 == 0:
            for line in ignored.splitlines():
                if not line.startswith("?? "):
                    continue
                rel = line[3:].strip()
                if not rel or rel in ("", "."):
                    continue
                name = rel.rsplit("/", 1)[-1]
                if name in TRACKED_FILE_CHECK_EXEMPT:
                    continue
                # Framework directories and dot-directories belong to the Hub
                # itself (docs, skills, contracts, tool config). Anything else
                # with a nested layout could be project source copied in.
                if (rel.startswith(("docs/", "templates/", "evals/", "scripts/",
                                    "tests/", "evidence/", "ops/", "contracts/",
                                    "skills/"))
                        or rel.startswith(".") or "/" not in rel):
                    continue
                problems.append(
                    f"untracked top-level directory that may hold project source: {rel} "
                    f"(move it under the workspace root, or ignore it explicitly)")

    # The Hub's own verification surface: a contract with no schema, negative
    # fixtures with no home, or an unwritable ledger would make every downstream
    # verdict unfounded. These are structural checks, not project execution.
    schema = HUB_ROOT / "contracts" / "quality.schema.json"
    if not schema.is_file():
        problems.append("contracts/quality.schema.json missing: the quality contract "
                        "has no declared schema")
    else:
        try:
            json.loads(schema.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeError) as error:
            problems.append(f"contracts/quality.schema.json is unreadable ({type(error).__name__})")

    conformance = HUB_ROOT / "tests" / "fixtures" / "conformance"
    if not conformance.is_dir():
        problems.append("tests/fixtures/conformance/ missing: AEH's own negative "
                        "fixtures have no home")
    else:
        try:
            if not any(child.is_dir() for child in conformance.iterdir()):
                problems.append("tests/fixtures/conformance/ holds no fixture directory")
        except OSError as error:
            problems.append(f"tests/fixtures/conformance/ unreadable ({type(error).__name__})")

    for script in ("conformance.py", "selfcheck.sh", "quality_contract.py"):
        if not (HUB_ROOT / "scripts" / script).is_file():
            problems.append(f"scripts/{script} missing")

    # A missing `.hub/` is normal in a fresh checkout: `verify` creates it when
    # it appends a record. Only a directory that exists and cannot be written,
    # or a Hub root that cannot be written at all, is a defect. (Before this,
    # `doctor` failed every fresh clone, which would have made CI red on the
    # first run for the wrong reason.)
    hub_state = HUB_ROOT / ".hub"
    if hub_state.exists():
        if not hub_state.is_dir() or not os.access(hub_state, os.W_OK):
            problems.append(f"{hub_state} is not writable: verification records cannot be appended")
    elif not os.access(HUB_ROOT, os.W_OK):
        problems.append(f"{HUB_ROOT} is not writable: verification records cannot be appended")

    if getattr(args, "json", False):
        emit_json("doctor", {"problems": problems, "notes": notes,
                             "project_count": len(reg["projects"])},
                  success=not problems)
        return int(bool(problems))
    for note in notes:
        print(f"  NOTE  {note}")
    if problems:
        for p in problems:
            print(f"  FAIL  {p}")
        print("RESULT: FAILURES PRESENT")
        return 1
    ok(f"  PASS  config, registry ({len(reg['projects'])} project(s)), "
       f"workspace containment, evidence dir")
    print("RESULT: ALL PASS" + (f" ({len(notes)} environment note(s))" if notes else ""))
    return 0


# --------------------------------------------------------------------- main

def emit_json(command: str, data: dict, *, success: bool = True):
    print(json.dumps({"schema_version": 1, "ok": success, "command": command,
                      "data": data}, sort_keys=True))


def project_snapshot(entry: dict) -> dict:
    path = entry_path(entry)
    if not path.is_dir():
        die(f"registered path no longer exists: {path}")

    def gate(gate_name: str) -> dict:
        command = entry.get(gate_name)
        record, malformed, error = latest_verification(entry["slug"], gate_name)
        return {"command": command, "record": record,
                "freshness": verification_freshness(record, path, command)
                if record and command else "UNVERIFIED",
                "malformed_lines": malformed, "read_error": error}

    return {"slug": entry["slug"], "path": str(path), "label": entry.get("state"),
            "git": git_state(path),
            "verification": gate("verify"), "acceptance": gate("acceptance")}


def usage_summary(path: Path) -> dict:
    if not path.exists():
        return {"availability": "unavailable", "records": None, "metrics": {}}
    rows, malformed = [], 0
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            if not isinstance(row, dict):
                raise TypeError("not an object")
            rows.append(row)
        except (ValueError, TypeError):
            malformed += 1
    fields = ("input_tokens", "output_tokens", "cost_usd", "tool_calls",
              "repeated_attempts", "wall_time_s", "rework_events",
              "verification_retries", "escaped_defects", "policy_violations",
              "ux_findings_reopened", "time_to_verified_outcome_s")
    metrics = {}
    for field in fields:
        totals = {"measured": None, "estimated": None}
        unavailable = 0
        for row in rows:
            value, quality = row.get(field), row.get("measurement", "unavailable")
            if (quality in totals and isinstance(value, (int, float))
                    and not isinstance(value, bool) and value >= 0
                    and (not isinstance(value, float) or math.isfinite(value))):
                totals[quality] = (totals[quality] or 0) + value
            else:
                unavailable += 1
        metrics[field] = {**totals, "unavailable_records": unavailable}
    return {"availability": "available", "records": len(rows),
            "malformed_lines": malformed, "metrics": metrics,
            "accepted": sum(row.get("accepted") is True for row in rows),
            "acceptance_unknown": sum(not isinstance(row.get("accepted"), bool) for row in rows),
            "first_pass_accepted": sum(row.get("first_pass_accepted") is True for row in rows),
            "first_pass_unknown": sum(not isinstance(row.get("first_pass_accepted"), bool) for row in rows)}


def cmd_json(args, cfg, reg):
    if args.cmd == "doctor":
        return cmd_doctor(args, cfg, reg)
    if args.cmd == "remove":
        # A mutation, not a read-only snapshot: run it and report the same way
        # as the text path rather than pretending to emit a registry view.
        return cmd_remove(args, cfg, reg)
    if args.cmd == "list":
        data = {"projects": [reg["projects"][s] for s in sorted(reg["projects"])]}
    elif args.cmd == "report":
        data = {"workspace_root": cfg["workspace_root"], "projects": []}
        for slug in sorted(reg["projects"]):
            entry = reg["projects"][slug]
            data["projects"].append(project_snapshot(entry) if entry_path(entry).is_dir()
                                    else {"slug": slug, "availability": "missing_path"})
    else:
        entry = require_project(reg, args.slug)
        path = entry_path(entry)
        if not path.is_dir():
            die(f"registered path no longer exists: {path}")
        if args.cmd == "where":
            data = {"slug": entry["slug"], "path": str(path)}
        elif args.cmd == "status":
            data = project_snapshot(entry)
        elif args.cmd == "assess":
            data = assess_data(entry, cfg)
            emit_json("assess", data, success=data["overall"]["verdict"] == "VERIFIED")
            return verdict_exit(data["overall"]["verdict"])
        elif args.cmd == "release-check":
            data = release_data(entry, cfg)
            emit_json("release-check", data, success=data["verdict"] == "VERIFIED")
            return verdict_exit(data["verdict"])
        else:
            data = usage_summary(path / cfg["usage_file"])
            data["slug"] = entry["slug"]
    emit_json(args.cmd, data)
    return 0

def main() -> int:
    ap = argparse.ArgumentParser(prog="hub.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add", help="register a project")
    p.add_argument("--slug", required=True,
                   help="project name; any case, spaces and punctuation, "
                        "but no path separator, control character or leading '-'")
    p.add_argument("--path", required=True)
    p.add_argument("--remote")
    p.add_argument("--state", default="active")
    p.add_argument("--verify", help="shell command returning 0 on success")
    p.add_argument("--acceptance",
                   help="shell command for the project's admission gate "
                        "(build/test/package); may be slower than --verify")
    p.add_argument("--release",
                   help="shell command for the release gate (hosted CI / artifact "
                        "identity); proves the shipped artifact, not the source")
    p.set_defaults(fn=cmd_add)

    p = sub.add_parser("new", help="create an empty project workspace")
    p.add_argument("--slug", required=True,
                   help="project name; also used verbatim as the directory name "
                        "under the workspace root")
    p.set_defaults(fn=cmd_new)

    p = sub.add_parser("list", help="list registered projects")
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("remove",
                       help="drop a registry entry; never touches the project directory")
    p.add_argument("slug", help="project name (any case)")
    p.add_argument("--forget", action="store_true",
                   help="also discard that project's recorded verification results")
    p.set_defaults(fn=cmd_remove)

    p = sub.add_parser("where", help="resolve slug to workspace path")
    p.add_argument("slug")
    p.set_defaults(fn=cmd_where)

    p = sub.add_parser("status", help="read-only Git and recorded verification status")
    p.add_argument("slug")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("assess",
                       help="read-only quality-evidence assessment (five verdicts)")
    p.add_argument("slug")
    p.set_defaults(fn=cmd_assess)

    p = sub.add_parser("release-check",
                       help="read-only release readiness: contract, exact source, artifact")
    p.add_argument("slug")
    p.set_defaults(fn=cmd_release_check)

    p = sub.add_parser("verify", help="explicitly run a project's verification")
    p.add_argument("slug")
    p.add_argument("--gate", choices=("verify", "acceptance", "release"), default="verify",
                   help="verify runs the cheap source gate; acceptance runs the "
                        "project's admission gate (may compile, test and package); "
                        "release runs the release-gate command when registered")
    p.add_argument("--timeout", type=int, default=RUN_TIMEOUT,
                   help=f"wall-clock bound in seconds (max {VERIFY_MAX_TIMEOUT})")
    p.set_defaults(fn=cmd_verify)

    p = sub.add_parser("usage", help="per-task efficiency/cost record")
    p.add_argument("--slug", required=True, help="project name (any case)")
    p.set_defaults(fn=cmd_usage)

    p = sub.add_parser("report", help="aggregate hub view")
    p.set_defaults(fn=cmd_report)

    p = sub.add_parser("doctor", help="hub self-check")
    p.set_defaults(fn=cmd_doctor)

    for name in ("list", "where", "status", "assess", "release-check", "report",
                 "usage", "doctor", "remove"):
        sub.choices[name].add_argument("--json", action="store_true",
                                      help="emit versioned structured output")

    args = ap.parse_args()
    try:
        cfg = load_config()
        reg = load_registry(cfg)
        if getattr(args, "json", False):
            return cmd_json(args, cfg, reg)
        return args.fn(args, cfg, reg)
    except SystemExit as error:
        if getattr(args, "json", False):
            emit_json(args.cmd, {"kind": getattr(error, "kind", "invalid_input"),
                                "message": getattr(error, "message", "Invalid request")}, success=False)
        return error.code
    except (OSError, ValueError, TypeError) as error:
        if getattr(args, "json", False):
            emit_json(args.cmd, {"kind": "invalid_data", "message": type(error).__name__},
                      success=False)
        else:
            print(f"hub: error: invalid data ({type(error).__name__})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
