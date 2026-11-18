# Issue sync API map

What an issue-sync action reads, where it records the issue, and how its tracker client is shaped. Phase 0 uses it to check that findings exist, Phase 1 to run the interview, and Phase 3 to write the code.

Every signature and CLI flag below was checked against the SDK release recorded as `verified-sdk` in the `metadata` block of `SKILL.md`, by `uv run --with 'roboto[analytics]==<verified-sdk>' python -c ...` printing `inspect.signature` and `__doc__`, and by `python -m roboto.cli <group> <command> --help` from the same release, on the date recorded as `verified-on`. The link snippet was run against that release. The dataset and session paths, the stamp, the secret handling, and the link snippet were also run end to end through `invoke-local` against a live org on that date, with a local fake of the GitHub issues API standing in for the tracker; the `list_events` exception below was observed there. The `/open` link form was checked against the web app's source, not in a browser, and the tracker sections against no real tracker: Phase 0 checks the first and Phase 4 the second. A newer release can change any of it: re-check what you use against source 1 of SKILL.md's "Sources, in order of authority". Where this file and a live source disagree, the live source wins.

## Durable references

These paths are stable; prefer them over search results.

| Resource | URL |
|---|---|
| Actions and triggers | https://www.roboto.ai/docs/learn/actions |
| Create your own action | https://www.roboto.ai/docs/user-guides/process-data-actions/creating-your-own-action |
| `action.json` reference | https://www.roboto.ai/docs/reference/action-json |
| Secrets | https://www.roboto.ai/docs/learn/secrets |
| `InvocationContext` | https://www.roboto.ai/docs/reference/python-sdk/roboto/action_runtime/invocation_context |
| `ActionInput` | https://www.roboto.ai/docs/reference/python-sdk/roboto/action_runtime/action_input/action_input |
| `Session` | https://www.roboto.ai/docs/reference/python-sdk/roboto/experimental/sessions/session |
| Dataset `Event` | https://www.roboto.ai/docs/reference/python-sdk/roboto/domain/events/event |
| `Secret` | https://www.roboto.ai/docs/reference/python-sdk/roboto/domain/secrets/secret |
| `roboto.uri` | https://www.roboto.ai/docs/reference/python-sdk/roboto/uri |
| SDK source | https://github.com/roboto-ai/roboto-python-sdk |
| Project template source | https://github.com/roboto-ai/cookiecutter-roboto-actions |

## How the invocation reaches the entity

| Invocation | Where the entity comes from | `context.dataset` |
|---|---|---|
| `invoke-local --dataset ds_...`, `actions invoke --dataset ds_...`, or a trigger on a file or dataset event | `context.dataset`; input files, if any, in `get_input().files` | The dataset |
| `--session-id se_...` (repeatable) or `--session-query`, or a trigger target whose `invocation_input` selects a session, such as `{{session.session_id}}` on `session.ingested` | `context.get_input().sessions`, a list of `Session` | Raises `ActionRuntimeException`, imported with `from roboto.action_runtime import ActionRuntimeException` (it is not in `roboto.exceptions`) |
| A trigger on `event.created` or `session_event.created`, or a schedule | Whatever the target's `invocation_input` selects | Raises `ActionRuntimeException` |

The session selectors and the dataset selectors are mutually exclusive on the CLI. An action keyed on sessions loops over `get_input().sessions` and handles an empty list by logging and returning.

## Where findings come from

| Entity | Finding | Call | Notes |
|---|---|---|---|
| Session | Tags, such as the labels a `SessionTriageGoal` agent applies | `session.tags` | `from roboto.experimental.sessions import Session` |
| Session | AI summary | `session.get_summary()` | Raises `RobotoNotFoundException` when the session was never summarized |
| Session | Events | `session.list_events(start_time=None, end_time=None)` | Yields `roboto.experimental.events.Event`. In an org without session events enabled, the call raises `RobotoFeatureNotAvailableException` rather than yielding nothing; it did so in an org whose `users orgs` record shows `"event_model": "legacy"` |
| Session | Metadata | `session.metadata` | Not filterable or sortable in RoboQL |
| Dataset | Tags, metadata | `dataset.tags`, `dataset.get_metadata()` | |
| Dataset | AI summary | `dataset.get_summary()` | Raises `RobotoNotFoundException` when never summarized |
| Dataset | Events | `roboto.Event.get_by_dataset(dataset_id)` | |
| File | Tags, metadata | `file.tags`, `file.metadata` | |
| Any | Events by query | `RobotoSearch.for_roboto_client(context.roboto_client, context.org_id).find_events(query)` | Yields dataset events and, where enabled, session events; add `session_id IS_NULL` for dataset events only |

