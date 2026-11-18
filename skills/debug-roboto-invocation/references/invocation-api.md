# Invocation API map

Where each piece of evidence about an invocation lives, how to find an invocation from what the user named, and how to re-run one on the same inputs. SKILL.md Phases 1 and 4 read it.

Every flag below was checked against the SDK release recorded as `verified-sdk` in the `metadata` block of `SKILL.md` with `python -m roboto.cli <group> <command> --help`, and every signature and field by printing `inspect.signature` and `model_fields` from `uv run --with roboto==<verified-sdk> python`, on the date recorded as `verified-on`. The CLI form and the SDK script under "Re-running on the same inputs" were run against a container action's invocations in a live org; neither was run for a Python action. The status details under "Status details" are observed platform behavior on that date, not an SDK contract. A newer release can change any of it: re-check what you use against source 1 of SKILL.md's "Sources, in order of authority". Where this file and a live source disagree, the live source wins.

## Durable references

These paths are stable; prefer them over search results.

| Resource | URL |
|---|---|
| Actions, invocations, and triggers | https://www.roboto.ai/docs/learn/actions |
| Python actions (runtime contract, compute, network) | https://www.roboto.ai/docs/learn/python-actions |
| Compute options | https://www.roboto.ai/docs/learn/compute |
| `roboto invocations` CLI | https://www.roboto.ai/docs/reference/cli/invocations |
| `roboto actions` CLI | https://www.roboto.ai/docs/reference/cli/actions |
| `Invocation` | https://www.roboto.ai/docs/reference/python-sdk/roboto/domain/actions/invocation |
| `InvocationRecord`, `InvocationStatus` | https://www.roboto.ai/docs/reference/python-sdk/roboto/domain/actions/invocation_record |
| `ExitCode` | https://www.roboto.ai/docs/reference/python-sdk/roboto/action_runtime/exit_codes |
| `InvocationContext` | https://www.roboto.ai/docs/reference/python-sdk/roboto/action_runtime/invocation_context |
| `Trigger` (current model) | https://www.roboto.ai/docs/reference/python-sdk/roboto/domain/triggers/trigger |
| `Session` | https://www.roboto.ai/docs/reference/python-sdk/roboto/experimental/sessions/session |
| SDK source | https://github.com/roboto-ai/roboto-python-sdk |

## Commands

| Command | Prints | Notes |
|---|---|---|
| `roboto invocations show <id>` | The whole record as JSON on one line, including the `status` list | Statuses appear as numbers; pipe through `python3 -m json.tool` |
| `roboto invocations status <id> [--tail]` | The `status` list only: `status` (by name), `timestamp`, `detail` | Start here. `--tail` polls until a terminal status |
| `roboto invocations logs <id> [--tail]` | Log lines under a `========== <process> ==========` header per process that logged | A process that logged nothing has no header. `--tail` streams until a terminal status |
| `roboto actions list-invocations <action> [--org]` | JSON list of `invocation_id`, `created`, `status`, newest first | Lists every invocation of the action; pipe through `head` |
| `roboto invocations cancel <id>`, `cancel-all [--org]` | A confirmation, or counts | Writes: `cancel-all` cancels every queued and running invocation in the org. Both need the user's yes |
| `roboto triggers dry-run <name> --dataset-id/--file-id/--invocation-id/--event-id/--scheduled-for [--org]` | A gate-by-gate trace | Read-only; exits 0 whether or not it would fire. Pass the reference the trigger's event names: a file event refuses `--dataset-id`. A schedule-fired trigger takes `--scheduled-for` or no reference. It stops before the target, so it cannot show why a dispatch `failed` |

`show`, `status`, `logs`, and `cancel` take no `--org` flag. `--log-level` is a global flag and goes before the group: `roboto --log-level=debug actions invoke ...`.

## Record fields

