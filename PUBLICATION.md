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