Both `get_summary()` calls return a `StreamingAISummary`. Its `complete_text` waits with no time limit while the summary is still generating; call `await_completion(timeout_s=...)` instead, which returns an `AISummary` (`text`, `status`) or raises the built-in `TimeoutError`, or `RobotoFailedToGenerateException` for a generation that fails while it waits. A summary that had already failed when `get_summary()` read it is returned with `status` `failed`, not raised, so check `status` before using `text` (rule 15).

A read-only script for Phase 0, run as `uv run check_findings.py se_...`:

```python
# /// script
# dependencies = ["roboto"]
# ///
import sys
import warnings

from roboto.warnings import ExperimentalWarning

warnings.filterwarnings("ignore", category=ExperimentalWarning)

from roboto.exceptions import RobotoFeatureNotAvailableException, RobotoNotFoundException  # noqa: E402
from roboto.experimental.sessions import Session  # noqa: E402

session = Session.from_id(sys.argv[1])
print("tags:", session.tags)
print("metadata:", session.metadata)
try:
    for event in session.list_events():
        print("event:", event.event_id, event.name, event.start_time, event.end_time, event.tags)
except RobotoFeatureNotAvailableException:
    print("events: session events are not enabled in this org")
try:
    summary = session.get_summary().await_completion(timeout_s=60)
    print("summary:", summary.status, summary.text[:500])
except RobotoNotFoundException:
    print("summary: none")
```

## The stamp

The stamp is two metadata keys on the entity that defines identity: the issue's identifier, in the form the tracker's update endpoint takes, and its URL. Record the tracker project as well, so a stamp written for one project reads as absent for another. Dots in a metadata key create nested fields, so use keys without dots, such as `issue_sync_id`, `issue_sync_url`, and `issue_sync_project`.

| Entity | Write | Returns | Read back |
|---|---|---|---|
| Session | `session.put_metadata(dict)` | The `Session`, refreshed from the server | `session.metadata`; `Session.from_id(id)` for a fresh copy |
| Dataset | `dataset.put_metadata(dict)` | `None` | `dataset.get_metadata()`; `dataset.refresh()` first for a fresh copy |
| File | `file.put_metadata(dict)` | The `File`, with its record replaced | `file.metadata`; `file.refresh()` |
| Dataset event (`roboto.Event`) | `event.put_metadata(dict)` | The `Event` | `event.metadata`; `event.refresh()` |
| Session event (`roboto.experimental.events.Event`) | `event.put_metadata(dict)` | The `Event` | `event.metadata`; `event.refresh()` |

The `Session` objects in `get_input().sessions` are built from records captured when the invocation was set up, so read the stamp from a fresh copy (rule 18). Creating the issue and writing the stamp are two remote writes with nothing making them atomic; rules 7 and 8 cover the gap.

## Parameters and secrets

- `context.get_optional_parameter(name, default_value=None)` returns `default_value` when the parameter is unset, and resolves a `roboto-secret://` value.
- `context.get_parameter(name)` raises `ActionRuntimeException` when the parameter is unset.
- `context.get_secret_parameter(name)` raises `ActionRuntimeException` when the resolved secret is missing.
- Every value arrives as a string.

