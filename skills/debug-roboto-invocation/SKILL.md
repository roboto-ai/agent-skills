---
name: debug-roboto-invocation
description: >-
  Diagnose a Roboto Action invocation that failed, hung, or did the wrong thing,
  find the cause, and prove the fix by re-running it on the same inputs. Use this
  skill whenever an invocation did not do what was expected, even if the user only
  pastes an iv_ ID or a log line, or says "my action isn't working", "the trigger
  fired but nothing happened", "it says Completed but the output is empty", or
  "this session never finished ingesting". Covers locating the invocation, reading
  its status history, record, and logs, localizing and reproducing the fault, a fix
  with an ambiguity-resolving interview (skipped under --yolo), and verification by
  a hosted re-run compared against the original. Not for building a new action (use
  the create-roboto-action skill) or making a trigger fire (use the
  create-roboto-trigger skill), and not for general Roboto questions or one-off
  scripts (use the roboto-guide skill).
license: MPL-2.0
compatibility: >-
  Needs a shell and network access to www.roboto.ai, pypi.org,
  files.pythonhosted.org, raw.githubusercontent.com, and api.github.com. Needs
  uv (or Python 3.10+ with pip), the roboto CLI, and Roboto credentials. Docker
  only for reproducing a container action locally.
metadata:
  verified-sdk: "0.64.0"
  verified-on: "2026-11-18"
argument-hint: <invocation ID, or a description of what went wrong> [--yolo]
---

Turn "the invocation failed" into a named cause, a fix, and a re-run that proves the fix. Every step rests on what the platform recorded for the invocation (its status history, its record, and its logs), not on what the failure looked like at a glance.

## What you need to run this

This skill does not know which agent is reading it, so it names the capabilities it needs rather than assuming them:

- **Run shell commands** and read their output.
- **Read and write files.** Writes are needed only when the fix lands in an action's source or a diagnostic script.
- **Hold a back-and-forth with the user.** Some causes are decisions, not defects, and Phase 3 asks about them.
- **Fetch a web page**, optionally. `curl` does the same for the docs lookups below.

uv is the preferred runner because it resolves the latest SDK on every run. Without uv, build one virtual environment for the session (`python3 -m venv`, then `pip install --upgrade 'roboto[analytics]'`) and use its interpreter wherever this file says `uv run`.

`references/` throughout means the directory alongside this file. Read `references/invocation-api.md` and `references/triage.md` before Phase 1. The first maps where each piece of evidence lives; the second maps evidence to a cause.

## The request

The user's description of the failure is the argument to this skill: an invocation ID, an action name, a trigger, a session, or a symptom. Strip a `--yolo` flag from anywhere in it; what remains is the description. If the description is empty, ask the user which invocation or symptom to look at and stop.

`--yolo` suppresses the Phase 3 questions and nothing else. The preflight, the evidence gathering, the re-run in Phase 4, and the recording of decisions all stand: every decision made by judgment lands in the Phase 5 report with its rationale, so the user audits the decisions after the fact instead of before.

`--yolo` never authorizes a write to the user's organization. Redeploying an action, publishing a new Python action version, re-invoking on hosted compute, and cancelling an invocation stay the user's call: give the exact command and wait for a yes.

## Sources, in order of authority

Three sources outrank every file in this skill. They are numbered by authority: when two disagree, the lower number wins. Start with the source whose Answers column fits the question, and stop at the first source that answers it.

| Source | What | How | Answers |
|---|---|---|---|
| 1 | The latest released SDK and CLI, resolved fresh from PyPI | `uv run --no-project --isolated --refresh-package roboto --with 'roboto[analytics]' python -c "import inspect, roboto; print(inspect.signature(roboto.Invocation.query))"`; for CLI flags, `uv run --no-project --isolated --refresh-package roboto --with roboto python -m roboto.cli invocations logs --help` | Exact signatures, enum members, docstrings, CLI flags |
| 2 | The Roboto docs at www.roboto.ai/docs | Fetch `https://www.roboto.ai/docs/<path>.md`; see "Docs lookups" | The invocation lifecycle, Python actions, compute options, triggers |
| 3 | The SDK CHANGELOG and GitHub releases | Fetch https://raw.githubusercontent.com/roboto-ai/roboto-python-sdk/refs/heads/main/CHANGELOG.md and https://api.github.com/repos/roboto-ai/roboto-python-sdk/releases/latest | Which release added or changed a behavior; the latest version number |

