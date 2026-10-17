#!/usr/bin/env python3
"""Skill trigger/latency/cost measurement harness.

Runs `opencode run --format json` for a set of labelled prompts and records what
is actually observable: token usage, cost, tool calls, wall time, and whether a
named skill was loaded.

Nothing is inferred. Fields the provider does not expose are recorded as
`unavailable`, never as zero.

Usage:
    python3 scripts/skill_eval.py --out evidence/before.json
    python3 scripts/skill_eval.py --out evidence/after.json --label after
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

HUB = Path(__file__).resolve().parent.parent
MODEL = "opencode/space-bunny-free"
TIMEOUT = 600

# label -> (prompt, [skills we EXPECT if the trigger is correct], [skills that
# would indicate contamination], cwd)
CASES = [
    # --- positive triggers: the named skill SHOULD load ---
    ("pos/verify-debug",
     "Our CI is red and I cannot tell why. Diagnose it properly.",
     ["verify-debug"], ["project-steward", "project-bootstrap"], "fixture"),
    ("pos/code-investigate",
     ("Where is the project registry written and read in this repo? "
      "Name the functions involved."),
     ["code-investigate"], [], "hub"),
    ("pos/security-review",
     "Before I commit this diff, review it for leaked secrets and unsafe dependencies.",
     ["security-review"], [], "fixture"),
    ("pos/skill-maintainer",
     "Add a new shared skill to our global library.",
     ["skill-maintainer"], [], "fixture"),
    ("pos/project-bootstrap",
     "I want to start a brand new small tool that converts CSV to JSON.",
     ["project-bootstrap"], ["project-steward"], "hub"),
    ("pos/project-steward",
     "Show the current progress of project abc-todo.",
     ["project-steward"], ["project-bootstrap"], "hub"),

    # --- negatives / near-misses: NO skill should load ---
    ("neg/trivial-listing",
     "List the top-level files in this repository and say what each one is for.",
     [], ["verify-debug", "project-bootstrap", "project-steward",
          "security-review", "skill-maintainer", "code-investigate"], "fixture"),
    ("neg/ordinary-read",
     ("Explain what DEFAULT_STORE is used for in src/abc_todo.py and whether "
      "changing its value would affect the tests."),
     [], ["project-bootstrap", "project-steward", "skill-maintainer"], "fixture"),
    ("neg/code-question",
     "What does the main() function in src/abc_todo.py do?",
     [], ["verify-debug", "project-steward"], "fixture"),
    ("neg/release-question",
     "Is abc-todo safe to delete? Just answer yes or no from what you can see.",
     [], ["project-steward", "project-bootstrap"], "hub"),
]


def cwd_for(kind: str) -> str:
    return str(HUB) if kind == "hub" else str(Path.home() / "Projects/abc-todo")


def run_case(label: str, prompt: str, expect: list[str],
             forbid: list[str], kind: str) -> dict:
    cmd = ["opencode", "run", "-m", MODEL, "--format", "json",
           "--dir", cwd_for(kind), prompt]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=TIMEOUT, check=False)
        raw, rc = r.stdout, r.returncode
    except subprocess.TimeoutExpired:
        return {"label": label, "error": f"timeout after {TIMEOUT}s"}
    wall = round(time.time() - t0, 1)

    tokens = {"input": None, "output": None, "reasoning": None,
              "cache_read": None, "total": None}
    cost = None
    tools: list[str] = []
    skill_calls: list[str] = []
    text = []

    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        part = ev.get("part") or {}
        ptype = part.get("type")
        if ev.get("type") == "step_finish" or ptype == "step-finish":
            # A multi-step run makes several API calls; each reports its own
            # usage. Sum them, otherwise long runs look artificially cheap.
            t = part.get("tokens") or {}
            for k in ("input", "output", "reasoning", "total"):
                if isinstance(t.get(k), int):
                    tokens[k] = (tokens[k] or 0) + t[k]
            cache = t.get("cache") or {}
            if isinstance(cache.get("read"), int):
                tokens["cache_read"] = (tokens["cache_read"] or 0) + cache["read"]
            if part.get("cost") is not None:
                cost = (cost or 0) + part["cost"]
        if ptype == "tool":
            name = part.get("tool") or part.get("name") or "?"
            tools.append(name)
            if name == "skill":
                # The invoked skill name lives in part.state.input.name.
                # `state` is a dict in some versions and a JSON string in
                # others, so accept both rather than silently reporting zero.
                state = part.get("state")
                if isinstance(state, str):
                    try:
                        state = json.loads(state)
                    except json.JSONDecodeError:
                        state = None
                inv = (state or {}).get("input") or {}
                skill_name = inv.get("name") if isinstance(inv, dict) else None
                if skill_name:
                    skill_calls.append(str(skill_name))
        if ptype == "text" and part.get("text"):
            text.append(part["text"])

    # Primary signal: the skill tool was actually invoked.
    loaded = sorted({s for s in skill_calls if s != "?"})
    # Secondary: the injected <skill_content> reached the model. This catches
    # a loader that injects the body without a visible tool call.
    injected = sorted({s for s in set(expect) | set(forbid)
                       if f'<skill_content name="{s}"' in raw})
    loaded = sorted(set(loaded) | set(injected))

    unexpected = [s for s in loaded if s in forbid]
    missing = [s for s in expect if s not in loaded]

    return {
        "label": label,
        "prompt": prompt,
        "cwd_kind": kind,
        "exit_code": rc,
        "wall_s": wall,
        "tokens": tokens,
        "cost_usd": cost if cost is not None else "unavailable",
        "tool_calls": len(tools),
        "tools": tools,
        "skills_loaded": loaded,
        "expected": sorted(expect),
        "missing_expected": missing,
        "unexpected_loaded": unexpected,
        "verdict": "correct" if not missing and not unexpected else "incorrect",
    }


SELFTEST_FIXTURE = HUB / "evidence/skill-load-fixture.jsonl"


def load_cases(path: Path) -> list[dict]:
    cases = []
    seen = set()
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        case = json.loads(line)
        if (not isinstance(case, dict)
                or not all(isinstance(case.get(k), str) and case[k]
                           for k in ("label", "input", "cwd_kind"))
                or case["cwd_kind"] not in ("hub", "fixture")
                or any(not isinstance(case.get(k), list)
                       or not all(isinstance(v, str) and v for v in case[k])
                       for k in ("expected_skills", "must_not_select",
                                 "required_behaviors", "forbidden_behaviors"))
                or case["label"] in seen
                or set(case["expected_skills"]) & set(case["must_not_select"])):
            raise ValueError(f"invalid case at line {number}")
        seen.add(case["label"])
        cases.append(case)
    if not cases:
        raise ValueError("empty corpus")
    return cases


def selftest() -> int:
    """Prove the parser can detect a skill load.

    A detection bug that always reports zero looks identical to 'skills never
    fire', so the harness is checked against a recorded stream that is known to
    contain exactly one real skill invocation.
    """
    if not SELFTEST_FIXTURE.exists():
        print(f"selftest: missing fixture {SELFTEST_FIXTURE}")
        return 1
    raw = SELFTEST_FIXTURE.read_text()
    found = []
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        part = (json.loads(line).get("part") or {})
        if part.get("type") != "tool" or part.get("tool") != "skill":
            continue
        state = part.get("state")
        if isinstance(state, str):
            try:
                state = json.loads(state)
            except json.JSONDecodeError:
                state = None
        inv = (state or {}).get("input") or {}
        if isinstance(inv, dict) and inv.get("name"):
            found.append(inv["name"])
    if found != ["security-review"]:
        print(f"selftest: FAIL expected ['security-review'], got {found}")
        return 1
    print("selftest: PASS (parser detects a known real skill load)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true",
                    help="verify skill-load detection against a recorded stream")
    ap.add_argument("--out")
    ap.add_argument("--cases", type=Path, help="versioned JSONL regression corpus")
    ap.add_argument("--check-fixtures", action="store_true",
                    help="validate corpus only; never call a model")
    ap.add_argument("--label", default="run")
    ap.add_argument("--only", help="substring filter on case label")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    cases = None
    if args.cases:
        try:
            cases = load_cases(args.cases)
        except (OSError, ValueError) as error:
            print(f"fixtures: FAIL ({error})")
            return 1
    if args.check_fixtures:
        if cases is None:
            ap.error("--check-fixtures requires --cases")
        print(f"fixtures: PASS ({len(cases)} contracts; live routing/output quality unverified)")
        return 0
    if not args.out:
        ap.error("--out required for live evaluation")

    results = []
    run_cases = CASES if cases is None else [
        (c["label"], c["input"], c["expected_skills"], c["must_not_select"], c["cwd_kind"])
        for c in cases]
    for label, prompt, expect, forbid, kind in run_cases:
        if args.only and args.only not in label:
            continue
        print(f"--> {args.label}: {label} ...", flush=True)
        res = run_case(label, prompt, expect, forbid, kind)
        if cases is not None:
            contract = next(c for c in cases if c["label"] == label)
            res["behavior_contract"] = {
                "required": contract["required_behaviors"],
                "forbidden": contract["forbidden_behaviors"],
                "assessment": "unavailable; requires observed output review"}
        print(f"    verdict={res.get('verdict')} skills={res.get('skills_loaded')} "
              f"tools={res.get('tool_calls')} wall={res.get('wall_s')}s "
              f"tok_in={res.get('tokens', {}).get('input')} "
              f"cost={res.get('cost_usd')}", flush=True)
        results.append(res)

    out = Path(args.out)
    if not out.is_absolute():
        out = HUB / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"label": args.label, "model": MODEL,
                               "results": results}, indent=2) + "\n")
    correct = sum(1 for r in results if r.get("verdict") == "correct")
    print(f"\n{correct}/{len(results)} routing verdicts correct -> {out}")
    return 0 if results and correct == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
