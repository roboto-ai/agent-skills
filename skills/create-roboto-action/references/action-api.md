# Roboto Action API surface

This file is a pre-scaffold map of the Action authoring surface: enough to run the requirements interview of SKILL.md Phase 1 and decide how an action takes input, reads parameters, and writes output before any files exist.

It is not the authority; it is the lowest rung of the SKILL.md "Ground truth" ladder. The SDK changes and this file does not, so it tells you what to look up rather than what to trust. Confirm every signature you call against the installed SDK, the generated `DEVELOPING.md`, or the `docs.roboto.ai` pages linked below. Where this file and a live source disagree, the live source wins.

## Durable references

These paths are stable; prefer them over search results.

| Resource | URL |
|---|---|
| Actions concept guide | https://docs.roboto.ai/learn/actions.html |
| Create your own action | https://docs.roboto.ai/user-guides/creating-your-own-action.html |
| Python SDK reference index | https://docs.roboto.ai/reference/python-sdk.html |
| `InvocationContext` | https://docs.roboto.ai/reference/python-sdk/roboto/action_runtime/invocation_context/index.html |
| `ActionInput` | https://docs.roboto.ai/reference/python-sdk/roboto/action_runtime/action_input/index.html |
| `ActionConfig` (the `action.json` schema) | https://docs.roboto.ai/reference/python-sdk/roboto/domain/actions/index.html#roboto.domain.actions.ActionConfig |
| `ActionParameter` | https://docs.roboto.ai/reference/python-sdk/roboto/domain/actions/action_record/index.html#roboto.domain.actions.action_record.ActionParameter |
| RoboQL query language | https://docs.roboto.ai/roboql/index.html |
| Programmatic access / tokens | https://docs.roboto.ai/getting-started/programmatic-access.html |
| SDK source | https://github.com/roboto-ai/roboto-python-sdk |
| Project template source | https://github.com/roboto-ai/cookiecutter-roboto-actions |

## What an action is

A containerized Python function that runs on Roboto's managed compute. Roboto provisions a container, optionally downloads the invocation's input files, executes the entrypoint, streams logs, uploads the contents of the action's output directory, and records a final status.

## Generated project layout

`roboto actions init` produces, for an action named `Tag Dataset`:

```
tag-dataset/
├── action.json                       # action definition: name, compute, parameters
├── DEVELOPING.md                     # authoritative authoring guide (read this)
├── Dockerfile                        # runtime image; system deps go here
├── pyproject.toml                    # Python deps (runtime + dev)
├── README.md
├── .python-version                   # keep in sync with Dockerfile's Python
├── scripts/{setup,verify,build,deploy}.sh
├── src/tag_dataset/
│   ├── __init__.py
│   ├── bin/entrypoint.py             # do not edit: builds context, calls main
│   ├── logger.py
│   └── main.py                       # action logic lives here
└── test/test_main.py                 # asserts main()'s signature contract
```

`roboto actions init [path]` writes into an existing directory: `path` defaults to the current working directory, and the command errors out when the target is not already a directory.

`init` lowercases the action name and turns spaces into hyphens for the directory and the Roboto identifier (`__project_slug`); hyphens become underscores for the Python package (`__package_name`).

`bin/entrypoint.py` is fixed machinery: it calls `roboto.InvocationContext.from_env()` and passes the result to `main`. Leave it alone.

## The `main` contract

```python
import roboto

def main(context: roboto.InvocationContext) -> None:
    ...
```

`main` takes exactly one positional parameter, annotated `roboto.InvocationContext`, and returns `None`. The generated `test/test_main.py` checks this by introspection, so signature drift fails `verify.sh` instead of failing at runtime. The check is narrower than it looks: it hard-asserts the parameter count and kind, but asserts the annotations only when they are present. Dropping the type hints does not itself break the action (the entrypoint passes the context positionally either way), but it blinds the annotation check, so a `main` written against the wrong parameter type passes `verify.sh` and fails only at runtime. Keep the hints.

## `InvocationContext`

Properties:

