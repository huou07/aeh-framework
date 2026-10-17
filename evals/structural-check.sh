#!/usr/bin/env bash
# Structural check for the shared skill library and instruction surface.
#
# Deterministic, zero-inference, read-only. Run from the Hub root:
#   bash evals/structural-check.sh
#
# Proves structure only: frontmatter validity, no duplicate skill discovery,
# a bounded global instruction file, and a resolvable toolchain. It does NOT
# prove that a model loads a skill, that routing is correct, or that any
# permission exists. Those need an authorized live run; see evals/README.md.
#
# Exit 0 when every check passes, 1 otherwise.
set -uo pipefail

failed=0

pass() { printf '  PASS  %s\n' "$1"; }
fail() { printf '  FAIL  %s\n' "$1" >&2; failed=1; }
warn() { printf '  WARN  %s\n' "$1"; }

# Resolve the Hub root from this script's own location: deterministic, and it
# holds even when Git is unavailable. The retired /srv/agent-workbench runtime
# is history; the preserved library, catalog and policy live in this repository.
HUB_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SHARED_SKILLS="${SHARED_SKILLS:-$HUB_ROOT/skills}"
SHARED_CATALOG="${SHARED_CATALOG:-$HUB_ROOT/docs/writing-agents-md/shared-skills-catalog.md}"
GLOBAL_AGENTS="${GLOBAL_AGENTS:-$HUB_ROOT/docs/writing-agents-md/shared-AGENTS.md}"
GLOBAL_AGENTS_MAX_LINES="${GLOBAL_AGENTS_MAX_LINES:-200}"

printf 'Structural check - %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# --- 1. Shared catalog and library exist -------------------------------------
if [[ -d "$SHARED_SKILLS" ]]; then
  pass "shared skill library present: $SHARED_SKILLS"
else
  fail "shared skill library missing: $SHARED_SKILLS (set SHARED_SKILLS)"
fi

if [[ -f "$SHARED_CATALOG" ]]; then
  pass "shared catalog present: $SHARED_CATALOG"
else
  fail "shared catalog missing: $SHARED_CATALOG (set SHARED_CATALOG)"
fi

