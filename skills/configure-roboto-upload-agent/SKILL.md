---
name: configure-roboto-upload-agent
description: >-
  Configure the Roboto upload agent (roboto-agent) on a robot, test rig, or
  upload station so recordings reach Roboto with no one running a command, and
  prove one upload round trip before anything deletes the local copy. Use this
  skill whenever data should leave a machine automatically, even if the user
  only describes the outcome ("our robots should upload their logs after every
  run", "set up an upload station", "stop copying bags off the rig by hand").
  Covers device credentials, an ambiguity-resolving interview (skipped under
  --yolo), the agent config and per-directory upload markers, verification by
  a scratch upload checked in Roboto, the delete-after-upload decision, and
  unattended operation under a service manager. Not for building an ingestion
  action for a format Roboto cannot read yet (use the
  create-roboto-ingestion-action skill), and not for one-off uploads, general
  Roboto questions, or one-off scripts (use the roboto-guide skill).
license: MPL-2.0
compatibility: >-
  Needs a shell on the uploading machine and network access to www.roboto.ai,
  pypi.org, files.pythonhosted.org, raw.githubusercontent.com, and
  api.github.com. Needs uv (or Python 3.10+ with pip), the roboto CLI, and
  Roboto credentials. Registering a device needs a personal access token;
  installing a service needs the privileges the machine's service manager
  requires.
metadata:
  verified-sdk: "0.64.0"
  verified-on: "2026-11-18"
argument-hint: <which machine should upload what, from where, and when> [--yolo]
---

Get recordings off a machine and into Roboto without anyone running a command, attributed to the machine's device when it uploads with a device credential, and prove the round trip in Roboto before anything is configured to delete the local copy.

## What you need to run this

This skill does not know which agent is reading it, so it names the capabilities it needs rather than assuming them:

- **Run shell commands** and read their output, on the machine that will upload. If your session runs elsewhere, Phase 0 says how to proceed.
- **Read and write files**, including under the home directory of the user the agent will run as.
- **Hold a back-and-forth with the user.** Phase 1 is an interview, and the deletion decision in Phase 4 is never made by judgment.
- **Fetch a web page.** Optional: `curl` does the same.

uv is the preferred runner because it resolves the latest SDK on every run. Without uv, build one virtual environment for the session (`python3 -m venv`, then `pip install --upgrade 'roboto[analytics]'`) and use its interpreter wherever this skill says `uv run`.

`references/` throughout means the directory alongside this file. Read `references/agent-api.md` and `references/authoring-rules.md` before Phase 1.

## The request

The user's description of the deployment is the argument to this skill. Strip a `--yolo` flag from anywhere in it; what remains is the description. If the description is empty, ask the user which machine should upload what, and stop.

`--yolo` suppresses the Phase 1 interview and nothing else. The preflight, the verification gates, and the recording of decisions all stand: every ambiguity resolved by judgment lands in `SPEC.md` with its rationale, so the user audits the decisions after the fact instead of before.

`--yolo` never authorizes a write to the user's organization or to the uploading machine. Registering a device, writing the agent config onto the robot, running the scratch upload, enabling deletion, and installing the service each stay the user's call: give the exact command and wait for a yes.

## Sources, in order of authority

Three sources outrank every file in this skill. They are numbered by authority: when two disagree, the lower number wins. Start with the source whose Answers column fits the question, and stop at the first source that answers it.

| Source | What | How | Answers |
|---|---|---|---|
| 1 | The latest released SDK and CLI, resolved fresh from PyPI | `uv run --no-project --isolated --refresh-package roboto --with 'roboto[analytics]' python -c "import inspect, roboto.upload_agent.files as f; print(inspect.getsource(f))"`; for flags, `uv run --no-project --isolated --refresh-package roboto --with roboto python -m roboto.upload_agent run --help` or `python -m roboto.cli <group> <command> --help` | Config fields and defaults, agent flags, CLI flags, signatures |
| 2 | The Roboto docs at www.roboto.ai/docs | Fetch `https://www.roboto.ai/docs/<path>.md`; see "Docs lookups" | Devices and device tokens, credentials, datasets, collections, triggers |
| 3 | The SDK CHANGELOG and GitHub releases | Fetch https://raw.githubusercontent.com/roboto-ai/roboto-python-sdk/refs/heads/main/CHANGELOG.md and https://api.github.com/repos/roboto-ai/roboto-python-sdk/releases/latest | Which release changed a behavior; the latest version; the release files, including the `roboto-agent` binaries |

Every lookup of the latest release runs with `--no-project --isolated`, so that a `uv run` started inside a Python project or virtual environment neither uses the `roboto` installed there (an older pinned release, for example) nor writes a `uv.lock` into the project, and with `--refresh-package roboto`, so that it does not reuse PyPI's answer from up to ten minutes earlier and miss a new release.

The files under `references/` rank below all three. The `metadata` block in this file's frontmatter records the SDK release (`verified-sdk`) and date (`verified-on`) they were last checked against. When Phase 0 finds a newer release, re-check anything you take from them against source 1 before using it. Cite the live source, not the reference file.

**Docs lookups.** To find a page, fetch `https://www.roboto.ai/docs/llms.txt`, which lists every page with its URL. To read one, fetch its Markdown copy by adding `.md` to the URL (`https://www.roboto.ai/docs/learn/actions.md`); without a fetch tool, `curl -sL <url>`. To find where an SDK symbol is documented, search `https://www.roboto.ai/docs/reference/python-sdk/objects.json` for its dotted name. For REST endpoints, read `https://www.roboto.ai/docs/reference/rest-api/openapi.json`. These files are large, so read them through a search (`grep`, or a Python one-liner) rather than printing them whole. If the agent runtime can start a subagent, run lookups in one and return only the answer.

- **The installed CLI and SDK are not authoritative.** They are whatever version the user last installed, and `roboto <command> --help` describes that version and nothing else. If the CLI is behind, say so and point to `roboto upgrade`; on a CLI older than 0.58.0, point to `brew upgrade roboto`, or to replacing the binary or `.deb` from the latest release.
- **The agent that will run is the authority on what it does.** Once Phase 0 has found the agent on the uploading machine, its `--help` and, for a Python install, its source under `site-packages/roboto/upload_agent/` describe the code the service will run. Record its version in `SPEC.md`. If it is behind source 1, say what differs and recommend upgrading it; never lower source 1 to match it.
- **A docs page can be ahead of the release.** When source 2 describes something source 1 lacks, source 3 says whether it is released. Build against the release, and tell the user what is coming.
- **Recommend the API that fits the task.** Ingestion rules and sessions live under `roboto.experimental`; that is not a reason to steer the user to an older mechanism. Scripts that import them filter `ExperimentalWarning` once at the top, as `references/agent-api.md` shows.

Never write a config field from memory: neither config model rejects unknown keys (rule 1).

Where a source cannot be reached, say which one and what you could not check. With no fetch tool and no `curl`, ask the user to paste the page.

## Phase 0 — Preflight

Run this before the interview. Every check below guards a step that would otherwise fail after the user has answered questions and you have written the configuration.

Every command runs on the uploading machine, as the user the agent will run as. If your session is not on that machine, say so now, run what you can where you are (the version and docs checks), and produce the remaining commands for the user to run there. A configuration verified on the wrong host has verified nothing: the search paths, the credentials, and the service manager all differ.

```bash
uname -s                                             # platform; macOS and Linux; Windows is untested
roboto --version                                     # installed CLI; compare with the latest release below
uv --version                                         # runner for source 1
roboto --suppress-upgrade-check users whoami         # credentials valid; which identity they carry
roboto --suppress-upgrade-check users orgs           # one pretty-printed JSON object per org
curl -s https://pypi.org/pypi/roboto/json | python3 -c 'import json,sys; print(json.load(sys.stdin)["info"]["version"])'
command -v roboto-agent && roboto-agent --help       # the agent binary, if installed
python3 -m roboto.upload_agent --help                # the agent from a Python install, if the binary is absent
ls -l ~/.roboto/upload_agent.json ~/.roboto/default_roboto_upload.json   # existing agent config and marker template
```

- **The agent's form.** The `.deb` and the release files provide a `roboto-agent` binary; `pip install roboto` provides only `python -m roboto.upload_agent` (table in `references/agent-api.md`). Record which form this machine has, because the service unit and the runbook name it. A downloaded release file keeps its release name (`roboto-agent-linux-x86_64`, for example), so `command -v roboto-agent` finds it only once it is installed under that name on the `PATH`, such as `/usr/local/bin/roboto-agent`; look for it where the user downloaded it. If neither works, stop and tell the user to install the `.deb` or the release binary (source 3).
- **The agent's version.** The binary has no `--version` flag. For the `.deb`, `roboto --version` reports the package version; for a release file, the version is the release it was downloaded from, which `sha256sum` against that release's `roboto-sha256sums.txt` confirms; for a Python install, `python3 -c "from roboto.version import roboto_version; print(roboto_version())"`. Compare it with the latest release.
- **`users whoami`** prints the identity as JSON. A device credential shows the device in `fully_qualified_device_id` (`<device_id>@<org_id>`); a personal token shows `null` there. If it fails, the credentials are missing, expired, or disabled; report the path or variable the error names. A token restricted with API scopes and lacking `api.everything_else` fails this check and `users orgs` even when it can upload (rule 14).
- **`users orgs`** lists the orgs a personal token can act in. A user in more than one org needs an org in every marker (rule 9); a device credential is bound to one org, so for it this check is informational.
- **Existing configuration.** Read any existing agent config and template, and carry forward what the user still wants. Check the service manager (`systemctl --version`, or `launchctl` on macOS) and whether the user can install units.

Never read `~/.roboto/config.json` to check credentials, and never print a token. If the latest release is newer than `verified-sdk`, say that the references predate it. If a check fails, stop and tell the user exactly what to install or run. Do not begin the interview.

## Phase 1 — Plan the deployment

### Step 1: Map the layout

Ask what the machine writes, where, and when, and look at a real example on disk. Before configuring anything, write down what one recording looks like: one directory or several, how deep below the intended search path, whether files are still being written when the agent could see them, and how much accumulates between uploads. A directory the agent uploads while it is still being written is uploaded partially and never revisited (rule 5).

### Step 2: Find the ambiguities

When an axis turns on platform behavior, resolve it against the sources before asking the user. Do not spend an interview question on something the code or docs answer.

| Axis | What is undetermined | Consequence of guessing wrong |
|---|---|---|
| Credential | A device credential, or a personal token? | Only a device credential attributes datasets to the device (rule 8) |
| Device ID | What names this machine in Roboto? | Must pass the device ID rules; the docs suggest a serial number |
| Search paths | Which directories the agent scans | Too narrow uploads nothing; too broad scans the whole tree every pass |
| Dataset granularity | One dataset per recording directory, or everything merged? | Merge mode skips collection membership and resolves conflicts in no fixed order (rule 11) |
| Completion signal | What marks a recording as finished? | The partial-upload failure (rule 5) |
| Marker source | Does the recorder write the marker, or does the agent auto-create it? | Auto-creation looks one level deep only (rule 6) |
| Dataset properties | Description, tags, metadata, collections, from what? | A name, device ID, or custom fields in a marker are not applied (rule 2) |
| Org | Which org the datasets land in | A multi-org personal token with no `org_id` in the marker fails the pass (rule 9) |
| Cadence | Run once per recording, on a timer, or continuously? | Decides whether a service manager is involved |
| After upload | Ingestion by the org's ingestion rules or a trigger; sessions? | Uploaded files are not ingested files (Phase 6) |
| Delete after upload | Remove the local copy once uploaded? | Destroys data; never resolved by judgment (rule 12) |
| Empty-directory cleanup | Remove emptied directories? | Milder, and still deletion (rule 13) |
| Failure posture | Who notices when uploads stop? | An error ends the pass, and a hung agent process holding the lock stops every later run (rules 15, 16) |

### Step 3: Resolve

**Without `--yolo`:** interview the user on the axes the layout and the sources cannot answer. Batch related questions and lead each with your recommendation, so the user confirms rather than composes. Use a structured multiple-choice prompt where your harness has one, for the axes with a small fixed set of answers (credential, granularity, cadence, failure posture).

**With `--yolo`:** resolve every axis except deletion yourself. Prefer a device credential named after the machine's serial number or hostname, the narrowest search paths that cover the data, one dataset per recording directory, a marker written by whatever ends the recording where that is possible, and `run --forever` under the service manager. Set both deletion settings off and say so in the report, with what turning them on would take. Record each choice in `SPEC.md` with its rationale, and mark it as a default in the hand-off report.

### Step 4: Confirm the plan

State the layout, each resolved axis, both files you will write, the credential plan, the verification you will run, and every command that writes to the org or the machine. Under `--yolo`, present this as what you are about to do and continue to the first write, where you wait for the user's yes.

## Phase 2 — Configure

### Step 1: Credentials

Recommend a device credential for any machine that uploads unattended. On a machine with the user's own credentials (usually their workstation, not the robot), registering the device creates it in the org and writes its credentials to a new file:

```bash
roboto --suppress-upgrade-check devices register <device_id> -f ./<device_id>-config.json
```

This writes to the org; wait for the user's yes. The command refuses to overwrite an existing file, and for a device that already exists it creates new credentials instead. The command writes the file with the default permissions (`0664` under a common umask), so `chmod 600` it at once. Copy the file to the uploading machine as `~/.roboto/config.json` of the service user, readable only by that user, or set `ROBOTO_CONFIG_FILE` in the service to point at it. Its one profile is named `<org_id>_<device_id>` and is the file's default profile, so leave `ROBOTO_PROFILE` unset in the service's environment: a `ROBOTO_PROFILE` naming any other profile fails every call with "User profile '...' was not found". Check it with `ROBOTO_CONFIG_FILE=<file> roboto --suppress-upgrade-check users whoami`, which shows `<device_id>@<org_id>` in `fully_qualified_device_id`. Record the device ID and the token's expiry date in `SPEC.md` (rule 14). If the user keeps a personal token instead, record that datasets will not be attributed to the device, and when that token expires.

### Step 2: The agent config

The agent reads `~/.roboto/upload_agent.json` from the home directory of the user it runs as (rule 3). `roboto-agent configure` writes it interactively, but it asks about only three of the fields and needs a terminal. Writing the file directly is usually simpler; take the field names from source 1 (the table in `references/agent-api.md` is the map), then check that it parses as you meant:

```bash
uv run --no-project --isolated --refresh-package roboto --with roboto python -c "import pathlib; from roboto.upload_agent.files import UploadAgentConfig as M; print(M.model_validate_json(pathlib.Path('upload_agent.json').read_text()).model_dump_json(indent=2))"
```

Compare the printed fields with the file. A key you wrote that is missing from the output was dropped (rule 1). Run the same check with `UploadConfigFile` for the marker and the template. Set both deletion settings to `false` for now, whatever Phase 1 decided; Phase 4 turns them on.

### Step 3: The marker

Write the per-directory marker as a template that the recorder writes when a recording ends, or as `~/.roboto/default_roboto_upload.json` when the agent auto-creates markers with `run -a`. Environment variables in the template are substituted when the agent auto-creates a marker (rule 7). A marker carries only its dataset's properties; search paths and deletion defaults belong in the agent config (rule 1). Its upload patterns match file names, not paths (rule 17), and no marker's directory may sit inside another's (rule 18).

### Step 4: The deliverable

Deliver the files as a directory the user can commit, not as edits made in place on one machine:

```
upload-agent/
├── upload_agent.json            # the machine's agent config
├── roboto_upload.json           # the per-directory marker template
├── roboto-upload-agent.service  # the unit that runs it unattended, if used
└── SPEC.md                      # decisions, credential plan, verification results, runbook, versions
```

`SPEC.md` also records the agent's form and version, the SDK release checked against, and each Phase 1 decision with its rationale. It documents the deployment, not how it was produced: it never mentions this skill, its phases, the interview, or `--yolo`. Copy the files onto the uploading machine only after the user's yes.

## Phase 3 — Verify one round trip

Run the agent once, not in its continuous mode, against one scratch recording, and check each step in Roboto, not on disk. The scratch upload creates a dataset in the org; say so and wait for the user's yes.

1. **Stage a scratch recording.** A new directory in the real layout under a real search path, holding a small representative file and the marker. Use data the user can lose, even though deletion is off.
2. **Run once at the default level.** It is INFO, which logs every decision step 3 reads. The verbosity flags go before the subcommand, and a single `-v` lowers the level to WARNING:

   ```bash
   roboto-agent run          # or: python3 -m roboto.upload_agent run
   ```

   Do not use `-vvv` here or under a service. It sets DEBUG for every library the agent uses, so the log fills with hundreds of boto3 lines, including the temporary S3 upload credentials (`x-amz-security-token`) and tracebacks of errors the agent handles; it adds only two agent lines, for writing the state files.

3. **Read the log for the decisions.** It names each search path it scanned, each marker it found, the dataset it created ("Created dataset ds_... for path ..."), and ends with "Uploaded N datasets". A run that logs "No upload config files found under any search path" uploaded nothing, whatever its exit code. A traceback after "Couldn't parse file as valid upload config files" means that marker was skipped and the pass went on; any other traceback means the pass stopped at that directory (rule 15). Read the log, not the exit code: the agent exits 0 after every error it logs itself (no agent config, an unparseable one, the lock held), and 1 only when an exception ends the pass.
4. **Confirm the dataset in Roboto.** `roboto --suppress-upgrade-check datasets show -d <ds_id>`: the org, `description`, `tags`, and `metadata` are what the marker asked for, and `device_id` is the device when the agent ran on a device credential (rule 8). `datasets list-files -d <ds_id>` lists the directory's files that the patterns allow. File listings leave out every file whose dataset path starts with a dot, so the marker and `.roboto_upload_complete.json` at the dataset root never appear there, uploaded or not. Confirm the completion file by path: `uv run --no-project --isolated --with roboto python -c "from roboto import Dataset; print(Dataset.from_id('<ds_id>').get_file_by_path('.roboto_upload_complete.json').file_id)"` prints a `fl_` ID, and raises `RobotoNotFoundException` if the file is missing. For each collection in the marker, run `roboto collections show <collection_id> --content-mode references`; a failed add is logged and does not fail the upload (rule 10).
5. **Confirm the local state.** The marker is gone, and `.roboto_upload_complete.json` names the dataset (rule 4).
6. **Run again.** The log must end with "Uploaded 0 datasets". A second dataset here is a defect to fix now.
7. **Test resumption.** Restore the marker, delete the completion file, and write `.roboto_upload_in_progress.json` naming the scratch dataset (format in `references/agent-api.md`). The next run must log "Found upload-in-progress file for dataset ds_... at path ..., resuming upload" and no "Creating a dataset" line. This is the state a power loss mid-upload leaves behind. A resumed upload does not apply the marker's description, metadata, or tags to the dataset.

Record each step, its command, and what it showed in `SPEC.md`. If the round trip fails, fix it here; every later phase assumes it works.

## Phase 4 — Enable deletion

Only if Phase 1 said yes, only after Phase 3 passed, and only on the user's explicit word for this step, including under `--yolo`. On a robot the local copy is often the only copy, and the agent deletes after its own notion of success (rule 12).

1. Stage a second scratch recording from data the user confirms they can lose. Ask; do not assume the first one qualified.
2. Set `delete_uploaded_files` (and `delete_empty_directories`, if chosen), re-check the file with the parse command from Phase 2, and run once.
3. Confirm in Roboto first that every file is in the dataset, then confirm the local files are gone. The other order proves nothing about the data.
4. If empty-directory cleanup is on, confirm the directory was removed, or explain why it was not (rule 13).

State in the hand-off, on its own line, that this machine deletes local data after upload.

## Phase 5 — Run unattended

Choose the form from the cadence axis:

- **Run by the recorder.** Whatever ends a recording writes the marker, then runs `roboto-agent run` once. This ties "the recording is complete" to "upload it" most directly. A run that starts while another run holds the lock exits without uploading (rule 16), so a recording that ends during an upload waits for the next run; add a timer so that next run comes.
- **Continuously.** `roboto-agent run --forever` under a service manager. It sleeps 30 seconds after each pass, a period the agent fixes. Any error ends the process, so the unit needs a restart policy (rule 15).
- **On a timer.** A systemd timer or cron entry runs `roboto-agent run` at the cadence the user wants. Overlapping runs are harmless: the second finds the lock held and exits (rule 16).

The unit runs as the user whose `~/.roboto/` holds the agent config and credentials, starts at boot, restarts on failure, and sets `ROBOTO_CONFIG_FILE` when the credentials live elsewhere. `references/agent-api.md` has a systemd template. Installing it is a write to the machine; wait for the user's yes.

**Verify it as installed.** Start the service, stage one more scratch recording, and confirm it uploads with no command from you, through `datasets show` and the service log (`journalctl -u roboto-upload-agent` under systemd). Then, if the user permits, reboot and confirm the service comes back and uploads. If you cannot install or start the service, say exactly why and deliver the unit file with the commands that install it.

## Phase 6 — Hand off

Report:

1. **What is configured, and where.** The machine, the agent's form and version, both config files, the marker template, the service unit, and the path to the delivered directory.
2. **Decisions made.** Every resolved axis, marked as a user answer or a `--yolo` default.
3. **Verification.** Each check from Phases 3 to 5 with its command and dataset ID, including whether the reboot test ran. Name any gate that did not run and why.
4. **Deletion status**, on its own line: on or off.
5. **Credentials.** Which identity uploads, whether datasets are attributed to the device, when the token expires, and how to renew it (`roboto devices generate-creds <device_id> -f <new-file>`, then restart the agent, which reads credentials once per process).
6. **The runbook**, also in `SPEC.md`: how to see that the agent is running and where its log goes; how to force a re-upload (delete the completion file and restore the marker, which creates a new dataset; rule 4); what the lock message means and how to find the process holding the lock (rule 16); how to cut the machine off (`roboto devices disable <device_id>`).
7. **Open items.** Directories outside the search paths, recordings that never get a marker, and the rest of the fleet. Configure and verify one machine before copying the directory to others.

Then point at what comes next, without running it. Uploaded files are not ingested files. If the org's ingestion rules match the uploaded paths with `auto_ingest` on, Roboto ingests them on upload; `references/agent-api.md` has a read-only check. Otherwise, an org admin creates an ingestion rule for those paths; for a format Roboto cannot read yet, the `create-roboto-ingestion-action` skill builds the ingestion action and gives the rule request. To run other work once the files are ingested, the `create-roboto-trigger` skill creates and verifies the trigger. The agent creates datasets, not sessions; making a session from each upload is a step after it, such as an action that calls `Dataset.create_session`, which the `create-roboto-action` skill builds. The `roboto-guide` skill answers follow-up questions.

End with one or two lines naming the sources verified against (page URLs, SDK version, the agent's version) and anything not verified.
