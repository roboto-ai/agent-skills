# Getting started with Roboto

This reference gives the onboarding path from nothing to a first ingested log, in the order a new user needs it. It was copied from the SDK README, the Get Started pages, and the user guides on the date recorded as `verified-on` in the `metadata` block of `SKILL.md`. The README changes with each SDK release and the docs pages change on their own schedule, so before you give install steps, fetch the README and confirm the commands still match:

- SDK README (install commands, extras, CLI binaries): https://raw.githubusercontent.com/roboto-ai/roboto-python-sdk/refs/heads/main/README.md
- Docs pages, via `scripts/roboto_docs.py fetch`: `getting-started/account`, `getting-started/programmatic-access`, and the `user-guides/get-started-ros` or `user-guides/get-started-px4` page that matches the user's log format.

Before answering, ask two questions if the user has not already answered them: which operating system they use, and whether they want the CLI, the Python SDK, or both. A user who only wants to upload and run actions needs the CLI. A user who wants to analyze topic data in Python needs the SDK.

## 1. Create an account

Sign up at https://app.roboto.ai/signup with an email address. The sign-up flow asks for an Individual or Team account; Team suits anyone who will invite collaborators. The web app's sidebar has Home, Search, Collections, Actions, Action Hub, and Settings; the `getting-started/account` docs page describes each.

## 2. Create a personal access token

1. Sign in and open https://app.roboto.ai/settings/tokens.
2. Fill in "Create a new access token" and click Create. The token is shown once.
3. Save it to `~/.roboto/config.json`:

```json
{
    "version": "v1",
    "profiles": {
        "prod": {
            "api_key": "robo_pat_..."
        }
    },
    "default_profile": "prod"
}
```

For CI and containers, set `ROBOTO_API_KEY` in the environment instead; it takes precedence over the file. To keep the file elsewhere, set `ROBOTO_CONFIG_FILE` or pass `--config-file` on the CLI.

One file can hold several profiles. `--profile <name>` on the CLI or `ROBOTO_PROFILE` selects one; when `default_profile` is omitted, the profile named `default` is used.

Never paste the token or the file into the conversation.

## 3. Install the CLI

The CLI is a standalone binary, distributed separately from the Python package. From the README:

| Platform | Steps |
|---|---|
| macOS | `brew install roboto-ai/tap/roboto`, or download `roboto-macos-aarch64` or `roboto-macos-x86_64` from the latest release |
| Linux, apt | Download the `roboto-linux-<arch>_<version>.deb` from the latest release and install it with `apt` (not the `roboto-agent` files) |
| Linux, other | Download `roboto-linux-x86_64` or `roboto-linux-aarch64`, `chmod +x`, and move it onto `PATH` such as `/usr/local/bin` |
| Windows | Download `roboto-windows-x86_64.exe` and put it in a folder on `PATH` |

Latest release: https://github.com/roboto-ai/roboto-python-sdk/releases/latest

To upgrade, run `brew upgrade roboto` on Homebrew; otherwise download the new file and replace the old one. When a newer version exists, the CLI prints `[notice] A new release of roboto is available` on stderr. It checks the GitHub releases API at most once an hour; `--suppress-upgrade-check` or `ROBOTO_CLI_SUPPRESS_UPGRADE_PROMPT=true` silences the notice.

Verify:

```bash
roboto --version
roboto users whoami
```

`whoami` returning the user's identity proves the token and the config file are correct. If the CLI exits with `roboto: error: No Roboto config file found at specified path '.../.roboto/config.json'`, step 2 was skipped or the file is in the wrong place (the SDK raises the same message as a `FileNotFoundError`). `roboto: error: ... is not valid JSON` means the file has a syntax error.

## 4. Install the Python SDK

Use Python 3.11 or newer and a virtual environment; installing into the system Python is the most common cause of failures.

```bash
python3 -m venv .venv && source .venv/bin/activate     # Windows: python -m venv .venv && .venv\Scripts\activate
pip install roboto
pip install 'roboto[analytics]'                        # add this for pandas DataFrames and signal search
python -m roboto.cli users whoami                      # the CLI is also available this way
```

