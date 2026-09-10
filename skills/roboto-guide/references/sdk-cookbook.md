# Roboto Python SDK cookbook

Worked patterns for ad hoc scripts against the Roboto Python SDK.

Every signature, enum member, and docstring claim below was checked against the SDK release recorded as `verified-sdk` in the `metadata` block of `SKILL.md`. The check resolved the wheel with `uv run --refresh-package roboto --with 'roboto[analytics]'` and printed `inspect.signature` and `__doc__` for each name; the RoboQL examples and ID prefixes were also run read-only against a Roboto deployment.

A newer SDK release can change any call shown here. Before you hand a script to the user, re-check every call you took from this file against the latest release (SKILL.md, "Sources, in order of authority", source 1). `roboto.__version__` does not exist; read the installed version with `importlib.metadata.version("roboto")`.

## Running a script against the latest SDK

Do not depend on whichever `roboto` is already installed. Declare the dependency in the script and let `uv` resolve the latest release at run time:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["roboto[analytics]"]
# ///
"""One-line statement of what this script does."""

import warnings

from roboto.warnings import ExperimentalWarning

warnings.filterwarnings("ignore", category=ExperimentalWarning)   # newer APIs such as sessions raise it on first use

from roboto import Dataset

...
```

Run it with `uv run script.py`. `uv` reads the inline metadata, builds an isolated environment, and runs the file. Add `--refresh-package roboto` the first time in a session so the resolver sees the newest release rather than a cached index.

Every script starts with the `warnings` lines. Newer APIs, sessions and session metrics among them, raise `ExperimentalWarning` the first time they are used; ignoring it at the top keeps the script's output to what the script prints.

### Without uv

The inline metadata block is a comment, so the same file runs under any Python 3.11 or newer interpreter that has the SDK installed. Build one environment for the session and use its interpreter wherever SKILL.md says `uv run`, for signature checks and scripts alike:

```bash
python3 --version                                                           # must be 3.11 or newer; see below
python3 -m venv ~/.cache/roboto-guide/venv                                  # Windows: py -3 -m venv %LOCALAPPDATA%\roboto-guide\venv
~/.cache/roboto-guide/venv/bin/pip install --upgrade 'roboto[analytics]'    # --upgrade is what --refresh-package roboto does under uv
~/.cache/roboto-guide/venv/bin/python -c "import inspect, roboto; print(inspect.signature(roboto.Dataset.upload_file))"
~/.cache/roboto-guide/venv/bin/python script.py
```

On Windows the environment lives under `%LOCALAPPDATA%\roboto-guide\venv` and the interpreter is `Scripts\python.exe`; `references/platforms.md` gives the PowerShell and cmd forms of every line above. Rerun the `pip install --upgrade` line at the start of each session so the environment tracks the latest release.

If the system Python is older than 3.11, `uv` is the shortest path, because it downloads a suitable interpreter on first use. The installers are listed at https://docs.astral.sh/uv/getting-started/installation/: `curl -LsSf https://astral.sh/uv/install.sh | sh` on Linux and macOS, `brew install uv` with Homebrew, `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"` on Windows, or `pip install uv` and `pipx install uv` anywhere. Confirm with `uv --version`.

Extras, from the README:

| Extra | Needed for |
|---|---|
| `analytics` | `Topic.get_data_as_df`, `MessagePath.get_data_as_df`, `find_similar_signals` (adds fsspec, numpy, orjson, pandas, pyarrow, stumpy) |
| `ingestion` | Writing topic data as Parquet in ingestion actions |
| `video` | `roboto.experimental.video` frame extraction (adds av, numpy, pillow) |
| `examples` | The notebooks under `examples/` in the SDK repo (adds ipython, jupyter, matplotlib, pillow) |

Calling a method whose extra is not installed raises an `ImportError` that names the extra to install.

## Authentication and client construction

Credentials resolve in this order, from `RobotoConfig.from_env`:

1. `ROBOTO_API_KEY` (alias `ROBOTO_BEARER_TOKEN`) in the environment, with optional `ROBOTO_SERVICE_ENDPOINT` (default `https://api.roboto.ai`).
2. The config file at `ROBOTO_CONFIG_FILE`, else `~/.roboto/config.json`, using the profile named by `ROBOTO_PROFILE`, else the file's `default_profile`, else `default`. An explicit profile (`RobotoClient.for_profile`, the CLI's `--profile`) overrides both.

