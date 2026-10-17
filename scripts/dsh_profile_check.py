#!/usr/bin/env python3
"""Check that the DSH profile still composes, and flag models that hide a trap.

Why: on 2026-10-17 a new session failed every turn with HTTP 400 because the
`opencode-go` model entry declared no reasoning capability. The harness therefore
offered a "High" level and sent `reasoning_effort`/`thinking`, which the LiteLLM
`custom_openai` route rejects. Composing the profile proves the patch parses; the
warning surfaces a model whose reasoning capability is undeclared, which is the
configuration that caused it.

Read-only: it runs `dsh --dump-config` and reads the user patch. It never starts an
agent, sends a request or writes configuration.

`--dump-config` normalizes the profile root file, so it needs write access to the
profile directory. A sandboxed session has none: the write fails with EACCES and
the guard that was supposed to protect that session could not run (AEH-D021). When
the real directory is not writable, the same files are copied into a temporary
`DSH_HOME` (with `node_modules` symlinked) and composed there; the parse result is
identical and nothing outside the temporary directory is touched.

Usage:
  python3 scripts/dsh_profile_check.py [--profile web]

Exit codes: 0 profile composes (warnings may still be printed), 1 profile does not
compose, 2 the environment could not be read.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROFILE_DIR = Path.home() / ".dsh" / "profiles"

SANDBOX_NOTE = ("note: the profile directory is not writable here, so a copy was "
                "composed under a temporary DSH_HOME\n")


def _compose_in_temporary_home(dsh: str, profile: str) -> tuple[int, str]:
    """Compose a copy of the profile, for a session that cannot write the real one."""
    source = PROFILE_DIR / profile
    if not source.is_dir():
        return 2, f"profile directory not found: {source}"
    try:
        with tempfile.TemporaryDirectory(prefix="dsh-profile-check-") as tmp:
            home = Path(tmp) / "home"
            target = home / "profiles" / profile
            target.parent.mkdir(parents=True)
            shutil.copytree(source, target, symlinks=True,
                            ignore=shutil.ignore_patterns("node_modules"))
            modules = source / "node_modules"
            if modules.exists():
                (target / "node_modules").symlink_to(modules.resolve())
            env = dict(os.environ, DSH_HOME=str(home))
            result = subprocess.run([dsh, "--profile", profile, "--dump-config"],
                                    capture_output=True, text=True, timeout=120,
                                    env=env)
    except (OSError, subprocess.TimeoutExpired) as error:
        return 2, f"could not compose the profile: {type(error).__name__}"
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def compose(profile: str) -> tuple[int, str]:
    dsh = shutil.which("dsh")
    if not dsh:
        return 2, "dsh is not on PATH"
    if not os.access(PROFILE_DIR / profile, os.W_OK):
        code, output = _compose_in_temporary_home(dsh, profile)
        return code, SANDBOX_NOTE + output
    try:
        result = subprocess.run([dsh, "--profile", profile, "--dump-config"],
                                capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as error:
        return 2, f"could not compose the profile: {type(error).__name__}"
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0 and "EACCES" in output:
        # The permission bits looked writable but the sandbox denied the write.
        code, sandboxed = _compose_in_temporary_home(dsh, profile)
        return code, SANDBOX_NOTE + sandboxed
    return result.returncode, output


def undeclared_reasoning_models(patch: Path) -> list[str]:
    """Model ids in the user patch that do not declare `reasoningEfforts`.

    Only `- id:` entries nested inside a `models:` block are models; plugin
    entries at the top level are not.
    """
    if not patch.is_file():
        return []
    models: list[tuple[str, bool]] = []
    models_indent: int | None = None
    current: str | None = None
    declared = False

    def flush():
        if current is not None:
            models.append((current, declared))

    for line in patch.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if not stripped:
            continue
        if re.match(r"^models:\s*$", stripped):
            flush()
            current, declared = None, False
            models_indent = indent
            continue
        entry = re.match(r"^- id:\s*(\S+)", stripped)
        if entry:
            if models_indent is not None and indent > models_indent:
                flush()
                current, declared = entry.group(1), False
            else:
                flush()
                current, declared = None, False
            continue
        if models_indent is not None and indent <= models_indent:
            flush()
            current, declared = None, False
            models_indent = None
            continue
        if current is not None and stripped.startswith("reasoningEfforts:"):
            declared = True
    flush()
    return [name for name, declared in models if not declared]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default=os.environ.get("DSH_PROFILE", "web"))
    args = parser.parse_args()

    code, output = compose(args.profile)
    if code == 2:
        print(output, file=sys.stderr)
        return 2

    for line in output.splitlines():
        if line.startswith("note:"):
            print(line)
    print(f"profile {args.profile!r}: compose exit {code}")
    if code != 0:
        tail = "\n".join(output.strip().splitlines()[-12:])
        print("the profile does not compose; a new session would fail to start:", file=sys.stderr)
        print(tail, file=sys.stderr)
        return 1

    patch = PROFILE_DIR / args.profile / "cordis.patch.yml"
    risky = undeclared_reasoning_models(patch)
    if risky:
        print("WARNING: these model entries declare no reasoningEfforts, so the harness")
        print("         inherits the installed capability and may send thinking")
        print("         parameters the route rejects (see AEH-D019):")
        for name in risky:
            print(f"           - {name}")
        print("         Declare the offered levels, or `false` for a route that rejects them.")
    else:
        print("every model entry in the user patch declares its reasoning capability")
    return 0


if __name__ == "__main__":
    sys.exit(main())
