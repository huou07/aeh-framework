#!/usr/bin/env python3
"""Selective legacy import with a hardcoded exclusion gate.

Copies only reviewed, allow-listed files from a legacy repository into a clean
destination repository, recording provenance. Old agent configuration and
credentials are NEVER copied, regardless of what is asked for.

Usage:
    python3 scripts/legacy_import.py --src LEGACY --dst DEST [--include PAT]...

Exit codes: 0 ok, 1 usage/error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

# Directories and files that must never cross the migration boundary.
NEVER_IMPORT_DIRS = {
    ".agents", ".opencode", ".codex", ".dsh", ".claude", ".vscode",
    ".github", ".idea", "node_modules", "__pycache__", ".venv", "venv",
    ".git",
}
NEVER_IMPORT_FILES = {
    "AGENTS.md", "CLAUDE.md", "GEMINI.md", ".env", ".env.local",
    "auth.json", "credentials.yaml", "credentials.json", ".netrc",
    "config.toml", "settings.json", "id_rsa", "id_ed25519",
}
# Skill/orchestration material, at any depth.
NEVER_IMPORT_SUFFIX = {".key", ".pem", ".pfx", ".p12", ".keystore"}

SECRET_NAME_HINTS = ("secret", "credential", "token", "password", "apikey",
                     "api_key", "cred", "private")


def blocked(path: Path, root: Path) -> str | None:
    rel = path.relative_to(root)
    parts = rel.parts
    if any(p in NEVER_IMPORT_DIRS for p in parts[:-1]):
        return f"agent/config directory in path: {'/'.join(parts[:-1])}"
    if any(p in NEVER_IMPORT_DIRS for p in parts):
        return f"agent/config directory: {'/'.join(parts)}"
    if parts[-1] in NEVER_IMPORT_FILES:
        return f"excluded filename: {parts[-1]}"
    if path.suffix.lower() in NEVER_IMPORT_SUFFIX:
        return f"secret material by extension: {path.suffix}"
    low = parts[-1].lower()
    if any(h in low for h in SECRET_NAME_HINTS):
        return f"secret-like filename: {parts[-1]}"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--include", action="append", default=[],
                    help="top-level dir/file prefix to import (default: none)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src, dst = Path(args.src).resolve(), Path(args.dst).resolve()
    if not src.is_dir():
        print(f"legacy-import: source not found: {src}", file=sys.stderr)
        return 1
    if src == dst or src in dst.parents or dst in src.parents:
        print("legacy-import: source and destination must not overlap", file=sys.stderr)
        return 1
    if not args.include or any(Path(i).is_absolute() or ".." in Path(i).parts
                               or i in ("", ".") for i in args.include):
        print("legacy-import: explicit contained --include paths required", file=sys.stderr)
        return 1
    if dst.exists() and not dst.is_dir():
        print("legacy-import: destination must be a directory", file=sys.stderr)
        return 1
    if dst.exists() and any(dst.iterdir()):
        print(f"legacy-import: destination not empty: {dst}", file=sys.stderr)
        return 1

    copied, skipped = [], []
    # os.walk (not rglob) so blocked directories are pruned rather than
    # reported file-by-file: git history is hundreds of files, one decision.
    for dirpath, dirnames, filenames in os.walk(src):
        rel_dir = Path(dirpath).relative_to(src)
        for d in sorted(n for n in dirnames
                        if n in NEVER_IMPORT_DIRS or (Path(dirpath) / n).is_symlink()):
            dirnames.remove(d)
            shown = str(rel_dir / d) if str(rel_dir) != "." else d
            reason = ("symlink directory is never imported" if (Path(dirpath) / d).is_symlink()
                      else "git history is never migrated" if d == ".git"
                      else "agent/config directory, contents never migrated")
            skipped.append({"path": f"{shown}/", "reason": reason})
        dirnames.sort()
        for fn in sorted(filenames):
            p = Path(dirpath) / fn
            if p.is_symlink():
                skipped.append({"path": str(p.relative_to(src)),
                                "reason": "symlinks are never imported"})
                continue
            if not p.is_file():
                continue
            rel = p.relative_to(src)
            reason = blocked(p, src)
            if (reason is None and args.include
                    and not any(rel == Path(i) or Path(i) in rel.parents for i in args.include)):
                reason = "not in --include allow-list"
            if reason is not None:
                skipped.append({"path": str(rel), "reason": reason})
                continue
            target = dst / rel
            if rel == Path("IMPORT-PROVENANCE.json"):
                skipped.append({"path": str(rel), "reason": "reserved provenance path"})
                continue
            if not args.dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, target)
            copied.append({
                "path": str(rel),
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                "size_bytes": p.stat().st_size,
                "destination": str(target),
                "origin": str(src / rel),
            })

    print(f"legacy-import: {len(copied)} file(s) copied, {len(skipped)} excluded")
    for c in copied:
        print(f"  COPY    {c['path']}")
    for s in skipped:
        print(f"  EXCLUDE {s['path']}  <- {s['reason']}")

    if not args.dry_run:
        dst.mkdir(parents=True, exist_ok=True)
        (dst / "IMPORT-PROVENANCE.json").write_text(json.dumps({
            "imported_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "source": str(src),
            "destination": str(dst),
            "history_imported": False,
            "note": "Agent config, credentials and git history are never imported.",
            "copied": copied,
            "excluded": skipped,
        }, indent=2) + "\n")
        if not (dst / ".git").exists():
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=dst, check=False)
            print(f"  git init at {dst} (clean history, provenance recorded)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
