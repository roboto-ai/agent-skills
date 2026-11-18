# Triage

Maps the evidence from SKILL.md Phase 1 (the last status reached, the terminal detail, and the log section it points to) to a fault domain and the check that confirms it. SKILL.md Phase 2 reads it.

Every log message quoted below was checked against the SDK release recorded as `verified-sdk` in the `metadata` block of `SKILL.md` by reading its `roboto/action_runtime` source, which the setup step and `InvocationContext` run, and every Python action limit by reading https://www.roboto.ai/docs/learn/python-actions, on the date recorded as `verified-on`. The `output_handler` message and the status details are observed platform behavior on that date. A newer release can change any of it: re-check what you use against source 1 of SKILL.md's "Sources, in order of authority". Where this file and a live source disagree, the live source wins.

## Step 1: Is there a verdict?

Only Completed, Cancelled, Failed, and Deadly are terminal. Use `InvocationStatus.is_terminal()`, not `is_running()`, which is false for a Queued invocation that is still live. Read the whole history, not only the last entry: the status model allows Failed to go back to Queued, so a later Queued after a Failed means the invocation ran again, and the last terminal entry is the verdict. Say which entry your diagnosis rests on.

## Step 2: Where did it stop?

| Stopped at | Fault domain | Check first |
|---|---|---|
| Queued, for longer than expected | Scheduling, not the action | The "Hung" step below. The action never ran, so its logs explain nothing |
| Downloading, or a `setup ...` detail | The request: inputs, parameters, secrets | The `setup` log section; Step 3 |
| Failed before Processing, image not started | The action's image | Whether the image exists and the action's `uri` points at it |
| Processing, or an `action ...` detail | The action's code, its dependencies, or its sizing | The detail's exit code, then the end of the `action` log section; Step 4 |
| Uploading, or an `output_handler ...` detail | What the action wrote, or where it was to go | The `output_handler` log section |
| Completed | The action's logic, its inputs, or the expectation | Step 5 |
| Cancelled | A person, a bulk cancel, a deleted dataset, or the timeout | The detail names which. `Exceeded <n> second timeout` is a timeout, so go to Step 4 |

## Step 3: Setup failures

Setup runs before the action's code. Its messages are in the `setup` log section.

| Log line | Cause | Fix goes in |
|---|---|---|
| `Failed to retrieve invocation input data! Reason: ...` | A selector names data that does not exist or that the invoker cannot read. Setup exits 64, or 70 on a server error | The invocation or the trigger target's input selection |
| `Failed to retrieve secret <uri>, because it does not exist.` | A `roboto-secret://` parameter names a secret that is missing or unreadable. Setup exits 70 | The secret, or the parameter value |
| `No files matched the provided input specification.` (or `sessions`, `topics`) | The selection resolved to nothing. This is a warning: the run continues with empty input and can end Completed | The selection; Step 5, item 1 |
| `Unexpected error during invocation setup` | An error setup did not anticipate | Report it with the traceback. A re-run on the same inputs, with the user's yes, shows whether it persists |

## Step 4: The action failed

Read the exit code from the terminal detail; it is not a field on the record.

| Evidence | Cause | Fix goes in |
|---|---|---|
| Exit 65 | The action rejected its input as corrupt, empty, or the wrong format, by the runtime's convention | The data (rule 1) |
| Exit 64 or 78 from the action | The action's own usage or configuration check failed; its log says which | The parameters, or `action.json` |
| Exit 1 with a Python traceback | An unhandled exception | The action's code, at the frame the traceback ends in |
| Exit 137, or `SIGKILL` and the OOM sentence, or `oom` | Out of memory | `compute_requirements`: raise memory within the pairs on https://www.roboto.ai/docs/learn/compute. A Python action is fixed at 2 GiB, so move the work to a container action |
| `Exceeded <n> second timeout`, or `timed_out` | The run reached its timeout | The timeout or the input size (rule 5). A Python action's longest run is 12 minutes 30 seconds |
| `No dataset is associated with this invocation. ...` | The action touched `InvocationContext.dataset` on a run invoked by query, session, or schedule, which names no dataset | The action (read inputs from `get_input()`), or the invocation (`--dataset`) |
| Exit 1 and `Could not find parameter '<name>'.` | The code read a parameter with `get_parameter` that has no value: `action.json` declares it optional with no default, or does not declare it. A declared required parameter with no value never gets this far: the platform refuses the invocation (`{'<name>'} is a required parameter for action ...`), and a trigger's dispatch fails with that detail | `action.json` (make it required or give it a default), or the action (`get_optional_parameter`) |
| A Python action fails on an outbound request | Its release allows Roboto only, the default | The release's network setting, which is a decision for the user |
| A Python action sees no inputs or an empty `ROBOTO_DATASET_ID` | It read the input manifest from the environment itself, or assumed one dataset | The action: read inputs with `InvocationContext.from_env().get_input()` |

