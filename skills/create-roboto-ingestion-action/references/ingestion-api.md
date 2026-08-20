# Ingestion API surface

A map for running the Phase 1 interview and knowing what to look up. Rung 4 of the Ground truth ladder — the lowest. Confirm anything you are about to write against the SDK installed in the action's venv before writing it.

## Durable documentation URLs

- Supported formats and their ingestion actions: `https://docs.roboto.ai/learn/formats.html`
- Topics, message paths, and the data model: `https://docs.roboto.ai/learn/concepts.html`
- Actions: `https://docs.roboto.ai/learn/actions.html`
- Python SDK reference: `https://docs.roboto.ai/reference/python-sdk.html`
- Compute sizing: `https://docs.roboto.ai/learn/compute.html`

**Check the formats page first.** Roboto ships ingestion actions for several common robotics formats, invocable from the action hub. If the user's format is on that list, this skill is the wrong tool.

## The data model, in the order you create it

A **file** belongs to a dataset. A **topic** belongs to a file and represents one stream of time-series data. A topic carries **message paths** — one per field, or per column, of that stream — each with a native type from the source format and a canonical type that Roboto normalizes to. A message path carries **representations**: pointers to where the data actually lives, in a supported storage format.

The last of those is the one that gets forgotten, and the reason for authoring rule 1: topics and message paths are metadata. Representations are the data. A topic with no representation is a schema with nothing behind it.

## Tier 1 — from a DataFrame

The high-level path, and the default. Confirm the signature:

```bash
.venv/bin/python -c "import inspect; from roboto import File; print(inspect.signature(File.add_topic))"
```

`File.add_topic(topic_name, df, timestamp_column=..., timestamp_unit=...)` takes a pandas DataFrame and does the rest: infers the schema and statistics from the frame, derives the message paths, serializes the data, and registers the representation. The SDK's own guidance is to prefer this over the equivalent classmethod on `Topic` for most cases.

Three properties matter for the phases above:

- **It updates in place.** A topic of the same name on the same file is updated rather than duplicated, which is where authoring rule 6's idempotency comes from on this tier.
- **The timestamp column must be identified.** A timezone-aware datetime column can be detected automatically; a numeric column cannot, and its unit must be stated. Valid units are the members of the SDK's `TimeUnit`.
- **It needs the ingestion extra.** `roboto[ingestion]`, which brings pandas and pyarrow. Distinct from `roboto[analytics]`, which is what reading data back needs.

`Topic.create_from_df(file_id, dataset_id, topic_name, df, ...)` is the same capability when you hold ids rather than a `File`.

Failures raise an ingestion exception naming the problem — a timestamp column that cannot be determined, is absent, is the wrong type, or needs a unit that was not given.

## Tier 2 — topic, message paths, representation

The low-level path. Three calls, and all three are required for readable data.

**`Topic.create(file_id, topic_name, ...)`** — optionally with start and end times in nanoseconds, a message count, a schema name and checksum, metadata, and message paths created alongside the topic. Its docstring states the trap plainly: on successful creation the topic is a metadata-only container and is not usable via data access methods until a representation is registered.

**`Topic.add_message_path(message_path, data_type, canonical_data_type, path_in_schema=..., metadata=...)`** — one call per field.

- `message_path` is the dot-delimited display path (`pose.position.x`).
- `data_type` is the source format's own type, as a string (`float32`, `uint8[]`, `geometry_msgs/Pose`). It is for display and fidelity to the source.
- `canonical_data_type` is Roboto's normalized type, and is what enables typed platform features. Read the members from `roboto.domain.topics.CanonicalDataType`; they cover numbers and number arrays, strings, booleans, bytes, categoricals, arrays, objects, images, timestamps, and an explicit unknown fallback the SDK says to use sparingly.
- `path_in_schema` is the exact path in the source schema, as a list. It defaults to splitting the message path on dots — which is why authoring rule 10 exists for nested or dot-containing names.

Adding a message path that already exists conflicts.

**`Topic.add_message_path_representation(message_path_id, association, storage_format, version, format=..., transformations=...)`** — the step that makes the data readable.

- `association` points at where the data lives, built with the helpers in `roboto.association` (a file association being the usual case).
- `storage_format` is a member of `roboto.domain.topics.RepresentationStorageFormat`; read the enum for the supported formats.
- `version` is the representation's version number.
- `format` describes the content (`jpeg`, `sensor_msgs/Image`), and `transformations` records any applied (`downsample:0.5`).

## Reading it back

The verification gate. Needs `roboto[analytics]`.

- `file.get_topics()` yields the file's topics — a generator that yields nothing for a file Roboto has not ingested.
- `file.get_topic(name)` raises when the topic is absent.
- `topic.get_data_as_df()` returns the topic's data as a DataFrame. **This is the check that distinguishes an ingested topic from a metadata-only one.** A topic that lists fine and returns an empty or failing frame here has no representation.
- The topic's message paths and their schema are on the topic record, and are what Phase 4 step 2 compares against the Phase 1 inventory.

## The experimental declarative path

`roboto.experimental.ingest` carries a declarative description of a recording's contents — a schema of fields, each with a name, a source path, a native type, a canonical type, and a unit, with schemas content-addressed server-side so identical declarations collapse to one stored schema.

It is worth reading to see where the platform is heading. It is not the basis for an action a user will run for years: the SDK states that importing from the experimental namespace is an acknowledgement that the API may change in shape, behavior, or semantics before it stabilizes, and that these APIs are for evaluation and feedback rather than long-lived production code. Parts of the module are still in motion — its own documentation references members the package does not yet export.

Build on the stable surface above. Mention this one in the final report as something to revisit once it graduates; the SDK's changelog records graduations, and the import path becomes a forwarding alias with a deprecation warning when it happens.

## Exit codes

An ingestion action is the canonical user of the runtime's data-error exit code: the input file was the wrong format, corrupted, or empty, and the action did the right thing by rejecting it. Read the codes from `roboto.action_runtime.exit_codes.ExitCode`, and see authoring rule 8.