The config file layout, from the Programmatic Access page:

```json
{
  "version": "v1",
  "profiles": { "prod": { "api_key": "robo_pat_..." } },
  "default_profile": "prod"
}
```

Most domain classes take an optional `roboto_client` and fall back to a default built from the environment, so a script that relies on `~/.roboto/config.json` needs no explicit client:

```python
from roboto import Dataset
ds = Dataset.from_id("ds_xxx")
```

Build a client explicitly to pick a profile or to reuse it across calls:

```python
from roboto import RobotoClient
client = RobotoClient.from_env()               # same resolution as above
client = RobotoClient.for_profile("staging")   # a named profile from config.json
ds = Dataset.from_id("ds_xxx", roboto_client=client)
```

Confirm identity and org membership before doing anything org-scoped:

```python
from roboto.domain.users import User
from roboto.domain.orgs import Org

me = User.for_self()                 # me.user_id is the email or id the token belongs to
for org in Org.for_self():           # every org the caller belongs to
    print(org.org_id, org.name)
```

A user in several orgs must pass `caller_org_id="og_..."` to creation calls and `owner_org_id="og_..."` to query methods (`Dataset.query`, `File.query`, `Invocation.query`) and name lookups (`Action.from_name`, `Trigger.from_name`); otherwise the API raises `RobotoNoOrgProvidedException`. Only `RobotoSearch.from_env()`, the action runtime, and the CLI read `ROBOTO_ORG_ID`; domain classes ignore it. Lookups by ID (`from_id`) need no org.

## Look up by ID or name

```python
from roboto import Dataset, File, Topic, Event, Collection, Invocation, Action, Trigger

ds  = Dataset.from_id("ds_xxx")
f   = File.from_id("fl_xxx")
t   = Topic.from_id("tp_xxx")                   # topic ids are tp_-prefixed strings; message paths are mp_
t   = Topic.from_name_and_file("/imu/data", file_id="fl_xxx")
ev  = Event.from_id("ev_xxx")
co  = Collection.from_id("cl_xxx")
iv  = Invocation.from_id("iv_xxx")
act = Action.from_name("ros_ingestion", owner_org_id="roboto-public")   # Action Hub actions are owned by roboto-public
tr  = Trigger.from_name("ingest-bags", owner_org_id="og_xxx")            # owner_org_id required for a multi-org user
```