Every lookup of the latest release runs with `--no-project --isolated`, so that a `uv run` started inside a Python project or virtual environment neither uses the `roboto` installed there (an older pinned release, for example) nor writes a `uv.lock` into the project, and with `--refresh-package roboto`, so that it does not reuse PyPI's answer from up to ten minutes earlier and miss a new release.

The files under `references/` rank below all three. The `metadata` block in this file's frontmatter records the SDK release (`verified-sdk`) and date (`verified-on`) they were last checked against. When Phase 0 finds a newer release, re-check anything you take from them against source 1 before using it. Cite the live source, not the reference file.

**Docs lookups.** To find a page, fetch `https://www.roboto.ai/docs/llms.txt`, which lists every page with its URL. To read one, fetch its Markdown copy by adding `.md` to the URL (`https://www.roboto.ai/docs/learn/actions.md`); without a fetch tool, `curl -sL <url>`. To find where an SDK symbol is documented, search `https://www.roboto.ai/docs/reference/python-sdk/objects.json` for its dotted name. For REST endpoints, read `https://www.roboto.ai/docs/reference/rest-api/openapi.json`. These files are large, so read them through a search (`grep`, or a Python one-liner) rather than printing them whole. If the agent runtime can start a subagent, run lookups in one and return only the answer.

- **The installed CLI and SDK are not authoritative.** They are whatever version the user last installed, and `roboto <command> --help` describes that version and nothing else. If the CLI is behind the latest release, say so and point to `roboto upgrade`; on a CLI older than 0.58.0, point to `brew upgrade roboto`, or to replacing the binary or `.deb` with the one from the latest release.
- **A copy that will run is the authority on what it does.** The SDK inside a container action's image, not the latest release, is what ran in the failed invocation. When the action's project is available, read its version with `.venv/bin/python -c "from roboto.version import roboto_version; print(roboto_version())"` (or from its `pyproject.toml` and lock file) and record it. If it is behind source 1, check the CHANGELOG between the two for a fix to the behavior you are diagnosing. Never lower source 1 to match it.
- **A docs page can be ahead of the release.** When source 2 describes something source 1 lacks, source 3 says whether it is released. Diagnose against the release, and tell the user what is coming.

Where a source cannot be reached, say which one, and tell the user what you could not check. With no fetch tool and no `curl`, ask the user to paste the page.

## Phase 0 — Preflight

Run this before reading any evidence. Every check below guards a step that would otherwise fail after you have already built a diagnosis on it.

```bash
uname -s                                             # platform; decides the pty form in Phase 2
roboto --version                                     # installed CLI; compare with the latest release below
uv --version                                         # runner for source 1
roboto --suppress-upgrade-check users orgs           # credentials valid; one JSON object per org
curl -s https://pypi.org/pypi/roboto/json | python3 -c 'import json,sys; print(json.load(sys.stdin)["info"]["version"])'
```

- **`users orgs`** is the credential check and the org inventory. If it lists more than one org, every org-scoped command below needs `--org`, and SDK queries need `owner_org_id`. Never read `~/.roboto/config.json` to check credentials, and never print a token.
- **The latest release** is the version source 1 resolves. If it is newer than `verified-sdk`, say that the references predate it.

The skill runs on macOS and Linux; Windows is untested. If a check fails, stop and tell the user exactly what to install or run.

## Phase 1 — Gather

### Step 1: Find the invocation

Use an ID the user gave. Otherwise find one from what they named, using the entry points in `references/invocation-api.md` ("Finding the invocation"):

- **An action:** `roboto actions list-invocations <action>` prints every invocation of it, newest first.
- **A trigger:** read its dispatch history. Each dispatch's `result_ref` is the invocation it started. A `failed` dispatch started nothing, and its `status_detail` states why, such as a required parameter the target does not set (`{'<name>'} is a required parameter for action ...`). A dry run does not check the target's request, and reports a trigger whose dispatches fail this way as one that would fire, so quote the `status_detail` instead. An empty history means the trigger never fired: run `roboto triggers dry-run <name>` for the entity that should have fired it, with the reference its event takes (`--file-id` for a file event; `--dataset-id` is refused there). Either way there is no invocation to debug: report the result, and say that fixing the trigger belongs to the `create-roboto-trigger` skill.
- **A session:** for one that is not finishing ingestion, its ingestion status names each pending file's latest ingestion invocation. For an action run on a session, query invocations on `input.session_id`.
- **A symptom across many runs:** query recent invocations by `last_status` and pick one representative failure.

