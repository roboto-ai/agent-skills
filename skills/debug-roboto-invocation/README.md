# debug-roboto-invocation

Diagnoses a [Roboto Action](https://docs.roboto.ai/learn/actions.html) invocation that failed, hung, or produced the wrong result — and proves the fix by re-running it against the same input.

## Install

With the [skills CLI](https://skills.sh), which detects your agent and installs into the right place:

```bash
npx skills add roboto-ai/agent-skills --skill debug-roboto-invocation
```

Or manually: keep this `debug-roboto-invocation` folder anywhere your coding agent can read, then tell the agent to follow `debug-roboto-invocation/SKILL.md`.

If your agent has a skills directory, move the folder there and the skill becomes available by name. For Claude Code that directory is `~/.claude/skills/` for every project, or `<repo>/.claude/skills/` for a single repository:

```bash
mv debug-roboto-invocation ~/.claude/skills/
```

Claude Code takes the command name from the directory rather than the frontmatter, so a folder named `debug-roboto-invocation` gives you `/debug-roboto-invocation`.

## Requirements

Your agent must be able to run shell commands and read files. It should be able to ask you a question, since some causes turn out to be decisions rather than defects. Fetching web pages is optional here — the authoritative sources for the invocation vocabulary are the installed SDK and the CLI's own `--help`, both local.

Your machine needs the `roboto` CLI on `PATH` and Roboto credentials — either a personal access token in `~/.roboto/config.json` or `ROBOTO_API_KEY` in the environment.

Docker and the action's source are needed only if the diagnosis calls for reproducing the failure locally. Without them the skill still runs; it delivers a diagnosis with evidence instead of a patch, and says so.

## Usage

In Claude Code, invoke the skill as a slash command:

```
/debug-roboto-invocation <invocation id, or what went wrong> [--yolo]
```

```
/debug-roboto-invocation iv_01h2x3y4z5

/debug-roboto-invocation my ingestion trigger fired but the topics never showed up

/debug-roboto-invocation the action says it completed but the output dataset is empty
```

On an agent without slash commands, point it at `debug-roboto-invocation/SKILL.md` and give it the same description.

## What it does

1. Finds the invocation, and establishes whether it has actually reached a verdict yet.
2. Reads the invocation's **status history** before anything else — every transition, with the timestamp and the detail message the platform recorded for it.
3. Reads the invocation's configuration, since a missing parameter, an input selection that resolved to nothing, or a timeout sized below the work are all diagnosable before a log is opened.
4. Reads the logs last, end first, with the localization already in hand — and reads *all* of them: the logs cover every container in the invocation, so a failure before the action ever started is explained in the setup container's section rather than by their absence.
5. Localizes the fault by where the invocation stopped and what exit code it reported, using the triage tree in `references/triage.md`.
6. Reproduces the failure locally, with the narrowest input that still fails, when the action's source is available.
7. Fixes the cause — in the action, in the invocation, in the data, or in an expectation — asking you when the cause is a decision rather than a defect.
8. **Proves the fix** by redeploying if needed and re-invoking against the same input the original invocation used, then reports both invocation ids side by side.

## Why it reads the status history first

An invocation records every status it passed through, and each transition can carry a detail message explaining it. Where an invocation stopped localizes the fault before a single log line is read: failing while inputs are being prepared points somewhere entirely different from failing while the action's own code is running, or while its outputs are being uploaded.

Opening with the logs and pattern-matching on a traceback skips the cheapest evidence available — and risks reading a traceback from a phase that was never the problem.

## Three rules it will not break

- **It will not diagnose an invocation that is still running.** It tells you what the invocation is currently doing instead.
- **It will not report an unreproduced hypothesis as a cause.** It says which one you have.
- **It will not report an unverified fix as a fix.** If it cannot re-run — no deploy permission, no access to the original input, an action owned by someone else — it says exactly what is unproven and the command that would settle it.

## The misdiagnosis it is built to prevent

The action runtime distinguishes "the action broke" from "the action worked correctly and the input was bad" — they are different exit codes with different fixes. The second one is routinely read as the first, and the resulting "fix" makes an action accept data it had correctly rejected. The symptom disappears and the bad data propagates.

`references/triage.md` collects that antipattern and six others, each of which produces a confident, incorrect verdict.

## Staying current with the SDK

Every SDK call, CLI flag, enum member, and exit code must be confirmed against a live source in the same session; the agent's memory and this skill's bundled reference do not count. A precedence ladder orders the sources: the installed SDK, then the CLI's own `--help`, then `docs.roboto.ai`. The bundled `references/invocation-api.md` sits at the bottom by design — it exists to tell the agent where the evidence lives, not to be cited.

The action's own source is a further source, and the skill treats it precisely: authority on what the action *intended* to do, and no authority at all on what the invocation *did*.
