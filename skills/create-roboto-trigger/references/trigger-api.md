# Trigger API surface

A map for running the Phase 1 interview and knowing what to look up. This file is rung 4 of SKILL.md's Ground truth ladder — the lowest. Confirm anything you are about to write against the installed SDK (rung 1) or `roboto triggers <verb> --help` (rung 2) before writing it.

## Durable documentation URLs

- Triggers, causes, for-each, and conditions: `https://docs.roboto.ai/learn/actions.html`
- Trigger CLI reference: `https://docs.roboto.ai/reference/cli.html#roboto-triggers`
- Python SDK reference: `https://docs.roboto.ai/reference/python-sdk.html`
- Invocation CLI reference: `https://docs.roboto.ai/reference/cli.html#roboto-invocations`

## Two trigger classes

| | `Trigger` | `ScheduledTrigger` |
|---|---|---|
| Fires on | A data event (its *cause*) | A cron schedule |
| Import | `from roboto.domain.actions import Trigger` | `from roboto.domain.actions import ScheduledTrigger, TriggerSchedule` |
| CLI | `roboto triggers ...` | Not managed by `roboto triggers` |
| Distinctive fields | `causes`, `for_each`, `required_inputs`, `condition` | `schedule`, `next_occurrence`, `invocation_input` |

Both cap against the organization's limit on active triggers.

`TriggerSchedule` builds the schedule value; `TriggerSchedule.cron("*/30 * * * *")` validates the expression at construction time, and named constructors exist for common schedules. Read the class for the current set rather than guessing a name.

## `Trigger.create`

Confirm the signature before calling it:

```bash
python -c "import inspect; from roboto.domain.actions import Trigger; print(inspect.signature(Trigger.create))"
```

The parameters that carry Phase 1's decisions:

| Parameter | Carries | Notes |
|---|---|---|
| `name` | The trigger's identity | Unique within the organization; how every later command addresses it |
| `action_name` | Which action to invoke | By name, resolved at evaluation time — not a pinned copy |
| `action_owner_id` | Whose action | Needed when the action belongs to another org |
| `action_digest` | Which version | Omit to track the latest version of the action |
| `required_inputs` | The Required inputs axis | List of glob patterns, validated as non-empty path specs |
| `additional_inputs` | The Additional inputs axis | Downloaded, but not considered when matching |
| `for_each` | The For-each axis | A `TriggerForEachPrimitive` member |
| `causes` | The Cause axis | **Not exposed by the CLI.** Omitting it accepts a server-side default |
| `condition` | The Condition axis | A `Condition` or `ConditionGroup` from `roboto.query` |
| `parameter_values` | The Parameters axis | Dict passed through to each invocation |
| `enabled` | Whether it is live on creation | **Not exposed by the CLI's `create`.** Pass `False` to author safely |
| `compute_requirement_overrides`, `container_parameter_overrides`, `timeout` | The Overrides axis | Override the action's own settings per invocation |
| `caller_org_id` | Which org owns it | Required in practice when the user belongs to more than one |

## Instance surface

Read the class for the full set. The members this skill's phases depend on:

- `enable()` / `disable()` — the safe-authoring pair behind rule 2
- `update(...)` — converges an existing trigger; takes the same fields, `NotSet` for anything left alone
- `delete()`
- `wait_for_evaluations_to_complete(timeout=..., poll_interval=...)` — blocks rather than sleeping a guessed interval; raises on timeout
- `latest_evaluation()` — the most recent evaluation record, or `None`
- `get_evaluations(limit=..., page_token=...)` — the evaluation history, newest first
- `get_invocations()` — the invocations this trigger produced
- `get_action()` — the action it targets
- `invoke(data_source, ...)` — invoke as if the trigger had fired; returns `None` when an idempotency id collides with an existing invocation
- `to_dict()` — the record as JSON, which is what Phase 3 writes to `<trigger-name>.json`
- Properties including `condition`, `enabled`, `for_each`, `name`, `org_id`, `trigger_id`, and `record`

Static and class methods: `Trigger.from_name(name, ...)`, `Trigger.query(spec, ...)`, and `Trigger.get_evaluations_for_dataset(dataset_id, ...)` — the last being how you learn whether *any* trigger evaluated a given dataset, which is the right question when your own trigger appears not to have been evaluated at all.

## The evaluation vocabulary

This is what Phase 4 reads. Every member below must be confirmed against the installed enum before you branch on it.

**`TriggerEvaluationCause`** — why the trigger was evaluated. Configure these via `causes`:

| Member | Fires when |
|---|---|
| `FileUpload` | A file is uploaded to a dataset |
| `FileIngest` | A file finishes ingestion |
| `DatasetMetadataUpdate` | Dataset metadata, tags, or description change |
| `FileMetadataUpdate` | A file's tags or metadata change |
| `RecurringSchedule` | Reserved for the platform's own use with `ScheduledTrigger`. Passing it to `Trigger.create` is an error |

**`TriggerEvaluationStatus`** — how far the evaluation got: pending, completed, or failed with an unexpected exception. A failed evaluation carries `status_detail`, which is where the exception surfaces.

**`TriggerEvaluationOutcome`** — what the completed evaluation decided: it either invoked the action or skipped.

**`TriggerEvaluationOutcomeReason`** — why a skip happened. Each member maps to one misconfiguration:

| Reason | Meaning |
|---|---|
| `NoMatchingFiles` | Nothing satisfied `required_inputs`. Semantics differ by `for_each` — see rule 4 |
| `ConditionNotMet` | The condition excluded this data source |
| `AlreadyRun` | The action has already run for this dataset or file |
| `TriggerDisabled` | The trigger is not enabled |

**`TriggerEvaluationRecord`** — the record itself, carrying the trigger id, the data source, the evaluation window, and the `status` / `outcome` / `outcome_reason` / `cause` fields above.

## Known discrepancies

Resolve these against rung 1 when they matter, and report what you found:

- **Docstring examples in the trigger module reference members that do not exist**, including an evaluation status member and a `trigger_name` attribute on the evaluation record. Read the enum and the record model; do not copy the example.
- **What a condition may reference** is stated inconsistently. The CLI describes conditions as dataset tag and metadata expressions; the SDK's prose is broader. If the trigger's correctness depends on a condition over file properties rather than dataset properties, do not assume — verify it in Phase 4 with a negative-path event, and record what you observed in `SPEC.md`.
- **The default `causes` set** when the parameter is omitted is not specified here. Read it back from the created trigger's record.

## CLI

Verbs: `create`, `update`, `get`, `search`, `delete`. Confirm flags with `--help`; the ones that shape a trigger are `--name`, the action reference, `--required-inputs`, `--additional-inputs`, `--for-each`, `--parameter-value`, `--timeout`, `--org`, and the condition flags below, plus compute and container override flags.

Conditions on the CLI come in two mutually exclusive forms. `--required-tag` and `--required-metadata` build a simple all-must-hold group for you; `--condition-json` takes a full expression as inline JSON or a path to a JSON file, parsed as a group when it carries an operator and as a single condition when it carries a comparator. Supplying both forms is an error.

`update` additionally carries `--enabled`, `--disabled`, and `--clear-condition`, and takes the trigger name positionally.

Two gaps drive Phase 2's choice of surface: **no flag sets `causes`**, and **`create` cannot create a disabled trigger**. Confirm both against `--help` before relying on them; if a flag has since appeared, the CLI becomes a viable authoring surface and this file is out of date.
