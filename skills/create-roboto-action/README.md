# create-roboto-action

Generates a deployable Roboto Action from a natural-language description of the job it should do.

## Install

With the [skills CLI](https://skills.sh), which detects your agent and installs into the right place:

```bash
npx skills add roboto-ai/agent-skills --skill create-roboto-action
```

Or manually: keep this `create-roboto-action` folder anywhere your coding agent can read, then tell the agent to follow `create-roboto-action/SKILL.md`.

If your agent has a skills directory, move the folder there and the skill becomes available by name. For Claude Code that directory is `~/.claude/skills/` for every project, or `<repo>/.claude/skills/` for a single repository:

```bash
mv create-roboto-action ~/.claude/skills/
```

Claude Code takes the command name from the directory rather than the frontmatter, so a folder named `create-roboto-action` gives you `/create-roboto-action`.

## Requirements

Your agent must be able to run shell commands, read and write files, and hold a back-and-forth with you, since the first phase is an interview. Fetching web pages is recommended: it is how the skill checks SDK signatures against `docs.roboto.ai` before the project is scaffolded. Without it, the skill asks you to paste documentation pages rather than guess. The skill needs no plugins, external tool servers (such as MCP servers), or sub-agents.

Your machine must have Docker running, since local invocation builds and runs a container; the `roboto` CLI on `PATH`; Roboto credentials, either a personal access token in `~/.roboto/config.json` or `ROBOTO_API_KEY` in the environment; and network access to GitHub, since the scaffolder downloads its project template from there. The skill runs on macOS and Linux; Windows is untested.

The skill checks Docker, the CLI, and your credentials before asking you anything, and stops with what to fix if something is missing. GitHub reachability is the one requirement it does not probe; a network failure there surfaces when the scaffolder runs.

## Usage

In Claude Code, invoke the skill as a slash command:

```
/create-roboto-action <description of what the action should do> [--yolo]
```

```
/create-roboto-action Tag any dataset whose CPU load topic peaks above 90%, and mark the high-load intervals as events

/create-roboto-action Transcode every .mp4 in the dataset to h264 and upload the result --yolo
```

On an agent without slash commands, point it at `create-roboto-action/SKILL.md` and give it the same description.

## What it does

1. Checks Docker, the CLI, and credentials, and records whether you are on macOS or Linux, before spending any of your time on questions.
2. Decomposes the description into a requirements table that separates what it states, what it implies, and what remains ambiguous.
3. Resolves the ambiguities by interviewing you or, under `--yolo`, by judgment. Either way, `SPEC.md` records each decision and its rationale.
4. Scaffolds with `roboto actions init`, which downloads Roboto's project template, so the layout and the shipped `DEVELOPING.md` come from the platform rather than from this skill.
5. Implements `action.json`, `main.py`, tests, dependencies, the project's `README.md`, and a `SPEC.md` that carries the intent behind the code.
6. Verifies with `./scripts/verify.sh` and a `roboto actions invoke-local --dry-run` against a dataset in your Roboto org rather than test fixtures, judging success by the logs, not the exit code alone.
7. Edits the generated code in the five passes of `references/edit-passes.md`: API truth, naming and shape, comments, the verify script, and a final diff review. The passes fix what they find rather than listing it.
8. Hands off the deploy command without running it, since deploying creates or updates a real action in your organization and pushes an image to its registry.

## Staying current with the SDK

Every SDK call must be confirmed against a live source in the same session; the agent's memory and the skill's bundled reference do not count. A precedence ladder orders the sources: the SDK installed in the action's own venv, then the scaffold's generated `DEVELOPING.md`, then `docs.roboto.ai`. The bundled `references/action-api.md` sits at the bottom by design: it exists to run the interview and to tell the agent what to look up, not to be cited. The generated `SPEC.md` records the SDK version consulted, so a later reader knows which version of the SDK's API the action was built against.

## `--yolo`

Skips the interview and lets the model resolve every ambiguity, favoring choices that keep the action reusable and tolerant of missing or unreadable input: parameters rather than hardcoded values, invocation-time input selection rather than runtime queries. The environment checks, the dry-run verification, and the edit passes (steps 1, 6, and 7 above) all still run, and every judgment call lands in `SPEC.md` marked as a default; your review of the decisions moves from the interview, before the build, to reading `SPEC.md` after it.

## Deliverables

Beyond a runnable action, the generated project carries `SPEC.md`: the requirements, the resolved ambiguities and why they went the way they did, the non-goals, the failure behavior, the compute sizing rationale, and what verification proved. It gives whoever changes the action next the reasoning that produced it.

## How the skill drives the Roboto CLI

Three CLI behaviors may show up in the transcript. `roboto actions init` reads its setup answers on stdin, in order: action name, description, input data type as a numbered choice, and whether to initialize a git repository; the skill pipes them rather than typing them. `roboto actions invoke-local` attaches its container to a terminal, so the skill wraps it in a pty using `script`, whose arguments differ between macOS and Linux. And if you belong to more than one Roboto organization, the skill passes `--org` and tells you which one it used.

## Input data for local invocation

When the action reads anything from Roboto, the `invoke-local` dry run needs input data: the skill uses, in order of preference, a dataset you name, one it finds that matches the action's input assumptions, or a scratch one it creates after telling you. It runs the dry run at least three times — the default path, a path with parameters overridden, and one that should fail — and once more for each further path the requirements name.

## Contents

- `SKILL.md` — the skill itself
- `references/action-api.md` — `InvocationContext` and `ActionInput` surface, the `action.json` schema, CLI commands, and documentation links
- `references/authoring-rules.md` — 22 rules covering the runtime contract, input handling, output, packaging, tests, and documentation, each stated as the failure mode it prevents
- `references/edit-passes.md` — the five-pass edit protocol the skill applies to the code it generated, loaded only when that phase begins
- `references/spec-template.md` — the `SPEC.md` structure written into the project
