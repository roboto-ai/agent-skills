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
| [create-roboto-ingestion-action](skills/create-roboto-ingestion-action/) | Builds a [Roboto Action](https://www.roboto.ai/docs/learn/actions) that ingests a log format Roboto cannot read yet into topics you can search, plot, and read, and verifies it by reading the ingested data back and comparing it with a sample file |
| [create-roboto-trigger](skills/create-roboto-trigger/) | Creates a [Roboto Trigger](https://www.roboto.ai/docs/learn/actions) that runs an existing action on a platform event or on a schedule, and verifies it with dry runs and a test dispatch on a trigger pinned to one test subject before handing you the command that puts it live |
| [debug-roboto-invocation](skills/debug-roboto-invocation/) | Diagnoses a failed, hung, or wrong [Roboto Action](https://www.roboto.ai/docs/learn/actions) invocation from its status history, record, and logs, and proves the fix by re-running it on the same inputs |
| [roboto-guide](skills/roboto-guide/) | Answers questions about Roboto and writes `roboto` CLI commands and ad hoc Python SDK scripts, consulting [docs.roboto.ai](https://docs.roboto.ai) and the latest released SDK |

Each skill's README covers its requirements and usage.

## License

[MPL-2.0](LICENSE)
