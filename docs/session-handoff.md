# Hand a prepared prompt to a project workspace

Type: How-to. Authority: how to deliver a prompt artifact. The prompt's content,
the project's gates and its `docs/AGENT-AUTHORITY.md` still govern what the
receiving agent may do.

Use this when a prompt artifact already exists and the owner wants it **running
in a project workspace they can watch**, instead of a detached terminal session.

Status: current
Last reviewed: 2026-10-17
## The chain

1. **Write the artifact.** `prompt-assist` produces the prompt; `project-steward`
   owns status and prioritisation. Save it in the receiving project as
   `<project>/docs/prompts/<NAME>.md` so the repository carries it.
2. **Confirm the authority.** The receiving project's `docs/AGENT-AUTHORITY.md`
   records what that agent may do without asking again. A prompt must not ask for
   more.
3. **Dry-run the delivery.**

   ```sh
   node scripts/dsh_gui_session.cjs --list
   node scripts/dsh_gui_session.cjs --dry-run OR docs/prompts/FINISH-OR.md
   ```
4. **Deliver.**

   ```sh
   node scripts/dsh_gui_session.cjs OR  "$(python3 scripts/hub.py where OR)/docs/prompts/FINISH-OR.md"
   node scripts/dsh_gui_session.cjs VCE "$(python3 scripts/hub.py where VCE)/docs/prompts/FINISH-VCE.md"
   ```
5. **Read the verdict.** Exit `0` means the session store gained a new session id
   **and** that session's transcript contains the prompt. Anything else is a
   failure, not a success.
6. **Watch it in the GUI.** It appears in the DSH Web sidebar with a `Running`
   badge; the composer shows the model and effort the profile selects
   (`DeepSeek V4.1 Flash · Default`).

## Workspace titles

Titles are the GUI's own names, read from `~/.dsh/storages/workspace.json`:

| Title | Path |
|---|---|
| `OR` | `<workspace-root>/OR` |
| `VCE` | `<workspace-root>/VCE` |
| `H07P` | `<workspace-root>/H07P` |
| `AEH` | the Hub checkout itself |

Resolve the real paths with `python3 scripts/hub.py where <slug>`; this table
shows the shape, not the owner's filesystem.
| `huou07-playground` | a retired duplicate checkout — **stale**; remove this workspace in the GUI rather than delivering into it |

## Very long prompts

A multi-thousand-line plan is better referenced than pasted. Save it as
`<project>/docs/prompts/<NAME>.md` and deliver a short kickoff that names the
file:

```sh
node scripts/dsh_gui_session.cjs H07P /tmp/h07p-kickoff.md
```

where the kickoff says to read and execute `docs/prompts/UPGRADE-H07P.md`. The
agent reads the plan itself, and the GUI stays responsive. Measured 2026-10-17:
the 40,327-character H07P plan was delivered this way and the agent did read it.

## What the launcher verifies, and what it cannot

`scripts/dsh_gui_session.cjs` drives the real GUI with Playwright: it opens
`http://127.0.0.1:3080` with the login token from `/run/huou07-dsh-link/url`
(never printed), dispatches the click on the per-workspace
`New session in <title>` control, fills the composer and sends. Then it checks
the session store for a new id and greps that session's `session.v4.jsonl.zstd`
for a marker taken from the prompt.

It does **not** verify that the agent does the work correctly, that the project's
gates pass, or that the result is acceptable. Those stay with the project and
with hosted CI. A verified delivery is not acceptance.

## Pitfalls, all measured on 2026-10-17

| Pitfall | Handling |
|---|---|
| The `New session in <title>` button is hidden until its row is hovered | The launcher dispatches the click through the DOM; React still handles it |
| Installed Playwright may request `chromium_headless_shell-<n>` while the cache holds another revision | The launcher picks the newest `chromium-<n>/chrome-linux64/chrome` from `~/.cache/ms-playwright` and passes `executablePath` |
| The GUI can create a new session but keep the **previous** session's composer active, so the prompt lands in the older session | The launcher waits for the new id before typing, then verifies the new session's own transcript and fails loudly. This happened with H07P: a new empty session was created and the prompt went into the older one |
| The session store updates asynchronously | Verification polls; do not shorten it to a fixed sleep |
| Sessions created from the **CLI** do not appear in the GUI workspace list | Deliver through the GUI when the owner wants to watch, through the CLI when they do not |
| GUI sessions run inside the web server, so `pgrep dsh` shows nothing | Verify from `~/.dsh/storages/workspace.json` and the transcript, not from processes |
| Two sessions in one repository fight over the same working tree | Deliver one session per repository; stop the previous one first |
| The login link rotates | The launcher reads it at call time; an expired file needs the H07P launcher to refresh it |
| `read_image` cannot read files under the owner's home from this session | Inspect the GUI through the DOM (sidebar text, session titles) instead of screenshots |

## Pausing a delivered session

Pause by **steering an instruction the agent acts on**, not by clicking the stop
control. A steer lets the agent finish the tool call it is in, reach a clean
committed-or-recorded state, and end its own turn. A stop click is a hard
interrupt: on 2026-10-17 a click on `[aria-label="Stop generating"]` left the
session running and recorded nothing (`AEH-D003`), so a click is never proof.

The delivered tools do this and verify from the durable transcript, not the click:

```sh
node scripts/dsh_gui_pause.cjs --survey                     # who is running
node scripts/dsh_gui_steer.cjs  --send --id <sessionId> --message <prompt>
node scripts/dsh_gui_answer.cjs --id <sessionId> --option "<label>"   # pending question
python3 scripts/skill_liveness.py                           # what a session can load
```

Rules that came from measured failures:

- **Address rows by key, never by text.** The tree exposes
  `[data-row-key="workspace:<uuid>"]` and `[data-row-key="session:<id>"]`; a
  text-walk click created two stray sessions (`AEH-D001`). Before typing, require
  `[data-conversation-session]` to equal the intended session id.
- **Check for an armed goal first.** A persisted goal keeps requesting rounds and
  the pause will not hold until the agent calls `update_goal` with `action: pause`
  (`AEH-D005`). Leave the goal paused when work is handed back.
- **Clear blocking read-only waits.** A step-boundary steer cannot preempt an
  in-flight blocking tool call; a session waiting on `job_output` for a CI watcher
  ignored the steer for 40 minutes (`AEH-D004`). Terminate the read-only waiter,
  then steer.
- **Answer the agent's own question.** A paused agent can sit on an
  `ask_user_question`; answer it as part of the pause (`AEH-D006`).
- **Prove the stop from the transcript.** A pause is verified only when the
  session's own transcript records `turn/end` with an `aborted` reason (hard
  interrupt) or a completed turn with a clean tree, and the file stops growing.
- **One session per repository.** Stop or pause the previous one before delivering;
  the GUI New-session path can reopen an existing blank session instead
  (`AEH-D011`), so verify which session actually received the message.

Session ids and the resume command for a paused batch are recorded in
[session-pause-2026-10-17.md](../evidence/README.md) and
[reorganization-2026-10-17.md](../evidence/README.md). Every
failure above is in the [incident ledger](../evidence/README.md).
