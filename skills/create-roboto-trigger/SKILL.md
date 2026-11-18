---
name: create-roboto-trigger
description: >-
  Create and verify a Roboto trigger that runs an existing action on a platform
  event or on a schedule. Use this skill whenever the user wants an action to
  run by itself, even if they only describe the outcome ("summarize every MCAP
  file once it is ingested", "check each session after it finishes ingesting",
  "rerun the fleet report every Monday morning") without saying "trigger".
  Covers decomposition, an ambiguity-resolving interview (skipped under
  --yolo), a reproducible trigger script, offline validation, and verification
  by dry runs and a test dispatch on a trigger pinned to one test subject. Not
  for writing the action itself (use the create-roboto-action skill), not for
  an invocation that already failed (use the debug-roboto-invocation skill),
  and not for general Roboto questions or one-off scripts (use the roboto-guide
  skill).
license: MPL-2.0
compatibility: >-
  Needs a shell and network access to www.roboto.ai, pypi.org,
  files.pythonhosted.org, raw.githubusercontent.com, and api.github.com. Needs
  uv (or Python 3.10+ with pip), the roboto CLI, and Roboto credentials. The
  action the trigger runs must already exist in Roboto; Docker is not needed.
metadata:
  verified-sdk: "0.64.0"
  verified-on: "2026-11-18"
argument-hint: <natural-language description of what should run automatically, and when> [--yolo]
---

Turn "this should run by itself" into a Roboto trigger that is shown to fire on the data it should and to skip the data it should not, and that lives as a script in version control rather than as a command someone typed once.

## What you need to run this

This skill does not know which agent is reading it, so it names the capabilities it needs rather than assuming them:

- **Run shell commands** and read their output.
- **Read and write files.**
- **Hold a back-and-forth with the user.** Phase 1 is an interview, and every write to the org waits for the user's yes.
- **Fetch a web page**, optionally. `curl` does the same.

uv is the preferred runner because it resolves the latest SDK on every run. Without uv, build one virtual environment for the session (`python3 -m venv`, then `pip install --upgrade 'roboto[analytics]'`) and use its interpreter wherever this skill says `uv run`.

`references/` throughout means the directory alongside this file. Read `references/trigger-api.md` and `references/authoring-rules.md` before Phase 1; Phase 2 reads `references/script-template.md` and `references/spec-template.md`.

## The request

The user's description of what should run automatically is the argument to this skill. Strip a `--yolo` flag from anywhere in it; what remains is the description. If the description is empty, ask the user which action should run, and on what, and stop.

`--yolo` suppresses the Phase 1 interview and nothing else. The preflight, the offline checks, the verification gate, the review pass, and the recording of decisions all stand: every ambiguity resolved by judgment lands in `SPEC.md` with its rationale, so the user audits the decisions after the fact instead of before.

`--yolo` never authorizes a write to the user's organization. Creating the guarded trigger, creating a scratch dataset, uploading test files, disabling the trigger, and putting it live all stay the user's call: give the exact command and wait for a yes.

Some requests sound like this one and are not. Say so and stop for each:

- Work that no action performs yet belongs to the `create-roboto-action` skill.
- Ingesting every file of a format as it is uploaded is the job of an org's ingestion rules (experimental, set up by an org admin, each owning its own trigger); an action for a format Roboto cannot read yet belongs to the `create-roboto-ingestion-action` skill.
- Starting an agent or posting to Slack uses a `start_agent` or `send_slack_message` target, which this skill does not build; the `roboto-guide` skill writes that command.
- Why an existing trigger did or did not fire is a `roboto triggers dry-run` question for the `roboto-guide` skill, and a failed invocation belongs to the `debug-roboto-invocation` skill. Changing a trigger once that cause is known is this skill's job: `trigger.py` updates a trigger in place.

## Sources, in order of authority

Three sources outrank every file in this skill. They are numbered by authority: when two disagree, the lower number wins. Start with the source whose Answers column fits the question, and stop at the first source that answers it.

