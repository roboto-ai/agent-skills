---
name: debug-roboto-invocation
description: >-
  Diagnose a Roboto Action invocation that failed, hung, or produced the wrong result,
  and prove the fix by re-running it. Use this skill whenever an invocation did not do
  what was expected even if the user only pastes an invocation id, a log line, or says
  "my action isn't working" or "the trigger fired but nothing happened". Covers
  evidence gathering from the invocation's own status history, fault localization,
  local reproduction, the fix, and re-verification against the same input. Not for
  writing a new action (use create-roboto-action) and not for an action that has
  never been invoked.
license: MPL-2.0
compatibility: Requires the roboto CLI (authenticated); Docker only if the fix is reproduced locally
argument-hint: <invocation id, or a description of what went wrong> [--yolo]
---

Turn "it failed" into a named cause, a fix, and a re-run that proves the fix — with the evidence for each step drawn from what the platform recorded, not from what the failure looked like at a glance.

## What you need to run this

This skill does not know which agent is reading it, so it names the capabilities it needs rather than assuming them:

- **Run shell commands** and read their output.
- **Read and write files.** Only needed when the fix lands in an action's source.
- **Hold a back-and-forth with the user.** Some causes are decisions, not defects.
- **Fetch a web page.** Used to check the invocation surface against `docs.roboto.ai`. Both higher rungs of the Ground truth ladder are local, so this matters less here than elsewhere.

Nothing beyond that. No plugins, no external tool servers (such as MCP servers), no sub-agents, no symbol-level code intelligence.

`references/` throughout means the directory alongside this file. Read `references/triage.md` before Phase 1; it carries the fault-localization tree that the phases below execute. `references/invocation-api.md` carries the status and exit-code vocabulary that tree branches on.

## The request

The argument is an invocation id, or a description of what went wrong. Strip a `--yolo` flag from anywhere in it.

`--yolo` suppresses the questions in Phase 4 and nothing else. It never suppresses Phase 5: a fix that has not been re-run is a hypothesis, and reporting one as a fix is the failure mode this skill exists to prevent.

If the argument names no invocation, Phase 0 finds it. If the user's action has never been invoked at all, there is nothing to debug; say so and point them at `create-roboto-action`.

## The discipline

Three rules govern every phase. They exist because the fastest-looking path through a failed invocation is usually the wrong one.

1. **Read the status history before the logs.** Every invocation carries a log of its status transitions, and each transition can carry a detail message. Where an invocation stopped localizes the fault before you read a single line of output. An agent that opens with `invocations logs` and starts pattern-matching on tracebacks has skipped the cheapest evidence there is.

2. **Never diagnose a non-terminal invocation.** Queued, Scheduled, Downloading, Processing, and Uploading are all live states. Test with `not status.is_terminal()`, never with `is_running()` — the latter covers only Downloading, Processing, and Uploading, so a Queued invocation returns `False` from both predicates. And note the sharp edge: `is_terminal()` returns `True` for `Failed`, while the transition rules still permit `Failed` to return to `Queued`. A `Failed` invocation therefore satisfies this rule and may still not be the last word. Prefer `Deadly` when both appear in the history, and say which you are reading.

3. **A cause is not confirmed until it is reproduced or the evidence is unambiguous.** "The log mentions memory, so it ran out of memory" is a hypothesis. The status detail saying so, or a local run that fails the same way, is evidence. Say which one you have.

## Ground truth

Never write an SDK call, a CLI flag, an enum member, or an exit code from memory.

| Rung | Source | How | When it wins |
|---|---|---|---|
| 1 | The installed SDK | `python -c "from roboto.domain.actions import InvocationStatus; print(list(InvocationStatus))"`, or read `site-packages/roboto/domain/actions/` and `site-packages/roboto/action_runtime/` | Highest authority: it defines the vocabulary the platform reports in |
| 2 | The CLI's own help | `roboto invocations status --help`, `roboto invocations logs --help` | Authoritative for flags and defaults |
| 3 | `docs.roboto.ai` | Fetch the durable URLs in `references/invocation-api.md` | Concepts, the invocation lifecycle, worked examples |
| 4 | `references/invocation-api.md` | Read it | Lowest authority: a map, not a citation |

A docstring is prose, not code: confirm enum members by reading the enum, not by trusting an example that uses one.

The action's own source, when available, is a fifth source and the authority on what the action intended to do. It is not authority on what the invocation did.

## Phase 0 — Establish the subject

You need one invocation id and the terminal status it reached.

If the user supplied an id, use it. Otherwise find it:

```bash
roboto --suppress-upgrade-check actions list-invocations <action-name> --org <org-id>
```

