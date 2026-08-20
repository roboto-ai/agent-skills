# Upload agent surface

A map for running the Phase 1 interview and knowing what to look up. Rung 4 of SKILL.md's Ground truth ladder — the lowest.

This component is thinly covered on the docs site, so the usual fallback is weaker than elsewhere and the installed module is correspondingly more authoritative. **Read the module.** `site-packages/roboto/upload_agent/` is small, and the pydantic models in it are the definitive statement of every config field, type, and default.

## Durable documentation URLs

- Devices, and how data is attributed to one: `https://docs.roboto.ai/learn/devices.html`
- Datasets and storage: `https://docs.roboto.ai/learn/storage.html`
- Collections: `https://docs.roboto.ai/learn/collections.html`
- Credentials and programmatic access: `https://docs.roboto.ai/getting-started/programmatic-access.html`
- CLI reference: `https://docs.roboto.ai/reference/cli.html`

## Invoking it

The module is runnable as `python -m roboto.upload_agent`. Its own log messages refer to a `roboto-agent` command, and whether that exists depends on how the SDK was installed — the public package's declared entry points do not guarantee it. **Establish which form works on the target machine during Phase 0**, and use that one consistently in the service unit and the runbook.

Two subcommands:

- **`configure`** — an interactive prompt that writes the machine's agent config. It asks for the marker filename, whether to delete uploaded files, and one or more search paths, validating that each is an existing directory. It overwrites an existing config after a confirmation prompt, so it needs a terminal.
- **`run`** — one scan-and-upload pass. Flags worth knowing, confirmed with `run --help`:
  - a flag to loop forever, sleeping between passes on a period fixed by the module
  - a flag to merge every upload into a single dataset (see authoring rule 10)
  - a flag to auto-create markers for directories that lack them (authoring rule 6)
  - a flag naming a custom default marker template, valid only alongside auto-creation

Verbosity is stackable and the useful detail sits below the default level; read the top-level `--help` for the exact flags. There is also a quiet flag that suppresses everything but errors.

## The agent config

One per machine, in the SDK's config directory, named for the upload agent. Read the `UploadAgentConfig` model for the current fields; as of writing it carries:

| Field | Purpose |
|---|---|
| `version` | Schema version literal |
| `search_paths` | The directories scanned recursively each run. The only required field |
| `upload_config_filename` | The marker filename to look for. Defaults to a dotted `.roboto_upload.json` |
| `delete_uploaded_files` | Machine-wide: remove local files after a successful upload. **See authoring rule 3** |
| `delete_empty_directories` | Machine-wide: remove directories left empty afterwards. **See authoring rule 4** |
| `default_org_id` | The org used where the operation would otherwise be ambiguous, such as the dataset created by merge mode |

The file is validated on load. A malformed one produces a parse error and a message telling the user to re-run `configure`; it does not fall back to defaults.

## The per-directory marker

One per recording directory. Its **presence is the signal** — it tells the agent that this directory is a dataset and that everything in it and below it should be uploaded. Read the `UploadConfigFile` model; it has two sections.

**The dataset section** extends the platform's own dataset-creation request, so it carries the same properties a dataset is created with — name, description, metadata, and `device_id` for attribution — plus two additions: an org id, and a list of collection ids to add the created dataset to (best-effort; authoring rule 13).

**The upload section** carries per-directory include and exclude patterns, and a per-directory override of the delete-uploaded-files setting.

A marker whose contents are an empty object is valid; that is what auto-creation writes when no template exists.

## State files

The agent keeps its state in the recording directory itself, as two dotted JSON files alongside the marker:

- **An in-progress file**, written when an upload starts, naming the dataset and the start time. Its presence on a later run means resume into that dataset (authoring rule 5).
- **A completion file**, written when the upload finishes, naming the dataset and the completion time. Its presence means skip, permanently, and an unparseable one still means skip (authoring rule 2).

Both matter to the runbook: forcing a re-upload means removing the completion file, and diagnosing a duplicate dataset usually means someone removed an in-progress file.

## Concurrency

A lock file in the SDK's config directory, acquired with a short timeout at the start of a run. A second instance fails to acquire it, logs that the agent appears to already be running, and exits without uploading. An orphaned lock therefore stops all uploads silently; the log line says so and names the file to delete. See authoring rule 8.

## Auto-creating markers

With the auto-creation flag, the agent writes a marker into every directory **one level under** each search path that does not already have a marker, an in-progress file, or a completion file. Empty directories are skipped. Contents come from a default template file in the SDK config directory, or from the path given by the custom-template flag; if neither exists, the marker is an empty object.

The template's contents are read with **environment variable references resolved**, which is the mechanism behind authoring rule 11 — a template setting dataset metadata from a hostname or robot id variable produces per-machine metadata from one shared file.

## Verifying the round trip

The upload is verified in Roboto, not on disk:

```bash
roboto --suppress-upgrade-check datasets show <ds_id>
roboto --suppress-upgrade-check datasets list-files <ds_id>
```

Confirm flags with `--help`. Check the dataset's name, description, tags, metadata, device attribution, and collection membership against what the marker asked for, and check the file list against what was in the directory. Then check the directory for its completion file, and run the agent again to confirm nothing is uploaded twice.

## What comes after

The agent uploads; it does not ingest. Files that have arrived are not yet topics. Automating that next step is a trigger on file upload invoking an ingestion action — `create-roboto-trigger` for the trigger, and `create-roboto-ingestion-action` if the format is not one Roboto already supports.
