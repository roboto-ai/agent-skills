# Ingestion authoring rules

Each rule below names either a failure mode that keeps an ingestion action from producing readable topics on its first invocation or a convention the generated repository must follow. Apply every rule that bears on the action being written; cite the rule number when a requirement forced a choice. SKILL.md Phases 1 through 5 read them, and `references/ingestion-api.md` has the calls they name.

## The ingestion contract

1. **Register a representation for every topic, and verify by reading the data back.** A topic made with `Topic.create` and message paths is a metadata-only container until a representation is registered: `File.get_topics()` lists it, its schema shows, and `get_data_as_df()` returns an empty frame. Nothing raises. The DataFrame path registers the representation; the other paths do not. Listing topics proves nothing, which is why Phase 4 Step 4 reads rows.

2. **Store time as nanoseconds since the Unix epoch.** Convert seconds, milliseconds, vendor epochs, and GPS time. A clock that counts from power-on has no Unix time of its own: find the offset (a wall-clock field, a file header, a start time the user trusts), and add it to every timestamp before writing on the DataFrame and `Topic.create` paths. On the declared path, keep the relative timestamps and anchor them with `anchor_ns`. `File.set_timeline_offset` sets the offset for reads through a session, not for `Topic.get_data_as_df` on a topic from `File.get_topics`, so it does not replace adding the offset on the first two paths. Data left in relative time sits in January 1970 and lines up with no other recording.

3. **State the unit of a numeric timestamp column.** `File.add_topic` detects a timezone-aware datetime column, but a numeric column needs `timestamp_unit`, and without it raises `IngestionException`. A wrong unit ingests without error and places the data a factor of 1000 off, which shows as a year near 1970 or far in the future.

4. **Choose each canonical type on purpose.** The type decides what the platform does with a field: plots for numbers, maps for the four latitude and longitude members, images, timestamps. Coordinates typed `number` plot as lines but never render on a map. A `categorical` path without `categories` metadata renders as a string. `number_array` is for numbers only, never for byte-width elements (`uint8`, `int8`, `byte`, `char`), which hold raw bytes; type those `array`. Use `unknown` only for a field you cannot type, and list it in `SPEC.md`.

5. **Keep topic names stable across files.** Queries, triggers, and session reads find data by topic name, and a session joins one topic across its files by that name. A name that embeds a file ID, a timestamp, or a run number turns one signal into many unrelated topics. Put the varying part in metadata. Names are unique within a file on the DataFrame and `Topic.create` paths, and within the org on the declared path.

6. **Make a rerun converge.** Triggers deliver at least once and operators re-invoke, so the action runs twice on one file. `File.add_topic` updates a same-name topic in place, and a resent declaration converges on the first. `Topic.create` and `add_message_path` raise `RobotoConflictException` on a second run: catch it, load the topic with `Topic.from_name_and_file`, and replace its message paths. Verify by running twice and comparing topic and row counts.

7. **Capture units when ingesting.** Adding a unit later means re-ingesting every file. On the DataFrame path only the timestamp gets a unit, so follow each `add_topic` with `topic.update_message_path(..., metadata_changeset=TaglessMetadataChangeset(put_fields={"unit": ...}))` for each field that has one. On the `Topic.create` path put `unit` in each message path's metadata; on the declared path set `Field.unit`. Where the format records no unit, ask; where nobody knows, record the gap in `SPEC.md`.

## Writing

8. **Report bad input as a data error.** A corrupt, truncated, empty, or wrong-format file is the input's fault, not the action's. Log the file and what was wrong, and exit with `ExitCode.DataError` (65), which Roboto's own ingestion actions use for the same case. An uncaught traceback exits 1 and sends whoever debugs the invocation to the code instead of the data.

9. **Mark the file ingested last, and only when the topics `SPEC.md` names are written.** `File.mark_ingested()` sets `ingested`, which post-ingestion triggers and `session.ingested` wait for. Without it the file stays `partly_ingested`: those triggers never run on it, and a complete session holding it never announces `session.ingested`. Calling it before the last topic is written lets downstream work read incomplete data.

