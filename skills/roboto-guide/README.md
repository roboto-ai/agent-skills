# roboto-guide

Teaches a coding agent to answer questions about [Roboto](https://www.roboto.ai) and to write `roboto` CLI commands and ad hoc Python SDK scripts that work against the latest release. The agent looks things up on [docs.roboto.ai](https://docs.roboto.ai) and in the latest SDK on PyPI.

## Install

With the [skills CLI](https://skills.sh), which detects your agent and installs into its skills directory for the current project:

```bash
npx skills add roboto-ai/agent-skills --skill roboto-guide
```

Add `-g` to install for every project on the machine instead.

Or manually: keep this `roboto-guide` folder anywhere your coding agent can read, then tell the agent to follow `roboto-guide/SKILL.md`.

If your agent has a skills directory, move the folder there and the skill becomes available by name. For Claude Code that directory is `~/.claude/skills/` for every project, or `<repo>/.claude/skills/` for a single repository:

```bash
mkdir -p ~/.claude/skills && mv roboto-guide ~/.claude/skills/
```

## Requirements

Your agent must be able to run shell commands and read files. The bundled docs script runs on Python 3.9 or newer, on macOS, Linux, and Windows; the skill starts each session by running its `env` subcommand to learn the platform, shell, Python, and tools available, and `references/platforms.md` translates its commands for Windows shells. Lookups need network access: `docs.roboto.ai` for documentation, `pypi.org` and `files.pythonhosted.org` for the latest SDK, and `raw.githubusercontent.com` and `api.github.com` for the SDK README and release tags.

[uv](https://docs.astral.sh/uv/) is recommended. The skill uses `uv run` to check SDK signatures against the latest release and to run generated scripts in an isolated environment rather than your own. The SDK needs Python 3.11 or newer; `uv` provides an interpreter if your system Python is older. Without `uv`, the skill builds one virtual environment with `pip` under `~/.cache/roboto-guide` and runs everything from it, which needs Python 3.11 or newer on the machine.

The `roboto` CLI on `PATH` and Roboto credentials are needed only when the agent runs commands or scripts against your organization. Credentials are a personal access token in `~/.roboto/config.json`, as described on [Programmatic Access](https://docs.roboto.ai/getting-started/programmatic-access.html), or the same token in the `ROBOTO_API_KEY` environment variable, which the SDK checks before the file.

The skill needs no plugins, MCP servers, or sub-agents. If the [Roboto MCP server](https://docs.roboto.ai/learn/ai/mcp-server.html) is connected, the skill prefers it for questions about your own data.

## Usage

Ask a question or describe a task that involves Roboto. The skill triggers on mentions of Roboto, RoboQL, the `roboto` CLI, `import roboto`, or Roboto's entities (datasets, files, topics, message paths, sessions, events, actions, invocations, triggers, collections, devices, agents). In Claude Code you can also invoke it directly:

```
/roboto-guide How do I get started with Roboto on a Mac?
/roboto-guide What is the difference between a topic and a message path?
/roboto-guide Write a script that lists every dataset tagged px4 from the last 30 days with its file count
/roboto-guide How do I invoke ros_ingestion on dataset ds_abc123 and tail its logs?
```

In an agent without slash commands, point it at `roboto-guide/SKILL.md` and ask the same question.

## What it does

1. Classifies the request: get started, explain a concept, produce a CLI command, write a script, or answer about your data.
2. Picks the documentation page that answers the question from a bundled map of docs.roboto.ai, then fetches it with `scripts/roboto_docs.py`, which resolves page and symbol names to URLs through the site's index and prints pages as text. The same script lists REST API endpoints with their parameters and schemas, which is how questions about visualizer layouts, workspaces, saved views, and AI Chat threads get answered from data rather than from UI walkthroughs.
3. Verifies every SDK call against the latest release on PyPI with `uv run` before handing over a script, and checks CLI flags against your installed `roboto --help`.
4. Tells you when your installed CLI or SDK is behind the latest release, and where to find the upgrade instructions.
5. Writes scripts with an inline dependency header so `uv run script.py` resolves the latest SDK, keeps them read-only unless you ask for a write, and runs read-only scripts when it can.
6. Indexes a dataset's files, topics, and message paths into a local JSON file before any analytics work, then fetches only the topic data a question needs and reuses the index for follow-ups.
7. Refuses to run destructive commands (any `delete`, `delete-files`, `delete-image`, `delete-repository`, `cancel`, `cancel-all`, `remove-user`, or `remove-role` subcommand) until you confirm the exact command, and never prints a token or the contents of `~/.roboto/config.json`.

## Layout

| Path | Purpose |
|---|---|
| `SKILL.md` | The procedure the agent follows |
| `scripts/roboto_docs.py` | `search` and `fetch` for docs.roboto.ai, `restapi` for the REST API reference, `versions` to compare the reference stamp with the latest release, and `env` to describe the machine; Python 3.9+, standard library only |
| `references/platforms.md` | Command translations and file locations for macOS, Linux, and Windows |
| `references/getting-started.md` | Onboarding in order: account, token, CLI and SDK install, first upload and ingestion |
| `references/docs-map.md` | Which page answers which question, plus the SDK module index |
| `references/cli-cookbook.md` | CLI conventions and worked commands |
| `references/sdk-cookbook.md` | Script template, running with or without `uv`, authentication, and worked SDK patterns including sessions, dataset indexing, and layouts |
| `references/roboql.md` | RoboQL syntax, fields, and examples |
| `LICENSE` | MPL-2.0 license text |

The references carry one stamp, the `metadata` block in `SKILL.md`, naming the SDK release and date they were last checked against. The SDK cookbook was checked against that release from PyPI, the CLI cookbook against the `--help` output of the CLI bundled with it, and the others against the live docs site and the SDK README on that date. They tell the agent what to look up; the live documentation and the latest SDK are the authority.

## Staying current

Nothing in this skill pins an SDK version. The docs script reads the site's inventory at run time (cached for 24 hours; `--refresh` forces a new download), and signature checks resolve the newest `roboto` release from PyPI on each run. `python3 scripts/roboto_docs.py versions` compares the stamp in `SKILL.md` with the latest release on PyPI and GitHub, so the agent knows how far the SDK has moved since the references were checked. Updating the references means re-running the checks their first paragraphs describe and changing that one stamp.

