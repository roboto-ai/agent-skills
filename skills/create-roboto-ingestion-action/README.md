# create-roboto-ingestion-action

Teaches a coding agent to build a [Roboto Action](https://www.roboto.ai/docs/learn/actions) that ingests a log format Roboto cannot read yet, so its recordings become topics you can search, plot, and read. The agent checks the [supported formats](https://www.roboto.ai/docs/learn/formats) first, works from a real sample file, looks up every SDK call in the latest release on PyPI and the docs at www.roboto.ai/docs, and verifies the action by reading the ingested data back and comparing it with the sample.

## Install

With the [skills CLI](https://skills.sh), which detects your agent and installs into its skills directory for the current project:

```bash
npx skills add roboto-ai/agent-skills --skill create-roboto-ingestion-action
```

Add `-g` to install for every project on the machine instead.

Or manually: keep this `create-roboto-ingestion-action` folder anywhere your coding agent can read, then tell the agent to follow `create-roboto-ingestion-action/SKILL.md`.

If your agent has a skills directory, move the folder there and the skill becomes available by name. For Claude Code that directory is `~/.claude/skills/` for every project, or `<repo>/.claude/skills/` for a single repository:

```bash
mkdir -p ~/.claude/skills && mv create-roboto-ingestion-action ~/.claude/skills/
```

## Requirements

Your agent must be able to run shell commands, read and write files, and hold a back-and-forth with you, since the first phase is an interview about your data and the verification asks before it writes to your organization. Fetching web pages is optional; the skill uses `curl` when there is no fetch tool.

Your machine needs Docker running, since local invocation builds and runs a container; the `roboto` CLI on `PATH`; and Roboto credentials, either a personal access token in `~/.roboto/config.json`, as described on [Programmatic Access](https://www.roboto.ai/docs/getting-started/programmatic-access), or the same token in the `ROBOTO_API_KEY` environment variable. It needs network access to `www.roboto.ai` for documentation, `pypi.org` and `files.pythonhosted.org` for the latest SDK, `raw.githubusercontent.com` and `api.github.com` for the SDK CHANGELOG and release tags, and GitHub for the action template. [uv](https://docs.astral.sh/uv/) is recommended; without it, the skill needs Python 3.10 or newer with `pip`. The skill runs on macOS and Linux; Windows is untested.

**You also need a real sample file of the format.** Every phase reads it, and the verification compares the ingested values with it. An action written from a format description and never run on real bytes cannot be verified.

The skill checks Docker, the CLI, your credentials, the sample file, and whether Roboto already ingests the format before asking you anything, and stops with what to fix if something is missing.

## Usage

In Claude Code, invoke the skill as a slash command:

```
/create-roboto-ingestion-action Ingest our robot's .tlm telemetry logs; sample at ./samples/flight_014.tlm
/create-roboto-ingestion-action Our arm controller writes binary .jlog files, one joint-state stream and one fault stream. Sample: ./run_0412.jlog
/create-roboto-ingestion-action Each .ep file holds several recorded episodes back to back; see ./ep_batch_07.ep --yolo
```

In an agent without slash commands, point it at `create-roboto-ingestion-action/SKILL.md` and give it the same description.

## What it does

1. Checks Docker, the CLI, credentials, and the sample file, and stops if Roboto's formats page or your org's ingestion rules already cover the format, unless you want a custom action anyway.
2. Inventories the sample: each stream, its fields and types, record counts, and time range.
3. Resolves what the file cannot answer, such as units, topic names, files that hold several runs, and what a corrupt file or a failed stream should do, by interviewing you or, under `--yolo`, by judgment.
4. Chooses how each stream is written: a DataFrame per topic, explicit topics with representations for images and binary payloads, or declared topics for files shared between sessions or recorded in relative time.
5. Scaffolds with `roboto actions init` and implements a parser you can test without a network, the action that writes topics and then marks the file ingested, tests, and a `SPEC.md`.
6. Verifies with the project's checks, the parser against values read independently from the sample, and a local dry run; then, after you approve the write, runs the action on the sample and reads the topics back, checks types, units, values, time range, ingestion status, and sessions, and runs it again to confirm nothing doubles.
7. Edits the code it wrote for API correctness, names, comments, and a final diff review.
8. Reports what was ingested and left out, and where the sample contradicts the format's documentation, and hands you the deploy command and an ingestion rule request without running them.

## `--yolo`

Skips the interview and lets the model resolve every ambiguity, favoring one topic per source stream with the source's names, every field ingested, the DataFrame path where it fits, and bad input reported as a data error. The environment checks, the verification gates, and the edit pass (steps 1, 6, and 7 above) all still run, and every judgment call lands in `SPEC.md` marked as a default. It never writes to your organization: the scratch dataset, the verification run, the deploy, and the ingestion rule each still wait for your yes.

## Deliverables

Beyond a deployable action, the project carries `SPEC.md`: the format inventory, each decision and its reason, which streams and fields were left out, the failure behavior, the compute sizing, and what verification proved. For many custom formats the inventory is the only written description of the format.

## Layout

| Path | Purpose |
|---|---|
| `SKILL.md` | The procedure the agent follows |
| `references/ingestion-api.md` | The three write paths, ingestion status and sessions, the read-back checks, ingestion rules, and exit codes |
| `references/authoring-rules.md` | Numbered rules for ingestion actions, each with the failure it prevents |
| `LICENSE` | MPL-2.0 license text |

The references carry one stamp, the `metadata` block in `SKILL.md`, naming the SDK release and date they were last checked against. The API map was checked against that release from PyPI and the `--help` output of its CLI, and against the live docs site on that date. They tell the agent what to look up; the live documentation and the latest SDK are the authority.

## Staying current

Nothing in this skill pins an SDK version. Signature and flag checks resolve the newest `roboto` release from PyPI on each run, and the preflight compares the stamp in `SKILL.md` with the latest release, so the agent knows how far the SDK has moved since the references were checked. Updating the references means re-running the checks their first paragraphs describe and changing that one stamp.
