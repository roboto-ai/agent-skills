# Upload agent API map

What the upload agent reads, writes, and sends to Roboto, for running the Phase 1 interview and knowing what to look up in Phases 2 to 5.

Every field, flag, and default below was checked against the SDK release recorded as `verified-sdk` in the `metadata` block of `SKILL.md`, by reading `roboto/upload_agent/` in that wheel from PyPI, by printing models through `uv run --with roboto python -c ...`, and by `python -m roboto.upload_agent <command> --help` and `python -m roboto.cli <group> <command> --help`, on the date recorded as `verified-on`. The release files were checked on the GitHub release of that version, and device attribution against the devices page of the Roboto docs (www.roboto.ai/docs). A newer release can change any of it: re-check what you use against source 1 of SKILL.md's "Sources, in order of authority". Where this file and a live source disagree, the live source wins.

## Durable references

These paths are stable; prefer them over search results.

| Resource | URL |
|---|---|
| Devices, registration, attribution | https://www.roboto.ai/docs/learn/devices |
| Access tokens, device tokens, scopes | https://www.roboto.ai/docs/getting-started/programmatic-access |
| `roboto devices` CLI | https://www.roboto.ai/docs/reference/cli/devices |
| `roboto datasets` CLI | https://www.roboto.ai/docs/reference/cli/datasets |
| Agent config models | https://www.roboto.ai/docs/reference/python-sdk/roboto/upload_agent/files |
| `Device.create_token` | https://www.roboto.ai/docs/reference/python-sdk/roboto/domain/devices/device |
| Platform events | https://www.roboto.ai/docs/reference/python-sdk/roboto/domain/platform_events/events |
| Sessions | https://www.roboto.ai/docs/reference/python-sdk/roboto/experimental/sessions/session |
| Ingestion and formats | https://www.roboto.ai/docs/learn/formats |
| SDK source and release files | https://github.com/roboto-ai/roboto-python-sdk/releases |

## Invoking the agent

| Form | Where it comes from | Command |
|---|---|---|
| Binary from the `.deb` | The Linux `.deb` of each release installs `/usr/bin/roboto` and `/usr/bin/roboto-agent` | `roboto-agent` |
| Standalone binary | Release files `roboto-agent-{linux,macos}-{x86_64,aarch64}` and `roboto-agent-windows-x86_64.exe`; the Linux `.deb` installs the same file | the downloaded file, made executable; install it as `roboto-agent` on the `PATH` (`/usr/local/bin/roboto-agent`) so the commands in this skill find it |
| Python module | `pip install roboto`; the wheel declares only the `roboto` console script | `python -m roboto.upload_agent` |

The install script (`install.sh`) installs only `roboto`. `roboto upgrade` upgrades the CLI and, for a `.deb` or Python install, prints the upgrade command; it does not replace a standalone `roboto-agent` file.

| Flag | Placement | Behavior |
|---|---|---|
| `-v`, `-vv`, `-vvv` | Before the subcommand | WARNING, INFO, DEBUG. With no flag the level is INFO. DEBUG applies to every library, and its boto3 lines carry the temporary S3 upload credentials |
| `-q` | Before the subcommand | ERROR only; hides the lock message (rule 16) |
| `configure` | Subcommand | Prompts for the marker filename, delete-after-upload, and search paths; writes those three and the defaults of every other field, so rerunning it resets them; asks before overwriting |
| `run` | Subcommand | One pass |
| `run -f`, `--forever` | After `run` | Repeats the pass, sleeping 30 seconds after each, until the process is stopped or a pass raises |
| `run -m`, `--merge-uploads` | After `run` | One new dataset per pass that finds markers, holding every marked directory (rule 11) |
| `run -a`, `--auto-create-upload-configs` | After `run` | Writes markers one level below each search path first (rule 6) |
| `run --default-roboto-upload-file <path>` | After `run` | Template for auto-created markers; only with `-a`. Its error message names a nonexistent `--default-upload-config` |

