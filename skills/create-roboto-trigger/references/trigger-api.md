# Trigger API map

The trigger surface this skill builds on: what Phase 1 needs to run the interview, and what Phases 2 to 4 call.

Every signature, field, enum member and flag below was checked against the SDK release recorded as `verified-sdk` in the `metadata` block of `SKILL.md`, on the date recorded as `verified-on`. Signatures, fields and enum members were printed with `uv run --no-project --isolated --refresh-package roboto --with 'roboto[analytics]' python -c ...` (`inspect.signature`, `model_fields`, and the enum members); flags with `python -m roboto.cli triggers <command> --help`; the event table was read from the SDK's platform event catalog; the input rules come from "Triggers" on https://www.roboto.ai/docs/learn/actions and from the SDK CHANGELOG. The `TriggerValidator` refusals that SKILL.md Phase 3 lists, and the condition matching behind the Phase 4 guard, were run locally against that release, with no request sent to Roboto. A newer release can change any of it: re-check what you use against source 1 of SKILL.md's "Sources, in order of authority". Where this file and a live source disagree, the live source wins.

## Durable references

These paths are stable; prefer them over search results.

| Resource | URL |
|---|---|
| Triggers concept guide (platform events, conditions, targets, required inputs, fire once per, testing, dispatch history) | https://www.roboto.ai/docs/learn/actions |
| `roboto triggers` CLI | https://www.roboto.ai/docs/reference/cli/triggers |
| `roboto.domain.triggers` | https://www.roboto.ai/docs/reference/python-sdk/roboto/domain/triggers |
| `roboto.domain.platform_events` | https://www.roboto.ai/docs/reference/python-sdk/roboto/domain/platform_events |
| `InvocationInput` | https://www.roboto.ai/docs/reference/python-sdk/roboto/domain/actions/invocation_record |
| Sessions (`roboto.experimental.sessions`) | https://www.roboto.ai/docs/reference/python-sdk/roboto/experimental/sessions |
| RoboQL | https://www.roboto.ai/docs/roboql/overview |
| SDK CHANGELOG (session events, ingestion rules) | https://raw.githubusercontent.com/roboto-ai/roboto-python-sdk/refs/heads/main/CHANGELOG.md |
| SDK source | https://github.com/roboto-ai/roboto-python-sdk |

## The model

A trigger is a firing source, an optional condition, and one or more targets. Import it from `roboto.domain.triggers`. `from roboto import Trigger` and `roboto.domain.actions.Trigger` are the legacy `causes`/`for_each` model, and `roboto.domain.actions.ScheduledTrigger` is the legacy schedule model; both raise `DeprecationWarning` and are not used here.

| Part | SDK type | Notes |
|---|---|---|
| Firing source | `EventSubscription(events=[...], once_per=...)` or `Schedule(cron="0 9 * * 1")` | `Trigger.create` also takes the shorthands `events=` with `once_per=`, or `schedule=`; exactly one source |
| Condition | `roboto.query.Condition` or `ConditionGroup` | JSON form `{"field": "dataset.tags", "comparator": "CONTAINS", "value": "x"}`, or `{"operator": "AND", "conditions": [...]}` |
| Targets | `InvokeActionTarget` (this skill), `StartAgentTarget`, `SendSlackMessageTarget` | Discriminated on `type`; each `target_id` is unique in the trigger |
| Name | `str` | Letters, digits, `_` and `-`; at most 256 characters |

Triggered work runs as the organization's service user, not as the person who saved the trigger.

## Platform events

| Event (`--on`) | `once_per` offered | Roots for conditions and `{{ }}` | Names a dataset |
|---|---|---|---|
| `file.uploaded` | `file`, `dataset`, `occurrence` | `dataset`, `file` | yes |
| `file.ingested` | `file`, `dataset`, `occurrence` | `dataset`, `file` | yes |
| `file.metadata_updated` | `file`, `dataset`, `occurrence` | `dataset`, `file`, `changed`, `tag` | yes |
| `dataset.created` | `dataset`, `occurrence` | `dataset` | yes |
| `dataset.metadata_updated` | `dataset`, `occurrence` | `dataset`, `changed`, `tag` | yes |
| `dataset.tag_added` | `occurrence` | `dataset`, `tag` | yes |
| `dataset.upload_completed` | `dataset`, `occurrence` | `dataset`, `upload` | yes |
| `invocation.completed`, `invocation.failed` | `invocation`, `occurrence` | `invocation`, `action` | no |
| `session.ingested` | `occurrence` | `session` | no |
| `event.created` | `event`, `occurrence` | `event` | no |
| `session_event.created` | `event`, `occurrence` | `event`, `session` | no |
| Schedule (`--schedule`) | `occurrence`, fixed | `schedule` | no |

