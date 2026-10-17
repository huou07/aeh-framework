#!/usr/bin/env bash
# Build a sanitised, publishable snapshot of the Hub.
#
# The Hub repository is private because it holds host-specific material: the
# registry with absolute paths, `ops/` administration scripts, `evidence/` with
# session and incident records, and the owner's runtime notes. None of that
# belongs on the internet. The *framework* does: the CLI, the quality standard,
# the contract schema, the conformance suite, the skills and the templates.
#
# This script produces that framework as a standalone tree and then proves it:
# the snapshot must pass `scripts/publication-check.sh` (no host-specific or
# secret material) AND `scripts/selfcheck.sh` (its own gate). A snapshot that
# cannot prove itself is not published.
#
#   bash scripts/build-public-snapshot.sh <target-dir>
#
# The target must be outside the Hub repository. Nothing in the Hub is modified.
set -uo pipefail

HUB_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_ARG="${1:?usage: build-public-snapshot.sh <target-dir>}"
# Resolve before creating anything: a refused build must leave no trace.
if command -v realpath >/dev/null 2>&1; then
  TARGET="$(realpath -m -- "$TARGET_ARG")"
else
  TARGET="$TARGET_ARG"
fi

if [[ "$TARGET" == "$HUB_ROOT" || "$TARGET" == "$HUB_ROOT"/* ]]; then
  echo "snapshot: target must not be inside the Hub repository" >&2
  exit 2
fi

mkdir -p "$TARGET"
TARGET="$(cd "$TARGET" && pwd)"

echo "building a public snapshot of $HUB_ROOT"
echo "target: $TARGET"
echo

# 1. Tracked files only: untracked scratch never reaches a publication.
git -C "$HUB_ROOT" archive HEAD | tar -x -C "$TARGET"

# 2. Remove what must not be published, and index what replaces it.
EXCLUDE_DIRS=(ops evidence .github)
EXCLUDE_FILES=(
  REPORT.md
  docs/normal-user-runtime.md
  docs/readiness-2026-10-17.md
)
for dir in "${EXCLUDE_DIRS[@]}"; do
  rm -rf "${TARGET:?}/$dir"
  echo "  excluded  $dir/"
done
for file in "${EXCLUDE_FILES[@]}"; do
  rm -f "${TARGET:?}/$file"
  echo "  excluded  $file"
done

# 3. Replace host-specific configuration with generic placeholders.
mkdir -p "$TARGET/projects" "$TARGET/ops" "$TARGET/evidence"
cat > "$TARGET/hub.config.json" <<'JSON'
{
  "$comment": "Public snapshot. Point workspace_root at your own projects directory.",
  "version": 1,
  "workspace_root": "/srv/aeh-workspace",
  "registry": "projects/registry.json",
  "usage_file": ".hub/usage.jsonl"
}
JSON
cat > "$TARGET/projects/registry.json" <<'JSON'
{
  "version": 1,
  "projects": {}
}
JSON
cat > "$TARGET/ops/README.md" <<'MD'
# Not part of the public snapshot

Host administration lives in the private Hub repository. It is deliberately not
published: it carries machine-specific service definitions, permission scripts
and network detail.
MD
cat > "$TARGET/evidence/README.md" <<'MD'
# Evidence — redacted for publication

The private Hub keeps dated evidence here: incident records, quality-gate
investigations and acceptance receipts, each carrying host paths, session
identifiers and run ids.

This snapshot publishes one file from it: `incidents.jsonl`, the ledger of
failures met while building the Hub, **redacted** — home paths, private
addresses, tunnel names, model-route names and session identifiers are replaced
with placeholders. The lessons are the valuable part and they are process
lessons, not host secrets. The schema is enforced by `tests/test_incidents.py`:
every entry names the failure, its root cause, the evidence and the guard that
keeps it from recurring.

The other evidence — quality-gate investigations and acceptance receipts — stays
private, because it describes the owner's machines, branches and run ids.
MD

# A redacted copy of the incident ledger: the process lessons are the point of
# publishing, the host detail is not.
HUB_ROOT="$HUB_ROOT" SNAPSHOT_ROOT="$TARGET" python3 - <<'PY'
import json
import os
import re
from pathlib import Path

source = Path(os.environ["HUB_ROOT"]) / "evidence" / "incidents.jsonl"
target = Path(os.environ["SNAPSHOT_ROOT"]) / "evidence" / "incidents.jsonl"
if not source.is_file():
    print("  note      no incident ledger to redact")
    raise SystemExit(0)

REDACTIONS = (
    (re.compile(r"/home/[a-z][a-z0-9_.-]*/"), "/<home>/"),
    (re.compile(r"/home/[a-z][a-z0-9_.-]*"), "/<home>"),
    (re.compile(r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "<private-ip>"),
    (re.compile(r"\b192\.168\.\d{1,3}\.\d{1,3}\b"), "<private-ip>"),
    (re.compile(r"\b172\.(?:1[6-9]|2[0-9]|3[01])\.\d{1,3}\.\d{1,3}\b"), "<private-ip>"),
    (re.compile(r"\butun\d+\b"), "<tunnel>"),
    (re.compile(r"\bwg\d+\b"), "<tunnel>"),
    (re.compile(r"wireguard", re.IGNORECASE), "<tunnel>"),
    (re.compile(r"litellm|omniroute|omni-route", re.IGNORECASE), "<model-route>"),
    (re.compile(r"[Vv][Pp][Nn][^.]{0,24}(?:port|PORT)"), "<private-network-detail>"),
    (re.compile(r"session-[0-9a-fA-F-]{8,}"), "<session>"),
    (re.compile(r"/srv/agent-workbench"), "<retired-root>"),
    (re.compile(r"\b(?:dsh-worker|codex-worker)\b"), "<worker-account>"),
)


def redact(value):
    if isinstance(value, str):
        for pattern, replacement in REDACTIONS:
            value = pattern.sub(replacement, value)
        return value
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


rows, changed = [], 0
for line in source.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    record = json.loads(line)
    redacted = redact(record)
    if redacted != record:
        changed += 1
    rows.append(json.dumps(redacted, ensure_ascii=False, sort_keys=True))
target.write_text("\n".join(rows) + "\n", encoding="utf-8")
print(f"  redacted  evidence/incidents.jsonl ({len(rows)} records, {changed} with host detail removed)")
PY

# 4. Rewrite the indexes so the snapshot is internally consistent: every link
#    resolves and every surviving document is listed.
SNAPSHOT_ROOT="$TARGET" python3 - <<'PY'
import os
import re
from pathlib import Path

root = Path(os.environ["SNAPSHOT_ROOT"])

def drop_table_rows(text: str, needles: tuple[str, ...]) -> tuple[str, list[str]]:
    kept, dropped = [], []
    for line in text.splitlines():
        if line.startswith("|") and any(n in line for n in needles):
            dropped.append(line)
            continue
        kept.append(line)
    return "\n".join(kept) + "\n", dropped

index = root / "docs" / "README.md"
text = index.read_text(encoding="utf-8")
text, dropped = drop_table_rows(text, (
    "normal-user-runtime.md",
    "readiness-2026-10-17.md",
))
for line in dropped:
    print("  index row dropped:", line.split("|")[1].strip())
index.write_text(text, encoding="utf-8")

# The archive section header now has no rows that point outside the snapshot;
# say what happened instead of leaving a dangling promise.
text = index.read_text(encoding="utf-8")
text = text.replace(
    "| [Writing AGENTS.md](writing-agents-md/README.md) | Preserved example | Historical shared policy and skill catalogs |",
    "| [Writing AGENTS.md](writing-agents-md/README.md) | Preserved example | Historical shared policy and skill catalogs |\n"
    "| ops/ and evidence/ | Not published | Host administration and dated host evidence stay in the private Hub |",
)
text = text.replace(
    "[REPORT](../REPORT.md) is a dated historical report\nwhose descriptions of Hub behaviour were superseded on 2026-10-14; the\ncommand-effect table in [hub-cli.md](hub-cli.md) wins on any disagreement.\n",
    "",
)
index.write_text(text, encoding="utf-8")

agents = root / "AGENTS.md"
text = agents.read_text(encoding="utf-8")
text, dropped = drop_table_rows(text, ("normal-user-runtime.md",))
for line in dropped:
    print("  AGENTS.md row dropped:", line.split("|")[1].strip())
text = text.replace(
    "| Dated proof / local runtime records | `evidence/` / ignored `.hub/`; never current acceptance by themselves |\n",
    "| Dated proof / local runtime records | ignored `.hub/` in your own checkout; never current acceptance by itself |\n",
)
text = text.replace(
    "- **This repository is private, and it holds host-specific material** — private\n"
    "  addresses, private-network detail, absolute home paths, `ops/` administration\n"
    "  scripts, incident and session records. Publishing it, pushing it to a public mirror or\n"
    "  changing its visibility requires `bash scripts/publication-check.sh` to pass;\n"
    "  on today's tree it fails by design (`evidence/incidents.jsonl` AEH-D024).",
    "- **This is the public framework snapshot of the Hub.** The private half — the\n"
    "  project registry with real paths, `ops/` host administration, and the dated\n"
    "  evidence that carries host paths, session ids and run ids — stays in the private\n"
    "  repository. `scripts/publication-check.sh` is the gate that keeps it that way; run\n"
    "  it before publishing anything from this tree.",
)
agents.write_text(text, encoding="utf-8")

readme = root / "README.md"
text = readme.read_text(encoding="utf-8")
note = (
    "# Agentic Engineering Hub\n\n"
    "> **This is the public framework snapshot.** [PUBLICATION.md](PUBLICATION.md) says\n"
    "> exactly what it contains and what deliberately stays in the private Hub: the\n"
    "> project registry with real paths, `ops/` host administration, and dated evidence.\n"
)
if text.startswith("# Agentic Engineering Hub\n"):
    text = note + text[len("# Agentic Engineering Hub\n"):]
    readme.write_text(text, encoding="utf-8")
    print("  README.md: added the public-snapshot notice")

# Every surviving document must keep resolving. Links that pointed into the
# excluded directories are redirected to the placeholder README that explains why
# the material is not published, instead of becoming dead links.
LINK = re.compile(r"\]\(([^)\s]+)\)")
DELINK = re.compile(
    r"\[([^\]]+)\]\((?:\.\./)*(?:docs/)?"
    r"(?:normal-user-runtime|readiness-2026-10-17)\.md(?:#[^)]*)?\)")
redirected = 0
delinked = 0


def redirect_excluded(target: str) -> str:
    global redirected
    path_part, _, anchor = target.partition("#")
    if not path_part or path_part.startswith(("http://", "https://", "mailto:")):
        return target
    normalised = path_part.replace("\\", "/")
    for directory in ("ops", "evidence"):
        if re.search(rf"(^|/){directory}/", normalised):
            depth = normalised.count("../")
            replacement = "../" * depth + f"{directory}/README.md"
            if replacement != path_part:
                redirected += 1
                return replacement + (f"#{anchor}" if anchor else "")
    return target


for document in sorted(root.rglob("*.md")):
    text = document.read_text(encoding="utf-8")
    delinked_text = DELINK.sub(lambda m: f"{m.group(1)} (not published)", text)
    if delinked_text != text:
        delinked += len(DELINK.findall(text))
    updated = LINK.sub(lambda m: "](" + redirect_excluded(m.group(1)) + ")", delinked_text)
    if updated != delinked_text:
        document.write_text(updated, encoding="utf-8")
    elif delinked_text != text:
        document.write_text(delinked_text, encoding="utf-8")
print(f"  redirected {redirected} link(s) into the excluded directories")
print(f"  de-linked {delinked} link(s) to documents the snapshot does not publish")
PY

cat > "$TARGET/PUBLICATION.md" <<'MD'
# What this repository is, and what it is not

This is the **public snapshot of the Agentic Engineering Hub (AEH)**: the
framework half of a control and knowledge workspace for developing software with
AI agents.

It contains the mechanisms and the standard:

- `scripts/hub.py` — project registry, read-only `assess` and `release-check`,
  bounded `verify`, and the five-verdict evidence model
- `scripts/quality_contract.py` + `contracts/quality.schema.json` — the
  project-owned quality contract, validated fail-closed with no shell commands
- `scripts/conformance.py` + `tests/fixtures/conformance/` — the adversarial
  suite that grades the Hub's own verdicts (16 negative fixtures)
- `scripts/publication-check.sh` — the gate this snapshot itself passed
- `docs/quality-standard.md` — the twelve product-quality criteria, the maturity
  ladder, release blockers and the three release questions
- `skills/`, `templates/`, `evals/`, `tests/` and the self gate
  `scripts/selfcheck.sh`

It deliberately does **not** contain the private half: the project registry with
real paths, `ops/` host administration, and `evidence/` with dated records that
carry host paths, session identifiers and run ids. Those stay in the private Hub
repository. `ops/` and `evidence/` here are placeholders explaining that.

## Verify it yourself

```bash
python3 -m unittest discover -s tests -q      # 140+ tests
python3 scripts/conformance.py                # 16 fixtures, no false-green
bash evals/structural-check.sh                # skill library and instructions
python3 scripts/hub.py doctor                 # config, containment, ledgers
bash scripts/selfcheck.sh                     # all of the above, one verdict
```

Nothing here needs a daemon, a database, a network or a paid service. The Hub
resolves projects through a registry you point at your own workspace; with an
empty registry every command still works and reports honestly.

## Regenerating this snapshot

From the private Hub repository:

```bash
bash scripts/build-public-snapshot.sh /tmp/aeh-public
```

The script excludes the private material, regenerates the indexes so every link
resolves, and refuses to finish unless the result passes both
`scripts/publication-check.sh` and `scripts/selfcheck.sh`.

Licence: GPL-3.0 (see `LICENSE`).
MD

echo
echo "verifying the snapshot"

if ! bash "$TARGET/scripts/publication-check.sh" "$TARGET"; then
  echo
  echo "SNAPSHOT=FAIL (host-specific material survived the exclusions)" >&2
  exit 1
fi

echo
if ! (cd "$TARGET" && bash scripts/selfcheck.sh >/tmp/aeh-snapshot-selfcheck.log 2>&1); then
  echo "SNAPSHOT=FAIL (the snapshot cannot pass its own gate)" >&2
  tail -25 /tmp/aeh-snapshot-selfcheck.log >&2
  exit 1
fi
grep -E "^(Ran|OK|fixtures:|RESULT:|AEH_SELFCHECK)" /tmp/aeh-snapshot-selfcheck.log | sed 's/^/  /'

echo
echo "SNAPSHOT=PASS  $TARGET"
echo "next: git -C $TARGET init -b main && commit && push to the public remote"