Quote the extra on zsh, or the shell treats the brackets as a glob. Extras: `analytics` (topic data as DataFrames, similarity search), `ingestion` (writing Parquet in ingestion actions), `video` (frame extraction), `examples` (Jupyter tooling for the notebooks).

For a one-off script, `uv` can build the environment from an inline metadata header instead; see `sdk-cookbook.md`.

## 5. Upload a first log and ingest it

```bash
roboto datasets create --name "First upload" -t test          # prints the new dataset as JSON; note the ds_ id
roboto datasets upload-files -d ds_xxx -p ./flight.ulg        # a file or a whole directory
```
Ingestion turns a log into searchable topics, and the file format decides which ingestion action to run. Roboto's ingestion actions live in the Action Hub, published by the `roboto-public` org (private deployments differ). A trigger can run them automatically on upload.

The SDK README maps formats to actions as below. Confirm the exact name in `roboto actions search --actionhub`, which prints the current Hub listing with each action's `org_id`, and invoke that.

| Format | Files | Action (per the SDK README) |
|---|---|---|
| ROS 2 | `.mcap`, `.db3` | `ros_ingestion` |
| ROS 1 | `.bag` | `ros_ingestion` |
| PX4 | `.ulg` | `ulog_ingestion` |
| ArduPilot | `.bin`, `.log`, `.tlog` | `ardupilot_ingestion` |
| Parquet | `.parquet` | `parquet_ingestion` |
| CSV | `.csv` | `csv_ingestion` |
| Video | `.mp4`, `.avi`, `.mkv` | `video_ingestion` |
| Journal | `.log` | `journal_log_ingestion` |

Invoke one manually the first time to see it work. A bare action name is looked up in the user's own org only, so a Hub action needs the owner org's ID in front of it:

```bash
roboto actions invoke roboto-public/ulog_ingestion --dataset ds_xxx --file-path '**/*.ulg'    # prints the invocation id
roboto invocations status --tail iv_xxx
roboto invocations logs --tail iv_xxx
```

`--file-path` takes a dataset-relative path or glob and can be repeated. The Hub ingestion actions have no required parameters.

The `user-guides/get-started-ros` and `user-guides/get-started-px4` pages walk through this with screenshots. `user-guides/trigger-ros` and `user-guides/trigger-px4` cover setting up the trigger so later uploads ingest automatically.

Users in more than one organization need `--org og_xxx` on `create`, `invoke`, and `actions search` (or `ROBOTO_ORG_ID` in the environment); `roboto users orgs` lists their organizations.

## 6. First look at the data

In the web app, Search shows the dataset, its files, and, after ingestion, its topics; the visualizer plots them. From Python:

```python
from roboto import Dataset

ds = Dataset.from_id("ds_xxx")
for f in ds.list_files():
    print(f.relative_path, f.ingestion_status)
topic = ds.get_file_by_path("flight.ulg").get_topic("vehicle_air_data")
df = topic.get_data_as_df()          # needs roboto[analytics]
```

A flight or drive that spans several files or devices is a session; `sdk-cookbook.md` ("Sessions") shows how to create one from the dataset and read its topics and metrics as one run.

From here, `learn/concepts` explains the entities, `roboql/overview` explains search, and the user guides cover triggers, events, collections, and actions.

## 7. Optional: connect an AI tool

The hosted Roboto MCP server lets Claude Code, Claude Desktop, Cursor, Codex, VS Code, and other MCP clients search and analyze the user's data in conversation. It acts as the signed-in user. Its tools do not modify or delete existing data; the few that write add new records (visualizer layouts and workspaces, thread forks). The one exception is sending a message to a Roboto AI thread, which runs Roboto's AI as the user and can do anything AI Chat can.

```bash
claude mcp add --transport http roboto https://mcp.roboto.ai/mcp
```

Then run `/mcp` inside Claude Code (or `claude mcp login roboto`) to finish the browser sign-in, which lasts up to 30 days. Headless setups instead pass a personal access token with full API access as an `Authorization: Bearer` header. Users in several orgs should ask the AI to call `whoami`, then `set_active_org`. For other clients, see `user-guides/use-roboto-mcp-server`.

## Where to get help

The docs are at https://docs.roboto.ai. Email info@roboto.ai, or join the community Discord linked from the SDK README.