`envelope.*` (the event's id, type, time, and its payload under `envelope.data`) and `trigger.*` are available on every event. All subscribed events must be about one kind of entity. `session.ingested` fires when a complete session has every ingestable file ingested, and fires again, as a new occurrence numbered by `ingestion_number`, each time its ingestable files change and are all ingested again. `session_event.created` fires for events created on a session; session events must be enabled for the org.

## What the action receives

| Firing | Data source | Input |
|---|---|---|
| File event at `once_per` `file` or `occurrence` | The file's dataset | That file, if it matches any `required_inputs` pattern; plus files matching `additional_inputs`; plus what `invocation_input` selects |
| Dataset event, or any event that names a dataset at `once_per=dataset` | The dataset | Waits until every `required_inputs` pattern has a file of its own (on `file.ingested`, each pattern is checked on its own, and every matching file must be ingested); then the files matching the patterns, or the `additional_inputs` files plus what `invocation_input` selects when that is set |
| Event that names no dataset, or a schedule | None | Only what `invocation_input` selects; `required_inputs` and `additional_inputs` must be empty |

## `InvokeActionTarget`

| Field | Type | Notes |
|---|---|---|
| `target_id` | `str` | Required. Once-per history is kept under it; a new id fires again for subjects the old one handled |
| `action` | `ActionReference(name, digest=None, owner=None)` | `owner` defaults to the trigger's org, `digest` to the latest version |
| `required_inputs` | `list[str]` | Git wildmatch patterns on the path within the dataset, such as `**/*.mcap`; only for events that name a dataset |
| `additional_inputs` | `list[str]` or `None` | Extra files passed to the action; only for events that name a dataset |
| `invocation_input` | `InvocationInput` or `None` | `InvocationInput.from_session_id(id)`, `.session_query(q)`, `.file_query(q)`, `.topic_query(q)`, `.from_dataset_file_paths(ds, paths)` |
| `parameter_values` | `dict` | String leaves may hold `{{root.path}}` placeholders |
| `timeout` | `int` or `None` | Minutes |
| `compute_requirement_overrides`, `container_parameter_overrides` | | Override the action's defaults for triggered runs |
| `upload_destination` | `InvocationUploadDestination` or `None` | A dataset the person saving the trigger may upload to; otherwise the save raises `RobotoUnauthorizedException` |

Placeholders work in string leaves of `parameter_values`, `invocation_input`, `required_inputs` and `additional_inputs`. Inside a RoboQL `query`, a placeholder must sit inside a quoted value: `dataset_id = "{{dataset.dataset_id}}"`.

## SDK calls

| Call | Behavior |
|---|---|
| `Trigger.create(name, targets, *, events, once_per, schedule, fires_on, condition, enabled=True, caller_org_id)` | `RobotoConflictException` when the name is taken; `RobotoInvalidRequestException` on a validation failure |
| `Trigger.from_name(name, owner_org_id)`, `Trigger.from_id(trigger_id)`, `Trigger.list(owner_org_id)` | Read; `list` includes managed triggers (`record.managed_by` set), which cannot be edited |
| `trigger.update(*, name, fires_on, events, once_per, schedule, condition, targets, enabled)` | Partial; `condition=None` clears it; `RobotoLimitExceededException` when enabling would pass the org's active-trigger limit |
| `trigger.enable()`, `trigger.disable()`, `trigger.delete()` | `delete` also removes the dispatch history |
| `trigger.dry_run(event=None, dataset_id=, file_id=, invocation_id=, event_id=, event_type=, scheduled_for=)` | Read-only gate trace: `TriggerDryRunResponse(would_fire, verdict, gates)` |
| `trigger.dispatches(limit=100)` | `TriggerDispatchRecord`s, newest first; only matches are recorded |
| `Trigger.platform_event_samples()` | One `PlatformEventSample` per event type, with `.paths` |
| `TriggerValidator().validate(fires_on=, condition=, targets=)` | Local, no network; raises `ValueError` naming the rule that failed |

## CLI

| Command | Flags |
|---|---|
| `roboto triggers create` | `--name`; `--on EVENT...` with `--once-per`, or `--schedule CRON`; `--targets-json` (inline or a file path); `--condition-json`; `--disabled`; `--org` |
| `roboto triggers update NAME` | `--new-name`, `--on`, `--once-per`, `--schedule`, `--targets-json`, `--condition-json` or `--clear-condition`, `--org` |
| `roboto triggers get`, `enable`, `disable`, `delete` NAME; `roboto triggers list` | `--org` |
| `roboto triggers dry-run NAME` | One of `--dataset-id`, `--file-id`, `--invocation-id`, `--event-id`, `--scheduled-for`; `--on EVENT` picks the event to synthesize; `--org` |
| `roboto triggers sample EVENT` | `--paths` prints only the `root.path` names |

The CLI has no command for dispatches; read them with `trigger.dispatches()`. A dry run cannot synthesize `session.ingested` from a reference; pass a full `PlatformEvent` to `trigger.dry_run(event=...)`.

## Dry-run gates and dispatch statuses

| Gate | Fails when |
|---|---|
| `subscribed` | The trigger does not subscribe to the event's type |
| `enabled` | The trigger is disabled; every later gate is then `not_evaluated` |
| `condition` | A leaf does not hold; every leaf is listed with the value it saw, even when another leaf fails |
| `target_prefilter` | No target accepts the event; the reason names the cause, such as a file uploaded before the trigger was created, a file not yet ingested on `file.ingested`, or a path matching no pattern |
| `already_fired` | Every accepting target already has a dispatch at this `once_per` that did not fail; expected on a file that already fired the trigger |

| Dispatch status | Meaning |
|---|---|
| `claimed` | The target is about to run |
| `dispatched` | The target ran; `result_ref` is the invocation ID |
| `failed` | The target raised; `status_detail` holds the error |
| `unknown` | The outcome could not be determined |