10. **Preserve the source path of nested and dotted names.** Message paths use dots for nesting, so a source field named `gps.fix` reads as `fix` inside `gps`. Pass `path_in_schema` (or `Field.path` on the declared path) with the source's exact path whenever the schema is nested or a name contains a dot. `AddMessagePathRequest` requires `path_in_schema`; `Topic.add_message_path` defaults it to the message path split on dots, and `Field.path` defaults to `[name]`.

11. **Upload derived files under a directory whose name starts with a dot.** An MCAP or Parquet file the action writes as a representation is a new file in the dataset. Under a dot-directory, as the DataFrame path's `.VISUALIZATION_ASSETS/` is, no trigger runs on it and no ingestion rule makes it ingestable. Elsewhere, an upload trigger or a rule for `**/*.parquet` or `**/*.mcap` runs another ingestion on the action's own output.

12. **Decide what a partial failure does.** When one stream fails to parse, writing the others keeps the good data visible; failing the whole file keeps partial data out. Either way, log which streams were skipped and why. Do not call `mark_ingested` on a partial result unless the user chose that, since downstream triggers and sessions then treat the file as complete.

13. **Gate every write on dry run, and log what it would do.** `roboto actions invoke-local --dry-run` sets `context.is_dry_run`, and topics, uploads, and `mark_ingested` all write to the org. A dry run that logs each planned topic with its row count, time range, and message paths is what makes Phase 4 Step 3 worth reading.

## Packaging

14. **Size compute against the largest expected file.** The sample is small. A DataFrame holds a whole stream in memory, and the DataFrame path writes a Parquet copy to local disk, so ask for the largest real recording and set `compute_requirements` for it. The template's defaults are 512 vCPU units (0.5 vCPU), 1024 MiB of memory, and 21 GiB of storage; an under-sized container fails partway through a long file. Build a container action, not one of the Python actions the docs also describe: those do not download input files and have a fixed 2 GiB of memory.

15. **Declare dependencies where the container installs them.** The Dockerfile installs `pyproject.toml`'s runtime dependencies; a parser library left in the `dev` extra imports in local tests and raises `ImportError` in the container. A library that links a system package needs that package in the Dockerfile's `apt-get` block, or it fails only in the container.

16. **Filter `ExperimentalWarning` once at the top of a module that imports from `roboto.experimental`.** Some releases raise it on first use of an experimental API, and the filter keeps it out of every invocation log:

    ```python
    import warnings
    from roboto.warnings import ExperimentalWarning
    warnings.filterwarnings("ignore", category=ExperimentalWarning)
    ```

    Import experimental names as `from roboto.experimental.ingest import Field` or `from roboto.experimental import ingest`. Any form that reaches the module as `roboto.experimental.<module>` fails, because `roboto.experimental` is a function on the `roboto` package: `import roboto.experimental.ingest as ingest` raises `ImportError`, and `roboto.experimental.topics.Topic` raises `AttributeError`.

## Tests and documentation

17. **Test the parser, not the platform.** Parsing needs no network: keep it in functions that take a path and return frames or plain values, and test them against a small fixture checked into the repository, plus a truncated and an empty file that must raise the error `main` turns into exit 65. Use a fixture the user may redistribute: a truncated real recording often is, a customer's full log often is not.

18. **Record the format in `SPEC.md`, and never the process that produced it.** The Phase 1 inventory (streams, fields, types, units, counts), what was left out and why, and the verification results belong in the repository; for many custom formats they are the only written description. `SPEC.md`, `README.md`, and comments never mention this skill, its phases, the interview, or `--yolo`.

19. **Report where the sample contradicts the documentation.** Field order, optional fields, format versions, and byte order often differ from the specification. Parse defensively, build for the file, and list every contradiction in the hand-off: it may mean the user's data differs from what they believe they have.
