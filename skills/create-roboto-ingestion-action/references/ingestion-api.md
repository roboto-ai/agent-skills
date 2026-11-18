# Ingestion API map

A map of the SDK surface an ingestion action writes and reads through, for running the SKILL.md Phase 1 interview, choosing the Phase 2 write path, and writing the Phase 4 read-back script.

Every signature, enum member, and docstring claim below was checked against the SDK release recorded as `verified-sdk` in the `metadata` block of `SKILL.md`, by printing `inspect.signature`, enum members, and `__doc__` with `uv run --with 'roboto[analytics]==<verified-sdk>' python -c ...`, and building each request model shown here without sending it; CLI flags came from `python -m roboto.cli <group> <command> --help` of the same release. The supported-formats list was read from `learn/formats` on www.roboto.ai/docs, and the ingestion-rule endpoints from the SDK CHANGELOG entry for 0.61.0 and the `roboto.experimental.ingestion_rules` module docstring, on the date recorded as `verified-on`. Behaviour marked "as of the `verified-on` date" is how the platform behaved on that date; the SDK does not document it, and a live run on that date confirmed it through the SDK only, so check it at run time. A newer release can change any of it: re-check what you use against source 1 of SKILL.md's "Sources, in order of authority". Where this file and a live source disagree, the live source wins.

## Durable references

These paths are stable; prefer them over search results.

| Resource | URL |
|---|---|
| Supported formats and their ingestion actions | https://www.roboto.ai/docs/learn/formats |
| Concepts: files, topics, ingestion, sessions | https://www.roboto.ai/docs/learn/concepts |
| Actions and triggers | https://www.roboto.ai/docs/learn/actions |
| Compute sizing | https://www.roboto.ai/docs/learn/compute |
| `action.json` reference | https://www.roboto.ai/docs/reference/action-json |
| `File` (`add_topic`, `declare_topics`, `mark_ingested`) | https://www.roboto.ai/docs/reference/python-sdk/roboto/domain/files/file |
| `Topic` | https://www.roboto.ai/docs/reference/python-sdk/roboto/domain/topics/topic |
| `CanonicalDataType`, `RepresentationStorageFormat`, `MessagePathMetadataWellKnown` | https://www.roboto.ai/docs/reference/python-sdk/roboto/domain/topics/record |
| Declared topics (`roboto.experimental.ingest`) | https://www.roboto.ai/docs/reference/python-sdk/roboto/experimental/ingest |
| `Session` | https://www.roboto.ai/docs/reference/python-sdk/roboto/experimental/sessions/session |
| `ExitCode` | https://www.roboto.ai/docs/reference/python-sdk/roboto/action_runtime/exit_codes |
| `roboto actions` CLI | https://www.roboto.ai/docs/reference/cli/actions |
| SDK source and CHANGELOG | https://github.com/roboto-ai/roboto-python-sdk |
| Project template source | https://github.com/roboto-ai/cookiecutter-roboto-actions |

## The data model

A **file** in a dataset holds **topics**; each topic is one stream of time-series records. Only a dataset's files hold topics: `File.add_topic` on a file associated with a device or the org raises `RobotoIllegalArgumentException`. A topic has **message paths**, one per field, each with the source's own `data_type` and Roboto's `canonical_data_type`. A **representation** points at an MCAP or Parquet file that holds the data. Topics and message paths are metadata; representations are what a read opens.

A file's `ingestion_status` is `not_ingested`, `partly_ingested`, or `ingested`. It becomes `partly_ingested` when its first topic is recorded, and `ingested` only when something calls `File.mark_ingested()`, by convention the ingestion action. Only `ingested` makes the file eligible for post-ingestion triggers, such as those on `file.ingested`. A **session** (a flight, drive, or test run spanning files) announces `session.ingested` once it is complete and every ingestable file in it is `ingested`; a file is ingestable when one of the org's ingestion rules matched its path at upload, or once it is partly or fully ingested.

## DataFrame path

`File.add_topic(topic_name, df, timestamp_column=None, timestamp_unit=None) -> Topic`. `Topic.create_from_df(file_id, dataset_id, topic_name, df, ...)` is the same with IDs; the SDK docstring prefers `add_topic`.