Domain objects expose record fields as properties (`ds.name`, `ds.tags`, `ds.metadata`, `f.relative_path`, `t.topic_name`, `t.message_paths`). `x.record` is the underlying pydantic record, which carries fields the object does not expose as properties (a file's size is `f.record.size`); `x.record.model_dump()` gives a dict.

## Search with RoboQL

```python
from roboto import RobotoSearch

rs = RobotoSearch.from_env()   # credentials as above; org from ROBOTO_ORG_ID if set
for ds in rs.find_datasets('tags CONTAINS "px4" AND created > "2026-08-01" SORT BY created DESC LIMIT 20'):
    print(ds.dataset_id, ds.name, ds.tags)

for f in rs.find_files('dataset.tags CONTAINS "Rainy" AND path CONTAINS ".ulg"'):   # path is an alias of relative_path
    print(f.file_id, f.relative_path)

for t in rs.find_topics('name = "cpuload" AND msgpaths[cpuload.load].mean > 0.8'):
    print(t.topic_id, t.dataset_id, t.file_id)

for mp in rs.find_message_paths('data_type = "uint8[]" AND created > "2024-09-25"'):
    print(mp.message_path_id, mp.topic_id, mp.path)
for ev in rs.find_events('name CONTAINS "spike" AND start_time > "2026-09-01"'):
    ...
for ds in rs.find_datasets('* SORT BY created DESC LIMIT 10'):   # * means no condition; a bare LIMIT is a syntax error
    ...
```

Construct it with `RobotoSearch.from_env()`, which reads `ROBOTO_ORG_ID`, or with `RobotoSearch.for_roboto_client(client, org_id="og_...")`. The bare constructor takes no org, and a user in several orgs must supply one.

Every `find_*` method returns a generator that pages through results; wrap it in `list(...)` or `itertools.islice` when you need a bounded count. Topics from `find_topics` come back with an empty `message_paths` list; load one with `Topic.from_id` to read its schema. Results can lag writes by a second or two (see "Eventual consistency").

Filter message paths on their own fields: `message_path`, `data_type`, `canonical_data_type`, `metadata.<stat>`, `topic_id`, and `created`. To find paths by their topic, file, or dataset, search that entity first and read its message paths, as the topics section shows.

The SDK also supports structured queries without RoboQL: build a `roboto.query.QuerySpecification` from `Condition` and `ConditionGroup` objects and pass it to `Dataset.query(spec)`, `File.query(spec)`, `Action.query`, `Invocation.query`, or `Trigger.query`. Prefer RoboQL for anything a person will read.

## Datasets and files

```python
import pathlib
from roboto import Dataset

ds = Dataset.create(name="Run 42", tags=["nightly", "px4"], metadata={"vehicle_id": "sn_1234"}, caller_org_id="og_xxx")

ds.put_tags(["reviewed"])
ds.put_metadata({"release": "2.4.0", "stats": {"max_alt": 120}})

# Upload
uploaded = ds.upload_file(pathlib.Path("flight.ulg"))                         # returns File
ds.upload_directory(pathlib.Path("./logs"), include_patterns=["**/*.mcap"], exclude_patterns=["**/*.tmp"])
mapping = ds.upload_files([pathlib.Path("a.bag"), pathlib.Path("b.bag")])     # {local path: relative path}

# Enumerate and download
for f in ds.list_files(include_patterns=["**/*.ulg"]):
    print(f.file_id, f.relative_path, f.ingestion_status)
f = ds.get_file_by_path("logs/flight.ulg")
f.download(pathlib.Path("./out/flight.ulg"))
downloaded = ds.download_files(pathlib.Path("./out"), include_patterns=["**/*.mcap"])   # [(FileRecord, Path)]

# Annotate a file
f.put_tags(["keep"])
f.put_metadata({"anomaly_count": 3})
```

`upload_directory` and `upload_files` default to batches of 500 and print progress; pass `print_progress=False` in non-interactive scripts.

## Topics and time-series data

Topics are the ingested time series inside a file. Message paths are the individual fields of a topic.

```python
ds = Dataset.from_id("ds_xxx")
bag = ds.get_file_by_path("scene57.bag")

for t in bag.get_topics():                       # or ds.get_topics() across every file
    print(t.topic_name, t.message_count, t.start_time, t.end_time, t.schema_name)

steering = bag.get_topic("/vehicle_monitor/steering")
for rec in steering.message_paths:                # MessagePathRecord: the schema, not a data handle
    print(rec.message_path, rec.data_type, rec.canonical_data_type, rec.metadata)

# Stream records: (epoch-nanosecond timestamp, dict matching the schema)
for ts, record in steering.get_data(start_time="1714513576", end_time="1714513590"):
    ...

# pandas DataFrame indexed by log time, one column per message path (needs roboto[analytics])
df = steering.get_data_as_df(message_paths_include=["angle", "rate"])

# One field as a MessagePath object: precomputed stats plus its own get_data / get_data_as_df
angle = steering.get_message_path("angle")
print(angle.path, angle.min, angle.max, angle.mean, angle.stddev, angle.count)
angle_df = angle.get_data_as_df(start_time=steering.start_time, end_time=steering.start_time + 5_000_000_000)
```

`Topic.message_paths` yields `MessagePathRecord` schema entries (`message_path`, `data_type`, `canonical_data_type`, `metadata`); `Topic.get_message_path(name)` yields a `MessagePath` domain object (`path`, `min`, `max`, `mean`, `median`, `stddev`, `count`, percentiles, `get_data`, `get_data_as_df`). A `MessagePath` for a nested message (`canonical_data_type` of `Object`) has `None` for `min`, `max`, `mean`, and the other stats; read them on leaf numeric paths.

`Dataset.get_topics()` and `RobotoSearch.find_topics` return topics with an empty `message_paths` list; the `Dataset.get_topics` docstring says the list is left empty for performance and points to `file.get_topics()`. Fetch the topic through `File.get_topic(name)`, `File.get_topics()`, or `Topic.from_id(id)` before reading its schema.

Time arguments accept several forms, converted by `roboto.time.to_epoch_nanoseconds`:

| Form | Interpreted as |
|---|---|
| `int` | nanoseconds since the Unix epoch |
| `str` such as `"1714513576"` or `"1714513576.250"` | seconds, `<sec>.<nsec>` style |
| `str` ISO 8601 such as `"2026-09-01T10:00:00Z"` | a datetime |
| `datetime.datetime` | a datetime |
| `float` | seconds, but precision can be lost; prefer `str` or `decimal.Decimal` |

Topic `start_time` and `end_time` properties are epoch nanoseconds. On `get_data`, `start_time` is inclusive and `end_time` is exclusive.

Topic data downloads are cached locally. Pass `cache_dir=` to `get_data` or `get_data_as_df` to choose the directory, and point it somewhere that outlives the script so a later question reuses the download instead of fetching it again.

### Suggestion: index a dataset before analyzing it

A may carry a many topics and many more message paths. Do not fetch topic data to find out what is there. Walk the schema once, write it to a local file, and answer every later question from that file, fetching data only for the paths and windows the question needs:

```python
import json, pathlib
from roboto import Dataset

ds = Dataset.from_id("ds_xxx")
index = {"dataset_id": ds.dataset_id, "name": ds.name, "tags": ds.tags, "files": []}
for f in ds.list_files():
    entry = {"file_id": f.file_id, "relative_path": f.relative_path, "ingestion_status": str(f.ingestion_status), "topics": []}
    for t in f.get_topics():                           # File.get_topics fills message_paths; Dataset.get_topics leaves it empty
        topic = {"topic_id": t.topic_id, "topic_name": t.topic_name, "schema_name": t.schema_name, "message_count": t.message_count,
                 "start_time": t.start_time, "end_time": t.end_time, "message_paths": []}
        for mp in t.message_paths:
            stats = {k: mp.metadata[k] for k in ("min", "max", "mean", "median", "count") if k in mp.metadata}
            topic["message_paths"].append({"path": mp.message_path, "data_type": mp.data_type,
                                           "canonical": str(mp.canonical_data_type), **stats})
        entry["topics"].append(topic)
    index["files"].append(entry)

out = pathlib.Path("roboto-index") / f"{ds.dataset_id}.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(index, indent=1, default=str))
```

This is cheap: a one-file ULog dataset with a hundred topics and nearly two thousand message paths indexes in a few seconds into a few hundred kilobytes, including each numeric path's precomputed `min`, `max`, `mean`, and `median`. The index then answers "which topics have a field like X", "what range does Y take", and "what window does this file cover" without another request. Every data fetch after that is narrow: `get_data_as_df(message_paths_include=[...], start_time=..., end_time=...)` on the one topic the question names, with `cache_dir=` pointed at a directory that outlives the script so the next question reuses the download.

Keep `roboto-index/` beside the user's work and reread it in later turns instead of rebuilding it. Rebuild when the dataset's `modified` timestamp changes or a file's `ingestion_status` was not yet complete. For a session, walk `Session.list_topics()` instead (next section); its topics carry only `name` and `topic_id`, so read the schema from `get_data_as_df(...).dtypes` over a short window.

## Sessions

A session is an operational time window of one or more devices: a flight, a drive, a test run. It groups the files recorded during that window, each optionally narrowed to a sub-window, so it can span several files or cover one slice of one. Start from a session whenever the question is about a run rather than a file: "what happened during flight 12", "compare CPU load across yesterday's drives", or any metric that belongs to a run. Import `Session` exactly as shown; the module form (`import roboto.experimental.sessions as x`) fails:

```python
from roboto.experimental.sessions import Session

# Create: from an existing dataset (devices inferred, files pre-populated), from a device, or bare
s = ds.create_session("Flight 12", include_patterns=["**/*.ulg"])
s = device.create_session("Drive 2026-09-09 am")
s = Session.create(name="Formation test", device_ids=["dv_a", "dv_b"], caller_org_id="og_xxx")
s.add_file(f, range_min_timestamp_ns=t0, range_max_timestamp_ns=t1)   # File or file ID; the range narrows the contribution

# Look up
s = Session.from_id("se_xxx")
for s in Session.for_dataset("ds_xxx"): ...
for s in Session.for_org(org_id="og_xxx"): ...                        # for_org takes org_id, not owner_org_id
for s in RobotoSearch.from_env().find_sessions(
    'duration > 60000000000 AND metric.cpu.load.max > 0.9 SORT BY min_timestamp_ns DESC LIMIT 10'): ...

print(s.session_id, s.name, s.min_timestamp_ns, s.max_timestamp_ns, list(s.list_devices()))
for view in s.list_files():                                            # SessionFileView
    print(view.file_id, view.dataset_id, view.relative_path, view.range_min_timestamp_ns, view.range_max_timestamp_ns)

# Topics are session-scoped: deduplicated across files, read window defaulting to the session bounds
for t in s.list_topics():
    print(t.topic_id, t.name)
df = s.get_topic("vehicle_air_data").get_data_as_df(fields_include=[("baro_alt_meter",)], flatten=True).sort_index()   # field addresses are tuples of path components

# Metrics: one value per name per session; publishing the same name again replaces it
for m in s.list_metrics():
    print(m.name, m.value, m.unit)
from roboto.domain.metrics.record import MetricEntry
s.publish_metrics([MetricEntry(name="cpu.load.max", value=0.93)])
```

`Session.min_timestamp_ns` and `max_timestamp_ns` are recomputed by Roboto across every file contribution on each add or remove. The topics `list_topics` and `get_topic` return are a different class from `roboto.Topic` (`roboto.experimental.topics.Topic`): their read methods take `fields_include` and `fields_exclude` rather than `message_paths_include`, and each entry is a tuple of path components such as `("pose", "position", "x")` rather than a dotted string (a string raises `TypeError`); `flatten=True` expands struct fields into dot-delimited columns; rows arrive grouped by file rather than in global time order (hence `sort_index()`), and outside a session `start_time` and `end_time` are required. `find_sessions` fields are listed in `references/roboql.md`.

## Events

```python
from roboto import Event

ev = Event.create(
    name="Fast Turn",
    start_time="1714513580",          # any form to_epoch_nanoseconds accepts
    end_time="1714513590",            # omit for an instantaneous event
    topic_ids=[steering.topic_id],    # or dataset_ids=[...], file_ids=[...], message_path_ids=[...]
    description="Steering rate above 2 rad/s",
    tags=["anomaly"],
    metadata={"peak_rate": 2.4},
)
ev.put_tags(["reviewed"])
df = ev.get_data_as_df(topic_name="/vehicle_monitor/steering")   # the data inside the event's window
```

An event must be associated with at least one dataset, file, topic, or message path; pass the matching `*_ids` argument.

## Collections

```python
from roboto import Collection, CollectionResourceType

co = Collection.create(
    name="Crash candidates",
    resource_type=CollectionResourceType.Dataset,
    dataset_ids=["ds_a", "ds_b"],
    tags=["triage"],
    caller_org_id="og_xxx",
)
co = Collection.from_id("cl_xxx")
```

Collections are versioned; `Collection.from_id(..., version=N)` reads an older revision.

## Actions, invocations, triggers

```python
from roboto import Action, InvocationSource, InvocationDataSourceType, Invocation

action = Action.from_name("ros_ingestion", owner_org_id="roboto-public")   # Action Hub actions are owned by roboto-public
iv = action.invoke(
    invocation_source=InvocationSource.Manual,
    data_source_id="ds_xxx",
    data_source_type=InvocationDataSourceType.Dataset,
    input_data=["**/*.bag"],
    parameter_values={"threshold": "0.8"},
    caller_org_id="og_xxx",
)
iv.wait_for_terminal_status(timeout=1800, poll_interval=10)   # raises roboto.waiters.TimeoutError; defaults 300 s, 5 s
print(iv.current_status)
for log in iv.get_logs():
    print(log.timestamp, log.process, log.log)   # LogRecord fields: log, timestamp, process, partial_id
```

`Action.from_name` takes the owning org's ID as `owner_org_id`; for Action Hub actions that is `roboto-public`.

`Invocation` also offers `refresh()`, `stream_logs()`, `cancel()`, `reached_terminal_status`, and `status_log`.

Event-driven triggers come from `Trigger.create(...)`. Cron schedules come from `roboto.domain.actions.ScheduledTrigger.create(name, schedule, action_name, ...)`, which the CLI does not expose (`roboto triggers create` has no schedule option).

## Agents

```python
from roboto.ai import AgentThread
from roboto.ai.agent_thread import AgentTextDeltaEvent

thread = AgentThread.start("Look at dataset ds_xxx and check /vehicle_monitor/steering for anomalies.")
for event in thread.events():
    if isinstance(event, AgentTextDeltaEvent):
        print(event.text, end="", flush=True)
```

This is the same agent as the web app's AI Chat and `roboto chat start`. The `learn/ai/agents` page covers forking a thread and client tools; `examples/agent_thread_client_tools.py` in the SDK repo is a worked client-tools example.

## Layouts, views, dashboards, workspaces, and AI threads

These are the objects the web app saves: visualizer layouts (panel arrangements), views (saved searches), metric dashboards, visualizer workspaces (a layout plus the data loaded into it, shared by URL), and AI Chat threads. Questions about them ("what is in a layout", "list my saved views", "export a chat") are answerable from code even though the docs pages describe only the UI.

The SDK ships record and request types for layouts, views, and dashboards (`roboto.domain.layouts.LayoutRecord` and `CreateLayoutRequest`, with `views` and `dashboards` equivalents) but no domain class with methods, and nothing for workspaces. Read and write them through `RobotoClient` against the endpoints `python3 scripts/roboto_docs.py restapi <term>` lists, and validate responses with the record type:

```python
from roboto import RobotoClient
from roboto.domain.layouts import LayoutRecord

client = RobotoClient.from_env()
page = client.get("v1/layouts", caller_org_id="og_xxx").to_dict()["data"]     # these endpoints take the org as caller_org_id
for item in page["items"]:                                                    # page["next_token"] continues the listing
    layout = LayoutRecord.model_validate(item)
    print(layout.layout_id, layout.name, layout.accessibility, list(layout.layout_definition))
ws = client.get("v1/viz/workspaces/id/<workspace_id>", caller_org_id="og_xxx").to_dict()["data"]   # workspace_id, org_id, config, created, created_by
```

`restapi layout`, `restapi view`, `restapi dashboard`, and `restapi viz` list the endpoints; `restapi --path /v1/layouts/create` prints the request body for a write. Pass the org as `caller_org_id`.

AI Chat threads have a domain class. `AgentThread.from_id("ath_xxx")` loads an existing thread with its messages: `transcript` is the whole conversation as text, `messages` the `AgentMessage` objects, `status` where the turn stands. `client.get("v1/ai/threads", caller_org_id=...)` lists the caller's threads in that org, and `POST v1/ai/threads/search` filters on `title`, `status`, `created`, `created_by`, `visibility`, `subject_id` (the dataset a thread is about), and `created_from_agent_id`. Reading a thread is read-only; `send`, `send_text`, `fork`, and `start` make Roboto's AI act as the user.

## Eventual consistency

Search reads (`RobotoSearch.find_*`, `query` results and counts) can lag a write by a second or two. Direct lookups by ID are strongly consistent. When a script writes and then searches, poll:

```python
import time
for attempt in range(5):
    found = [d for d in rs.find_datasets('tags CONTAINS "my-new-tag"') if d.dataset_id == ds.dataset_id]
    if found:
        break
    time.sleep(1)
```

## Raw HTTP for anything without a domain class

```python
from roboto import RobotoClient
client = RobotoClient.from_env()
resp = client.get("v1/datasets/ds_xxx")
print(resp.to_dict())
```

The path is joined to the client's endpoint, and a leading slash is stripped. `get`, `post`, `put`, `patch`, and `delete` accept `caller_org_id=`, `owner_org_id=`, `query=`, and `headers=`. Take paths from the REST API reference page. Prefer a domain class whenever one exists; the raw client skips validation and typing.

## Script hygiene

- State the SDK version the script was checked against in its docstring.
- Default to read-only. A script that creates, tags, uploads, deletes, or invokes anything should say so at the top and, unless the user explicitly asked for the write, take a `--dry-run` flag that prints what it would do.
- Never embed a token. Rely on `~/.roboto/config.json` or `ROBOTO_API_KEY` from the environment.
- Bound generators with `itertools.islice` or a `LIMIT` clause so a typo in a query does not walk an entire org.
- Print IDs alongside names; names are not unique.