| Source | What | How | Answers |
|---|---|---|---|
| 1 | The latest released SDK and CLI, resolved fresh from PyPI | `uv run --no-project --isolated --refresh-package roboto --with 'roboto[analytics]' python -c "import inspect; from roboto.domain.triggers import Trigger; print(inspect.signature(Trigger.create))"`; for CLI flags, `uv run --no-project --isolated --refresh-package roboto --with roboto python -m roboto.cli triggers create --help` | Exact signatures, parameter names, defaults, enum members, docstrings, CLI flags |
| 2 | The Roboto docs at www.roboto.ai/docs | Fetch `https://www.roboto.ai/docs/<path>.md`; see "Docs lookups" | Concepts, how-tos, RoboQL fields, REST endpoints |
| 3 | The SDK CHANGELOG and GitHub releases | Fetch https://raw.githubusercontent.com/roboto-ai/roboto-python-sdk/refs/heads/main/CHANGELOG.md and https://api.github.com/repos/roboto-ai/roboto-python-sdk/releases/latest | Which release added or changed a behavior; the latest version number |

Every lookup of the latest release runs with `--no-project --isolated`, so that a `uv run` started inside a Python project or virtual environment neither uses the `roboto` installed there (an older pinned release, for example) nor writes a `uv.lock` into the project, and with `--refresh-package roboto`, so that it does not reuse PyPI's answer from up to ten minutes earlier and miss a new release.

The files under `references/` rank below all three. The `metadata` block in this file's frontmatter records the SDK release (`verified-sdk`) and date (`verified-on`) they were last checked against. When Phase 0 finds a newer release, re-check anything you take from them against source 1 before using it. Cite the live source, not the reference file.

**Docs lookups.** To find a page, fetch `https://www.roboto.ai/docs/llms.txt`, which lists every page with its URL. To read one, fetch its Markdown copy by adding `.md` to the URL (`https://www.roboto.ai/docs/learn/actions.md`); without a fetch tool, `curl -sL <url>`. To find where an SDK symbol is documented, search `https://www.roboto.ai/docs/reference/python-sdk/objects.json` for its dotted name. For REST endpoints, read `https://www.roboto.ai/docs/reference/rest-api/openapi.json`. These files are large, so read them through a search (`grep`, or a Python one-liner) rather than printing them whole. If the agent runtime can start a subagent, run lookups in one and return only the answer.

- **The installed CLI and SDK are not authoritative.** They are whatever version the user last installed, and `roboto <command> --help` describes that version and nothing else. If the installed CLI is behind the latest release, say so and point to `roboto upgrade`; on a CLI older than 0.58.0, point to `brew upgrade roboto`, or to replacing the binary or `.deb` with the one from the latest release.
- **A docs page can be ahead of the release.** The docs site can describe a feature newer than the latest release. When source 2 describes something source 1 lacks, source 3 says whether it is released. Build against the release, and tell the user what is coming.
- **Recommend the API that fits the task.** Build on `roboto.domain.triggers`. `roboto.Trigger` and `ScheduledTrigger` in `roboto.domain.actions` are the legacy trigger model; name them only to say not to use them (rule 2). Sessions live in `roboto.experimental.sessions`, which the docs mark experimental; that is no reason to avoid a session trigger when the work is about a whole run.

Where a source cannot be reached, say which one, and tell the user what you could not check. When there is no fetch tool and no `curl`, ask the user to paste the page.

## Phase 0 — Preflight

Run this before the interview. Every check below guards a step that would otherwise fail after the user has spent time answering questions.

```bash
uname -s                                             # platform; decides POSIX vs Windows command forms
roboto --version                                     # installed CLI; compare with the latest release below
uv --version                                         # runner for source 1 and for trigger.py
roboto --suppress-upgrade-check users orgs           # credentials valid; one JSON object per org
curl -s https://pypi.org/pypi/roboto/json | python3 -c 'import json,sys; print(json.load(sys.stdin)["info"]["version"])'
roboto --suppress-upgrade-check actions show <action-name> --org <org-id>
roboto --suppress-upgrade-check triggers list --org <org-id>
```

