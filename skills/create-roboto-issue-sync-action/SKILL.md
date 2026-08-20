---
name: create-roboto-issue-sync-action
description: >-
  Build and verify a Roboto Action that carries findings out of Roboto and into an
  issue tracker — GitLab, GitHub, Jira, Linear — filing an issue per finding and
  keeping it in sync as the data is re-analyzed. Use this skill whenever results
  should reach the place work is tracked even if the user only describes the outcome
  ("open a ticket when a log fails triage", "our engineers live in GitHub, not
  Roboto", "sync the analysis summary to Jira"). Covers what makes an issue "the
  same issue" across re-runs, credential handling, and verification by re-running
  until a duplicate would appear. Not for writing the analysis itself, and not for
  pulling work items into Roboto.
license: MPL-2.0
compatibility: Requires the roboto CLI (authenticated), Docker, and a writable project in the target issue tracker
argument-hint: <what findings should become issues, in which tracker> [--yolo]
---

Turn results that live in Roboto into issues in the tracker where work actually happens — and keep them one-to-one when the same data is analyzed again.

## Read this first

An issue-sync action is an ordinary Roboto Action, so scaffolding, local verification, the edit passes, and deployment are covered by **`create-roboto-action`**. This skill does not repeat that machinery. It supplies the three things specific to syncing:

1. **The identity decision** — what makes an issue "the same issue" on the next run. Get this wrong and every re-ingest files a duplicate.
2. **The sync contract** — stamping, staleness, state, traceability, and credentials.
3. **A verification gate built on re-running**, which is where every defect in this kind of action lives.

Where a phase says "delegate", follow the corresponding phase of `create-roboto-action` and return here. If that skill is not installed, this one still works; say which you did.

**This skill writes to systems outside Roboto.** Every verification step files real issues in a real project, and a defect here is visible to whoever watches that project's issue feed. Phase 0 establishes a scratch project for that reason, and Phase 5 keeps the first production run narrow.

## What you need to run this

- **Run shell commands** and read their output.
- **Read and write files.**
- **Hold a back-and-forth with the user.** The identity decision is theirs.
- **Fetch a web page.** Required, not optional: the tracker's REST API is the other half of this action, and its documentation is not bundled here.

No plugins, no external tool servers (such as MCP servers), no sub-agents. In particular, do not reach for a tracker MCP server if one happens to be available in your harness: the action must call the tracker's API from inside a container at runtime, so a tool that only you can call proves nothing about whether the action works.

`references/` throughout means the directory alongside this file. Read `references/sync-contract.md` and `references/authoring-rules.md` before Phase 1.

## Ground truth

This action straddles two systems, and each has its own authority.

| Rung | Source | Authoritative for |
|---|---|---|
| 1 | The SDK in the action's venv | Everything on the Roboto side: reading findings, parameters, secrets, stamping metadata |
| 2 | **The tracker's own API responses** | Everything on the tracker side. Not its documentation — its responses |
| 3 | The tracker's REST API documentation, fetched this session | The shape of a request before you have made one |
| 4 | `docs.roboto.ai` | Roboto concepts |
| 5 | `references/` here | Lowest: a map for the interview, not a citation |

Rung 2 outranks rung 3 deliberately. Issue-tracker APIs differ between their cloud and self-hosted versions, between API versions, and between plan tiers — a field the documentation describes may be absent, ignored, or rejected on the instance in front of you. **Make one real call early**, against the scratch project from Phase 0, and read what comes back. A response body is worth more than a documentation page, and the difference is usually discovered at the worst possible moment otherwise.

Never write an SDK call or an API field name from memory.

## Phase 0 — Preflight

Delegate the standard action preflight, then add:

- **A writable scratch project in the target tracker**, separate from anything anyone watches. Every gate in Phase 4 files real issues; running them against a live project puts test issues in front of a team.
- **A credential with the right scope**, and confirmation of what that scope is. Read-only tokens are a common and confusing failure: authentication succeeds, reads succeed, and only the create call fails.
- **One real API call**, made now, to confirm the base URL, the project identifier form, and the credential all work together:

  ```bash
  curl -sS -o /dev/null -w '%{http_code}\n' -H "<the tracker's auth header>" "<the tracker's issue-list endpoint for the scratch project>"
  ```

  Confirm the header name and endpoint against the tracker's documentation first (rung 3). A non-2xx here is a configuration problem to solve before writing any code, and the status code distinguishes a bad token from a bad project identifier from a bad base URL.

- **Where the findings come from.** This action reads results that already exist in Roboto — tags, events, a dataset summary, an analysis action's output, an agent's triage verdict. Confirm they are actually there for a real dataset. An action that syncs findings nothing produces is untestable.

**Never put the credential on a command line or in a file in the repository**, including during preflight. Read it from the environment for the manual call, and see rule 5 for how it reaches the action.

## Phase 1 — Decompose and resolve

### Step 1: Establish the mapping

Before asking anything, state the mapping in one sentence: *one `<Roboto thing>` becomes one issue in `<project>`, titled `<pattern>`, carrying `<content>`, labelled `<labels>`.*

If that sentence cannot be written, the ambiguity is in the mapping, and it is Step 2's first question rather than something to discover in code.

### Step 2: Resolve the ambiguities

| Axis | What is undetermined | Consequence of guessing wrong |
|---|---|---|
| **Identity** | What makes an issue the same issue next run — one dataset, one file, one detected incident? | **The central decision.** Wrong, and every re-analysis files a duplicate. See rule 1 |
| Stamp location | Where the issue's identity is recorded on the Roboto side | Determines whether identity survives, and whether the issue is discoverable from Roboto |
| Trigger scope | Which datasets or files sync at all | An over-broad trigger files issues for everything in the org |
| Content | Which findings become the issue body — summary, events, tags, links, all of it? | An issue nobody reads is worse than no issue |
| Labels | Which findings become labels, and under what naming scheme? | Providers differ on whether unknown labels are created or rejected (rule 7) |
| Clean-result posture | What happens when the analysis finds nothing wrong? | Three defensible answers, and they produce very different issue lists. See rule 3 |
| State transitions | Should the issue close when a finding clears, and reopen when it returns? | Determines whether the open-issue list means anything |
| Assignment | Should issues be assigned, or given a milestone or project field? | Usually the reason a team asked for this at all |
| Unconfigured posture | What happens when the tracker parameters are absent? | Degrading to a written report keeps the action useful and testable (rule 8) |
| Failure posture | Tracker unreachable or rejecting — fail the invocation, or log and continue? | Decides whether a tracker outage pages whoever owns the trigger |
| Direction | Does anything flow back from the tracker into Roboto? | Out of scope for this skill. Say so if the user wants it |

**Without `--yolo`**, interview on identity, clean-result posture, content, and failure posture. The others usually follow. Lead with your recommendation.

**With `--yolo`**, resolve them all: identity at the coarsest entity the findings describe, stamp on that entity's metadata, a closed record for a clean result, state kept in sync on re-runs, degrade to a written report when unconfigured, and log-and-continue on tracker failure. Mark each as a default.

### Step 3: Confirm the plan

State the mapping sentence, the resolved axes, and the verification you will run — including that it will file real issues in the scratch project.

## Phase 2 — Implement

Delegate scaffolding, then implement against `references/sync-contract.md`, which carries the mechanics in full. The shape:

- **A thin tracker client** — create, update, fetch-one, and set-state, each with a timeout, each returning a result rather than raising into the action's main path (rules 9 and 10).
- **A rendering step** that turns findings into the issue body, and rewrites any Roboto-internal URIs into browser-openable links so a reader can click from the issue back into the data (rule 6).
- **A sync step** that reads the stamp, decides create-or-update, and re-stamps on create — confirming the stamp landed, since a create that succeeds while its stamp fails duplicates forever (rule 11).
- **A `main` that stays an orchestrator**, with the decisions in module-level functions taking plain values, so the tests in Phase 3 can reach them without a network.

Keep everything the tracker's API shape touches inside the client. The rest of the action should not know whether it is talking to GitLab or GitHub, which is also what makes a second provider cheap later.

## Phase 3 — Test without the network

Delegate the standard test rules. The sync logic is unusually well suited to them, and this is where its edge cases are cheapest to cover:

- Stamp absent → create.
- Stamp present and the issue exists → update, and **no create call**.
- Stamp present and the issue is gone → create, and re-stamp.
- Stamp present and the existence check **errored** → update, not create (rule 2).
- Clean result → whatever Phase 1's posture said.
- Finding clears, then returns → the state transitions both ways.

Each of those is a function taking plain values and a fake client. None of them needs a tracker.

## Phase 4 — Verify against the real tracker

Delegate the standard gates, then run these against the scratch project. The property under test is not "an issue appeared" — it is **"exactly one issue exists after running twice."**

1. **First run.** An issue appears. Its title matches the pattern, its body carries the findings and links back to the dataset and the invocation, its labels are what the findings said, and its state matches the clean-result posture.
2. **The Roboto side is stamped.** The entity carries the issue's identity and its URL, so the link works in both directions (rule 4).
3. **Second run, same input, nothing changed.** **The gate.** The same issue is updated. No second issue exists. Confirm by listing the project's issues, not by reading the log.
4. **Second run with a changed finding.** The body and labels update, and the state follows the transition rules Phase 1 settled.
5. **Deleted-issue recovery.** Delete the issue in the tracker, then run again. A fresh issue is created, the entity is re-stamped, and nothing raises. Users tidy issue boards; a stamp pointing at a deleted issue is a matter of when, not if.
6. **Unconfigured.** Run with the tracker parameters absent and confirm the action degrades as Phase 1 decided rather than failing.
7. **Bad credential.** Run with an invalid token and confirm the failure posture holds — and that the token does not appear in the logs (rule 12).

Read the tracker, not the log, for every check that concerns the tracker. A log line saying an issue was created is the action's belief; the project's issue list is the fact.

Record each in `SPEC.md` with the issue identity it produced. Then **clean up the scratch project**, or say plainly that you left the test issues behind and where.

## Phase 5 — Edit pass and first production run

Delegate the edit pass, adding one check: confirm no credential, project identifier, or instance URL is a literal anywhere in the repository.

Then, on the handoff:

- The first production run should be **narrow and manual** — one dataset the user picks, in the real project — before any trigger exists. An action that files issues is one of the few whose first wide run is genuinely hard to undo, because the cleanup is somebody closing issues by hand.
- Only after that, point at automation. `create-roboto-trigger` builds and verifies the trigger, and its own blast-radius step is worth more here than anywhere else: the count it reports is the number of issues that will appear.

## Phase 6 — Hand off

Delegate the standard report, and add:

1. **The mapping sentence** from Phase 1, as the one-line description of what this action does.
2. **The identity rule**, stated explicitly: what makes an issue the same issue, and where that is recorded.
3. **What the tracker will look like** — how many issues, in what state, with which labels, and what a clean result produces.
4. **The credential** — which scope it needs, where it is stored, and that rotating it means updating the secret rather than the action.
5. **Verification** — every gate, including the re-run and deleted-issue tests, with the issue identities produced. Say whether the scratch project was cleaned up.
6. **What is not synced** — findings deliberately left out, and the fact that nothing flows back from the tracker into Roboto.

Then the deploy command, unrun, and the trigger as a separate follow-on — also unrun, and with the blast radius named.
