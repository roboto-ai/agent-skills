# configure-roboto-upload-agent

Configures, verifies, and runs the Roboto upload agent on a robot, test rig, or upload station, so recordings reach Roboto without anyone typing a command.

## Install

With the [skills CLI](https://skills.sh), which detects your agent and installs into the right place:

```bash
npx skills add roboto-ai/agent-skills --skill configure-roboto-upload-agent
```

Or manually: keep this `configure-roboto-upload-agent` folder anywhere your coding agent can read, then tell the agent to follow `configure-roboto-upload-agent/SKILL.md`.

If your agent has a skills directory, move the folder there and the skill becomes available by name. For Claude Code that directory is `~/.claude/skills/` for every project, or `<repo>/.claude/skills/` for a single repository:

```bash
mv configure-roboto-upload-agent ~/.claude/skills/
```

Claude Code takes the command name from the directory rather than the frontmatter, so a folder named `configure-roboto-upload-agent` gives you `/configure-roboto-upload-agent`.

## Requirements

Your agent must be able to run shell commands, read and write files, and ask you questions — one decision in this skill can destroy data and is never resolved by judgment.

**Run it on the uploading machine.** Every command targets the robot, rig, or upload station that will do the uploading, not your laptop. A configuration verified on the wrong host has verified nothing: the search paths do not exist there, the credentials differ, and the service manager may not be the same one. If your agent session is elsewhere, the skill says so and produces the configuration and commands for you to run on the machine.

That machine needs a Python environment with the `roboto` SDK installed, and Roboto credentials available **non-interactively** — a headless machine has nobody to complete a login prompt. Installing a service unit needs whatever privileges your service manager requires.

Docker is not required.

## Usage

In Claude Code, invoke the skill as a slash command:

```
/configure-roboto-upload-agent <what machine should upload what, and when> [--yolo]
```

```
/configure-roboto-upload-agent Our test rig writes a directory per run under /data/runs — those should upload to Roboto automatically and be tagged with the rig's hostname

/configure-roboto-upload-agent Set up the upload station in the lab; it has a few hundred GB of bags in /mnt/incoming
```

On an agent without slash commands, point it at `configure-roboto-upload-agent/SKILL.md` and give it the same description.

## What it does

1. Establishes how the agent is invoked on this machine, how credentials reach it, and whether a configuration is already in place.
2. Maps your actual directory layout before configuring anything — including the question that decides whether this works at all: **how the agent knows a recording is finished.**
3. Interviews you on the axes your layout cannot answer, and writes both config files: the machine's agent config, and the per-directory marker whose presence is what says "this directory is a dataset".
4. **Verifies one complete round trip** with deletion turned off: a scratch recording uploads, the dataset in Roboto carries the right files and the right attribution, the local state file names it, a second run uploads nothing, and an interrupted run resumes into the same dataset rather than creating a second one.
5. Only then revisits the delete-after-upload decision, and verifies it separately.
6. Makes it unattended — a service unit or a hook on whatever ends a recording — and verifies it as installed, including across a reboot if you permit one.
7. Hands off a runbook: how to tell whether it is running, how to force a re-upload, and what a silently stopped agent looks like.

## The decision this skill will not make for you

Deleting uploaded files removes the local copy. On a robot, that is frequently the only copy, and the agent deletes after **its** notion of a successful upload.

So the skill defaults it off, keeps it off through the entire first round trip, and asks you before turning it on — **including under `--yolo`**, which relaxes every other question. When it does verify deletion, it uses a second scratch recording, and it confirms the dataset is complete in Roboto *before* confirming the local files are gone.

## The failure that isn't in any log

A directory that is still being written when the agent scans it gets uploaded partially — and then gets a completion marker, which means the agent will never look at it again. No error, no retry, a dataset that is quietly short a few files.

The reliable fix is for whatever ends a recording to write the marker as its last act, so the marker means "this recording is finished" rather than "this directory exists". The skill treats that as a first-class question in the interview rather than a detail.

## Deliverables

```
upload-agent/
├── upload_agent.json           # the machine's agent config
├── roboto_upload.json          # the per-directory marker template
├── roboto-upload-agent.service # the unit that runs it unattended, if used
└── SPEC.md                     # decisions, verification results, and the runbook
```

Delivered as a directory you can commit, so the second machine is a copy of a proven configuration rather than a re-derivation. Where a fleet is involved, the skill configures and verifies **one** machine end to end first — rolling out is cheap after the round trip is proven and expensive before.

## Staying current with the SDK

This component is thinly covered on `docs.roboto.ai` compared to the rest of the platform, which raises the authority of the installed module and lowers everything else. The skill's ladder puts `python -m roboto.upload_agent --help` and the module's own config models first, and treats its bundled `references/agent-api.md` as a map rather than a citation. No config field is written from memory: both files are validated on load, and a misspelled field fails at run time rather than being ignored.

One consequence worth knowing up front: the module's log messages refer to a `roboto-agent` command, and whether that command exists depends on how the SDK was installed. The skill establishes which invocation form actually works before writing any service unit or runbook that depends on one.

## After it ships

The agent uploads; it does not ingest. Files that have arrived are not yet topics. Automating that step is a trigger on file upload invoking an ingestion action — [`create-roboto-trigger`](../create-roboto-trigger/) for the trigger, and [`create-roboto-ingestion-action`](../create-roboto-ingestion-action/) if your format is not one Roboto already supports.