For a failure the user attributes to a trigger, the trigger's own invocation list is the narrower path; `create-roboto-trigger`'s reference covers it, and `Trigger.get_invocations()` is the call.

Then take the invocation's status history — the first and most informative command in this skill:

```bash
roboto --suppress-upgrade-check invocations status <invocation_id>
```

This prints every status transition with its timestamp and, where the platform recorded one, a detail message. Read all of it before anything else. Note three things:

- **The terminal status**, or that there is not one yet. If the invocation is still running, stop and report that (discipline rule 2). `--tail` follows it to completion if the user wants to wait.
- **The last status reached before the failure.** This is the localization, and Phase 2 branches on it.
- **Every detail message.** Details are the platform's own account of what went wrong, and they are frequently the whole answer.

Also capture the invocation's configuration, since several causes are visible in it rather than in the logs:

```bash
roboto --suppress-upgrade-check invocations show <invocation_id>
```

This prints the whole record as one JSON object, so it also carries the status log and the idempotency id. Read the action reference and its image digest (there is no version field, and an older invocation may carry no digest at all), the data source and input specification, the parameter values, the compute requirements, and the timeout. A parameter that is absent, an input specification that selects nothing, or a timeout smaller than the work needs are all diagnosable here, before a log is opened.

## Phase 1 — Read the evidence

Now read the logs, with the localization from Phase 0 in hand:

```bash
roboto --suppress-upgrade-check invocations logs <invocation_id>
```

Read them in this order, which is not the order they are printed in:

1. **The end.** The last lines before the process stopped carry the proximate failure. The exit code is *not* a field here — there is no `exit_code` anywhere on the invocation surface; where one surfaces it is inside the terminal status's `detail` string from Phase 0, which is another reason that command comes first.
2. **The beginning.** Startup lines establish whether the action reached its own code at all. A container that fails during import never logged anything the action wrote.
3. **The middle**, only for what the requirements in question depend on: which inputs it found, which branch it took, what it reported writing.

**The logs are not only the action's.** `invocations logs` returns records from every container in the invocation — setup, monitor, action, output handler, and the log router — under a per-process header, with no filtering. Read the headers before concluding anything from silence:

- **No output under the action's own header** means the action's code never logged. Combined with a pre-Processing terminal status, the fault is in the platform's preparation of the invocation — and the setup container's section is where that is explained. This is the branch where the logs matter most, not least.
- **Logs that stop mid-work with no error** point at a limit rather than a defect — a timeout, or the container being stopped. Check the elapsed time against the invocation's configured timeout, and check the last status detail.

An action that logs nothing below error level may simply not have set its log level from the invocation context, in which case the absence of detail is a defect in the action's observability rather than evidence about this failure. `references/triage.md` covers that case.

## Phase 2 — Localize

Take the last status reached, the exit code if one was reported, and the details, into `references/triage.md`. It maps each combination to a fault domain and to the evidence that would confirm it.

The spine of that tree is short enough to state here: **where it stopped tells you whose fault it is.** Failing while the platform is preparing inputs points at the invocation's input specification or at the data. Failing while the action's own code is running points at the action. Failing while outputs are being uploaded points at what the action wrote, or where it was to be written. And an invocation that never left the queue has not failed at all in the usual sense — it was never scheduled.

Exit codes narrow it further, where one was reported. The runtime *defines* a set adapted from `sysexits.h` — a usage error, an input-data error, an internal software error, a configuration error — four verdicts that look identical in a log and carry four different fixes. Read the exact set from the installed `roboto.action_runtime.exit_codes` enum, and note what that enum is: a vocabulary offered to action authors, not a set the platform emits on their behalf. An action that does not follow the convention exits with whatever its process exited with, so a code outside the enum is ordinary rather than anomalous.

One of those deserves naming here because it is the most commonly misdiagnosed signal on the platform: **there is an exit code whose meaning is "the action behaved correctly and the input was bad."** Treating it as an action defect and changing the action's code is fixing the wrong thing — and it will look like it worked, because the action will then accept data it should have rejected. Confirm the code's meaning against the enum, and when it is that one, the finding is about the data.

State the localization explicitly before moving on: the fault domain, the evidence for it, and the confidence. If the evidence is ambiguous, say so and let Phase 3 settle it.

## Phase 3 — Reproduce

Reproduction converts a hypothesis into a cause. Skip it only when the evidence is already unambiguous — a status detail that names the failure, or a configuration error visible in `invocations show` — and say that you skipped it and why.

When the action's source is available, reproduce locally with the narrowest input that still fails:

```bash
roboto --suppress-upgrade-check --log-level=info actions invoke-local --dry-run <args>
```

Local invocation runs its container with an interactive terminal attached, so from a non-interactive shell the container never starts — **and the CLI still exits `0`**, so an unwrapped scripted run looks like it passed while reproducing nothing. Supply a pty. `create-roboto-action`'s Phase 4 documents the platform-specific `script` forms; use the one matching `uname -s`.

Match the failing invocation's conditions, taking them from `invocations show`: the same parameter values, and the same input where you can select it. Then narrow: one file rather than the dataset, the smallest input that still reproduces. A reproduction that takes twenty minutes will be run once; one that takes twenty seconds will be run after every change.

When the source is **not** available — a Roboto-provided action, or one owned by another org — local reproduction is not on the table. Say so plainly. The diagnosis still stands on the evidence from Phases 0 through 2, and the deliverable becomes a report rather than a fix (Phase 6).

Some causes do not reproduce locally by construction: compute limits the local run does not impose, credentials that exist only in the hosted environment, inputs whose size is the problem. For these, the reproduction step is a hosted re-invocation with one variable changed, which is Phase 5 run early. Say which variable you changed and why.

## Phase 4 — Fix

The fix belongs wherever the cause is, and the cause is not always a defect.

- **In the action's code or configuration** — change it, and keep the change minimal and aimed at the confirmed cause. Do not opportunistically refactor around it; an unrelated change in the same commit makes Phase 5 prove less than it appears to.
- **In the invocation's parameters, input specification, or compute sizing** — the action is fine and the invocation was wrong. The fix is a different invocation, or a change to the trigger that produced it.
- **In the data** — the action correctly rejected bad input. The fix is upstream of Roboto, and the finding is a report, not a patch.
- **In an expectation** — the invocation did what it was configured to do, and the configuration encodes a misunderstanding. Say so directly; this is a real and common outcome.

When the cause is a decision rather than a defect — whether to accept the malformed input, whether to raise the memory allocation and its cost, whether the action should skip a bad file or fail the invocation — ask the user rather than choosing for them. Under `--yolo`, choose the option that fails loudly rather than silently, and record the choice for the report.

If the action's source is under version control, keep the fix reviewable as its own diff.

## Phase 5 — Prove

A fix that has not been re-run is a hypothesis. This phase is not optional, including under `--yolo`.

1. **Redeploy the action** if the fix changed its code or image. A hosted invocation runs the deployed image, not your working tree, and an unredeployed fix produces a re-run that fails identically and is easy to misread as "the fix didn't work". The action project's own `deploy.sh` is the mechanism; deploying is the user's call, so ask before running it.

2. **Re-invoke against the same input the original invocation used.** Not a smaller one, not a clean one — the same one, taken from `invocations show`. A fix proven against easier input is not proven.

   ```bash
   roboto --suppress-upgrade-check actions invoke <action-name> <same input selection> <same parameters> --org <org-id>
   ```

3. **Verify the same way you diagnosed:** read the new invocation's status history to its terminal status, then read its logs to confirm the work actually happened. A run that completes without doing anything is not a fix.

4. **Compare the two invocations explicitly.** Old id, new id, what changed between them, what the status and logs now show. That comparison is the evidence in the report.

If the re-run fails differently, that is progress, not failure: the original cause is fixed and a second one is now visible. Return to Phase 2 with the new evidence rather than reporting a partial fix as a whole one.

If the re-run cannot happen — no permission to deploy, no access to the original input, the action belongs to another org — stop and say exactly what is unproven and what command would prove it. Do not report an unverified fix as a fix.

## Phase 6 — Report

1. **What failed** — the invocation id, the action, the terminal status, and the exit code if one was reported.
2. **The cause** — one sentence naming the fault domain and the specific defect, decision, or datum.
3. **The evidence** — the status detail, log excerpt, or configuration field the cause rests on, quoted. If the cause was reproduced, say so; if it was inferred, say that instead and name the residual uncertainty.
4. **The fix** — what changed and where. If the fix was a decision, whose decision and what the alternatives were.
5. **The proof** — the original and new invocation ids, and what the re-run showed. Or, if Phase 5 could not run, exactly what remains unproven and the command that would settle it.
6. **What else this surfaced** — anything found along the way that was not the cause. An action that logs nothing useful, an over-broad trigger, a timeout that is going to fail again under slightly larger input. List these; do not fix them silently.

When the deliverable is a report rather than a patch — an action you could not modify, a cause in the data, a cause in someone else's configuration — say that in the first line, so the reader does not go looking for a diff that does not exist.