Pass a secret as `roboto-secret://<secret-name>` (the caller's org) or `roboto-secret://<secret-name>@<org_id>`. The secrets page in the docs documents the form; `roboto secrets --help` does not. `invoke-local` resolves secret URIs before the container starts, and a URI naming a secret that does not exist stops the run with "Failed to retrieve secret <uri>, because it does not exist."

`roboto secrets write <name> <value>` takes the value as a positional argument, which puts the token in the process list and the shell history. Create the secret through the web app (Settings, Secrets tab) or with the SDK, reading the value from the environment. Both are writes to the user's org, so they are the user's to run:

```bash
read -rs TRACKER_TOKEN && export TRACKER_TOKEN
uv run --with roboto python -c 'import os; from roboto.domain.secrets import Secret; Secret.create(name="<secret-name>", caller_org_id="<og_...>", initial_value=os.environ["TRACKER_TOKEN"])'
```

`Secret.create` raises `RobotoConflictException` when the name exists; rotate with `Secret.from_name("<secret-name>", org_id="<og_...>").update_value(...)` the same way. The docs page's `from roboto import Secret` raises `ImportError`; import from `roboto.domain.secrets`.

## Links

`roboto.uri.RobotoUri(type=RobotoUriType.Session, id=...)` renders `roboto://session/se_...`, Roboto's reference to an entity that names no web address; AI summaries contain them. The web app opens one passed to its `/open` page as a percent-encoded `uri` query parameter. Phase 0 confirms that form against the user's web app. Keep the web app address a parameter, defaulting to `https://app.roboto.ai`.

```python
import re
import urllib.parse

from roboto.uri import ROBOTO_URI_IN_TEXT_PATTERN, RobotoUri, RobotoUriType


def web_link(uri: str, web_app_url: str) -> str:
    return f"{web_app_url.rstrip('/')}/open?uri={urllib.parse.quote(uri, safe='')}"


def rewrite_roboto_uris(markdown: str, web_app_url: str) -> str:
    def replace(match: re.Match) -> str:
        uri = match.group(0).rstrip(".")
        return web_link(uri, web_app_url) + match.group(0)[len(uri) :]

    return ROBOTO_URI_IN_TEXT_PATTERN.sub(replace, markdown)


session_link = web_link(str(RobotoUri(type=RobotoUriType.Session, id="se_...")), "https://app.roboto.ai")
```

`ROBOTO_URI_IN_TEXT_PATTERN` matches a URI followed by a sentence's closing period, and takes the period into the URI. `replace` strips trailing dots from the match before encoding and puts them back after the link. `RobotoUriType` also has `Dataset`, `File`, `Event`, `Invocation`, `Topic`, and others; a `?t=` timestamp in the URI opens a time-aware page at that instant.

## The tracker client

Four operations, each with a timeout and each returning a result instead of raising into `main` (rules 17 and 20).

| Operation | Purpose | Behavior |
|---|---|---|
| Create | File an issue with title, body, labels | Returns the identifier and URL to stamp |
| Fetch one | Confirm a stamped issue still exists | Not found means create; any other failure means assume it exists (rule 6) |
| Update | Overwrite title, body, labels | |
| Set state | Close or reopen | A no-op when the issue is already in that state |

Check each of these against the tracker in front of you, by its responses:

- **Authentication.** Header names and token formats differ, and so does an insufficient permission: a clear 403, or a 404 that reads as "no such project".
- **Project identity.** A numeric ID, a slug, a `group/project` path, or a key. Path forms usually need URL-encoding, including the slash.
- **Unknown labels.** Created on first use, rejected, or dropped while the issue is created (rule 14).
- **A deleted issue.** What fetching one returns (a 404, a 410, or a redirect for a moved issue), and whether deleting an issue needs more permission than the token has. The sync decision's "not found" branch must match the first; Phase 4 Step 3's deleted-issue check needs the second, or a person who can delete.
- **State on create.** Some trackers cannot create a closed issue, so a closed record is create then close.
- **Body format.** Markdown dialects differ in tables and links.
- **Rate limits and search.** Limits differ by plan. Whether issue search finds a marker string, and how soon after a create, decides whether rule 8's search narrows the duplicate window.

## The issue body

- A header naming the entity, with its link, and a link to the invocation built from `context.invocation_id` (rule 10).
- One marker line holding the entity's `roboto://` URI as plain text, which rule 8's search looks for.
- The findings: prose where the source is prose, such as a summary with its `roboto://` references rewritten, and a table for structured findings, such as events with their times or tags with what they mean.

## The sync decision

```
read the entity fresh, then its stamp for this project
├─ absent  -> search the tracker for the marker (rule 8)
│             ├─ found  -> stamp it, then update
│             └─ none   -> create, then stamp and confirm (rule 7)
└─ present -> fetch the issue
              ├─ exists             -> update body and labels, then set state
              ├─ not found          -> create, then re-stamp
              └─ check failed       -> assume it exists, update (rule 6)
```

State follows the clean-result posture (rule 9): a run with no findings closes, a run with findings reopens.