As of the `verified-on` date, a Python action's invocations did not appear in invocation queries, so `list-invocations` and the invocation queries above can return nothing for one. Take its ID from the user, from the output of the command that started it, or from the trigger's dispatch history; `invocations show`, `status`, and `logs` find it by ID.

If several invocations match and the user did not say which, list them with their status and creation time and ask.

### Step 2: Read the status history

```bash
roboto --suppress-upgrade-check invocations status <invocation_id>
```

This prints the `status` list as JSON: each transition with its status name, timestamp, and `detail`. Read it first and note three things:

- **Whether a verdict exists.** If the current status is not Completed, Cancelled, Failed, or Deadly, the invocation is still live: do not diagnose it as failed. If it has been live longer than the user expects, take the "Hung" step of `references/triage.md`, or follow it with `roboto invocations status <id> --tail`.
- **The last status reached before the end.** This localizes the fault before any log is read.
- **Every `detail`, verbatim.** The terminal detail often states the cause outright: the container that failed and its exit code, a timeout, an out-of-memory kill, or who cancelled it.

### Step 3: Read the record

```bash
roboto --suppress-upgrade-check invocations show <invocation_id> | python3 -m json.tool
```

`show` prints the whole record as JSON on one line, so pipe it through a formatter. It gives statuses as numbers (`last_status`, and each entry of `status`); the "Status vocabulary" table in `references/invocation-api.md` maps them to names. Read what the invocation was asked to do; `references/invocation-api.md` ("Record fields") lists each field. The ones that settle most cases are `provenance` (the action digest that ran, and the trigger that started it, if any), `rich_input_data` against `resolved_input_data` (what was asked for, and what it ran on), `upload_destination`, `parameter_values`, and `timeout`. A missing parameter or no upload destination is visible here before any log is opened. As of the `verified-on` date, `resolved_input_data` was `null` on a container action's invocations even when setup resolved and downloaded files; the `setup` log's `Looking up ...` and `Downloading {<n>} file(s) ...` lines then say what it ran on, and a selection that resolved to nothing shows there.

### Step 4: Read the logs

```bash
roboto --suppress-upgrade-check invocations logs <invocation_id>
```

The output has one section per process that logged something, each under a `========== <process> ==========` header: `setup`, `action`, `output_handler`, and possibly `monitor` or `firelens_log_router`. A process that logged nothing has no header at all. A Python action's log is its script's stdout and stderr. Read the section that matches where Step 2 says the invocation stopped: its end first, then its start, then only the middle lines the hypothesis depends on. No `action` section means the action's code never ran or logged nothing at its level, which for a run started with `roboto actions invoke` is `ERROR` by default (`references/triage.md`, Step 7), so read the `setup` section and the status history before concluding anything from that silence.

## Phase 2 — Diagnose

### Step 1: Localize

Take the last status, the terminal detail, and the log section into `references/triage.md`. It maps each combination to a fault domain and to the evidence that would confirm it. State the result before going on: the fault domain, the evidence for it, and whether that evidence is direct (a detail or log line that names the cause) or inferred.

### Step 2: Reproduce

A cause is a hypothesis until a detail or log line states it, or a reproduction shows it. Skip reproduction only when the evidence is direct, and say that you skipped it and why.

For a container action whose project is available, reproduce locally from the project directory, with the failing invocation's parameters and the narrowest input that still fails. Run `docker info` first. `invoke-local` attaches its container to a terminal, so from a non-interactive shell it exits after building the image unless you supply a pty, and its own exit status does not carry the container's, so read the output:

```bash
case "$(uname -s)" in
  Darwin) script -q /dev/null roboto --suppress-upgrade-check --log-level=debug actions invoke-local --dry-run <input flags> -p <name>=<value> ;;
  *)      script -qec "roboto --suppress-upgrade-check --log-level=debug actions invoke-local --dry-run <input flags> -p <name>=<value>" /dev/null ;;
esac
```

Take the input flags from `rich_input_data`: `--dataset` with `--file-path`, or `--file-query`, `--topic-query`, `--session-id`, `--session-query`. Only `--dataset` gives the run a dataset, so an action that touches `InvocationContext.dataset` fails under any other selection, locally and hosted alike.