| Member | Type | Notes |
|---|---|---|
| `input_dir` | `pathlib.Path` | Where input files land when downloaded |
| `output_dir` | `pathlib.Path` | Write outputs here; auto-uploaded on hosted success |
| `is_dry_run` | `bool` | Gate every side effect on this being false |
| `log_level` | `int` | Feed to `logger.setLevel(...)` |
| `dataset_id` / `dataset` | `str` / `Dataset` | Invocation's dataset context |
| `invocation_id` / `invocation` | `str` / `Invocation` | |
| `org_id` / `org` | `str` / `Org` | |
| `roboto_client` | `RobotoClient` | For `RobotoSearch` and direct SDK calls |
| `file_changeset_manager` | `FilesChangesetFileManager` | Pending tag/metadata edits for not-yet-uploaded outputs |

Methods:

| Method | Returns | Notes |
|---|---|---|
| `get_input()` | `ActionInput` | The invocation's resolved input data |
| `get_parameter(name)` | `str` | Raises `ActionRuntimeException` when the parameter has no value |
| `get_optional_parameter(name, default_value=None)` | `str \| None` | The keyword is `default_value`, not `default` |
| `get_secret_parameter(name)` | `str` | Looks the parameter's name up in the runtime secrets file |
| `from_env()` | `InvocationContext` | Classmethod; only `entrypoint.py` calls it |

`get_parameter` and `get_optional_parameter` detect a `roboto-secret://` value and delegate to `get_secret_parameter`, so an action that reads a secret through either of them still gets the resolved value.

Prefer these members over reading `ROBOTO_*` environment variables directly; the env vars are an implementation detail and may change between SDK versions.

## `ActionInput`

A dataclass with two fields:

- `files: Sequence[tuple[File, Optional[Path]]]` — the `Path` is the local file when it was downloaded, and `None` otherwise (see `requires_downloaded_inputs`).
- `topics: Sequence[Topic]`

`ActionInput` also offers `get_topics_by_name(topic_name) -> list[Topic]`.

Files carry `file_id` and `relative_path`, and offer `get_topics()`, `get_topic("<name>")`, and `download(local_path)`. Topics carry `topic_name`, `topic_id`, `schema_name`, `association`, and `get_data_as_df(start_time=..., end_time=...)` returning a pandas DataFrame.

Topic data access needs the analytics extra: depend on `roboto[analytics]`.

## `action.json` (`ActionConfig`)

Only `name` is required.

| Field | Type | Notes |
|---|---|---|
| `name` | `str` | The Roboto Action identifier; kebab-case |
| `description` | `str` | |
| `short_description` | `str` | |
| `parameters` | `list[ActionParameter]` | See below |
| `compute_requirements` | object | `vCPU`, `memory` MiB, `storage` GiB (see the constraints below) |
| `container_parameters` | object | Container-level overrides |
| `requires_downloaded_inputs` | `bool` | Default true |
| `timeout` | `int` | Minutes. Server default: 30 minutes for free-tier orgs, 12 hours otherwise |
| `metadata` | object | |
| `tags` | `list[str]` | |
| `inherits` | `ActionReference` | |
| `docker_config` / `image_uri` | object / `str` | Mutually exclusive; the template uses neither and lets `deploy.sh` build |

`ActionParameter` fields: `name`, `description`, `required` (default `false`), `default` (optional-only; coerced to a string).

### Compute requirement constraints

An out-of-range value here fails at action-create time, after the image has already been built and pushed. Roboto does not support GPU compute; `gpu` is pinned to `False`. The tier-dependent values in this file (the `timeout` default and the `storage` cap) were last checked August 2026.

| Field | Default | Allowed |
|---|---|---|
| `vCPU` | 512 (0.5 vCPU) | One of 256, 512, 1024, 2048, 4096, 8192, 16384 |
| `memory` | 1024 (1 GiB) | A discrete set per `vCPU` (see below) |
| `storage` | 21 (GiB) | 21 to 200 GiB (200 requires a premium-tier org) |

`memory` is not a range but an enumerated set fixed by the chosen `vCPU`, so a value like 1536 fails validation even though it falls between two legal ones:

