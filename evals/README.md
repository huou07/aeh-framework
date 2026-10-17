# Skill regression corpus

Versioned inputs, expected routing and required/forbidden output behaviour.

```bash
python3 scripts/skill_eval.py --check-fixtures --cases evals/skill-contracts.jsonl
python3 scripts/skill_eval.py --selftest
bash evals/structural-check.sh
```

`structural-check.sh` is deterministic and read-only. It checks that every skill
named in the shared catalog has exactly one canonical `SKILL.md`, that frontmatter
is valid and agrees with its directory name, that no skill is reachable through
two discovery paths, that no Hub-local skill is a byte-identical copy of a shared
canonical body, that the global `AGENTS.md` stays inside a line budget, and that
the toolchain resolves. It warns about rollback snapshots sitting beside a
canonical body. Override `SHARED_SKILLS`, `SHARED_CATALOG`, `GLOBAL_AGENTS` or
`GLOBAL_AGENTS_MAX_LINES` to point it elsewhere.

It was referenced by five dated evidence files while living only at
`~/.config/agent-workbench/evals/`. It now lives here, so those citations resolve
from inside the repository.

These commands validate schema, parser and structure only, without inference. A
live evaluation requires an authorized model run and candidate discovery on the
target harness: `--cases evals/skill-contracts.jsonl --out <result>`. Hub-local
candidates are not automatically installed. The runner observes skill loading;
behaviour contracts require review of actual outputs, recorded as unavailable
until reviewed. Corpus validity is not routing accuracy, output quality or
promotion evidence.