## The agent config

`~/.roboto/upload_agent.json`, in the home directory of the user the agent runs as. `ROBOTO_CONFIG_FILE` moves the credentials file, not this one. Model: `roboto.upload_agent.files.UploadAgentConfig`. A missing or unparseable file logs an error naming `roboto-agent configure`, and the run uploads nothing and exits 0.

| Field | Default | Behavior |
|---|---|---|
| `version` | `"v1"` | Only value |
| `search_paths` | required | Directories searched recursively for markers on each pass; a path that is not a directory logs an error and is skipped. `~` is not expanded, and a relative path resolves against the agent's working directory, so write absolute paths |
| `upload_config_filename` | `".roboto_upload.json"` | The marker filename |
| `delete_uploaded_files` | `false` | Delete local files after upload; a marker can override it (rule 12) |
| `delete_empty_directories` | `false` | Remove a directory left empty, or holding only the completion file (rule 13) |
| `default_org_id` | `null` | Org of the dataset merge mode creates; nothing else reads it |

## The per-directory marker

A file named `upload_config_filename`. Its directory, with everything below it, becomes one dataset. Model: `roboto.upload_agent.files.UploadConfigFile`. `{}` is a valid marker. An unparseable marker logs an error with a traceback and its directory is skipped on every pass.

| Field | Behavior |
|---|---|
| `dataset.description`, `dataset.metadata`, `dataset.tags` | Applied when the dataset is created |
| `dataset.org_id` | The org to create the dataset in (rule 9) |
| `dataset.add_to_collections` | Collection IDs; each add is attempted after upload, and a failure is logged (rule 10) |
| `dataset.name`, `dataset.device_id`, `dataset.custom_fields` | Accepted and not applied (rule 2). `name` over 120 characters makes the marker unparseable |
| `upload.include_patterns`, `upload.exclude_patterns` | Gitignore-style patterns, matched against each file's name, not its path (rule 17). Exclude wins over include |
| `upload.delete_uploaded_files` | Overrides the agent config for this directory |

An auto-created marker without a template is the full model: `version` `"v1"`, `metadata` `{}`, `tags` `[]`, and every other field `null`.

## State files

Written next to the marker. Neither is listed in the agent config.

| File | Written | Contents | Effect on the next pass |
|---|---|---|---|
| `.roboto_upload_in_progress.json` | When the dataset is chosen, before upload | `{"version": "v1", "dataset_id": "ds_...", "started": "<ISO 8601 time>"}` | Uploads into that dataset instead of creating one, without applying the marker's dataset properties; never uploaded. If the file does not parse, it is ignored and a new dataset is created |
| `.roboto_upload_complete.json` | After upload | `{"version": "v1", "dataset_id": "ds_...", "completed": "<ISO 8601 time>"}` | Directory skipped, even if the file is unparseable (rule 4) |

## What one pass does

1. Takes the lock `~/.roboto/tmp/upload_agent.lock` with a 1-second timeout; if another running agent process holds it, logs at INFO that the agent appears to be running already and exits (rule 16).
2. With `-a`, writes markers into eligible directories one level below each search path.
3. Finds every marker under every search path. For each marker:
   - skips the directory if the completion file exists;
   - with an in-progress file, loads that dataset; otherwise creates one with the marker's description, metadata, tags, and `org_id`, and writes the in-progress file;
   - uploads the directory tree, in upload transactions of up to 500 files, excluding the in-progress file and anything the marker's patterns exclude; if deletion is on, deletes the uploaded files (not directories) after all of them are uploaded;
   - deletes the marker, writes the completion file, deletes the in-progress file, and uploads the completion file to the dataset root;
   - removes the directory if `delete_empty_directories` allows (rule 13);
   - adds the dataset to the marker's collections.
4. Logs "Uploaded N datasets". An exception at any point ends the pass, and the process (rule 15).

## Credentials and org