| `vCPU` | Allowed `memory` (MiB) |
|---|---|
| 256 | 512, 1024, 2048 |
| 512 | 1024 to 4096, step 1024 |
| 1024 | 2048 to 8192, step 1024 |
| 2048 | 4096 to 16384, step 1024 |
| 4096 | 8192 to 30720, step 1024 |
| 8192 | 16384 to 61440, step 4096 |
| 16384 | 32768 to 122880, step 8192 |

Raise `vCPU` alongside `memory` rather than raising `memory` alone.

`storage` caps how much input a single invocation can hold on disk. The default of 21 GiB is also the minimum, so an action that downloads more must raise `storage`.

## Parameters are always strings

Every parameter value arrives as a string regardless of the declared default's JSON type. Parse and validate in `main`:

```python
threshold = int(context.get_parameter("threshold"))
if not 0 <= threshold <= 100:
    raise ValueError("Invalid threshold parameter: must be between 0 and 100")

enabled = context.get_optional_parameter("enabled", "false").lower() == "true"
config = json.loads(context.get_parameter("config"))
tags = context.get_parameter("tags").split(",")
```

### Secrets

A secret is an ordinary parameter. Declare it in `action.json` like any other (an undeclared name is rejected at invocation time) and pass its value as `roboto-secret://<secret-name>`, which `get_secret_parameter` resolves:

```bash
roboto secrets write my-api-key API_KEY_VALUE
roboto actions invoke-local --parameter api_key="roboto-secret://my-api-key"
```

`roboto secrets write` takes the name and the value as two positionals, and creates the secret when it does not already exist.

## Input

### Selected at invocation time (preferred)

The invoker or trigger selects the data, and the action reads `context.get_input()`, which keeps the action reusable and lets triggers drive it.

### Queried at runtime

The action queries Roboto itself:

```python
search = roboto.RobotoSearch.for_roboto_client(context.roboto_client)
for file in search.find_files("path LIKE '%.log' AND size < 1000000"):
    ...
```

Query at runtime only for batch jobs with a fixed query and no trigger. Otherwise let the invoker select the data.

### `requires_downloaded_inputs`

This flag affects file-query and dataset/file-path input only. When `false`, `local_path` in every `ActionInput.files` tuple is `None` and only file metadata is available. That is the right setting for topic-driven actions, which fetch data over the API rather than off disk.

## Output

Write to `context.output_dir`. On hosted compute, files there upload after successful completion, into the invocation's output dataset if one was given, or, when all inputs came from a single dataset, into that dataset. Input spanning multiple datasets skips the automatic upload. Local invocation never uploads: outputs stay in `.workspace/output/` for inspection until the next local invocation wipes the workspace.

```python
(context.output_dir / "results.json").write_text(json.dumps(summary))
```

### Dataset tags and metadata

A classification action often writes no files at all, and instead tags the dataset:

```python
context.dataset.put_tags(["ERROR"])
context.dataset.put_metadata({"voltage_spikes_seen": 693})
```

`context.dataset` raises `ActionRuntimeException` when the invocation has no associated dataset. What causes the raise is a missing dataset id, not local execution: `invoke-local --dataset <ds_id>` sets one and `context.dataset` resolves normally, while query-based input (`--file-query` / `--topic-query`), a bare `invoke-local` with no `--dataset`, and scheduled triggers all leave it unset. An action whose only output is a dataset tag therefore crashes under exactly those invocation modes. Rule 12 of `authoring-rules.md` gives the remedy: when the invocation mode permits an unspecified dataset, either derive the dataset from an input or guard the access.

### Annotating input files

Mutate already-uploaded files directly, not through the changeset:

```python
existing = context.dataset.get_file_by_path("already_uploaded.txt")
existing.put_tags(["reviewed"])
existing.put_metadata({"anomaly_count": 3})
```

`File` objects from `get_input().files` expose the same `put_tags` and `put_metadata`, so an action that annotates its own inputs can skip the dataset lookup.

### Output-file tags and metadata

To attach tags or metadata to a file that has not been uploaded yet, stage the edits through the changeset manager; they apply after the upload:

```python
mgr = context.file_changeset_manager
mgr.put_tags("results.json", ["anomaly"])
mgr.put_fields("results.json", {"peak_load": 0.94})
mgr.set_description("results.json", "Per-topic load summary")
```

Also available: `remove_tags(relative_path, tags)` and `remove_fields(relative_path, keys)`.

