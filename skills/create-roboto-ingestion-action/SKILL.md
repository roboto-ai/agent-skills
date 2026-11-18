---
name: create-roboto-ingestion-action
description: >-
  Build a Roboto Action that ingests a log format Roboto cannot read yet into
  topics Roboto can search, plot, and read, and verify it by reading the data
  back. Use this skill whenever the user has recordings in a format Roboto does
  not ingest, even if they only describe the goal ("get our .tlm telemetry into
  Roboto", "Roboto doesn't understand our robot's log format", "turn these
  proprietary logs into topics"). Covers a support check, an inventory of a
  sample file, an ambiguity-resolving interview (skipped under --yolo), choosing
  how topics are written, scaffolding, implementation, and verification by a
  local dry run and an approved run whose topics are read back and compared with
  the sample. Not for actions that process data already ingested (use the
  create-roboto-action skill), not for an ingestion that failed (use the
  debug-roboto-invocation skill), and not for a format Roboto already ingests,
  general Roboto questions, or one-off scripts (use the roboto-guide skill).
license: MPL-2.0
compatibility: >-
  Needs a shell and network access to www.roboto.ai, pypi.org,
  files.pythonhosted.org, raw.githubusercontent.com, and api.github.com. Needs
  uv (or Python 3.10+ with pip), the roboto CLI, and Roboto credentials. Needs
  Docker for local invocation, network access to GitHub for the action
  template, and a real sample file of the format.
metadata:
  verified-sdk: "0.64.0"
  verified-on: "2026-11-18"
argument-hint: <description of the format to ingest, with a path to a sample file> [--yolo]
---

Turn a log format Roboto cannot read into a deployable ingestion action whose topics, read back through the SDK, return the values the sample file holds. An action that exits 0 has not met that standard; data read back from Roboto and compared with the sample has.

## What you need to run this

This skill does not know which agent is reading it, so it names the capabilities it needs rather than assuming them:

- **Run shell commands** and read their output.
- **Read and write files.**
- **Hold a back-and-forth with the user.** Phase 1 is an interview about their data, and Phase 4 asks before it writes to their organization.
- **Fetch a web page**, optionally. `curl` does the same.

uv is the preferred runner because it resolves the latest SDK on every run. Without uv, build one virtual environment for the session (`python3 -m venv`, then `pip install --upgrade 'roboto[analytics]'`) and use its interpreter wherever this skill says `uv run`.

**You also need a real sample file of the format.** Every phase reads it, and Phase 4 compares the ingested values with it. If the user has none, ask for one and stop: an action written from a format description and never run on real bytes cannot be verified.

`references/` throughout means the directory alongside this file. Read `references/ingestion-api.md` and `references/authoring-rules.md` before Phase 1.

## The request

The user's description of the format is the argument to this skill. Strip a `--yolo` flag from anywhere in it; what remains is the description. If the description is empty, ask the user which format to ingest and where a sample file is, and stop.

`--yolo` suppresses the Phase 1 interview and nothing else. The preflight, the verification gates, the Phase 5 edit pass, and the recording of decisions all stand: every ambiguity resolved by judgment lands in `SPEC.md` with its rationale, so the user audits the decisions after the fact instead of before.

`--yolo` never authorizes a write to the user's organization. Creating a scratch dataset, uploading the sample, running the action without `--dry-run`, deploying, and creating an ingestion rule stay the user's call: give the exact command and wait for a yes.

## Sources, in order of authority

Three sources outrank every file in this skill. They are numbered by authority: when two disagree, the lower number wins. Start with the source whose Answers column fits the question, and stop at the first source that answers it.

| Source | What | How | Answers |
|---|---|---|---|
| 1 | The latest released SDK and CLI, resolved fresh from PyPI | `uv run --no-project --isolated --refresh-package roboto --with 'roboto[analytics]' python -c "import inspect, roboto; print(inspect.signature(roboto.File.add_topic))"`; for CLI flags, `uv run --no-project --isolated --refresh-package roboto --with roboto python -m roboto.cli actions invoke-local --help` | Exact signatures, parameter names, defaults, enum members, docstrings, CLI flags |
| 2 | The Roboto docs at www.roboto.ai/docs | Fetch `https://www.roboto.ai/docs/<path>.md`; see "Docs lookups" | Concepts, supported formats, how-tos, SDK reference pages |
| 3 | The SDK CHANGELOG and GitHub releases | Fetch https://raw.githubusercontent.com/roboto-ai/roboto-python-sdk/refs/heads/main/CHANGELOG.md and https://api.github.com/repos/roboto-ai/roboto-python-sdk/releases/latest | Which release added or changed a behavior; the latest version number |

Every lookup of the latest release runs with `--no-project --isolated`, so that a `uv run` started inside a Python project or virtual environment neither uses the `roboto` installed there (an older pinned release, for example) nor writes a `uv.lock` into the project, and with `--refresh-package roboto`, so that it does not reuse PyPI's answer from up to ten minutes earlier and miss a new release.

The files under `references/` rank below all three. The `metadata` block in this file's frontmatter records the SDK release (`verified-sdk`) and date (`verified-on`) they were last checked against. When Phase 0 finds a newer release, re-check anything you take from them against source 1 before using it. Cite the live source, not the reference file.

**Docs lookups.** To find a page, fetch `https://www.roboto.ai/docs/llms.txt`, which lists every page with its URL. To read one, fetch its Markdown copy by adding `.md` to the URL (`https://www.roboto.ai/docs/learn/actions.md`); without a fetch tool, `curl -sL <url>`. To find where an SDK symbol is documented, search `https://www.roboto.ai/docs/reference/python-sdk/objects.json` for its dotted name. For REST endpoints, read `https://www.roboto.ai/docs/reference/rest-api/openapi.json`. These files are large, so read them through a search (`grep`, or a Python one-liner) rather than printing them whole. If the agent runtime can start a subagent, run lookups in one and return only the answer.

- **The installed CLI and SDK are not authoritative.** They are whatever version the user last installed, and `roboto <command> --help` describes that version and nothing else. If the installed CLI is behind the latest release, say so and point to `roboto upgrade`; on a CLI older than 0.58.0, point to `brew upgrade roboto`, or to replacing the binary or `.deb` from the latest release.
- **A copy that will run is the authority on what it does.** After Phase 3 scaffolds the project, the SDK in its `.venv` is the code the container runs. Read its version with `.venv/bin/python -c "from roboto.version import roboto_version; print(roboto_version())"` and record it in `SPEC.md`. If it is behind source 1, say what differs. Never lower source 1 to match it.
- **The sample file outranks every description of the format.** A vendor specification and the user's memory say what the format should contain; the file shows what it does contain. Build for the file, and report each place they disagree (rule 19).
- **A docs page can be ahead of the release.** When source 2 describes something source 1 lacks, source 3 says whether it is released. Build against the release, and tell the user what is coming.
- **Recommend the API that fits the task.** Phase 2 picks the write path by what the format needs. Declared topics live under `roboto.experimental.ingest`; that is not a reason to avoid them when the format needs them, and a module that imports from `roboto.experimental` filters `ExperimentalWarning` once at the top (rule 16).

Where a source cannot be reached, say which one, and tell the user what you could not check. Without a fetch tool and without `curl`, ask the user to paste the page, explaining that the alternative is writing SDK calls that may not exist.

## Phase 0 — Preflight

Run this before the interview. Every check below guards a step that would otherwise fail after the user has spent time answering questions and you have written the whole action.

```bash
uname -s                                             # platform; decides the Phase 4 pty form
roboto --version                                     # installed CLI; compare with the latest release below
uv --version                                         # runner for source 1
docker info                                          # daemon reachable, not merely installed
roboto --suppress-upgrade-check users orgs           # credentials valid; one JSON object per org
curl -s https://pypi.org/pypi/roboto/json | python3 -c 'import json,sys; print(json.load(sys.stdin)["info"]["version"])'
```

- **`uname -s`** decides which `script` form Phase 4 uses. The skill runs on macOS and Linux; Windows is untested.
- **`docker info`** must succeed. Local invocation builds and runs a container, so a stopped daemon fails Phase 4.
- **`users orgs`** fails without valid credentials and otherwise prints one JSON object per organization. With more than one, Phases 4 and 6 need `--org`; carry the list forward. Never read `~/.roboto/config.json` to check credentials, and never print a token.
- **The latest release** is what source 1 resolves. If it is newer than `verified-sdk`, say that the references predate it.
- **`roboto actions init`** downloads the project template from GitHub, so Phase 3 needs network access to GitHub. Tell the user it is a prerequisite.

Then two checks specific to ingestion:

- **The sample file opens.** Look at its first bytes (`file <path>`, `head -c 512 <path> | xxd`) and open it with the library the format needs. If no Python library reads it, say so now: Phase 3 then writes a parser from the format specification, and the plan in Phase 2 must include that work.
- **The format is not already ingested.** Fetch `https://www.roboto.ai/docs/learn/formats.md` and compare the sample's extension and contents with its table. Then ask the org which ingestion rules match the sample's path, a read-only request that `references/ingestion-api.md` ("Ingestion rules") shows. A request to ingest a format on that list belongs to the `roboto-guide` skill, which explains how to run its ingestion action or enable its rule; an ingestion that ran and failed belongs to the `debug-roboto-invocation` skill. Say so and stop, unless the user asks for a custom action anyway, for example for a variant the listed action cannot parse; record the reason in `SPEC.md`.

If a check fails, stop and tell the user exactly what to install or run. Do not begin the interview.

## Phase 1 — Decompose the format

### Step 1: Inventory the sample

Open the sample and build a table with one row per stream: its name, each field with its source type, the record count, and the first and last timestamp. Show it to the user. This table is the requirements table for the rest of the skill, and often the only written description of the format that exists. Do not spend an interview question on anything you can read from the file.

### Step 2: Find the ambiguities

| Axis | What is undetermined | Consequence of guessing wrong |
|---|---|---|
| Topic granularity | What becomes one topic: a stream, a message type, a device, the whole file? | Too coarse puts unrelated signals on one timeline; too fine makes one plot need ten topics |
| Topic naming | What topics are called, and whether the name is stable across files | Queries, triggers, and session reads find data by name; a per-file name breaks fleet comparison (rule 5) |
| Timestamps | Which field is time, in what unit, from what epoch | Data that ingests cleanly at the wrong time (rules 2, 3) |
| Clock | Monotonic? Resets, gaps, per-stream clocks, time since power-on? | Decides whether one timeline is honest and whether data needs an anchor (rule 2, Phase 2) |
| Field selection | Every field, or a subset? | A wide record may need a decision; a skipped field needs a recorded reason |
| Canonical types | Which fields are numbers, number arrays, strings, categoricals, coordinates, images? | A wrong type turns off plotting or map rendering for that field (rule 4) |
| Units | The unit of each numeric field | Not recoverable later without re-ingesting every file (rule 7) |
| Nesting | Flat or nested records, and names containing dots | Decides message-path names and `path_in_schema` (rule 10) |
| Non-tabular payloads | Images, video, point clouds, large binary blobs? | Decides the write path in Phase 2 |
| Shared files | Does one file hold several runs that belong to different sessions? | Decides whether Phase 2 needs declared topics with `data_range` |
| Scale | The largest expected file and record count | Drives `compute_requirements` and whether a stream fits in memory (rule 14) |
| Bad-input posture | What a corrupt, truncated, or empty file should do | Decides the exit code an operator sees (rule 8) |
| Partial failure | If one stream fails to parse: ingest the rest, or fail the file? Mark the file ingested or not? | Decides whether downstream triggers and sessions treat partial data as complete (rule 12) |

### Step 3: Resolve

**Without `--yolo`:** interview the user on the axes the file cannot answer: units first, then naming, shared files, and the two failure postures. Batch related questions, and lead each with your recommendation so the user can confirm rather than compose an answer. When an answer will produce a fragile action, say so once with the concrete failure, then record what the user decides.

**With `--yolo`:** resolve every axis yourself. Use one topic per named stream with the source's own names, ingest every field, map canonical types from the source types, carry units the format records and list the ones it does not, and use the DataFrame path unless Phase 2 rules it out. Treat bad input as a data error (exit code 65). When one stream fails, write the others, leave the file unmarked, and exit 65 naming the stream. Mark each choice as a default in `SPEC.md`.

## Phase 2 — Choose the write path

Three paths write topics. `references/ingestion-api.md` maps each; confirm every call you will use against source 1 before choosing.

**DataFrame (`File.add_topic`).** Parse each stream into a pandas DataFrame and pass it with its timestamp column and unit. Inside the action's container, the SDK writes the frame to Parquet, infers message paths and statistics, uploads the Parquet to the dataset under `.VISUALIZATION_ASSETS/`, and registers it as the topic's representation. A rerun updates the topic in place. It is the default for tabular data. It maps canonical types from Arrow types and puts a unit only on the timestamp path, so other units and any type correction need `Topic.update_message_path` afterwards (rule 7).

**Topic, message paths, representation (`Topic.create`, then `set_default_representation`).** Use it for data a DataFrame cannot hold (images, point clouds, large binary payloads) and for streams already stored as MCAP or Parquet. You write every step, and a topic without a representation lists normally but returns no rows (rule 1). A representation is an MCAP or Parquet file, never the original binary: write an MCAP whose messages carry the payload in an encoding the SDK decodes, upload it under a directory whose name starts with a dot, and register it (rule 11).

**Declared topics (`File.declare_topics`, experimental).** One call registers each topic's schema (fields carry their own unit and, for fixed-width arrays, element names), its timeline sources, the files a read opens, and optionally a `data_range` slice of the file and an `anchor_ns` wall-clock instant. Use it when one file holds several runs that belong to different sessions, when timestamps count from zero and must be anchored without rewriting them, or when the file's own bytes are MCAP or Parquet that a read can open in place. As of the `verified-on` date, `File.get_topics` and the web app's per-file topic views do not list a declared topic; it is read through a session or through `roboto.experimental.topics.Topic`. Tell the user this before choosing it.

One action may combine paths: the DataFrame path for telemetry and the second path for a camera stream is normal. Every path ends the same way. After every topic `SPEC.md` names is written, the action calls `file.mark_ingested()` (rule 9). A file stays `partly_ingested` from its first topic until that call, and a session holding the file does not announce `session.ingested` while one of its ingestable files is not `ingested`.

**Confirm the plan.** State the inventory, each resolved axis, the write path per stream with its reason, and the action name, which says what it ingests (`acme-tlm-ingestion`, not `parser`). Under `--yolo`, present this as what you are about to build and continue. Otherwise, get the user's go-ahead before writing files.

## Phase 3 — Scaffold and implement

### Step 1: Scaffold

Never hand-write the project layout. `roboto actions init <parent-dir>` wraps Roboto's project template; `<parent-dir>` must already exist, and the project is created in a subdirectory named after the action. It reads four answers from stdin: the action name, the description, the input type as a number (`1` = files, which an ingestion action takes), and whether to initialize a git repository (`y`, so Phase 5 can review a diff):

```bash
printf '%s\n' '<Action Name>' '<description>' '1' 'y' \
  | roboto --suppress-upgrade-check actions init <parent-dir>
cd <parent-dir>/<action-slug> && ./scripts/setup.sh
```

Read the generated `DEVELOPING.md` before writing code; it is rendered from the template on every scaffold and is the authority on this project's workflow. Record the `.venv` SDK version (see "Sources, in order of authority").

### Step 2: Implement

Before writing a call, check its signature against the SDK in `.venv`. Then write, in this order:

1. **`action.json`**: name, description, parameters with `required` and `default`, and `compute_requirements` sized for the largest expected file, not the sample (rule 14). Leave `requires_downloaded_inputs` unset: the action reads the raw file.
2. **The parser**, in its own module: functions that take a path and return frames or plain values, and import nothing from `roboto` (rule 17).
3. **`main.py`**: set the log level from the context; for each input file, confirm it is in a dataset, parse it, and on a parse failure log the file and the problem and exit with `ExitCode.DataError` (rule 8). Write the topics, then call `mark_ingested`. Gate every write on `not context.is_dry_run`, and log what each write would do: topic name, row count, time range, message paths (rule 13). Leave `bin/entrypoint.py` and `main`'s signature as the template has them.
4. **`pyproject.toml` and `Dockerfile`**: the template's `roboto[analytics]` dependency already brings pandas and pyarrow for the DataFrame path. Add the parser's libraries as runtime dependencies and its system packages to the Dockerfile (rule 15).
5. **Tests**: the parser against a small fixture you may redistribute, including a truncated and an empty file (rule 17).
6. **`SPEC.md`**: the format inventory, each decision with its rationale (marked user answer or default), the write path per stream, what is not ingested and why, failure behavior, compute sizing, the `.venv` SDK version, and a verification table with every row pending (rule 18).
7. **`README.md`**: what format the action reads, the topics it writes, its parameters, and how to invoke it.

## Phase 4 — Verify

Four steps, cheapest first. Ingestion is verified by reading the data back, not by watching the action exit cleanly.

### Step 1: Run the project's checks

If Phase 3 changed `pyproject.toml`, re-run `./scripts/setup.sh` first, or a missing dependency fails as an `ImportError` that reads like a code bug. Then run `./scripts/verify.sh` and fix what it reports until it passes. If `ruff` disagrees with your code, change the code, not the configuration.

### Step 2: Check the parser against the sample, offline

From `.venv`, run the parser on the sample and print, per topic, the row count, the first and last timestamp as UTC, and three values (first record, middle, last). Read the same three values from the file independently: a hex dump, the vendor's viewer, or a second library. Values that are plausible are not values that are correct. Record both sets; Step 4 compares the platform's values with them.

### Step 3: Dry-run a local invocation

This needs the sample in a dataset in the org. Use one the user names. Otherwise, propose a scratch dataset and give the commands, unrun, with what they write:

```bash
roboto --suppress-upgrade-check datasets create -n <action-slug>-verification
roboto --suppress-upgrade-check datasets upload-files -d <ds_id> -p <sample>
```

An upload fires the org's upload triggers and ingestion rules that match the file's path. Before asking, list the triggers (`roboto triggers list`), test the path against the rules (Phase 0), and tell the user which, if any, would run. Wait for a yes.

`invoke-local` attaches its container to a terminal, so from a non-interactive shell it exits before the container starts. Supply a pty; BSD `script` on macOS and util-linux `script` take the command differently:

```bash
case "$(uname -s)" in
  Darwin) script -q /dev/null roboto --suppress-upgrade-check --log-level=info actions invoke-local --dry-run --dataset <ds_id> --file-path <path> ;;
  *)      script -qec "roboto --suppress-upgrade-check --log-level=info actions invoke-local --dry-run --dataset <ds_id> --file-path <path>" /dev/null ;;
esac
```

Run it from the project root, with `--org` when Phase 0 found several orgs (`datasets create` takes `--org` too). `--file-path` takes the file's path in the dataset, not on disk: `upload-files -p <sample>` stores the sample under its file name, so pass `--file-path flight_014.tlm`, not `--file-path ./samples/flight_014.tlm`. A path the dataset does not hold selects no input, and the run still exits 0. Read the log, not the exit code: `invoke-local` does not check the container's exit status and exits 0 whether the action succeeded or failed. The planned topics, row counts, and time ranges must match Step 2. A clean exit that planned nothing has verified nothing.

### Step 4: Write, then read back

Running without `--dry-run` writes to the org: it creates the topics, uploads representation files, and marks the file ingested, which makes it eligible for the org's `file.ingested` triggers. Show the command (Step 3's, without `--dry-run`), say what it writes and to which dataset, and wait for a yes. Then read the result with a script run by `uv run --no-project` against source 1, using the checks in `references/ingestion-api.md` ("Reading back"):

