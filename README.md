# Roboto Agent Skills

[Agent Skills](https://agentskills.io) that teach AI coding agents to build on [Roboto](https://www.roboto.ai). Each skill is a self-contained folder of instructions and reference material that an agent loads on demand.

## Install

The [skills CLI](https://skills.sh) detects your agent (Claude Code, Cursor, and others) and installs skills into that agent's skills directory:

```bash
npx skills add roboto-ai/agent-skills
```

Or install a single skill:

```bash
npx skills add roboto-ai/agent-skills --skill create-roboto-action
```

To install without the CLI, copy a skill's folder into your agent's skills directory; each skill's README gives the exact steps.

## Skills

| Skill | What it does |
|---|---|
| [create-roboto-action](skills/create-roboto-action/) | Generates a [Roboto Action](https://docs.roboto.ai/learn/actions.html) from a natural-language description of the job it should do, and dry-runs the action locally against a dataset in your Roboto org before handing it to you |
| [roboto-guide](skills/roboto-guide/) | Answers questions about Roboto and writes `roboto` CLI commands and ad hoc Python SDK scripts, consulting [docs.roboto.ai](https://docs.roboto.ai) and the latest released SDK |

Each skill's README covers its requirements and usage.

## Plugins and MCP server

This repo is also a plugin that bundles these skills with the hosted [Roboto MCP server](https://roboto.ai/docs) at `https://mcp.roboto.ai/mcp`, so agents can search and analyze your Roboto data directly. Manifests for each agent sit in the repo root:

| File | Agent |
|---|---|
| `plugin.json` + `mcp.json` | [Agent Plugins](https://agent-plugins.org) standard (Cursor and others) |
| `.cursor-plugin/plugin.json` | Cursor |
| `.claude-plugin/plugin.json` + `.mcp.json` | Claude Code |
| `gemini-extension.json` | Gemini CLI |

The first time you connect, your agent opens a browser sign-in to Roboto; a sign-in lasts up to 30 days.

## License

[MPL-2.0](LICENSE)