### Events

Events mark time ranges on datasets, files, topics, or message paths:

```python
roboto.Event.create(
    name="High CPU load",
    start_time=start_ns,
    end_time=end_ns,
    topic_ids=[topic.topic_id],
    description="...",
    metadata={"peak": peak},
    tags=["anomaly"],
    roboto_client=context.roboto_client,
)
```

Times are nanoseconds. Omit `end_time` for an instantaneous event.

## CLI commands

```bash
roboto actions init [path]              # scaffold a project (wraps the cookiecutter)

./scripts/setup.sh                      # build .venv from pyproject.toml
./scripts/verify.sh                     # ruff + pytest
./scripts/build.sh                      # build the Docker image
./scripts/deploy.sh [ROBOTO_ORG_ID]     # build, push, create/update the action

# run in Docker against a dataset in the org
roboto actions invoke-local --dry-run \
  --dataset <ds_id> --file-path '*.txt' --parameter key=value
roboto actions invoke-local --dry-run --topic-query "<roboql>"

roboto actions invoke <action-name> --dataset <ds_id> --file-path '*.txt'
roboto invocations status --tail <iv_id>   # invocation IDs are prefixed iv_
roboto invocations logs --tail <iv_id>

roboto datasets create
roboto datasets upload-files -d <ds_id> -p ./log.txt
roboto datasets show -d <ds_id>

roboto triggers create --name <n> --action <a> \
  --required-inputs 'log.txt' --for-each dataset_file
```

`invoke-local` always runs inside Docker for production parity, rebuilding the image each time; layer caching keeps the rebuild short. Run from an action directory, it creates `.workspace/` in the project root and wipes it clean at the start of every invocation. Given an action name instead, it fetches the published image and works in a temp directory unless `--workspace-dir` names another.

Every run seeds `.workspace/output/` with `.metadata/dataset_metadata_changeset.json`, so the directory is never empty; that file belongs to the runtime, not the action.

Input selection is either query-based (`--file-query` / `--topic-query`) or dataset-and-path-based (`--dataset` with `--file-path`). The two groups are mutually exclusive, and `--file-path` requires `--dataset`. Both groups are optional: a bare `invoke-local` selects no input at all, which is the correct verification run for an action that reads nothing.

`--parameter` (`-p`) takes `name=value` and repeats. The value is taken as a raw string, never parsed as JSON, and a name not declared in `action.json` is rejected before the container starts. (`roboto triggers create` uses a different flag, `--parameter-value`, whose values are parsed as JSON.)

Two more failures land before the container starts. `invoke-local` requires `--org` when the caller belongs to more than one organization. It also attaches the container to a terminal, so in a non-interactive shell it builds the image and then exits — with status 0, because the CLI never checks whether the container launched, so a scripted run can pass while verifying nothing. Supply a pty via `script`, branching on `uname -s` because BSD (macOS) and util-linux (Linux) `script` take their arguments differently.

```bash
script -q /dev/null roboto ... invoke-local ...          # macOS (BSD script)
script -qec "roboto ... invoke-local ..." /dev/null      # Linux (util-linux script)
```

`roboto triggers create` builds an event-driven trigger: `--for-each` of `dataset_file` or `dataset` (default `dataset`), glob `--required-inputs`, and `--required-tag` / `--required-metadata` / `--condition-json` conditions. Roboto evaluates such a trigger on File Uploaded, File Ingested, Dataset Metadata Updated, and File Metadata Updated; the CLI exposes no flag to narrow that set.

Cron schedules are a separate resource, `ScheduledTrigger`, reachable only through the SDK. Scheduled invocations carry no dataset, which is why `context.dataset` raises under them.

## Dependencies

Runtime deps go in `[project].dependencies` in `pyproject.toml`; dev-only tools go in `[project.optional-dependencies].dev`. The deployed image omits the dev deps. Re-run `./scripts/setup.sh` after editing either.

System packages go in the `Dockerfile` under the `# -- INSTALL SYSTEM DEPENDENCIES --` marker:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg \
    && rm -rf /var/lib/apt/lists/*
```

A library that works on the workstation but goes undeclared fails only inside the container; that is why local invocation runs in Docker.
