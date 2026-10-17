#!/usr/bin/env python3
"""Measure which skills each workspace's live agent session can actually load.

Why: a skill on disk is not a skill an agent can use. The 2026-10-17 audit found
eight shared procedures that no session could load and one workspace whose
sessions received no catalog at all. This script reads the live session
transcripts and reports, per workspace, the catalog the agent was actually given.

It is read-only: it decompresses session transcripts under ~/.dsh/sessions and
reads skill directories. It never starts an agent and never writes project state.

Usage:
  python3 scripts/skill_liveness.py            # table + exit code
  python3 scripts/skill_liveness.py --json

Exit codes: 0 every workspace exposes every expected skill, 1 a gap was measured,
2 the environment could not be read.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parent.parent
SESSIONS = Path.home() / ".dsh" / "sessions"
STORE = Path.home() / ".dsh" / "storages" / "workspace.json"
USER_SKILL_ROOT = Path.home() / ".dsh" / "skills"
# prompt-assist is a Hub-local candidate that the owner exposes to every session;
# keep it explicit so its absence is a visible finding rather than a surprise.
EXTRA_SHARED = ("prompt-assist",)


def read_registry() -> dict:
    try:
        return json.loads((HUB_ROOT / "projects" / "registry.json").read_text())
    except (OSError, json.JSONDecodeError):
        return {"projects": {}}


def shared_expected() -> set[str]:
    """Shared skills exposed on the user discovery root, plus the local candidate."""
    names = set()
    if USER_SKILL_ROOT.is_dir():
        for entry in USER_SKILL_ROOT.iterdir():
            if (entry / "SKILL.md").is_file() or (entry.is_symlink() and (entry / "SKILL.md").is_file()):
                names.add(entry.name)
    names.update(EXTRA_SHARED)
    return names


def project_expected(path: Path) -> set[str]:
    """Project-local skills: <repo>/.agents/skills/<name>/SKILL.md."""
    root = path / ".agents" / "skills"
    names = set()
    if root.is_dir():
        for entry in root.iterdir():
            if (entry / "SKILL.md").is_file():
                names.add(entry.name)
    return names


def session_dir_for(workspace: Path) -> Path | None:
    """The DSH session-store directory for a workspace path.

    DSH encodes a workspace path as "--" + path without its leading slash, with
    "/" replaced by "-", then "--" (for example --home-huou07-AEH--).
    """
    slug = "--" + str(workspace).lstrip("/").replace("/", "-") + "--"
    candidate = SESSIONS / slug
    return candidate if candidate.is_dir() else None


def newest_transcript(directory: Path, session_ids: list[str] | None = None) -> Path | None:
    """Newest transcript, preferring the workspace's own sessions over subagents.

    Subagent sessions are stored under a bare UUID directory and never carry the
    workspace catalog, so picking purely by mtime would measure the wrong file.
    """
    candidates = []
    if session_ids:
        for sid in session_ids:
            f = directory / sid / "session.v4.jsonl.zstd"
            if f.is_file():
                candidates.append(f)
    if not candidates:
        for session in directory.iterdir():
            f = session / "session.v4.jsonl.zstd"
            if f.is_file():
                candidates.append(f)
    if not candidates:
        return None
    return max(candidates, key=lambda f: f.stat().st_mtime)


def store_sessions_for(path: Path) -> list[str]:
    try:
        store = json.loads(STORE.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    for workspace in store.get("tables", {}).get("workspaces", {}).values():
        if Path(workspace.get("path", "")) == path:
            return list(workspace.get("sessionIds") or [])
    return []


def latest_catalog(transcript: Path) -> list[str] | None:
    """Names from the newest skill-catalog event in one transcript."""
    try:
        raw = subprocess.run(["zstd", "-dc", str(transcript)],
                             capture_output=True, check=True).stdout.decode("utf-8", "replace")
    except (OSError, subprocess.CalledProcessError):
        return None
    hits = [m.start() for m in re.finditer(r'"kind":"skill-catalog"', raw)]
    if not hits:
        return None
    idx = hits[-1]
    j = raw.find('"entries"', idx)
    if j < 0 or j - idx > 600:
        return []
    k = raw.find("[", j)
    depth = 0
    for i in range(k, min(len(raw), k + 30000)):
        if raw[i] == "[":
            depth += 1
        elif raw[i] == "]":
            depth -= 1
            if depth == 0:
                try:
                    return sorted(e.get("name", "?") for e in json.loads(raw[k:i + 1]))
                except json.JSONDecodeError:
                    return []
    return []


def main() -> int:
    as_json = "--json" in sys.argv
    if not SESSIONS.is_dir():
        print("cannot read the DSH session store at", SESSIONS, file=sys.stderr)
        return 2

    workspaces = [("AEH", HUB_ROOT)]
    for slug, entry in sorted(read_registry().get("projects", {}).items()):
        workspaces.append((slug, Path(entry["path"])))

    shared = shared_expected()
    rows = []
    gaps = 0
    for label, path in workspaces:
        expected = set(shared) | project_expected(path)
        directory = session_dir_for(path)
        seen = None
        transcript = None
        if directory:
            transcript = newest_transcript(directory, store_sessions_for(path))
            if transcript:
                seen = latest_catalog(transcript)
        if seen is None:
            missing = sorted(expected)
            rows.append({"workspace": label, "expected": len(expected), "live": None,
                         "missing": missing, "note": "no live catalog event in the newest transcript"})
            gaps += 1
            continue
        missing = sorted(expected - set(seen))
        extra = sorted(set(seen) - expected)
        rows.append({"workspace": label, "expected": len(expected), "live": len(seen),
                     "missing": missing, "extra": extra,
                     "transcript": str(transcript) if transcript else None})
        if missing:
            gaps += 1

    if as_json:
        print(json.dumps({"schema_version": 1, "shared_expected": sorted(shared),
                          "rows": rows, "workspaces_with_gaps": gaps}, indent=2, sort_keys=True))
        return 1 if gaps else 0

    print(f"shared skills on {USER_SKILL_ROOT}: {len(shared)} -> {sorted(shared)}")
    print(f"{'WORKSPACE':<10} {'EXPECTED':>8} {'LIVE':>5}  RESULT")
    for row in rows:
        live = "n/a" if row["live"] is None else str(row["live"])
        if row["missing"] and row["live"] is None:
            result = f"NO CATALOG (expected {len(row['missing'])} skills)"
        elif row["missing"]:
            result = "MISSING: " + ", ".join(row["missing"])
        else:
            result = "complete"
        if row.get("extra"):
            result += f" | extra: {', '.join(row['extra'])}"
        print(f"{row['workspace']:<10} {row['expected']:>8} {live:>5}  {result}")
    print()
    print("A skill on disk is not a skill an agent can load: this reads the catalog the")
    print("session was actually given. Missing entries are a discovery gap, not a doc gap.")
    return 1 if gaps else 0


if __name__ == "__main__":
    sys.exit(main())
