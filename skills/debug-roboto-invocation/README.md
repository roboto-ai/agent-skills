# debug-roboto-invocation

Teaches a coding agent to diagnose a [Roboto](https://www.roboto.ai) action invocation that failed, hung, or did the wrong thing, find the cause, and prove the fix by re-running it on the same inputs. The agent works from the invocation's status history, record, and logs, checks the SDK and CLI against the latest release on PyPI, and looks up behavior in the [Roboto docs](https://www.roboto.ai/docs).

## Install

With the [skills CLI](https://skills.sh), which detects your agent and installs into its skills directory for the current project:

```bash
npx skills add roboto-ai/agent-skills --skill debug-roboto-invocation
```

Add `-g` to install for every project on the machine instead.

Or manually: keep this `debug-roboto-invocation` folder anywhere your coding agent can read, then tell the agent to follow `debug-roboto-invocation/SKILL.md`.

If your agent has a skills directory, move the folder there and the skill becomes available by name. For Claude Code that directory is `~/.claude/skills/` for every project, or `<repo>/.claude/skills/` for a single repository:

```bash
mkdir -p ~/.claude/skills && mv debug-roboto-invocation ~/.claude/skills/
```

## Requirements

Your agent must be able to run shell commands, read and write files, and ask you questions, since some causes are decisions rather than defects. Fetching web pages is optional; the skill uses `curl` for docs lookups when there is no fetch tool.

Your machine needs the `roboto` CLI on `PATH` and Roboto credentials: a personal access token in `~/.roboto/config.json`, as described on [Programmatic Access](https://www.roboto.ai/docs/getting-started/programmatic-access), or the same token in the `ROBOTO_API_KEY` environment variable. Lookups need network access to `www.roboto.ai`, `pypi.org`, `files.pythonhosted.org`, `raw.githubusercontent.com`, and `api.github.com`. [uv](https://docs.astral.sh/uv/) is recommended; without it, the skill needs Python 3.10 or newer to build a virtual environment. Docker is needed only to reproduce a container action locally. The skill runs on macOS and Linux; Windows is untested.

The skill checks the CLI version, uv, your credentials, and the latest SDK release before reading any evidence, and stops with what to fix if something is missing.

## Usage

In Claude Code, invoke the skill as a slash command:

```
/debug-roboto-invocation iv_abc123
/debug-roboto-invocation my ingestion trigger fired but the topics never showed up
/debug-roboto-invocation the action says Completed but the output dataset is empty --yolo
/debug-roboto-invocation session se_abc123 has been ingesting for an hour
```

In an agent without slash commands, point it at `debug-roboto-invocation/SKILL.md` and describe the failure the same way.

## What it does

1. Checks the CLI, uv, credentials, and the latest SDK release, and lists your organizations.
2. Finds the invocation from an ID, an action, a trigger's dispatch history, or a session's ingestion status, then reads its status history, its record (including the inputs it resolved to), and its logs, in that order.
3. Localizes the fault by where the invocation stopped and what the platform recorded about it, using `references/triage.md`, and reproduces it locally or with a one-variable hosted re-run when the evidence is not direct.
4. Fixes the cause where it lies: the action, the invocation's request, the data, or the expectation, asking you when the fix is a decision.
5. Proves the fix by re-running on the same inputs after you approve the redeploy and the re-run, and compares the new invocation with the original.
6. Reports the cause, the evidence, the decisions, and both invocation IDs, and gives every command that writes to your organization without running it.

## `--yolo`

Skips the questions in the fix phase and lets the model make those decisions, choosing the option that fails visibly rather than silently. The preflight, the evidence gathering, and the re-run that proves the fix (steps 1, 2, and 5 above) all still run, and every judgment call is recorded in the report. It never redeploys, re-invokes, or cancels anything without your yes.

## Layout

| Path | Purpose |
|---|---|
| `SKILL.md` | The procedure the agent follows |
| `references/invocation-api.md` | CLI commands, record fields, status and exit-code vocabulary, ways to find an invocation, and the re-run command and script |
| `references/triage.md` | Evidence-to-cause tables for setup failures, action failures, completed-but-wrong runs, and hung runs, plus eight wrong turns to avoid |
| `LICENSE` | MPL-2.0 license text |

The references carry one stamp, the `metadata` block in `SKILL.md`, naming the SDK release and date they were last checked against. Each file's first paragraph says how. They tell the agent what to look up; the live documentation and the latest SDK are the authority.

## Staying current

Nothing in this skill pins an SDK version. Signature and flag checks resolve the newest `roboto` release from PyPI on each run, and the preflight compares the stamp in `SKILL.md` with the latest release, so the agent knows how far the SDK has moved since the references were checked. Updating the references means re-running the checks their first paragraphs describe and changing that one stamp.
