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
| [create-roboto-trigger](skills/create-roboto-trigger/) | Creates a [Roboto Trigger](https://docs.roboto.ai/learn/actions.html) that invokes an existing action automatically when data arrives or on a schedule, and verifies it against real trigger evaluation records before handing you the command to enable it |
| [debug-roboto-invocation](skills/debug-roboto-invocation/) | Diagnoses a Roboto Action invocation that failed, hung, or produced the wrong result, working from the invocation's own status history and exit code, and proves the fix by re-running it against the same input |
| [create-roboto-ingestion-action](skills/create-roboto-ingestion-action/) | Builds an action that ingests a custom or unsupported log format into topics, and verifies it by reading the ingested data back as a dataframe rather than by watching the action exit cleanly |

Each skill's README covers its requirements and usage.

## License

[MPL-2.0](LICENSE)