- **`roboto --version`** below 0.56.0 speaks the legacy trigger flags (`--action`, `triggers search`), so this skill's `roboto triggers` commands fail on it. Stop and point to the upgrade. A CLI below 0.61.0 does not know `session.ingested`, and one below 0.63.0 does not know `session_event.created`, so `--on`, `dry-run --on` and `sample` refuse them.
- **`users orgs`** doubles as the credential check and the org inventory. With more than one org, every later command needs `--org`, and `trigger.py` needs `--org` or `ROBOTO_ORG_ID`. Never read `~/.roboto/config.json` to check credentials, and never print a token.
- **The PyPI version**, if newer than `verified-sdk`, means the references predate it; say so, and re-check what you take from them.
- **`actions show`** must find the action. Note its exact name, its owner org (an Action Hub action from another org needs `owner` in the target), and its parameters. `roboto actions search` lists candidates when the name is uncertain.
- **`triggers list`** shows whether a trigger already does this job and which names are taken. Triggers with `managed_by` set, such as `roboto-session-metrics`, belong to Roboto or to an ingestion rule and cannot be edited.

This skill runs on macOS and Linux; Windows is untested. If a check fails, stop and tell the user exactly what to install or run. Do not begin the interview.

## Phase 1 — Decompose and resolve

### Step 1: Decompose the description

Turn the description into a requirements table before asking anything. Each row is one testable behavior in the present tense, written as "given this event, the trigger fires" or "does not fire": "runs `summarize-mcap` once per `.mcap` file ingested into a dataset tagged `production`", not "handles MCAP files". A requirement that cannot be written that way belongs to the action, not the trigger.

Classify each row as **stated**, **implied** (the goal cannot be met without it, and only one reading is plausible; record the inference), or **ambiguous** (more than one reading changes what gets built).

### Step 2: Find the ambiguities

Walk these axes. Each changes the saved trigger, so an unresolved one becomes a guess that fires, or fails to fire, in the user's org. Answer what `references/trigger-api.md` or the docs answer yourself; do not spend an interview question on platform behavior.

| Axis | What is undetermined | Consequence of guessing wrong |
|---|---|---|
| Subject | A file, a dataset, a session (a whole run), an invocation, an event, or the clock? | Picks the event family; events about different kinds of entity need separate triggers (rule 8) |
| Event | Which event in that family? | The most common failure: an action that reads topics runs before ingestion (rule 6) |
| Grain | `once_per` file, dataset, or every occurrence? | Changes invocation count, re-run behavior, and what the action receives (rules 7, 11) |
| Required inputs | Which path patterns? | A file that never matches, or a dataset that waits for a file that never comes (rule 12) |
| Invocation input | On an event that names no dataset, what does the action read? | The action runs with no input (rule 13) |
| Condition | Which data is in scope, by which field? | No condition covers the whole org (rule 19); an unqualified field reads the wrong entity (rule 16) |
| Parameters | Which values does the action need? | Every firing ends in a `failed` dispatch, or the action runs with the wrong setting (rule 20) |
| Version and overrides | Pin the digest? Different compute, timeout, or output dataset? | A redeploy changes behavior (rule 21); an action sized for one file times out (rule 22) |
| Schedule | Which cron expression, and in which time zone was it meant? | Runs at the wrong hour (rule 9) |
| Test subject | Which data Phase 4 pins the trigger to | Answered by you, not asked: a scratch dataset, or a session, invocation or event the user names |

Also settle the trigger name if the description does not imply one (rule 5).

### Step 3: Resolve

**Without `--yolo`:** interview the user. Where your harness offers a structured multiple-choice prompt, use it for subject, event and grain; ask in prose for values only the user holds, such as patterns, tag keys, parameter values and the test session. Batch related questions, and lead each with your own recommendation so the user confirms rather than composes. Carry anything the description already answered as a stated guess to confirm, never as a settled fact.

Warn once, with the concrete failure, when an answer leads to one: an action that reads topic data on `file.uploaded` finds no topics; no condition with `'**/*'` fires for every upload in the org; `session.ingested` runs again on each announcement (rule 10). Then record whatever the user decides.

**With `--yolo`:** resolve every ambiguity yourself, keeping the trigger narrow and its misfires cheap: the most specific pattern the description supports, `file.ingested` whenever the action reads topic data, `once_per=file` for per-file work, a condition whenever the description names a scope, the action's defaults, the latest digest, and a scratch dataset as the test subject. Mark each choice as a default when you record it.