1. **Topics**: names and count match the inventory; nothing missing, nothing extra.
2. **Message paths**: canonical types and units match `SPEC.md`. A path typed `unknown` that should be a number is a defect even though nothing failed.
3. **Rows**: each topic's data comes back non-empty. An empty frame means a missing representation (rule 1).
4. **Values**: the three values per topic equal the Step 2 values read independently from the file.
5. **Time**: first and last timestamps match the sample. A year of 1970 or one far in the future means a wrong unit (rule 3).
6. **Status**: the file's `ingestion_status` is `ingested`.
7. **Sessions**: if the file belongs to a session, `Session.list_topics()` includes the topics and `Session.ingestion_status()` counts the file as ingested. If no session holds it, say this check did not run.
8. **Rerun**: run the same command again, then repeat checks 1 and 3: topic count and row counts are unchanged (rule 6).

When the user also agrees to upload a truncated copy of the sample, invoke on it and confirm from the log that the action named the file and the problem and wrote no topics, and that the file is not marked `ingested`. `invoke-local` exits 0 here too, so it cannot show exit code 65; record that the exit code was not observed, and rely on the rule 17 tests for the error `main` turns into 65.

If the data does not read back, do not change the check until it passes. Return to Phases 2 and 3: on the DataFrame path the cause is usually the timestamp column or unit; on the other paths, a missing representation. If the user declines Step 4, the action is unverified against the platform: say so in the report.

