# create-roboto-trigger

Teaches a coding agent to create a [Roboto](https://www.roboto.ai) trigger that runs an existing action on a platform event (a file ingested, a session ingested, an invocation failed) or on a schedule, and to verify it before it goes live. The agent checks the trigger API against the latest SDK on PyPI and the [Roboto docs](https://www.roboto.ai/docs/learn/actions).

## Install

With the [skills CLI](https://skills.sh), which detects your agent and installs into its skills directory for the current project:

```bash
npx skills add roboto-ai/agent-skills --skill create-roboto-trigger
```

Add `-g` to install for every project on the machine instead.

Or manually: keep this `create-roboto-trigger` folder anywhere your coding agent can read, then tell the agent to follow `create-roboto-trigger/SKILL.md`.

If your agent has a skills directory, move the folder there and the skill becomes available by name. For Claude Code that directory is `~/.claude/skills/` for every project, or `<repo>/.claude/skills/` for a single repository:

```bash
mkdir -p ~/.claude/skills && mv create-roboto-trigger ~/.claude/skills/
```

## Requirements

Your agent must be able to run shell commands, read and write files, and hold a back-and-forth with you, since the first phase is an interview and every write to your organization waits for your yes. Fetching web pages helps; `curl` does the same.

Your machine needs the `roboto` CLI (0.56.0 or newer; 0.61.0 for `session.ingested` triggers and 0.63.0 for `session_event.created`) on `PATH` and Roboto credentials: a personal access token in `~/.roboto/config.json`, or the same token in the `ROBOTO_API_KEY` environment variable. It needs network access to `www.roboto.ai`, `pypi.org`, `files.pythonhosted.org`, `raw.githubusercontent.com`, and `api.github.com`. [uv](https://docs.astral.sh/uv/) is recommended; without it, the skill builds one virtual environment with `pip`, which needs Python 3.10 or newer. Docker is not needed. The skill runs on macOS and Linux; Windows is untested.

The action the trigger runs must already exist in Roboto. The skill checks the CLI version, your credentials, the latest SDK release, the action and its parameters, and the triggers your org already has before asking you anything.

## Usage

In Claude Code, invoke the skill as a slash command:

```
/create-roboto-trigger Run summarize-mcap on every MCAP file once it is ingested, only for datasets tagged production
/create-roboto-trigger Run session-report on each session once all its files are ingested
/create-roboto-trigger Run fleet-weekly every Monday at 06:00 UTC on the last week's sessions --yolo
```

In an agent without slash commands, point it at `create-roboto-trigger/SKILL.md` and give it the same description.

## What it does

1. Checks the CLI, credentials, latest SDK release, target action, and existing triggers before spending any of your time on questions.
2. Decomposes the description into requirements written as "given this event, the trigger fires or does not fire", and resolves the ambiguities (which event, which grain, which file patterns, which condition) by interviewing you or, under `--yolo`, by judgment.
3. Writes the trigger as a directory you can commit: a `trigger.py` that creates the trigger or updates it in place, and a `SPEC.md` that records the requirements and the reasoning.
4. Checks the trigger without writing anything: the SDK's validator, the condition fields and placeholders, the file patterns against real paths, the inputs a query would select, the action's parameters, and the expected firing rate.
5. Creates the trigger pinned to one test subject, dry-runs it against real data, and, where it can produce the event, reads the dispatch and the invocation it started, for data that should fire it and data that should not.
6. Reviews the script and spec against the latest SDK and the saved trigger.
7. Hands off the go-live command without running it.

## `--yolo`

Skips the interview and lets the model resolve every ambiguity, favoring choices that keep the trigger narrow: the most specific file pattern the description supports, `file.ingested` for actions that read topic data, and a condition whenever the description names a scope. The preflight, the offline checks, the verification, and the review (steps 1, 4, 5, and 6 above) all still run, and every judgment call lands in `SPEC.md` marked as a default. `--yolo` never writes to your organization: creating the test trigger, uploading test files, and putting the trigger live each still wait for your yes.

## Verification

A dry run of a disabled trigger stops at its enabled check, so the skill verifies an enabled trigger whose condition is pinned to one test subject: a scratch dataset, or a session, invocation or event you name. Going live replaces the pinned condition with the real one.

## Layout

| Path | Purpose |
|---|---|
| `SKILL.md` | The procedure the agent follows |
| `references/trigger-api.md` | Platform events, `once_per`, target fields, what the action receives, SDK calls, CLI flags, dry-run gates, and documentation links |
| `references/authoring-rules.md` | 28 rules, each stated as the failure it prevents, covering the script, firing source, inputs, conditions, invocation, verification, and documentation |
| `references/script-template.md` | The `trigger.py` skeleton and its flags |
| `references/spec-template.md` | The `SPEC.md` structure written into the trigger directory |
| `LICENSE` | MPL-2.0 license text |

The references carry one stamp, the `metadata` block in `SKILL.md`, naming the SDK release and date they were last checked against. The API map and the script template were checked against that release from PyPI and the `--help` output of its CLI, and the rules against the live docs and the SDK CHANGELOG on that date. They tell the agent what to look up; the live documentation and the latest SDK are the authority.

## Staying current

Nothing in this skill pins an SDK version. Signature and flag checks resolve the newest `roboto` release from PyPI on each run. `trigger.py` does so when run with `uv run --upgrade-package roboto`, as the offline check runs it; a plain `uv run trigger.py` reuses the release uv resolved for it earlier. The preflight compares the stamp in `SKILL.md` with the latest release, so the agent knows how far the SDK has moved since the references were checked. Updating the references means re-running the checks their first paragraphs describe and changing that one stamp.