Local reproduction is not available for a Python action, which has no image to run, for an action whose source the user does not have, or for a cause that depends on hosted compute (memory, storage, timeout, network access). For those, the reproduction is a hosted re-run that changes one variable, which is Phase 4 run early with the user's yes. Say which variable you changed and why.

## Phase 3 — Fix

The fix goes where the cause is, and the cause is not always a defect:

- **The action's code, image, or `action.json`.** Make the smallest change aimed at the confirmed cause. Do not refactor around it; an unrelated change in the same diff makes Phase 4 prove less than it appears to.
- **The invocation's inputs, parameters, compute, or timeout.** The action is correct and the request was wrong. The fix is a different invocation, or a change to the trigger target that produced it, which the `create-roboto-trigger` skill handles.
- **The data.** The action correctly rejected bad input (exit code 65 by the runtime's convention). The fix is upstream of Roboto, and the deliverable is a report.
- **The expectation.** The invocation did what it was configured to do. Say so directly.

When the fix is a decision, ask the user and wait: whether to accept malformed input, whether to raise memory or the timeout and pay for it, whether to skip a bad file or fail the run, whether to open network access for a Python action. Lead with your recommendation. Under `--yolo`, choose the option that fails visibly rather than silently, and record the choice for the report.

Keep the fix reviewable as its own diff when the source is under version control.

## Phase 4 — Prove

A fix that has not been re-run is a hypothesis. This phase runs under `--yolo` too.

1. **Get the fix onto the platform.** A hosted run uses the deployed action, not your working tree, so a re-run before redeploying fails the same way and reads as "the fix did not work". For a container action, give the project's deploy command (for a project from `roboto actions init`, `./scripts/deploy.sh`); for a Python action, publishing a new version from its page in the web app is the redeploy. A trigger set to an exact action version or digest keeps running the old code until it is changed. Deploying is the user's call: ask, and wait.
2. **Re-invoke on the same inputs**, not a smaller or cleaner one. When the fix is the request itself (a selection, a parameter, the timeout), change only the part the cause names and keep the rest. `references/invocation-api.md` ("Re-running on the same inputs") gives the CLI form and an SDK script that copies the original record. Do not reuse its `idempotency_id`; the platform refuses a second invocation with the same one. Give the exact command, and run it only after the user says yes.
3. **Verify the way you diagnosed.** Follow the new invocation to a terminal status with `roboto invocations status <new_id> --tail`, then read its record and logs. Confirm that the new run took the same files, sessions, or topics as the original: compare `resolved_input_data` where both records have it, and otherwise the `setup` log's `Looking up ...` and `Downloading {<n>} file(s) ...` lines. Confirm that the log shows the work happening. A Completed run that processed nothing has proved nothing.
4. **Compare the two invocations.** Old ID, new ID, what changed between them, and what the status history and logs now show.

If the re-run fails differently, the first cause is fixed and a second is now visible: go back to Phase 2 with the new evidence. If the re-run cannot happen (no permission to deploy, the input is gone, the action belongs to another org), say exactly what is unproven and give the command that would prove it. Do not report an unverified fix as a fix.

## Phase 5 — Hand off

When the deliverable is a report rather than a fix (an action you could not change, a cause in the data, a trigger that never fired), say so in the first line. Then report:

1. **What failed:** the invocation ID, the action and digest, the terminal status, and the terminal detail, quoted.
2. **The cause:** one sentence naming the fault domain and the specific defect, decision, or datum.
3. **The evidence:** the detail, log lines, or record fields the cause rests on, quoted. Say whether it was reproduced or inferred, and name what remains uncertain.
4. **Decisions made:** each one marked as a user answer or a `--yolo` judgment, with the alternatives.
5. **The proof:** the exact commands run, the original and new invocation IDs, and what the re-run showed. Or, if Phase 4 could not run, what is unproven and the command that would settle it.
6. **Open items:** anything found that was not the cause, such as an action that logs nothing below error level or a timeout that larger input will exceed. List them; do not fix them unasked.

Then add one or two lines naming the sources verified against (page URL, SDK version, the action image's SDK version if known) and anything not verified. Give every command that writes to the org without running it, and say why. If the fix changed how the action should be triggered, add one line: "To change when the action runs, the `create-roboto-trigger` skill creates and verifies the trigger."
