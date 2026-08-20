# create-roboto-trigger

Creates a verified [Roboto Trigger](https://docs.roboto.ai/learn/actions.html) that invokes an existing action automatically — when data arrives, when ingestion finishes, when metadata changes, or on a schedule.

## Install

With the [skills CLI](https://skills.sh), which detects your agent and installs into the right place:

```bash
npx skills add roboto-ai/agent-skills --skill create-roboto-trigger
```

Or manually: keep this `create-roboto-trigger` folder anywhere your coding agent can read, then tell the agent to follow `create-roboto-trigger/SKILL.md`.

If your agent has a skills directory, move the folder there and the skill becomes available by name. For Claude Code that directory is `~/.claude/skills/` for every project, or `<repo>/.claude/skills/` for a single repository:

```bash
mv create-roboto-trigger ~/.claude/skills/
```

Claude Code takes the command name from the directory rather than the frontmatter, so a folder named `create-roboto-trigger` gives you `/create-roboto-trigger`.

## Requirements

Your agent must be able to run shell commands, read and write files, and hold a back-and-forth with you, since the first phase is an interview. Fetching web pages is helpful but not critical here: the trigger surface is covered by the installed SDK and the CLI's own `--help`, both of which are local. The skill needs no plugins, external tool servers (such as MCP servers), or sub-agents.

Your machine needs the `roboto` CLI on `PATH`, a Python environment with the `roboto` SDK installed, and Roboto credentials — either a personal access token in `~/.roboto/config.json` or `ROBOTO_API_KEY` in the environment. Docker is not required; nothing here builds an image.

**The action must already exist and be deployed.** A trigger names its action, so there is nothing to create or verify until the action is there. If the work you want automated has no action yet, run [`create-roboto-action`](../create-roboto-action/) first.

The skill checks the CLI, your credentials, the SDK import, and the target action before asking you anything, and stops with what to fix if something is missing.

## Usage

In Claude Code, invoke the skill as a slash command:

```
/create-roboto-trigger <what should run automatically, and when> [--yolo]
```

```
/create-roboto-trigger Run my anomaly-detection action on every .mcap file once it finishes ingesting, but only for datasets tagged production

/create-roboto-trigger Ingest every rosbag as soon as it's uploaded --yolo
```

On an agent without slash commands, point it at `create-roboto-trigger/SKILL.md` and give it the same description.

## What it does

1. Checks the CLI, credentials, the SDK, and that the target action exists and is deployed, before spending any of your time on questions.
2. Decomposes the description into requirements stated as "given this event, the trigger fires or does not fire", separating what it states, what it implies, and what remains ambiguous.
3. Resolves the ambiguities by interviewing you or, under `--yolo`, by judgment — including the two that decide whether a trigger works at all: which event causes it, and how its input patterns are matched.
4. Measures the blast radius: how much data in your org this trigger would match today, reported before anything goes live.
5. Writes the trigger as a directory you can commit — an idempotent `create_trigger.py`, the server's own record as JSON, and a `SPEC.md` carrying the intent.
6. Creates the trigger **disabled**, then verifies it by producing a real event against a scratch dataset and reading the evaluation record Roboto wrote in response — both a path that should fire and a path that should not.
7. Reviews its own work against the installed SDK, and against the live trigger record, so a server default you did not intend becomes visible.
8. Hands off the enable command without running it.

## Why it creates the trigger disabled

Enabling a trigger changes what happens to your data without further input from you, and it spends real compute. So the skill authors the trigger inert, proves it fires on the data it should and skips the data it should not, and then stops. Turning it on is one command, and it is yours to run — including under `--yolo`.

## How it verifies

Reading a trigger back only proves the create call worked. This skill's gate is Roboto's own evaluation record: it produces the cause event, waits for evaluation to complete, and reads the outcome.

That record is unusually informative. When a trigger skips, it says why — no matching files, condition not met, already run, or disabled — and each reason maps to exactly one thing to change. The skill uses that vocabulary both as its pass/fail gate and as its debugging table, which is why it runs the gate more than once: once for a path that should fire, once for a path that should not.

## Deliverables

```
triggers/<trigger-name>/
├── create_trigger.py       # idempotent: creates, or converges an existing trigger
├── <trigger-name>.json     # the trigger as the server returned it
└── SPEC.md                 # requirements, decisions and why, blast radius, verification
```

`SPEC.md` carries what the org copy cannot: why the cause is the cause, why the globs are that narrow, which server defaults you accepted, and what the verification actually proved. It gives whoever changes the trigger next the reasoning that produced it.

## Staying current with the SDK

Every SDK call, CLI flag, and enum member must be confirmed against a live source in the same session; the agent's memory and this skill's bundled reference do not count. A precedence ladder orders the sources: the installed SDK, then the CLI's own `--help`, then `docs.roboto.ai`. The bundled `references/trigger-api.md` sits at the bottom by design — it exists to run the interview and to tell the agent what to look up, not to be cited.

That ladder puts the installed SDK first, with one caveat the skill states outright: a docstring is prose, not code. Examples inside the SDK are neither executed nor tested, and the trigger module has at least one that references members which do not exist. The skill confirms enum members against the enum itself.
