# create-roboto-issue-sync-action

Builds a [Roboto Action](https://docs.roboto.ai/learn/actions.html) that carries findings out of Roboto and into the issue tracker where work actually happens — GitLab, GitHub, Jira, Linear — and keeps the issue in sync as the data is re-analyzed.

## Install

With the [skills CLI](https://skills.sh), which detects your agent and installs into the right place:

```bash
npx skills add roboto-ai/agent-skills --skill create-roboto-issue-sync-action
```

**Install [`create-roboto-action`](../create-roboto-action/) alongside it.** A sync action is an ordinary action, so this skill delegates scaffolding, local verification, the edit passes, and deployment to that one and supplies only what is specific to syncing. Installing both is one command:

```bash
npx skills add roboto-ai/agent-skills
```

If your agent has a skills directory, move the folder there and the skill becomes available by name. For Claude Code that directory is `~/.claude/skills/` for every project, or `<repo>/.claude/skills/` for a single repository:

```bash
mv create-roboto-issue-sync-action ~/.claude/skills/
```

Claude Code takes the command name from the directory rather than the frontmatter, so a folder named `create-roboto-issue-sync-action` gives you `/create-roboto-issue-sync-action`.

## Requirements

Your agent must be able to run shell commands, read and write files, hold a back-and-forth with you, and **fetch web pages** — the tracker's REST API is the other half of this action and its documentation is not bundled here.

Your machine needs Docker, the `roboto` CLI on `PATH`, Roboto credentials, and network access to GitHub for the project scaffolder.

You need **a writable scratch project in the target tracker** and a token whose scope permits creating issues. Every verification step files real issues; a scratch project keeps test issues out of a feed your team watches.

You also need **findings that already exist in Roboto** — tags, events, a dataset summary, a prior action's output, an agent's verdict. This action does not analyze anything; it moves results that are already there.

## Usage

In Claude Code, invoke the skill as a slash command:

```
/create-roboto-issue-sync-action <what findings become issues, in which tracker> [--yolo]
```

```
/create-roboto-issue-sync-action When a dataset gets tagged with a fault label, open a GitLab issue with the summary and the event timeline

/create-roboto-issue-sync-action Sync our anomaly-detection results into the GitHub repo where the firmware team works, one issue per affected log
```

On an agent without slash commands, point it at `create-roboto-issue-sync-action/SKILL.md` and give it the same description.

## The decision the whole skill turns on

**What makes an issue "the same issue" on the next run?**

A tracker has no idea which Roboto entity an issue came from, so nothing links them unless you store the link yourself. Get this wrong and every re-ingest, every re-analysis, every trigger retry files another duplicate — quietly, and forever, until a human scrolls a polluted issue list.

So the skill treats identity as the first interview question, stamps the issue's identifier back onto the Roboto entity, and reads that stamp before every sync. It also handles the two cases that follow from it:

- **The stamped issue was deleted.** People tidy issue boards. The action creates a fresh one and re-stamps, rather than failing on a 404.
- **The existence check itself failed.** A timeout or a rate limit is not evidence the issue is gone. The action assumes it exists, because a missed update is recoverable and a duplicate is manual cleanup.

## How it verifies

The property under test is not "an issue appeared." It is **"exactly one issue exists after running twice."**

The gate runs against your scratch project and checks the tracker, not the log — the log records what the action believed, and the belief is what is being tested:

1. First run files an issue with the right title, body, labels, and state.
2. The Roboto entity is stamped, so the link works in both directions.
3. **Second run with the same input updates that issue and creates no second one.**
4. A changed finding updates the body and labels, and moves the state.
5. A deleted issue is recovered from — fresh issue, re-stamped, nothing raises.
6. Unconfigured degrades to a written report instead of failing.
7. A bad credential fails the way you chose — and does not print the token into the invocation logs.

## What it will not do quietly

An action that files issues is one of the few whose first wide run is genuinely hard to undo, because the cleanup is somebody closing issues by hand. So the skill ends with a **narrow, manual first production run** on one dataset you pick, before any trigger exists — and hands off the trigger as a separate, unrun step whose blast-radius count is, quite literally, the number of issues that will appear.

## Provider differences it makes you check

Trackers differ in ways that are invisible until they bite. The skill's ladder puts **the tracker's own API responses above its documentation**, because cloud and self-hosted versions of the same product disagree, and so do plan tiers.

The one worth naming up front: **unknown labels**. A tracker may create a label on first use, reject the request, or silently drop the unknown ones and file the issue anyway — successfully, and missing exactly the information it was filed to convey. Which of the three yours does is something the skill makes you verify empirically against a scratch project, not something it assumes.

## Deliverables

A deployable action, plus a `SPEC.md` whose first section is the identity rule: what makes an issue the same issue, where that is recorded, and what a clean result produces. Those are the three things the next person to change this action will change, and the spec is where they learn the current answer and why.

## Out of scope

Nothing flows back from the tracker into Roboto. Closing an issue does not clear a tag. If you want that, it is a different action reading the tracker on a schedule, and the skill says so rather than bolting it on.
