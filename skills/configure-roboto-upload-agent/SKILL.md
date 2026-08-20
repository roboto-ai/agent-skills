---
name: configure-roboto-upload-agent
description: >-
  Configure, verify, and run the Roboto upload agent on a robot, test rig, or upload
  station so recordings reach Roboto without anyone typing a command. Use this skill
  whenever data should get off a machine automatically even if the user only describes
  the outcome ("our robots should upload their logs after every run", "set up an upload
  station", "how do we stop copying bags by hand"). Covers deployment decomposition,
  agent and per-directory configuration, a verified upload round trip, the delete-after-upload
  decision, and unattended operation under a service manager. Not for one-off uploads
  (use the CLI directly) and not for ingesting what was uploaded.
license: MPL-2.0
compatibility: Requires a Python environment with the roboto SDK installed on the uploading machine, and Roboto credentials available to it non-interactively
argument-hint: <what machine should upload what, and when> [--yolo]
---

Get recordings off a machine and into Roboto on their own — and prove the round trip before anything is configured to delete the local copy.

## What you need to run this

- **Run shell commands** and read their output, on the machine that will do the uploading.
- **Read and write files**, including under the user's home directory.
- **Hold a back-and-forth with the user.** One decision in this skill can destroy data; it is not resolvable by judgment.
- **Fetch a web page.** Optional here. The authoritative source for this component is the installed module.

No plugins, no external tool servers (such as MCP servers), no sub-agents.

`references/` throughout means the directory alongside this file. Read `references/agent-api.md` and `references/authoring-rules.md` before Phase 1.

## Where you are running matters

Every command in this skill runs **on the uploading machine** — the robot, the rig, the upload station — not on the user's laptop. If your session is not on that machine, say so at Phase 0 and produce the configuration and commands for the user to run there. A configuration verified on the wrong host has verified nothing: the search paths do not exist, the credentials differ, and the service manager may not be the same one.

Where the user's fleet is more than one machine, configure and verify **one** end to end first. Rolling out to the rest is a copy of a proven configuration, and it is much cheaper after the round trip is proven than before.

## Ground truth

This component is thinly documented on the docs site compared to the rest of the platform, which raises the authority of the installed module and lowers everything else.

| Rung | Source | How | When it wins |
|---|---|---|---|
| 1 | The installed module | `python -m roboto.upload_agent --help`, `python -m roboto.upload_agent run --help`, and reading `site-packages/roboto/upload_agent/` | Highest authority. It is the code that will run, and the flags it accepts are definitive |
| 2 | The config models in that module | Read the pydantic models that define both config files | Definitive for every field name, type, and default in the files you are about to write |
| 3 | `docs.roboto.ai` | Devices, datasets, collections, and credentials | Authoritative for the concepts the agent config refers to, not for the agent itself |
| 4 | `references/agent-api.md` | Read it | Lowest authority: a map, not a citation |

Never write a config field from memory. **Neither model rejects unknown keys.** A misspelled or misplaced field is silently dropped and the run proceeds on the default, so a typo presents as "the setting had no effect" with nothing in the log to say so. The only outright parse failures are a structurally invalid file or a missing `search_paths`. Write the field, then read the parsed config back and confirm the value you meant is in it.

**The module runs as `python -m roboto.upload_agent`, and only that.** The public package declares a single console script, `roboto` — there is no `roboto-agent` binary. The module nevertheless calls itself `roboto-agent` in its help banner and in its error messages ("Please run `roboto-agent configure`"), which are not runnable as printed. Use the module form in the service unit and the runbook, and warn the user that the log text names a command they do not have. One of its error messages also names a `--default-upload-config` flag that does not exist; the real one is `--default-roboto-upload-file`.

## Phase 0 — Preflight

Run these on the uploading machine:

```bash
python -c "import roboto; print('sdk ok')"           # SDK importable
python -m roboto.upload_agent --help                 # the only invocation form
python -m roboto.upload_agent run --help             # confirm this build's run flags
roboto --suppress-upgrade-check users orgs           # credentials valid; enumerates orgs
```

Record:

- **Which invocation form works.** Everything downstream — the service unit, the runbook — names one.
- **The org**, and whether the user belongs to more than one. A machine that uploads unattended cannot answer an ambiguity prompt.
- **How credentials reach the agent.** It resolves an API key or bearer token from the environment if one is set, and otherwise falls back to a profile in the SDK's config file — either is fine. What matters is that the credential is readable **by the user the service will run as** and survives a reboot; a key exported in an interactive shell profile satisfies neither, and is the most common reason an agent that worked during setup is not running the next morning. Credentials are also resolved once per process, so under the continuous mode a rotated key needs a restart.
- **The service manager**, if the machine has one, and whether the user can install units on it.
- **Whether an existing agent configuration is already present.** The configure step overwrites it after prompting. Read it first and preserve anything the user still wants.

**Do not plan on the agent attributing data to a device.** The marker's model accepts a device id and a dataset name, and the agent passes neither when it creates the dataset — only description, metadata, tags, and the org. Both fields parse cleanly and are discarded, so a dataset the agent uploads arrives unnamed and unattributed. If the user needs either, it is a step after upload (`roboto datasets update`, or a trigger), and it belongs in the plan as such.

## Phase 1 — Decompose the deployment

### Step 1: Establish the shape

Ask what the machine writes, where, and when. Produce a picture of the directory layout before configuring anything: what a single recording session looks like on disk, whether it is one directory or many, whether files are still being written when the agent might see them, and how much accumulates between uploads.

That last one is not a detail. An agent scanning a directory a recording is still being written into will upload a partial file, and the complete marker it then writes means it will never revisit it.

### Step 2: Resolve the ambiguities

| Axis | What is undetermined | Consequence of guessing wrong |
|---|---|---|
| Search paths | Which directories the agent scans | Too narrow and nothing uploads; too broad and it scans the whole disk every cycle |
| Dataset granularity | What becomes one dataset — a run, a day, a directory, everything merged? | Structural, and expensive to change once a fleet has uploaded under the wrong shape |
| Marker discipline | Does something already write the per-directory marker, or must the agent create markers itself? | Decides whether auto-creation is needed, and auto-creation only looks one level deep (rule 6) |
| Completion signal | How does the agent know a recording is finished? | The failure above. A marker written by whatever ends the recording is the reliable answer |
| Device attribution | Which device produced this data, and what names the dataset? | The agent sets neither — both are dropped on the floor. Decide now what applies them afterwards, or accept unnamed, unattributed datasets |
| Dataset metadata | Tags, description, name, collections — set from what? | The marker file carries them, and environment variables can be interpolated (rule 11) |
| Cadence | One shot per recording, or a continuously running agent? | Decides whether a service manager is involved at all |
| Delete after upload | Should the local copy be removed once uploaded? | **Destroys data.** See rule 3; this axis is never resolved by judgment |
| Empty-directory cleanup | Should emptied directories be removed? | Milder, and still deletion |
| Failure posture | What should happen when the upload fails or the network is down? | Determines whether anyone finds out |

**Without `--yolo`**, interview the user on the axes their layout cannot answer, and lead with your recommendation.

**With `--yolo`**, resolve every axis except deletion yourself, preferring the narrowest search paths that cover the data, one dataset per recording directory, and markers written by whatever ends the recording where that is possible. **Deletion stays a question even under `--yolo`** (rule 3). Default both deletion settings off, and say in the report that they are off and what it would take to turn them on.

### Step 3: Confirm the plan

State the directory layout, each resolved axis, both config files you are about to write, and the verification you will run before anything is automated.

## Phase 2 — Configure

Two files, two scopes, and confusing them is the most common configuration error (rule 1):

- **The agent config**, one per machine, in the user's Roboto config directory. It says which directories to scan, what marker filename to look for, and the machine-wide deletion settings.
- **The per-directory marker**, one per recording, whose presence is what tells the agent "this directory is a dataset, upload it". It carries that dataset's own properties — of which the agent applies description, metadata, tags, the org, and the per-directory include and exclude patterns. The model also accepts a name and a device id and the agent ignores both.

The module ships an interactive `configure` subcommand that writes the agent config after prompting. Prefer it over hand-writing the file — it is authoritative about field *spelling*, though not coverage: it asks about three of the six fields and writes the rest at their defaults. Read the file back and set what the prompts never raised. Note that it overwrites an existing config after a confirmation prompt, which means it needs a terminal; when you cannot supply one, write the file directly against the model in `references/agent-api.md` and confirm it parses by running the agent.

Write the marker as a **template** the user can copy or generate, not just as one file in one directory. Where recordings are created by another process, the durable answer is that process writing the marker when it finishes; where they are not, auto-creation covers it, with the constraint in rule 6.

Deliver both files, plus the service unit from Phase 5, as a committed directory rather than as edits made in place on one machine:

```
upload-agent/
├── upload_agent.json           # the machine's agent config
├── roboto_upload.json          # the per-directory marker template
├── roboto-upload-agent.service # the unit that runs it unattended, if used
└── SPEC.md                     # decisions, verification results, and the runbook
```

Set both deletion settings to off for now, whatever Phase 1 decided. Phase 4 turns them on, after the round trip is proven.

## Phase 3 — Verify one round trip

Run the agent once — not in its continuous mode — against one scratch recording, and check every link in the chain.

1. **Stage a scratch recording.** A new directory under a real search path, containing a small representative file and the marker. Do not use a directory holding data the user cannot lose; deletion is off, but this is the run that proves it.

2. **Run once, at maximum verbosity.** The verbosity flag is counted but **not monotonic**: the default is already INFO, one `-v` drops it to WARNING, two returns it to INFO, and only three adds DEBUG. So `-v` makes the run quieter than no flag at all — use `-vvv`. A single run is the right gate: continuous mode adds a sleep loop and nothing you want to debug through.

3. **Read the log for the decisions, not just the outcome.** It reports which search paths it scanned, which directories it skipped and why, how many markers it found, and how many datasets it created. A run that reports finding no markers has not uploaded anything, whatever else it says.

4. **Confirm the dataset in Roboto**, not on disk: it exists, it is in the right org, and its description, tags, metadata, and collection membership are what the marker asked for. Do **not** check the name or device attribution — the agent does not set them (rule 1). `roboto datasets show` and `roboto datasets list-files` are the check.

   The file list will not match the directory exactly. Expect two extra artifacts: the marker itself is uploaded before being deleted locally, and the completion file is uploaded after the fact. Only the in-progress file is excluded. Count those as expected rather than as a defect.

5. **Confirm the local state files.** A completed upload leaves a completion marker in the directory naming the dataset it went to. That file is the agent's memory, and it is why the next run does not upload the same data again.

6. **Run again and confirm nothing is re-uploaded.** This proves idempotency, and it is what makes a continuously running agent safe. A second dataset appearing here is a defect to fix now, not after the agent is running every thirty seconds.

7. **Test the interrupted case.** Interrupt a run mid-upload — the marker survives, since it is deleted only on success — and confirm the next run resumes into the same dataset rather than creating a second one (rule 5). Staging the case by hand needs **both** the marker and an in-progress file naming a dataset that really exists: discovery is driven by the marker alone, so an in-progress file on its own is never seen, and a fabricated dataset id raises rather than resuming.

Record each check and what it showed in `SPEC.md`. If the round trip fails, fix it here; every later phase assumes it works.

## Phase 4 — The deletion decision

Only now, and only if Phase 1 said yes.

Deleting uploaded files removes the local copy of the user's data. On a robot, that local copy is frequently the only copy, and the agent deletes after **its** notion of success. Enabling it before a proven round trip is how a fleet loses a day of recordings.

So: turn it on only after Phase 3 passed, only with the user's explicit word — including under `--yolo` — and verify it separately.

1. Stage a second scratch recording, using data the user can afford to lose. Say that requirement out loud rather than assuming the last directory qualified.
2. Enable the setting and run once.
3. Confirm the dataset in Roboto is complete **first**, then confirm the local files are gone. In that order; the reverse tells you nothing you want to learn that way.
4. If empty-directory cleanup is also enabled, confirm the directory was removed, and understand the narrow condition under which it is (rule 4).

Then state plainly in the handoff that this machine deletes local data after upload, and what the user should check if they ever suspect it deleted something that did not arrive.

## Phase 5 — Make it unattended

Setup that only works while someone is logged in is not automation. Two forms, and the choice follows Phase 1's cadence axis:

- **Triggered by the recording process** — whatever ends a recording runs the agent once. Simplest, and the closest coupling between "the data is complete" and "upload it".
- **Continuously running** — the agent's own loop, under a service manager that restarts it on failure and starts it at boot. Its scan period is fixed by the module, so any different cadence has to come from the service manager scheduling single runs instead.

Whichever form, the service unit or scheduler entry must carry the credential the agent needs, the working directory, the user it runs as, and a restart policy. Deliver it as a file in the directory from Phase 2. The concurrency lock means overlapping runs are harmless — the second one exits without doing anything — so a scheduler that fires while a long upload is in flight is not a problem (rule 8).

**Verify it as installed**: start the service, stage one more scratch recording, and confirm it uploads without you running anything. Then reboot the machine if the user permits, and confirm it comes back on its own. An agent that does not survive a reboot is a manual process with extra steps.

If you cannot install or start the service — no permission, no service manager, not the right machine — say exactly that, and deliver the unit file with the command that would install it.

## Phase 6 — Hand off

1. **What is configured, and where** — the machine, both config files, the service unit, and the path to the delivered directory.
2. **What was verified** — every check from Phases 3 through 5, including whether the reboot test ran.
3. **Deletion status**, stated explicitly whether it is on or off. If on, say so in its own line; this is the fact the user must not learn later.
4. **Credentials** — how the agent gets them, and what will break the setup: an expiring token, a rotated key, a credential that lives only in an interactive shell profile.
5. **What is not covered** — directories outside the search paths, recordings that never get a marker, the rest of the fleet.
6. **The runbook**, in `SPEC.md` and in the report: how to check whether it is running, where the logs go, how to force a re-upload (two steps — delete the completion file *and* restore the marker, since a successful upload deletes the marker and without it the directory is no longer discovered at all), and what an orphaned lock looks like when it silently stops everything (rule 8).

Then point at what happens next, unrun: uploaded files are not ingested files. Getting topics out of them is an ingestion action on upload, which is `create-roboto-trigger` plus whichever ingestion action fits the format — `create-roboto-ingestion-action` if the format is not one Roboto already supports.
