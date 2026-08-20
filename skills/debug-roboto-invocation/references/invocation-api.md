# Invocation API surface

A map for locating evidence. This file is rung 4 of SKILL.md's Ground truth ladder — the lowest. Confirm anything you are about to write against the installed SDK (rung 1) or `roboto invocations <verb> --help` (rung 2) before writing it.

## Durable documentation URLs

- Invocations, the lifecycle, and monitoring: `https://docs.roboto.ai/learn/actions.html`
- Invocation CLI reference: `https://docs.roboto.ai/reference/cli.html#roboto-invocations`
- Action configuration reference: `https://docs.roboto.ai/reference/action-json.html`
- Compute sizing and how usage is measured: `https://docs.roboto.ai/learn/compute.html`
- Python SDK reference: `https://docs.roboto.ai/reference/python-sdk.html`

## The three sources of evidence

Every diagnosis in this skill rests on one of these. Read them in this order.

| Source | Command | What it settles |
|---|---|---|
| Status history | `roboto invocations status <id>` | Where it stopped, when, and what the platform said about each transition. **Read this first** |
| Configuration | `roboto invocations show <id>` | What it was asked to do. Prints the whole record as one JSON object: action name, owner, and image digest (there is no version field); data source and input specification; parameter values; compute requirements; timeout — plus the status log and idempotency id |
| Logs | `roboto invocations logs <id>` | What the action itself reported while running |

`status` and `logs` both accept a flag to follow a live invocation to completion.

`logs` returns records from **every container in the invocation** — setup, monitor, action, output handler, and the log router — printed under a per-process header, with no filtering. So a stop before the action ran still produces logs: the setup container's, which is where that failure is explained. Absence of output under the *action's* header means the action's own code never logged; it does not mean there is nothing to read.

## Status vocabulary

`InvocationStatus` (in `roboto.domain.actions`) is an ordered progression through queueing, scheduling, input download, processing, upload, and completion, plus states outside that progression for cancellation and for failure. Failure is represented at two levels of finality — an ordinary failure that the platform may retry, and the state an invocation reaches once it will not be retried. Read the members from the installed enum.

The enum carries its own logic, and using it beats reimplementing it:

- `is_running()` — whether the invocation is currently doing work
- `is_terminal()` — whether a verdict is available at all (SKILL.md discipline rule 2)
- `can_transition_to(other)` — the legal transitions, including which failed states can return to the queue
- `next()` — the next status in the linear progression, or `None` at a terminal state
- `from_value(v)` — parse a status from its name or its numeric value

**`InvocationStatusRecord`** is one entry in the history: a `status`, a `timestamp`, and an optional **`detail`**. The detail field is the platform's own account of a transition and is frequently the whole diagnosis. Never skip it.

## Exit codes

`roboto.action_runtime.exit_codes.ExitCode` is the vocabulary the action runtime **defines** for actions to exit with, adapted from `sysexits.h` — success, a usage error, an input-data error, an internal software error, a configuration error. It is a convention, not a set the platform emits: the SDK itself raises only the usage and internal-error codes, and only while preparing the environment. The data and configuration codes reach a status because an action's own code chose them, which is why an action ignoring the convention reports codes outside the enum. `triage.md` Step 3 maps each class to where its fix belongs.

The exit code is **not a field on the invocation**. Nothing on `InvocationRecord` or `InvocationStatusRecord` carries it and no CLI command prints one; where an exit code surfaces, it is inside the terminal status's `detail` string.

Codes above 128 are neither in the enum nor action-authored: by POSIX convention they are `128 + signal`, so `137` is a SIGKILL — most commonly the container exceeding its memory allocation, with no traceback anywhere to find.

The input-data code is the one worth reading the docstring for: it exists so an action can say "I worked correctly and the input was wrong" as distinct from "I broke", and Roboto's own ingestion actions use it that way for a file that is the wrong format, corrupted, or empty.

`roboto.action_runtime.exceptions` carries the runtime's exception types, including one that pairs an exit code with a human-readable reason for failures raised while the environment is being prepared.

## `Invocation`

Import from `roboto.domain.actions`. Confirm the surface before calling it:

```bash
python -c "import inspect; from roboto.domain.actions import Invocation; print([m for m in dir(Invocation) if not m.startswith('_')])"
```

The members this skill's phases depend on:

- `Invocation.from_id(invocation_id, ...)` — the entry point when you have an id
- `Invocation.query(spec, ...)` — finding invocations by condition, including by the trigger that produced them
- `status_log` — the full status history, as `InvocationStatusRecord` entries. The single most valuable property here
- `current_status`, `reached_terminal_status` — the discipline-rule-2 check
- `get_logs(page_token=...)` and `stream_logs(...)` — the action's own output
- `record` — the full invocation record, including provenance
- `action`, `executable`, `source` — provenance: which action, which image, and whether a person or a trigger started it. `source` is how you learn a failure came from a trigger rather than a human
- `input_data`, `parameter_values`, `compute_requirements`, `timeout`, `data_source`, `upload_destination` — the configuration, for causes visible without logs
- `refresh()` — re-read from the platform while following a live invocation
- `cancel()` — stop a running invocation
- `wait_for_terminal_status(...)` — block until a verdict exists rather than sleeping a guessed interval

`Invocation.record` also carries the idempotency id, which explains an invocation that appears not to have run: an invoke that collides with an existing idempotency id does not create a second invocation.

## CLI

Under `roboto invocations`: `status`, `show`, `logs`, `cancel`, `cancel-all`. Confirm flags with `--help`.

Related verbs elsewhere:

- `roboto actions list-invocations <action-ref>` — find recent invocations of an action
- `roboto actions invoke <action-ref> ...` — the hosted re-invocation of SKILL.md Phase 5. Its input selection and parameter flags are shared with local invocation; take the values from `invocations show` so the re-run matches the original
- `roboto actions invoke-local ...` — local reproduction, which needs Docker and a pty from a non-interactive shell

`cancel-all` operates in bulk. A cancelled invocation's status detail names *who* cancelled it, not whether it was an individual stop or a bulk sweep; that can only be inferred, from many invocations in the org being cancelled by the same actor at the same moment. Report it as inferred.

## What this skill cannot see

The evidence available to a Roboto user is the status history, the invocation configuration, and the action's logs. Diagnoses that would require platform-internal telemetry are out of reach; when the evidence runs out, say what would be needed and stop, rather than presenting a guess as a finding.