# --- 2. Every catalog entry has exactly one canonical SKILL.md ---------------
if [[ -d "$SHARED_SKILLS" && -f "$SHARED_CATALOG" ]]; then
  catalogued=()
  while IFS= read -r name; do
    [[ -n "$name" ]] && catalogued+=("$name")
  done < <(sed -n 's/^| \([a-z][a-z0-9-]*\) |.*/\1/p' "$SHARED_CATALOG" | sort -u)

  ondisk=()
  while IFS= read -r path; do
    [[ -n "$path" ]] && ondisk+=("$path")
  done < <(find "$SHARED_SKILLS" -mindepth 2 -maxdepth 2 -name SKILL.md -printf '%h\n' \
    | while IFS= read -r d; do basename -- "$d"; done | sort -u)

  missing_body=()
  for name in "${catalogued[@]:-}"; do
    [[ -f "$SHARED_SKILLS/$name/SKILL.md" ]] || missing_body+=("$name")
  done
  if ((${#missing_body[@]})); then
    fail "catalogued skill(s) with no canonical SKILL.md: ${missing_body[*]}"
  else
    pass "all ${#catalogued[@]} catalogued skill(s) have a canonical SKILL.md"
  fi

  uncatalogued=()
  for name in "${ondisk[@]:-}"; do
    found=0
    for c in "${catalogued[@]:-}"; do [[ "$c" == "$name" ]] && found=1; done
    ((found)) || uncatalogued+=("$name")
  done
  if ((${#uncatalogued[@]})); then
    warn "skill(s) on disk but not in the catalog: ${uncatalogued[*]}"
  else
    pass "no skill directory is missing from the catalog"
  fi

  # Duplicate discovery: a skill reachable through two names under the library
  # would be loaded twice with no way for the agent to choose between them.
  dupes=$(find "$SHARED_SKILLS" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort | uniq -d)
  if [[ -n "$dupes" ]]; then
    fail "duplicate skill directories under $SHARED_SKILLS: $dupes"
  else
    pass "no duplicate skill directories (single discovery path per name)"
  fi
fi

# --- 3. Frontmatter validity for every SKILL.md ------------------------------
if [[ -d "$SHARED_SKILLS" ]]; then
  bad_fm=()
  while IFS= read -r skill; do
    dir="$(dirname -- "$skill")"
    name="$(basename -- "$dir")"
    if [[ "$(head -n1 -- "$skill")" != '---' ]]; then
      bad_fm+=("$name: missing opening --- frontmatter fence")
      continue
    fi
    closing="$(awk 'NR>1 && /^---[[:space:]]*$/ {print NR; exit}' "$skill")"
    if [[ -z "$closing" ]]; then
      bad_fm+=("$name: unterminated frontmatter")
      continue
    fi
    body="$(sed -n "2,$((closing - 1))p" "$skill")"
    grep -q '^name:' <<<"$body" || bad_fm+=("$name: no name field")
    grep -q '^description:' <<<"$body" || bad_fm+=("$name: no description field")
    declared="$(sed -n 's/^name:[[:space:]]*//p' <<<"$body" | head -n1 | tr -d '"'"'" | tr -d '\r')"
    if [[ -n "$declared" && "$declared" != "$name" ]]; then
      bad_fm+=("$name: frontmatter name '$declared' does not match the directory name")
    fi
  done < <(find "$SHARED_SKILLS" -mindepth 2 -maxdepth 2 -name SKILL.md | sort)
  if ((${#bad_fm[@]})); then
    for b in "${bad_fm[@]}"; do fail "frontmatter: $b"; done
  else
    pass "every shared SKILL.md has valid frontmatter matching its directory"
  fi

  # Rollback snapshots must not sit beside a canonical body: they are history,
  # and a loader that globs *.md would expose two versions of one skill.
  snaps="$(find "$SHARED_SKILLS" -mindepth 2 -maxdepth 2 -name 'SKILL.md.bak*' | sort)"
  if [[ -n "$snaps" ]]; then
    while IFS= read -r s; do
      [[ -n "$s" ]] && warn "rollback snapshot beside a canonical body: ${s#"$SHARED_SKILLS"/} (relocate outside the library; see evals/README.md)"
    done <<<"$snaps"
  else
    pass "no rollback snapshots beside canonical skill bodies"
  fi
fi

# --- 4. Hub-local candidate is not a copy of a shared canonical body ---------
# A promoted skill is exposed from the shared library by a symlink; that is one
# source, not a fork. Only a real file that is byte-identical to the canonical
# body is a duplicate, so symlinked entries are skipped here.
if [[ -n "${HUB_ROOT:-}" && -d "$HUB_ROOT/.opencode/skills" ]]; then
  copied=0
  while IFS= read -r local_skill; do
    [[ -L "$local_skill" ]] && continue
    local_dir="$(dirname -- "$local_skill")"
    [[ -L "$local_dir" ]] && continue
    name="$(basename -- "$local_dir")"
    if [[ -f "$SHARED_SKILLS/$name/SKILL.md" ]] && cmp -s "$local_skill" "$SHARED_SKILLS/$name/SKILL.md"; then
      fail "Hub-local skill '$name' is a byte-identical copy of the shared canonical body"
      copied=1
    fi
  done < <(find "$HUB_ROOT/.opencode/skills" -mindepth 2 -maxdepth 2 -name SKILL.md)
  ((copied)) || pass "no Hub-local skill duplicates a shared canonical body"
elif [[ -n "${HUB_ROOT:-}" ]]; then
  pass "no Hub-local skill directory (nothing to duplicate)"
fi

# --- 5. Global instruction file stays bounded -------------------------------
if [[ -f "$GLOBAL_AGENTS" ]]; then
  lines="$(wc -l <"$GLOBAL_AGENTS")"
  if ((lines <= GLOBAL_AGENTS_MAX_LINES)); then
    pass "global AGENTS.md is $lines lines (limit $GLOBAL_AGENTS_MAX_LINES)"
  else
    fail "global AGENTS.md is $lines lines, over the $GLOBAL_AGENTS_MAX_LINES limit; move detail into docs/"
  fi
else
  warn "global AGENTS.md not readable at $GLOBAL_AGENTS"
fi

# --- 6. Toolchain resolvable ------------------------------------------------
for tool in python3 git; do
  if command -v "$tool" >/dev/null 2>&1; then
    pass "toolchain: $tool -> $(command -v "$tool")"
  else
    fail "toolchain: $tool not found on PATH"
  fi
done

printf '\n'
if ((failed)); then
  printf 'RESULT: FAIL\n'
  exit 1
fi
printf 'RESULT: ALL PASS\n'
