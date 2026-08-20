# create-roboto-ingestion-action

Builds a [Roboto Action](https://docs.roboto.ai/learn/actions.html) that ingests a custom or unsupported log format — turning raw recordings into topics whose data can actually be read back and plotted.

## Install

With the [skills CLI](https://skills.sh), which detects your agent and installs into the right place:

```bash
npx skills add roboto-ai/agent-skills --skill create-roboto-ingestion-action
```

**Install [`create-roboto-action`](../create-roboto-action/) alongside it.** An ingestion action is an ordinary action, so this skill delegates scaffolding, local verification, the edit passes, and deployment to that one rather than repeating them, and supplies only what is specific to ingestion. Installing both is one command:

```bash
npx skills add roboto-ai/agent-skills
```

Without it, this skill still works — the delegated phases are ordinary action authoring — but the agent carries them out from the platform's scaffolder instead of from a checklist.

If your agent has a skills directory, move the folder there and the skill becomes available by name. For Claude Code that directory is `~/.claude/skills/` for every project, or `<repo>/.claude/skills/` for a single repository:

```bash
mv create-roboto-ingestion-action ~/.claude/skills/
```

Claude Code takes the command name from the directory rather than the frontmatter, so a folder named `create-roboto-ingestion-action` gives you `/create-roboto-ingestion-action`.

## Requirements

Your agent must be able to run shell commands, read and write files, and hold a back-and-forth with you, since the first phase is an interview about your data. Fetching web pages is recommended, for checking SDK signatures before the project exists.

Your machine needs Docker running, the `roboto` CLI on `PATH`, Roboto credentials, and network access to GitHub for the project scaffolder.

**You also need a real sample file of the format.** Not a specification, not a description — a file. Every phase reads it, and the verification gate compares the ingested values against it. An ingestion action written from a format document and never run against real bytes cannot be verified, and format documents are wrong more often than they are right.

## Usage

In Claude Code, invoke the skill as a slash command:

```
/create-roboto-ingestion-action <the format, and a path to a sample file> [--yolo]
```

```
/create-roboto-ingestion-action Ingest our robot's .tlm telemetry logs — sample at ./samples/flight_014.tlm

/create-roboto-ingestion-action These CSV exports from our test rig should become topics, one per sensor group. Sample: ./rig_export.csv
```

On an agent without slash commands, point it at `create-roboto-ingestion-action/SKILL.md` and give it the same description.

## Check first: is your format already supported?

Roboto ships ingestion actions for several common robotics formats, listed on the [formats page](https://docs.roboto.ai/learn/formats.html) and invocable from the action hub. If yours is there, you do not need this skill. If it is there and it failed, that is [`debug-roboto-invocation`](../debug-roboto-invocation/).

## What it does

1. Checks the environment, that your sample file is readable, and that the format is not already supported.
2. **Inventories the file** — what streams it contains, what fields each carries, their types, and how many records. Shows you the table. This is often the first time anyone has seen the format laid out this way.
3. Interviews you on what the file cannot answer: units above all, plus topic naming, and what should happen to a corrupt file or an unparseable stream.
4. Chooses the ingestion path — a DataFrame per topic, or the lower-level topic/message-path/representation calls for images, video, and large binaries.
5. Builds the action, keeping the parser in plain functions that are unit-testable against a checked-in fixture with no network.
6. **Verifies by reading the data back**, not by watching the action exit cleanly.
7. Reports what ingested, what did not, and every place your sample file contradicted the format documentation.

## The failure this skill exists to prevent

Topics and message paths are metadata. Representations are the data.

An action that creates topics and adds message paths — and stops there — produces topics that appear in every listing, carry a full schema, and look completely ingested. They return nothing to any data-access call. Nothing errors. The action exits zero.

So the gate is not "do the topics exist". It is: **fetch each topic's data as a dataframe and confirm it returns rows**, with the right columns, with a time index that spans the source file's range, and with three values spot-checked against the source read independently. Then ingest the same file twice and confirm nothing doubled.

The high-level DataFrame path registers the representation for you, which is why the skill prefers it. The low-level path does not, which is why the skill's first authoring rule is about it.

## Which API it builds on

The stable one: `File.add_topic` for tabular data, and `Topic.create` with message paths and representations for everything else.

The SDK also carries the beginnings of a declarative ingestion API under its experimental namespace — currently two model classes, with no call yet that submits them. It is worth watching rather than building on, and it is not what this skill teaches, because the SDK states that experimental APIs may change in shape, behavior, or semantics before they stabilize and are meant for evaluation rather than long-lived production code — and an ingestion action is exactly the sort of thing a user runs for years. The skill points at it in the final report as something to revisit once it graduates.

## Deliverables

A deployable ingestion action, plus a `SPEC.md` carrying the format inventory, the resolved decisions, what was deliberately not ingested, and what the verification proved. That inventory table is frequently the most valuable artifact produced — for many custom formats it is the only written description that exists.

## After it ships

An ingestion action earns its keep when every upload is ingested without anyone asking. That is a trigger on file upload, and [`create-roboto-trigger`](../create-roboto-trigger/) builds and verifies one. This skill hands off the command rather than creating it.