### Step 4: Confirm the plan

State, compactly: the trigger name, the requirements table, each resolution, the files you will write, and the writes Phase 4 will ask for. Under `--yolo`, present this as what you are about to build and continue. Otherwise, get the user's go-ahead.

## Phase 2 — Author

The deliverable is a directory, next to the action's project when there is one:

```
triggers/<trigger-name>/
├── trigger.py           # creates the trigger, or updates it in place; from references/script-template.md
├── SPEC.md              # from references/spec-template.md
└── <trigger-name>.json  # the saved trigger, written in Phase 4 from `roboto triggers get`
```

Fill in `NAME`, `FIRES_ON`, `CONDITION`, `TARGETS` and the docstring's first line in the `references/script-template.md` skeleton and keep the rest. Leave the verification rows of `SPEC.md` pending. Apply every rule in `references/authoring-rules.md` that bears on this trigger, and cite the rule number where a rule forced a choice.

## Phase 3 — Check offline

Nothing in this phase writes to the org. Each check catches a mistake that would otherwise surface only once the trigger is live, as a trigger that never fires or an invocation that fails.

### Step 1: Validate locally

```bash
uv run --upgrade-package roboto trigger.py --check
```

This runs the SDK's `TriggerValidator`, which applies the save's own rules locally. It refuses a `once_per` the event does not offer, events about two kinds of entity, a condition root the events do not expose, a condition on topics or message paths, file patterns on an event that names no dataset, a file-event target without the pattern it needs, an unquoted placeholder in a query, a placeholder root the events do not expose, and a duplicate `target_id`. Building the request then checks the name (rule 5). Fix what it reports and re-run until it prints the request.

### Step 2: Check every path the trigger reads

```bash
roboto --suppress-upgrade-check triggers sample <event> --paths
```

Every condition field and every `{{placeholder}}` must appear in that list, for every subscribed event (rule 17). For a schedule, the event is `schedule.fired`. The validator checks only the first segment, so a misspelled path passes Step 1.

### Step 3: Match the patterns against real paths

For a target with `required_inputs`, list the files of a dataset the trigger should fire on and test each pattern the way the platform does (rule 12):

```bash
uv run --with roboto python -c '
import sys
from roboto import Dataset
from roboto.paths import is_dotfile_path, pathspec_from_patterns
patterns = sys.argv[2:]
for f in Dataset.from_id(sys.argv[1]).list_files():
    hits = [p for p in patterns if pathspec_from_patterns([p]).match_file(f.relative_path)]
    print("IGNORED" if is_dotfile_path(f.relative_path) else (hits or "-"), f.relative_path)
' <ds_id> '**/*.mcap'
```

A per-file target needs the intended files to match a pattern and the others not to. A dataset target needs each pattern to have a file of its own.

### Step 4: Preview what the action will receive

When the target sets `invocation_input`, put a real value in each placeholder and run the selector's query read-only with a `LIMIT`, through `RobotoSearch.find_files`, `find_sessions` or `find_topics`; for `from_session_id`, load the session with `Session.from_id` (`roboto.experimental.sessions`). An empty result is an action that runs with no input.

### Step 5: Check parameters and scale

Every parameter the action marks required needs a value in `parameter_values` (rule 20). Then count, read-only with RoboQL, the files, datasets or sessions from the last 30 days that the condition and patterns would have matched. The trigger does not process older data (rule 15), so this is a rate, not a backlog; record it in `SPEC.md`.

## Phase 4 — Create and verify

A trigger is verified by dry runs that walk its gates against real data and by a dispatch it produced, not by reading it back. A dry run of a disabled trigger stops at the `enabled` gate, so verify an enabled trigger that a guard clause pins to one test subject (rule 23).

### Step 1: Pick the guard

`--guard FIELD=VALUE` ANDs `FIELD EQUALS VALUE` onto the condition, so the trigger fires only for the test subject. Check the field against `roboto triggers sample <event> --paths` (`schedule.fired` for a schedule).

