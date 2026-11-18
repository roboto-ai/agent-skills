# create-roboto-issue-sync-action

Builds a Roboto Action that files findings from Roboto (session or dataset tags, AI summaries, events, metadata) as issues in a tracker such as GitHub, GitLab, Jira, or Linear, and updates the same issue on every re-run instead of filing a duplicate. The agent consults the [Roboto docs](https://www.roboto.ai/docs), the latest SDK on PyPI, and the tracker's own API.

## Install

With the [skills CLI](https://skills.sh), which detects your agent and installs into its skills directory for the current project:

```bash
npx skills add roboto-ai/agent-skills --skill create-roboto-issue-sync-action
```

Add `-g` to install for every project on the machine instead.

Or manually: keep this `create-roboto-issue-sync-action` folder anywhere your coding agent can read, then tell the agent to follow `create-roboto-issue-sync-action/SKILL.md`.

If your agent has a skills directory, move the folder there and the skill becomes available by name. For Claude Code that directory is `~/.claude/skills/` for every project, or `<repo>/.claude/skills/` for a single repository:

```bash
mkdir -p ~/.claude/skills && mv create-roboto-issue-sync-action ~/.claude/skills/
```

## Requirements

Your agent must be able to run shell commands, read and write files, hold a back-and-forth with you, and fetch web pages (or run `curl`): the tracker's REST API documentation is not bundled.

Your machine needs the `roboto` CLI on `PATH`, Docker running, Git, and Roboto credentials: a personal access token in `~/.roboto/config.json`, as described on [Programmatic Access](https://www.roboto.ai/docs/getting-started/programmatic-access), or the same token in the `ROBOTO_API_KEY` environment variable. Lookups need network access to `www.roboto.ai`, `pypi.org`, `files.pythonhosted.org`, `raw.githubusercontent.com`, and `api.github.com`, and the action template comes from GitHub. [uv](https://docs.astral.sh/uv/) is recommended; without it, the skill uses one virtual environment built with `pip`, which needs Python 3.10 or newer. The skill runs on macOS and Linux; Windows is untested.

You also need a writable scratch project in the target tracker, a token that can create and edit issues in it, and a session or dataset whose findings already exist in Roboto. Verification files real issues, so the scratch project keeps them away from your team. The skill checks all of this before asking you anything, and stops with what to fix if something is missing.

## Usage

In Claude Code, invoke the skill as a slash command:

```
/create-roboto-issue-sync-action When a session gets a fault tag from triage, open a GitHub issue with its summary and events
/create-roboto-issue-sync-action Keep one Jira ticket per flight in sync with its AI summary, closed when nothing is wrong --yolo
/create-roboto-issue-sync-action File a GitLab issue for every dataset tagged needs-review
```

In an agent without slash commands, point it at `create-roboto-issue-sync-action/SKILL.md` and give it the same description.

## What it does

1. Checks the CLI, Docker, Git, credentials, and the latest SDK release, makes one read call against your scratch tracker project, and reads the findings of a real session or dataset.
2. States the mapping in one sentence (one session becomes one issue in this project, with this title, content, and labels) and lists what remains ambiguous, starting with what makes an issue the same issue on the next run.
3. Resolves the ambiguities by interviewing you or, under `--yolo`, by judgment, and records each decision in `SPEC.md`.
4. Scaffolds the project with `roboto actions init`, which downloads Roboto's action template.
5. Implements a tracker client, a renderer that turns `roboto://` references into web links, and a sync step that records the issue on the Roboto entity and reads that record before every run.
6. Verifies with lint and unit tests, a local dry run, and, after you approve, real runs against the scratch project: two runs must leave one issue, a deleted issue must be recreated, and a bad token must not appear in the log.
7. Reviews its own code for SDK accuracy and for credentials or identifiers written into the repository.
8. Hands off the deploy command and a first hosted run on one entity without running them, since both write to your organization and your tracker.

## `--yolo`

Skips the interview and resolves every ambiguity by judgment: one issue per session (or per the coarsest entity the findings describe), a closed issue as the record of a clean result, issue state that follows the findings, and logging rather than failing when the tracker is unreachable. The preflight, the verification gates, and the edit pass (steps 1, 6, and 7 above) all still run, and every judgment lands in `SPEC.md` marked as a default. `--yolo` never creates a secret, runs against the tracker, deploys, or invokes on hosted compute without your yes.

## Deliverables

A deployable action whose `SPEC.md` opens with the identity rule: what makes an issue the same issue, which Roboto entity records it, and what a clean result produces. Those are the three things the next person to change the action will change.

## Layout

| Path | Purpose |
|---|---|
| `SKILL.md` | The procedure the agent follows |
| `references/sync-api.md` | How an invocation reaches a session or dataset, where findings come from, where the issue is recorded, secrets, links, the tracker client, and the sync decision |
| `references/authoring-rules.md` | 23 numbered rules, each stated as the failure it prevents |
| `LICENSE` | MPL-2.0 license text |

The references carry one stamp, the `metadata` block in `SKILL.md`, naming the SDK release and date they were last checked against. The SDK calls were checked against that release from PyPI and the CLI flags against the `--help` output of the CLI bundled with it. They tell the agent what to look up; the live documentation and the latest SDK are the authority.

## Staying current

Nothing in this skill pins an SDK version. Signature and flag checks resolve the newest `roboto` release from PyPI on each run, and the preflight compares the stamp in `SKILL.md` with the latest release, so the agent knows when the references predate the SDK. Updating the references means re-running the checks their first paragraphs describe and changing that one stamp.