Record every run in `SPEC.md`'s verification table: the command, the input, and what it showed.

## Phase 5 — Edit pass

Review the files you wrote (the parser, `main.py`, tests, `SPEC.md`, `README.md`) in four passes, fixing what you find:

1. **API truth.** Check every SDK name, keyword argument, and enum member against `.venv`, in particular `CanonicalDataType`, `RepresentationStorageFormat`, `TimeUnit`, and `ExitCode`. An invented member fails at ingestion time, not at import.
2. **Names.** Topic and message-path names match `SPEC.md`; function names say what they do.
3. **Comments.** Each says why, not what. None mentions this skill, its phases, the interview, or `--yolo` (rule 18).
4. **Diff.** Read `git diff`; only your files changed. Re-run `./scripts/verify.sh`.

Escalate to the report only a fix that would contradict a user decision or go beyond `SPEC.md`.

## Phase 6 — Hand off

Report:

1. **What the action does**: one paragraph, and the project path.
2. **The format inventory** from Phase 1.
3. **Decisions made**: every resolved axis, marked as a user answer or a `--yolo` judgment.
4. **Write path** per stream, and why.
5. **Verification**: each gate with its command and input, and what it showed. Name any gate that did not run and why.
6. **Not ingested**: every field, stream, or record type left out, and why.
7. **Contradictions**: each place the sample disagreed with the format documentation or the user's description.
8. **Open items**: units the format does not record, which need a decision before a fleet's files are ingested without them, and anything escalated from Phase 5.

Then name the sources you verified against (page URLs, the SDK version from source 1 and from `.venv`) and anything you could not verify.

Give these commands without running them, since each writes to the user's organization:

- **Deploy**: `./scripts/deploy.sh [ROBOTO_ORG_ID]`, which creates or updates the action and pushes its image. The org ID is required when the user belongs to several orgs.
- **Ingest every upload**: an ingestion rule naming the format's path patterns and this action, created by an org admin with the request in `references/ingestion-api.md` ("Ingestion rules"). Prefer it to a plain upload trigger: a file the rule matches is ingestable from upload, so a complete session waits for its ingestion before it announces `session.ingested`. A file no rule matches becomes ingestable only when the action writes its first topic, so the session can announce `session.ingested` before the action has run.
- **Files already uploaded**: the rule's existing-files ingestion, or `POST /v1/ingestion-rules/ingest` for up to 100 file IDs.
- **Clean up**: `roboto datasets delete -d <ds_id>` for a scratch dataset Phase 4 created.

To run something else automatically once these files are ingested, the `create-roboto-trigger` skill creates and verifies a trigger on `file.ingested` or `session.ingested`.