- **What it does.** Writes the frame to Parquet in a temporary directory inside the action's container, infers message paths and per-path statistics from the Arrow schema, uploads the Parquet to the dataset at `.VISUALIZATION_ASSETS/<topic>_<file_id>.parquet`, and sets it as the topic's default representation. The container needs memory for the frame and disk for the Parquet.
- **Reruns.** A topic of the same name on the same file is updated in place, with its message paths replaced.
- **Timestamp.** A timezone-aware datetime column is detected without arguments. A numeric column needs `timestamp_column` and `timestamp_unit`, one of `TimeUnit`: `s`, `ms`, `us`, `ns`. Failures raise `IngestionException` (`from roboto.exceptions import IngestionException`) naming the problem.
- **Types and units.** Canonical types come from Arrow types. A list of numbers, of fixed or variable length, becomes `number_array`, except a list of `int8` or `uint8`, which becomes `array`. Only the timestamp path gets a `unit`. Set other units and correct types afterwards with `topic.update_message_path(message_path, metadata_changeset=TaglessMetadataChangeset(put_fields={"unit": "m/s"}), canonical_data_type=...)`; `TaglessMetadataChangeset` is in `roboto.updates`.
- **Extra.** Needs `roboto[ingestion]` (pandas, pyarrow). `roboto[analytics]`, which the action template declares, includes both.

## Topic, message paths, representation

Three steps, all required before a read returns rows.

1. **`Topic.create(file_id, topic_name, end_time=None, message_count=None, metadata=None, schema_checksum=None, schema_name=None, start_time=None, message_paths=None, ...)`.** Pass everything after `topic_name` by keyword; the positional order is not the order a reader expects. Pass `caller_org_id=file.org_id` too: unlike `File.add_topic`, `Topic.create` does not take the org from the file, and a caller who belongs to several orgs gets `RobotoUnauthorizedException` ("You must set the X-Roboto-Org-Id HTTP header") without it, including under `invoke-local`, which runs with the user's own credentials. Times are nanoseconds since the Unix epoch. Its docstring: the topic is "a metadata-only container" until a representation is registered. A second create on the same file raises `RobotoConflictException`; on a rerun, load it with `Topic.from_name_and_file(topic_name, file_id)` and call `topic.update(message_path_changeset=MessagePathChangeset.from_replacement_message_paths(requests), ...)`, which is what the DataFrame path does. `Topic.create` accepts an `end_time` before `start_time` without error, and only a later `topic.update` with such a range raises `RobotoInvalidRequestException`, so check the order before creating.
2. **Message paths**, passed to `Topic.create` as `AddMessagePathRequest(message_path=..., data_type=..., canonical_data_type=..., path_in_schema=[...], metadata={...})` (`roboto.domain.topics`), or added one at a time with `topic.add_message_path(message_path, data_type, canonical_data_type, path_in_schema=None, metadata=None)`. `AddMessagePathRequest` requires `path_in_schema` and raises `ValidationError` without it; `add_message_path` defaults it to `message_path.split(".")`.
3. **Representation.** `topic.set_default_representation(association=Association.file(file_id), storage_format=RepresentationStorageFormat.MCAP, version=1, format=None, transformations=None)`; `Association` is in `roboto.association`. `topic.add_message_path_representation(message_path_id, ...)` does the same for one path whose data lives in another file.

`RepresentationStorageFormat` has two members, `MCAP` and `PARQUET`. The SDK's MCAP reader decodes JSON, msgpack, and the ROS encodings (`ros1msg`, `ros2msg`, `ros2idl`, `omgidl`), so an MCAP the action writes uses one of those, with `format` naming the payload's content (`jpeg`). The `mcap` package is a dependency of the SDK. A read of an MCAP representation reads every channel in the file, takes each row's time from the message's log time, and finds each field by its message path's `path_in_schema`; so write one MCAP per topic, with log times in nanoseconds since the Unix epoch. Upload the MCAP or Parquet the action writes under a directory whose name starts with a dot, as the DataFrame path does: triggers never run on such paths and no ingestion rule matches them. `Dataset.from_id(file.dataset_id).upload_file(local_path, file_destination_path=".acme-tlm/camera.mcap")` returns the uploaded `File`, whose `file_id` goes into `Association.file(...)`.