| Field | Notes |
|---|---|
| `status` | Every transition: `status`, `timestamp`, `detail`. The terminal `detail` is the first thing to read |
| `provenance.action` | `name`, `org_id` (the action's owner), `digest` (the version that ran) |
| `provenance.executable` | `container_image_uri`, `container_image_digest` |
| `provenance.source` | `source_type` `Trigger` (then `source_id` is the trigger ID) or `Manual` (`source_id` is the user ID) |
| `rich_input_data` | Inputs as requested: `files`, `sessions`, `topics` selectors by `query`, `ids`, `names`, or `paths`. A `paths` selector without `dataset_id` is relative to `data_source`. A trigger-started run's `files` can be a list of selectors, by `ids` |
| `resolved_input_data` | The files, sessions, and topics the request resolved to, as IDs. `null` when the invocation recorded none, which, as observed on the `verified-on` date, included every container action's invocation; read the `setup` log's `Looking up ...` and `Downloading {<n>} file(s) ...` lines instead |
| `input_data` | Deprecated list of dataset-relative paths; read `rich_input_data` instead |
| `data_source` | The dataset named at invocation, or `__UNSPECIFIED_DATA_SOURCE__` when none was |
| `upload_destination` | Where files in the output directory go; `null` when none was named |
| `parameter_values`, `compute_requirements`, `container_parameters`, `timeout` | As run. `timeout` is in minutes |
| `idempotency_id`, `last_heartbeat`, `duration` | A reused `idempotency_id` is refused with a conflict error |

In the SDK, `Invocation.from_id(id)` exposes the same data as properties (`status_log`, `current_status`, `source`, `resolved_input_data`, and so on), plus `get_logs()` and `wait_for_terminal_status(timeout=300, poll_interval=5)`.

## Status vocabulary

| Member | Value | Notes |
|---|---|---|
| `Queued`, `Scheduled` | 0, 1 | Waiting for compute, then starting it. `is_running()` is false for both, so test `is_terminal()` |
| `Downloading` | 2 | Setup runs and, if the action requires it, downloads input files |
| `Processing`, `Uploading` | 3, 4 | The action's code runs, then its outputs upload |
| `Completed`, `Cancelled` | 5, 997 | Terminal |
| `Failed` | 998 | Terminal, but `can_transition_to` still allows `Queued` after it |
| `Deadly` | 999 | Terminal; a failure that will not run again |

In a query, `last_status` takes a number or a name in any case, and `LessThan 5` matches every live invocation.

## Status details

As of the `verified-on` date, a container action's details read like this. Some invocations, Python actions among them, open a terminal detail with a short code instead (`exit_<n>`, `oom`, `timed_out`, `setup_failed`, `outputs_failed`, `never_started`, `environment_lost`, `launch_failed`, `capacity_refused`, `by_request`), optionally followed by `: ` and a sentence. Quote whatever the record says; if it matches neither form, report it verbatim.

| Detail | Status | Meaning |
|---|---|---|
| `Preparing execution environment and (optionally) downloading inputs` | Downloading | Setup started |
| `Running '<action>'@<digest>` | Processing | The action's container started |
| `Uploading action outputs, if any` | Uploading | The output handler started |
| `setup failed with exit code <n>` | Failed | The action's code never ran; see the `setup` log section |
| `action failed with exit code <n>` | Failed | The action's process exited non-zero |
| `output_handler failed with exit code <n>` | Failed | The action succeeded and the upload of its outputs failed |
| `... (SIGKILL). This is likely due to ... Out-of-Memory ('OOM') error ...` | Failed | Exit code 137: killed, most often for exceeding its memory |
| `<containers> stopped before starting. The image may be missing or unpullable.` | Failed | The image could not be started |
| `Exceeded <n> second timeout` (such as `Exceeded 60.0 second timeout`) | Cancelled | The invocation reached its timeout. Where details use codes, this is `timed_out` under Failed |
| `Invocation cancelled by <principal>` | Cancelled | Someone cancelled this invocation |
| `Cancelled by <principal>` | Cancelled | A bulk cancel, such as `cancel-all` |
| `Cancelled due to dataset deletion` | Cancelled | Its dataset was deleted |

A Python action's history can go from Scheduled straight to Processing with no Downloading entry. That is normal for one.

## Exit codes

`roboto.action_runtime.ExitCode` is a convention adapted from `sysexits.h`: `Success` 0, `UsageError` 64, `DataError` 65 (the action worked and the input was bad; Roboto's ingestion actions use it for a corrupt, empty, or wrong-format file), `InternalError` 70, `ConfigurationError` 78. Setup uses 64, 70, and 78 itself (`triage.md`, Step 3). An action that ignores the convention exits with whatever its process returned: 1 for an unhandled Python exception, 128 plus the signal number for a kill.

## Finding the invocation

Every snippet is read-only. Filter `ExperimentalWarning` at the top of a script that imports `roboto.experimental`:

```python
import itertools, warnings
from roboto.warnings import ExperimentalWarning
warnings.filterwarnings("ignore", category=ExperimentalWarning)
```

Recent failures of one action, newest first. `limit` sets the page size, not a cap, so slice the generator:

```python
from roboto import Invocation
from roboto.query import Comparator, Condition, ConditionGroup, ConditionOperator, QuerySpecification, SortDirection

spec = QuerySpecification(
    condition=ConditionGroup(operator=ConditionOperator.And, conditions=[
        Condition(field="provenance.action.name", comparator=Comparator.Equals, value="<action>"),
        Condition(field="last_status", comparator=Comparator.Equals, value="failed"),
    ]),
    sort_by="created", sort_direction=SortDirection.Descending,
)
for iv in itertools.islice(Invocation.query(spec, owner_org_id="og_xxx"), 10):
    print(iv.id, iv.created, iv.current_status, iv.status_log[-1].detail)
```

The invocations API accepts these condition fields: `provenance.action.name`, `provenance.action.org_id`, `provenance.action.digest`, `provenance.source.source_id` (a trigger ID finds that trigger's invocations), `provenance.source.source_type`, `last_status`, `created`, `org_id`, `data_source_id`, `data_source_type`, `idempotency_id`, `last_heartbeat`, and `input.session_id`. `input.session_id` takes only `Equals`, and matches only inputs that named the session by ID, not by query or name.

As of the `verified-on` date, a Python action's invocations did not appear in query results, so a query, and `roboto actions list-invocations`, can return nothing for one. The ID-based commands and `Invocation.from_id` still find it.

What a trigger dispatched. Import `Trigger` from `roboto.domain.triggers`: the top-level `roboto.Trigger` is the legacy model and cannot read every trigger.

```python
from roboto.domain.triggers import Trigger

trigger = Trigger.from_name("<trigger-name>", owner_org_id="og_xxx")
for d in itertools.islice(trigger.dispatches(), 20):
    print(d.claimed_at, d.event_type, d.subject, d.status, d.result_ref, d.status_detail)
```

`result_ref` is the invocation ID for an invoke-action target. A `dispatched` entry with an empty `result_ref` started nothing new; its `status_detail` says why. A `failed` entry has no `result_ref`, and its `status_detail` is the refusal, such as `{'threshold'} is a required parameter for action '<org>/<action>@<digest>'` when the target's `parameter_values` lack one. A failed dispatch does not count as fired, so the next matching event for that subject tries again, and its entry replaces the failed one in the history: quote a `status_detail` before the subject changes. Only matched events are recorded, so an empty history means the trigger never fired. `Trigger.from_id(<provenance.source.source_id>)` loads the trigger behind a trigger-started invocation.

Why a session has not finished ingesting:

```python
from roboto.experimental.sessions import Session

status = Session.from_id("se_xxx").ingestion_status()
print(status.state, status.pending_file_count, status.failed_file_count)
for f in status.pending_files:
    run = f.last_run
    print(f.relative_path, f.ingestion_status, run and (run.status, run.invocation_id, run.detail))
```

`run.status` is `running`, `failed`, or `finished`, and `run.invocation_id` is the ingestion invocation to debug.

## Re-running on the same inputs

Both forms create one invocation in the org. Give the command and wait for the user's yes. Never pass the original `idempotency_id`.

The CLI form rebuilds the request from `rich_input_data`. `--log-level` reaches the action as `ROBOTO_LOG_LEVEL`:

```bash
roboto --suppress-upgrade-check --log-level=debug actions invoke <owner_org>/<action> \
  <--dataset ds_xxx --file-path <path> ... | --file-query '<q>' | --topic-query '<q>' | --session-id se_xxx ... | --session-query '<q>'> \
  -p <name>=<value> ... [--output-dataset-id ds_xxx] [--timeout <minutes>] [--org og_xxx]
```

`-p` sends every value as a string. A query is resolved again at re-run time, so compare what the new run took with the original's (SKILL.md Phase 4, step 3). A selector by `ids` or `names`, which a trigger-started run records, has no CLI flag: use the SDK form. `roboto actions invoke` always sends `ROBOTO_LOG_LEVEL` as a container environment override, even without `--env`. If it is refused with a message that the action "starts no customer container to apply them to", the action has no container (a Python action): use the SDK form below with the two marked lines deleted.

The SDK form copies the original record, including the exact resolved inputs, and runs the action's latest version:

```python
import sys
from roboto import Action, Invocation, InvocationSource

old = Invocation.from_id(sys.argv[1])
src = old.data_source
container = old.container_parameters.model_copy(deep=True)
container.env_vars = {**(container.env_vars or {}), "ROBOTO_LOG_LEVEL": "DEBUG"}
action = Action.from_name(old.action.name, owner_org_id=old.action.org_id)
new = action.invoke(
    invocation_source=InvocationSource.Manual,
    input_data=old.resolved_input_data or old.input_data,
    data_source_id=None if src.is_unspecified() else src.data_source_id,
    data_source_type=None if src.is_unspecified() else src.data_source_type,
    parameter_values=old.parameter_values,
    compute_requirement_overrides=old.compute_requirements,  # delete for a Python action
    container_parameter_overrides=container,  # delete for a Python action
    timeout=old.timeout,
    upload_destination=old.upload_destination,
    caller_org_id=old.org_id,
)
print(new.id)
```

For a Python action, delete the two marked lines. Its compute is fixed, and an invocation that asks for more vCPU or memory, or for a storage size, is refused; it also takes no container parameters. `ROBOTO_LOG_LEVEL` changes the output only of an action that applies `InvocationContext.log_level` to its logger.