## Step 5: Completed, but wrong

The platform reports Completed when the code exits 0, whatever it did. Check these in order:

1. **It processed nothing.** Look for `No files matched ...` in the `setup` section and for what the action logged about its inputs. Compare what it took (item 2 says where to read it) with what the user expected. A clean exit on zero inputs is a failure with a success status.
2. **It processed the wrong thing.** The `setup` log's `Looking up ...` and `Downloading {<n>} file(s) ...` lines, or `resolved_input_data` where the record has it, say exactly what it got: an over-broad query, the wrong dataset, or a trigger firing on data nobody meant to include. Files from several datasets are placed at `<input_dir>/<dataset_id>/<relative_path>`, and files from one dataset at `<input_dir>/<relative_path>`, so an action that builds paths for one layout misses files in the other.
3. **Its outputs went nowhere.** Only files in the output directory are uploaded, and only to a destination. With no `upload_destination`, the platform infers one only when the inputs' files and topics all come from one dataset. Otherwise the `output_handler` section logs `No destination (e.g. a dataset) was provided for this invocation's outputs. Skipping output upload.` and the run still completes. Session-only and multi-dataset inputs need `--output-dataset-id`. A Python action's working-directory files are run artifacts, not dataset files.
4. **It did what it was told.** The expectation was wrong. Say so plainly.

## Step 6: Hung

- **Queued.** The run is waiting for compute. Count the org's other live invocations with a `last_status` `LessThan 5` query (see `invocation-api.md`, "Finding the invocation"): a long queue of them points at the org's limit on concurrent invocations. The web app does not show that limit to org members, so Roboto support confirms it. Do not cancel anything without the user's yes.
- **Processing for a long time.** Compare the elapsed time with `timeout` (minutes) in the record. Follow it with `roboto invocations logs <id> --tail`; output that stopped long ago with the status unchanged is worth reporting with `last_heartbeat`. The timeout ends it if nothing else does.

## Step 7: The logs say nothing

An action that logs nothing below error level may not apply `InvocationContext.log_level` to its logger. If it does apply it, `roboto actions invoke` sets that level from the CLI's own `--log-level`, which defaults to `ERROR`, while a run with nothing set falls back to `INFO`. So a manual run can be quieter than a trigger-started one. Re-run with `roboto --log-level=debug actions invoke ...` for the diagnosis, and report the missing `setLevel` call as an open item. None of this applies to a Python action, whose log is whatever its script prints.

## Wrong turns

Each rule below names a step that produces a confident, wrong verdict.

1. **Do not change the action to accept input it rejected with exit 65.** The symptom goes away and the bad data propagates. The finding belongs to the data.
2. **Read the status history before any traceback.** It is cheaper, often decisive, and says whether the traceback comes from the stage that failed.
3. **Re-run on the input that failed, not on a cleaner one.** A fix proven on easier input has not been proven.
4. **Redeploy before re-running.** A hosted run uses the deployed action; an old image fails the same way and reads as a failed fix.
5. **Do not read a timeout as a bug.** The run may be sized for less work than it got. The fix can be the timeout, the compute, or a narrower input selection.
6. **Do not diagnose from the action's source alone.** It shows intent; the record shows what happened.
7. **Find out who cancelled before looking for a defect.** The detail says whether it was one person, a bulk cancel, a dataset deletion, or a timeout.
8. **Do not reuse the original `idempotency_id`.** The platform refuses the second invocation as a conflict, which reads as a failed re-run.