| Fires on | `--guard` | Test subject | Live test |
|---|---|---|---|
| File events, dataset events | `dataset.dataset_id=<ds_id>` | A scratch dataset, created with the tags and metadata the condition needs (`datasets create -t ... -m ...`) | Upload files, or change tags or metadata; none for `dataset.created` |
| `session.ingested`, `session_event.created` | `session.session_id=<session-id>` | A session the user names | Only if the user lets you change that session |
| `invocation.completed`, `invocation.failed` | `invocation.invocation_id=<iv_id>` | An invocation that has already finished | None |
| `event.created` | `event.event_id=<ev_id>` | An existing event | None |
| Schedule | `schedule.scheduled_for=<YYYY-MM-DDTHH:MM:00Z>` | A past minute the cron expression matches | None |

A finished invocation, an existing event, and a past minute never fire again, so with those guards the trigger answers dry runs and does nothing else.

### Step 2: Create the guarded trigger

Ask for a yes, then run:

```bash
roboto --suppress-upgrade-check datasets create -n trigger-test-<trigger-name> -t <tags> --org <org-id>   # file and dataset events only
uv run trigger.py --org <org-id> --guard <FIELD=VALUE>
roboto --suppress-upgrade-check triggers get <trigger-name> --org <org-id> > <trigger-name>.json
```

Read `<trigger-name>.json` back: `enabled` must be `true` (rule 24), and the events, `once_per`, condition and targets must be the ones Phase 1 settled. A difference is a finding for the report.

### Step 3: Dry-run the condition against real data

Run a dry run against one real entity the trigger should fire for and one it should not, using the reference that fits the event (`--dataset-id`, `--file-id`, `--invocation-id`, `--event-id`; `--on <event>` picks the event when the trigger subscribes to several):

```bash
roboto --suppress-upgrade-check triggers dry-run <trigger-name> --file-id <file-id> --org <org-id>
```

The guard leaf misses for both, which is expected, but the `condition` gate lists every leaf with the value it saw. Read the leaves of the real condition: each should hold for the first entity, and the one you expect should miss for the second. An `actual` of `None` means the field path resolved to nothing (rules 16, 17).

`--scheduled-for <minute>` dry-runs a schedule. A dry run cannot synthesize `session.ingested` from a reference, so pass the event whole:

```python
import datetime
from roboto.domain.platform_events import PlatformEvent, PlatformEventType, SessionIngestedPayload, platform_event_source
from roboto.domain.triggers import Trigger

trigger = Trigger.from_name("<trigger-name>", owner_org_id="<org-id>")
trace = trigger.dry_run(event=PlatformEvent(
    id="dry-run", source=platform_event_source(None, trigger.org_id), type=PlatformEventType.SessionIngested,
    time=datetime.datetime.now(datetime.timezone.utc), org_id=trigger.org_id,
    data=SessionIngestedPayload(session_id="<session-id>", ingestion_number=1),
))
print(trace.model_dump_json(indent=2))
```

### Step 4: Fire it on the test subject

Dry-run the test subject itself: every gate should pass, and the verdict should say the trigger would fire. A file trigger at `once_per` `file` or `occurrence` ignores files uploaded before it was created (rule 15), and the scratch dataset has no files until the upload below, so for a file event this check follows the upload and uses the uploaded file's `--file-id`. By then the trigger may already have fired for that file: at `once_per` `file` or `dataset` the dry run then fails only at `already_fired`, which is the expected result, and the dispatch read below is the proof.

Where Step 1 allows a live test, ask for a yes and produce the event: upload one file that should fire the trigger and one that should not (`roboto datasets upload-files -d <ds_id> -p <path>`), or change the tag or metadata the trigger watches (`roboto datasets update -d <ds_id> --put-tags <tag>`). On `file.ingested`, the org must already ingest that format. Read the dispatches every 15 seconds for up to 10 minutes, longer while a file is still ingesting:

```bash
uv run --with roboto python -c '
import sys
from roboto.domain.triggers import Trigger
for d in Trigger.from_name(sys.argv[1], owner_org_id=sys.argv[2]).dispatches():
    print(d.claimed_at, d.status, d.event_type, d.subject, d.result_ref, d.status_detail)
' <trigger-name> <org-id>
```

A verified positive path is a `dispatched` dispatch for the event that should fire the trigger, with an invocation ID in `result_ref`. Then check what the invocation did:

```bash
roboto --suppress-upgrade-check invocations status <iv_id>
roboto --suppress-upgrade-check invocations logs <iv_id>
roboto --suppress-upgrade-check invocations show <iv_id>      # rich_input_data: the inputs it was given (file or session IDs, queries, or patterns)
```

An invocation that failed after a `dispatched` dispatch means the trigger works and the action does not; report the two facts separately (rule 25). For a per-file target, the file that should not fire must produce no dispatch, and a dry run with its `--file-id` must fail at `target_prefilter` with a reason naming the patterns (rule 26). On `file.ingested`, a file the org never ingests fails earlier, with "The file has not finished ingestion.", which says nothing about the patterns; for that trigger the negative file must be one the org ingests and the patterns exclude.

### When the gate fails

| What you see | What to change |
|---|---|
| `enabled` false after the create | The org is at its active-trigger limit (rule 24); tell the user |
| A condition leaf with `actual` `None` | The field path or its root (rules 16, 17) |
| `target_prefilter`: the file was uploaded before the trigger was created | Use a file uploaded after the create (rule 15) |
| `target_prefilter`: the file matches no pattern | The patterns, or the file's real path (rule 12) |
| `target_prefilter`: the file has not finished ingestion | On `file.ingested`, wait for ingestion; if it never comes, the org does not ingest that format |
| `already_fired`, with a `dispatched` dispatch for the test file | Nothing: the trigger fired for it, which is the result Step 4 wants |
| `already_fired` before any test upload | An earlier test already fired at this grain; use a new file (rule 7) |
| A `failed` dispatch | Read `status_detail`: a placeholder that did not resolve points to rule 17, a missing required parameter to rule 20 |

If the gate cannot run (no credentials, no test subject, no way to produce the event), stop and tell the user what is blocking it and exactly what to run. Do not report an unverified trigger as working. Where the table in Step 1 allows no live test, the dry runs are the verification; say that no live dispatch was observed.

### Step 5: Record and tear down

Record every run in `SPEC.md`'s verification table: what was done, the verdict and failing gate, the dispatch, and the invocation's result, one row per path including the negative one. Then ask for a yes to disable the trigger (`roboto triggers disable <trigger-name> --org <org-id>`), so it holds no slot under the active-trigger limit until it goes live, and to delete the scratch dataset (`roboto datasets delete -d <ds_id>`).

## Phase 5 — Review

Scope: `trigger.py` and `SPEC.md`. Three passes, in order.

1. **API truth.** Check every import, call, enum member and CLI flag against source 1. Nothing may import `Trigger` from `roboto` or `roboto.domain.actions` (rule 2).
2. **Spec against the saved trigger.** Compare `<trigger-name>.json` with `SPEC.md`: events, `once_per`, condition, targets, parameters and overrides. The saved condition carries the guard; `SPEC.md` describes it without.
3. **Names and reuse.** The name states the rule (rule 5), each `target_id` is final (rule 4), nothing is a literal ID or token (rule 3), and `--check` still passes.

Fix what you find. Escalate to the report only when a fix would contradict a decision the user made.

## Phase 6 — Hand off

Report:

1. **What the trigger does**: one paragraph, and the path to the directory.
2. **Requirements coverage**: the Phase 1 table, each row mapped to the field that implements it.
3. **Decisions made**: every resolved ambiguity, marked as a user answer or a `--yolo` judgment call.
4. **Verification**: each path from Phase 4 with the exact command, the input, the verdict, the dispatch and the invocation result. Name any gate that did not run and why.
5. **Expected rate**: the Phase 3 count, as what will happen once the trigger is live.
6. **Open items**: anything escalated from Phase 5, and any answer you warned about.

Then name the sources you verified against (page URLs and the SDK version), and anything you could not verify. Give the go-live command without running it:

```bash
uv run triggers/<trigger-name>/trigger.py --org <org-id>
```

It replaces the guarded condition with the real one and enables the trigger. From then on the action runs on the org's data, and uses compute, without further input from the user, so do not run it for them, including under `--yolo`. If a triggered invocation fails later, the `debug-roboto-invocation` skill diagnoses it.
