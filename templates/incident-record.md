# Incident record — <project>

Copy this into the project's own evidence location, or append a line to its
ledger, whenever a failure is met while doing the work. A failure that is not
recorded is paid for twice.

Authority: this records what happened. The project's gates, Git history and
observed runtime remain the authority for current behaviour.

| Field | Value |
|---|---|
| id | `<project>-DNNN` |
| date | `YYYY-MM-DD` |
| class | `harness` / `process` / `host` / `product` |
| where | `<file, command, session or control>` |
| symptom | What was observed, in one sentence. |
| root cause | Why it happened, once known. Say `unknown` and say what would tell you. |
| evidence | The real command and its output, the file:line, or the session event. Not a paraphrase. |
| disposition | `fixed` / `guarded` / `open` / `superseded` / `delegated` |
| guard | The test, check or fail-loud branch that keeps it from recurring. Required: a failure without a guard is a story, not a fixed defect. |
| related | The document, prompt or decision that closed it, or that would. |

## Rules

1. Write the observed text, not your summary of it.
2. Prefer an executable guard over a sentence in a document. A guard that cannot
   exist yet means the disposition is `open`, and `related` names the decision.
3. When the failure shows the procedure was wrong, change the procedure in the
   same pass.
4. A green run that hid a skip, a gate that passed while the product failed, and a
   control that looked successful but did nothing are all incidents: they are worse
   than a red check because they remove the signal.
5. Never record a credential, a token or a secret value in the evidence field.

The Hub's own ledger is [`../evidence/incidents.jsonl`](../evidence/README.md),
validated by `tests/test_incidents.py`.
