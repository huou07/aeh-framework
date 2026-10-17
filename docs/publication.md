# Publishing the Hub

Type: How-to.

Authority: the operating procedure for publishing any part of this repository.
The repository is private by decision; this document is how a public artefact is
produced without publishing the owner's machine.

Applies to: anyone publishing, mirroring or changing the visibility of the Hub.

Status: current

Last reviewed: 2026-10-18

## Why there are two halves

The Hub is one workspace with two very different kinds of content.

| Private half | Public half |
|---|---|
| `projects/registry.json` — real absolute paths | `scripts/hub.py`, the CLI and the five verdicts |
| `ops/` — host administration: services, permissions, network failover | `contracts/` + `scripts/quality_contract.py` — the quality contract |
| `evidence/` — dated records with host paths, session ids, run ids | `scripts/conformance.py` + `tests/fixtures/conformance/` — the adversarial suite |
| `docs/normal-user-runtime.md` — applications and private-network detail | `docs/quality-standard.md`, `docs/quality-interface.md` |
| `hub.config.json` — the owner's workspace root | `skills/`, `templates/`, `evals/`, `tests/`, the self gate |

The framework is genuinely useful to other people. The control data is not theirs
to have, and publishing it is the mistake recorded as incident AEH-D024: the
repository was made public for about fifteen minutes and took three pushes before
anyone checked what a public control workspace exposes. No credential leaked
(gitleaks found nothing), but the private-network detail, the operations scripts
and the dated evidence were world-readable. Visibility was switched back to private.

## The rule

1. **This repository stays private.** Do not change its visibility, and do not
   push its tree to a public remote.
2. **Publish the snapshot, not the tree.** `scripts/build-public-snapshot.sh`
   produces the public half as a standalone directory.
3. **A snapshot that cannot prove itself is not published.** The builder refuses
   to finish unless the result passes `scripts/publication-check.sh` (no
   host-specific or secret material) *and* its own `scripts/selfcheck.sh`.
4. **AEH has no remote and no CI.** Its gate is `scripts/selfcheck.sh`, run
   locally; the snapshot is proved at build time, before it is published. Never
   make a hosted check the condition for Hub work.
5. **`scripts/publication-check.sh` is not part of the self gate.** It fails by
   design on the private tree; a gate that is always red trains people to ignore
   red. Run it before publishing, and in CI of the public repository if desired.

## Procedure

```bash
# 1. Build and prove the snapshot (about a minute).
bash scripts/build-public-snapshot.sh /tmp/aeh-public
#    → PUBLICATION CHECK PASSED, then AEH_SELFCHECK=PASS, then SNAPSHOT=PASS

# 2. Inspect it. It should contain no absolute home path, no private address and
#    no operations or evidence record other than the redacted incident ledger.
bash /tmp/aeh-public/scripts/publication-check.sh /tmp/aeh-public

# 3. Publish it as its own repository.
git -C /tmp/aeh-public init -b main
git -C /tmp/aeh-public add -A
git -C /tmp/aeh-public -c user.name="AEH" -c user.email="aeh@localhost" \
  commit -m "AEH framework snapshot"
gh repo create huou07/aeh-framework --public --source /tmp/aeh-public --push
```

The snapshot carries no workflow and needs none: the proof happened before the
push, when the builder ran both gates on the exact tree being published. It
carries `PUBLICATION.md`, which states what the repository is and is not.

## What the builder changes

- **Excludes** `ops/`, `evidence/`, `REPORT.md`, `docs/normal-user-runtime.md`,
  `docs/readiness-2026-10-17.md`.
- **Regenerates** `hub.config.json` (generic workspace root) and
  `projects/registry.json` (empty) so the Hub runs anywhere.
- **Redacts** the incident ledger instead of dropping it: home paths, private
  addresses, tunnel names, model-route names, private-network phrases and session ids
  become placeholders. The process lessons are the valuable part.
- **Rewrites** `docs/README.md`, `AGENTS.md` and `README.md` so the snapshot is
  internally consistent: every surviving document is indexed, links into the
  excluded directories point at the placeholder README that explains why, links
  to unpublished documents are de-linked, and the snapshot is labelled as such.

## Refreshing the published snapshot

The public repository is a generated mirror, not a working tree. Rebuild it and
publish the new tree:

```bash
bash scripts/build-public-snapshot.sh /tmp/aeh-public
git -C /tmp/aeh-public init -b main && git -C /tmp/aeh-public add -A
git -C /tmp/aeh-public -c user.name="AEH" -c user.email="aeh@localhost" commit -m "AEH framework snapshot"
git -C /tmp/aeh-public remote add origin https://github.com/huou07/aeh-framework
git -C /tmp/aeh-public push -u --force origin main
```

A force-push is intended here: the mirror is a build artefact whose history has
no independent value, and the private repository keeps the real history. The
mirror carries no CI and no required check — the signal that the published
framework is sound is the build-time proof, not a hosted run.

## What this does not do

- It does not sanitise the private repository. That tree keeps its host detail on
  purpose; the gate is what stops it being published.
- It does not prove the published framework works for anyone else beyond its own
  gate. A stranger-with-no-dev-environment check of the snapshot is still an
  owner task.
- It does not remove anything already published. Once a commit is public, treat it
  as public: rotate anything sensitive, and prefer making the mistake visible in
  the incident ledger over quietly rewriting history.
