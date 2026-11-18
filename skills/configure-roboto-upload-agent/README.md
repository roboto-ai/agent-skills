# configure-roboto-upload-agent

Teaches a coding agent to configure the [Roboto](https://www.roboto.ai) upload agent (`roboto-agent`) on a robot, test rig, or upload station, so recordings reach Roboto without anyone running a command, and to prove one upload round trip in Roboto before anything is set to delete the local copy. The agent checks the agent's config models and flags against the latest SDK on PyPI, and devices and credentials against the Roboto docs (www.roboto.ai/docs).

## Install

With the [skills CLI](https://skills.sh), which detects your agent and installs into its skills directory for the current project:

```bash
npx skills add roboto-ai/agent-skills --skill configure-roboto-upload-agent
```

Add `-g` to install for every project on the machine instead.

Or manually: keep this `configure-roboto-upload-agent` folder anywhere your coding agent can read, then tell the agent to follow `configure-roboto-upload-agent/SKILL.md`.

If your agent has a skills directory, move the folder there and the skill becomes available by name. For Claude Code that directory is `~/.claude/skills/` for every project, or `<repo>/.claude/skills/` for a single repository:

```bash
mkdir -p ~/.claude/skills && mv configure-roboto-upload-agent ~/.claude/skills/
```

## Requirements

Your agent must be able to run shell commands, read and write files, and hold a back-and-forth with you, since the first phase is an interview and deleting uploaded files is never decided without you. Fetching web pages is optional; `curl` does the same. The skill needs no plugins, MCP servers, or sub-agents.

Run it on the machine that will upload, as the user the agent will run as; from anywhere else, the skill gives you the commands to run there. That machine needs the agent, either the `roboto-agent` binary (from the Linux `.deb` or a release file) or the `roboto` Python package (`python -m roboto.upload_agent`), and Roboto credentials: a device token, which the skill recommends because it attributes uploads to the device, or a personal access token in `~/.roboto/config.json` or the `ROBOTO_API_KEY` environment variable. Registering a device needs the `roboto` CLI and your own personal access token. Installing a service needs the privileges your service manager requires.

Lookups need network access to `www.roboto.ai`, `pypi.org`, `files.pythonhosted.org`, `raw.githubusercontent.com`, and `api.github.com`. [uv](https://docs.astral.sh/uv/) is recommended for checking config fields against the latest SDK; without it, the skill builds one virtual environment with `pip`, which needs Python 3.10 or newer. The skill runs on macOS and Linux; Windows is untested.

The skill checks the agent, the CLI, your credentials, and any existing agent configuration before asking you anything, and stops with what to fix if something is missing.

## Usage

In Claude Code, invoke the skill as a slash command:

```
/configure-roboto-upload-agent Our test rig writes one directory per run under /data/runs; upload each run when it finishes and tag it with the rig's hostname
/configure-roboto-upload-agent Set up the lab upload station: bags land in /mnt/incoming/<robot>/<date>/
```

In an agent without slash commands, point it at `configure-roboto-upload-agent/SKILL.md` and give it the same description.

## What it does

1. Checks the agent's form and version, the CLI, the credentials and the identity they carry, any existing configuration, and the service manager, on the uploading machine.
2. Maps the recording layout on disk and interviews you on what it cannot settle: the credential, search paths, dataset granularity, how a recording is marked finished, dataset properties, org, cadence, and deletion.
3. Registers the device for a device credential when you agree, writes the agent config and the per-directory marker template, and checks that each parses with the fields you meant.
4. Verifies one round trip on a scratch recording: the dataset in Roboto carries the right files, properties, device, and collections; a second run uploads nothing; and a staged interrupted upload resumes into the same dataset.
5. Turns on delete-after-upload only if you asked for it, on your word, and verifies it on a second scratch recording.
6. Installs the agent under a service manager or hooks it to the recorder, and verifies that it uploads without a command, across a reboot if you permit one.
7. Hands off a report and a runbook: the deletion status, token expiry and renewal, how to force a re-upload, what the lock message means, and what ingests the uploaded files next.

## `--yolo`

Skips the interview and lets the model resolve every ambiguity except deletion, favoring a device credential, the narrowest search paths, one dataset per recording, and a continuously running service. The preflight, the round-trip verification, and the installed-service check (steps 1, 4, and 6 above) all still run, and every judgment call lands in `SPEC.md` with its rationale and is marked as a default in the final report. It never writes to your organization or the machine without your yes, and it never turns on deletion.

## Deliverables

A directory you can commit: the agent config (`upload_agent.json`), the marker template, the service unit, and `SPEC.md` with the decisions, the credential plan, the verification results, the agent and SDK versions checked, and the runbook. Configure and verify one machine first; the directory then copies to the rest of the fleet.

## Layout

| Path | Purpose |
|---|---|
| `SKILL.md` | The procedure the agent follows |
| `references/agent-api.md` | The agent's forms and flags, both config files, state files, one pass step by step, credentials, what happens after upload, and a systemd template |
| `references/authoring-rules.md` | Numbered rules for the failures that keep data from reaching Roboto or delete it |
| `LICENSE` | MPL-2.0 license text |

The references carry one stamp, the `metadata` block in `SKILL.md`, naming the SDK release and date they were last checked against. They were checked against the `roboto.upload_agent` source and `--help` output of that release from PyPI, its GitHub release files, and the devices page of the Roboto docs on that date. They tell the agent what to look up; the live documentation and the latest SDK are the authority.

## Staying current

Nothing in this skill pins an SDK version. Config field and flag checks resolve the newest `roboto` release from PyPI on each run, and the preflight compares the stamp in `SKILL.md` with the latest release, so the agent knows how far the SDK has moved since the references were checked. The version of the agent on the uploading machine is recorded separately, because it is the code that runs. Updating the references means re-running the checks their first paragraphs describe and changing that one stamp.