The agent builds one client per process from `ROBOTO_API_KEY` or `ROBOTO_BEARER_TOKEN`, or else from the profile in `ROBOTO_CONFIG_FILE` or `~/.roboto/config.json` (`ROBOTO_PROFILE`, then the file's `default_profile`). It sends an org only from a marker's `org_id`, or `default_org_id` in merge mode. It reads neither `ROBOTO_ORG_ID` nor a profile's `org_id`, which the CLI reads (rule 9).

| Credential | Created by | Lifetime | Attribution |
|---|---|---|---|
| Device token | `roboto devices register <id> -f <file>` or `roboto devices generate-creds <id> -f <file>`, run with a personal token | 366 days | Datasets are attributed to the device; bound to one org |
| `roboto auth login` token | Browser sign-in | 30 days by default, up to 365 with `--expiry-days` | None |
| `roboto setup` token | Browser sign-in during setup | 180 days by default, up to 365 | None |

A device ID must not be empty, `.`, or `..`, and must not contain a control character or any of `:`, `@`, `/`, `?`, `#`, `%`. `roboto devices disable <id>` turns off the device's tokens without deleting them; `enable` turns them back on.

## After upload

The completion file is the last file the agent uploads for a directory, so a `file.uploaded` event for `.roboto_upload_complete.json` arrives once per recording, after all of its files. `dataset.upload_completed` fires once per upload transaction, which is at least twice per recording. Building a trigger on either belongs to the `create-roboto-trigger` skill.

Ingestion rules (experimental) decide which uploaded dataset files are ingested. A file whose path a rule matches when it is uploaded is ingestable, and while the rule's `auto_ingest` is on, Roboto runs the rule's action on it with no trigger to write. There is no client class for rules in this release. This read-only script, run with the user's own credentials, prints which rules match the paths the agent will upload. A path is relative to the dataset, and the dataset root is the marker's directory, so a recording's `vehicle.mcap` is `vehicle.mcap`, not `<recording dir>/vehicle.mcap`:

```python
import warnings
from roboto.warnings import ExperimentalWarning
warnings.filterwarnings("ignore", category=ExperimentalWarning)

from roboto.experimental.ingestion_rules import MatchIngestionRulesRequest, MatchIngestionRulesResponse
from roboto.http import RobotoClient

response = RobotoClient.from_env().post(
    "v1/ingestion-rules/match",
    data=MatchIngestionRulesRequest(paths=["vehicle.mcap", "logs/system.log"]),
    caller_org_id="og_xxx",
).to_record(MatchIngestionRulesResponse)
for path, rules in response.matches.items():
    print(path, [(rule.name, rule.auto_ingest) for rule in rules])
```

`og_xxx` is the org the datasets land in. An empty list means no rule matches that path.

The agent creates datasets, not sessions. `Dataset.create_session(name, ...)` makes a session from a dataset's files, and `Session.complete()` (both experimental) marks it complete, after which `session.ingested` fires once its ingestable files are ingested.

## systemd template

For `run --forever` on Linux. Replace the placeholders, and use the Python form in `ExecStart` when the machine has no binary. `ExecStart` names the binary by its absolute path, or the absolute path of the interpreter that has `roboto` installed (`/opt/roboto-venv/bin/python -m roboto.upload_agent run --forever`); a bare `python3` passes `systemd-analyze verify` and runs the system interpreter. Check the file with `systemd-analyze verify ./roboto-upload-agent.service` before installing it; it reports an `ExecStart` path that does not exist.

```ini
[Unit]
Description=Roboto upload agent
Wants=network-online.target
After=network-online.target

[Service]
User=<service-user>
ExecStart=/usr/bin/roboto-agent run --forever
# Environment=ROBOTO_CONFIG_FILE=/path/to/<device_id>-config.json
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Install it as `/etc/systemd/system/roboto-upload-agent.service`, then `systemctl daemon-reload` and `systemctl enable --now roboto-upload-agent`. The log goes to the journal: `journalctl -u roboto-upload-agent`.