| Message-path field | Notes |
|---|---|
| `data_type` | The source's type as a string (`float32`, `uint8[]`, `float64[7]`). A trailing `[N]` declares a fixed width, which `MessagePath.array_length` reads |
| `canonical_data_type` | A `CanonicalDataType` member, below |
| `metadata["unit"]` | Free text on most paths. On a `timestamp` path it must be a `TimeUnit` value; readers assume `ns` when it is missing |
| `metadata["categories"]` | Required on a `categorical` path: the ordered list of values, so a plot maps each to its index |

| `CanonicalDataType` | Notes |
|---|---|
| `Number`, `Boolean`, `String`, `Byte`, `Timestamp` | Scalars |
| `NumberArray` | A flat sequence of numbers. Never for byte-width elements (`uint8`, `int8`, `byte`, `char`), which hold raw bytes |
| `Array`, `Object` | Other sequences; structs with child paths |
| `Categorical` | Needs `categories` metadata |
| `Image` | Data a client renders as an image |
| `LatDegFloat`, `LonDegFloat`, `LatDegInt`, `LonDegInt` | Latitude and longitude in degrees, as floats or integer-encoded; what map rendering reads |
| `Unknown` | Fallback; the SDK says to use it sparingly |

## Declared topics (experimental)

`File.declare_topics(topics: Sequence[FileTopicDeclaration]) -> BatchResponse[roboto.experimental.topics.Topic]`, and `File.declare_topic(...)` for one. Import the models with `from roboto.experimental.ingest import Field, Schema, FileTopicDeclaration, SchemaFieldSource, RepresentationDeclaration`. Never reach an experimental module through `roboto.experimental.<module>`: on the `roboto` package that name is a function, so `import roboto.experimental.ingest as x` raises `ImportError`, and `roboto.experimental.topics.Topic` after a plain `import` raises `AttributeError`. The same holds for `topics`, `sessions`, and `ingestion_rules`.

| `FileTopicDeclaration` field | Notes |
|---|---|
| `topic_name` | Unique within the org on this path |
| `topic_schema` | `Schema(name, fields=[Field(name, data_type, canonical_data_type, unit, element_names, path)])`. A `Timestamp` field must declare a `TimeUnit` unit or raises `ValidationError`. `element_names` names each element of a top-level fixed-width `number_array` |
| `timeline_sources` | `SchemaFieldSource(field_path, min_file_timestamp_ns, max_file_timestamp_ns)` for a timestamp field; `McapLogTimeSource`, `McapPublishTimeSource`, `Mp4PresentationTimeSource` for times the container carries. Bounds are in the file's own timestamps |
| `data_range` | The slice of the file this topic occupies (rows, or media time for video), or `None` for the whole file |
| `anchor_ns` | Wall-clock instant at which the slice's time 0 occurred; places zero-based data without rewriting it |
| `representations` | `RepresentationDeclaration(file_id, storage_format, content_format, transformations, field_path)`; the files a read opens. With none, the topic is registered but reads return no rows |

Resending a declaration converges on what the first call registered. The platform applies each declaration separately; check `BatchResponse.failed`. `File.set_representations` replaces a topic's representations, and `File.set_timeline_offset(offset)` anchors data after the fact for reads through a session. Declaring topics does not change `ingestion_status`, so the action still calls `mark_ingested`.

As of the `verified-on` date, a declared topic has no counterpart in the per-file topic list: `File.get_topics`, `File.get_topic`, and the web app views built on them do not show it. Read it with `Topic.from_id(topic_id, context=FileContext(file_id=...))` after `from roboto.experimental.topics import FileContext, Topic`, or through a session.

## Reading back

Phase 4 Step 4 runs a read-only script like this one with `uv run --no-project --with 'roboto[analytics]'`:

```python
import warnings

from roboto.warnings import ExperimentalWarning

warnings.filterwarnings("ignore", category=ExperimentalWarning)

from roboto import File
from roboto.experimental.sessions import Session

file = File.from_id("fl_xxx")
print(file.relative_path, file.ingestion_status.value)
for topic in file.get_topics():
    df = topic.get_data_as_df()
    print(topic.name, len(df), df.index.min(), df.index.max())
    for mp in topic.message_paths:
        print("   ", mp.message_path, mp.data_type, mp.canonical_data_type.value, dict(mp.metadata).get("unit"))
for session in Session.for_dataset(file.dataset_id):
    if any(view.file_id == file.file_id for view in session.list_files()):
        print(session.session_id, [t.name for t in session.list_topics()], session.ingestion_status())
```

- `topic.get_data_as_df()` returns a frame indexed by a UTC `DatetimeIndex`, one column per message path. An empty frame from a topic that lists normally means it has no representation. `NotImplementedError` "No compatible reader found" means its representations mix storage formats. `ImportError` means the analytics extra is missing.
- `topic.get_data()` yields `(timestamp, record)` pairs with the timestamp in nanoseconds since the epoch; use it to check raw timestamp values.
- `file.get_topic(name)` raises `RobotoNotFoundException` when the topic is absent.
- `Session.for_dataset` lists the dataset's sessions, and `session.list_files()` yields `SessionFileView` records with `file_id` and `ingestion_status`.
- The script's `file.get_topics()` loop finds no declared topic (see "Declared topics" above). For those, have the action log the IDs in `declare_topics(...).succeeded`, load each with `Topic.from_id(topic_id, context=FileContext(file_id=...))` (both from `roboto.experimental.topics`), and run the same checks on its `get_data_as_df()`.

## Ingestion rules

An org's ingestion rules (experimental) decide which uploaded dataset files are ingestable and which action ingests them. A rule has Git wildmatch `include_patterns` and `exclude_patterns`, an `invocation` naming the action, and `auto_ingest`. While `auto_ingest` is on, a trigger the rule owns runs the action on each matching upload, passing the uploaded file as the first input. Rules never match a path with a component that starts with a dot, and do not apply to files of a device or the org. The SDK has the request and response models in `roboto.experimental.ingestion_rules` but no client class, so call the endpoints with `RobotoClient`. Reading and matching rules is open to every member; creating, updating, and deleting them is for org admins.

Test which rules match a path (read-only):

```python
from roboto.experimental.ingestion_rules import MatchIngestionRulesRequest, MatchIngestionRulesResponse
from roboto.http import RobotoClient

client = RobotoClient.defaulted()
matches = client.post(
    "v1/ingestion-rules/match",
    data=MatchIngestionRulesRequest(paths=["logs/flight_014.tlm"]),
    caller_org_id="og_xxx",
).to_record(MatchIngestionRulesResponse)
print({path: [rule.name for rule in rules] for path, rules in matches.matches.items()})
```

Create a rule (org admin; a write, so Phase 6 gives it unrun):

```python
from roboto.domain.actions import ActionReference
from roboto.domain.triggers import ActionInvocationSpec
from roboto.experimental.ingestion_rules import CreateIngestionRuleRequest, IngestionRuleRecord

rule = client.post(
    "v1/ingestion-rules",
    data=CreateIngestionRuleRequest(
        name="acme-tlm",
        include_patterns=["**/*.tlm"],
        invocation=ActionInvocationSpec(action=ActionReference(name="acme-tlm-ingestion")),
    ),
    caller_org_id="og_xxx",
).to_record(IngestionRuleRecord)
```

For files uploaded before the rule existed: `GET v1/ingestion-rules/<rule_id>/existing-files` previews them (`ExistingFilesPreview`), and `POST v1/ingestion-rules/<rule_id>/existing-files/ingest` (org admins, while `auto_ingest` is on) starts a run for each in the background. `POST v1/ingestion-rules/ingest` with `IngestFilesRequest(file_ids=[...])`, up to 100 IDs, marks each file ingestable and runs its matching rule, as if it had just been uploaded. `POST v1/ingestion-rules/runs/latest` with `LatestIngestionRunsRequest(file_ids=[...])`, up to 200 IDs, returns each file's latest run (`running`, `failed`, `finished`); `finished` leaves `ingestion_status` to say how much was ingested.

## Exit codes

`roboto.action_runtime.exit_codes.ExitCode`: `Success` 0, `UsageError` 64, `DataError` 65, `InternalError` 70, `ConfigurationError` 78. The SDK documents `DataError` as what Roboto's own ingestion actions use when "the input file was the wrong format, corrupted, a 0-byte file". The template's entrypoint catches nothing, so an uncaught exception exits 1; to exit 65, `main` logs the problem and calls `sys.exit(ExitCode.DataError)`.
