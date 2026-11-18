---
name: create-roboto-issue-sync-action
description: >-
  Build and verify a Roboto Action that files findings from Roboto (session or
  dataset tags, AI summaries, events, metadata) as issues in a tracker such as
  GitHub, GitLab, Jira, or Linear, and updates the same issue on every re-run
  instead of filing a duplicate. Use this skill whenever results in Roboto should
  reach the place work is tracked, even if the user only describes the outcome
  ("open a ticket when a flight fails triage", "our engineers live in GitHub, not
  Roboto", "sync the session summary to Jira"). Covers the identity decision, an
  ambiguity-resolving interview (skipped under --yolo), scaffolding,
  implementation, and verification by running twice against a scratch tracker
  project and counting the issues. Not for writing the analysis that produces the
  findings (use the create-roboto-action skill), not for running the action
  automatically (use the create-roboto-trigger skill), and not for general Roboto
  questions or one-off scripts (use the roboto-guide skill).
license: MPL-2.0
compatibility: >-
  Needs a shell and network access to www.roboto.ai, pypi.org,
  files.pythonhosted.org, raw.githubusercontent.com, api.github.com, and the
  issue tracker's API. Needs uv (or Python 3.10+ with pip), the roboto CLI, and
  Roboto credentials. Needs Docker and Git for local invocation and the action
  template, and a writable scratch project in the target tracker.
metadata:
  verified-sdk: "0.64.0"
  verified-on: "2026-11-18"
argument-hint: <which findings become issues, in which tracker> [--yolo]
---

Build an action that turns findings already stored in Roboto into issues in the user's tracker, and that leaves exactly one issue per finding however many times it runs. The standard is the tracker's issue list after two runs, not the action's log.

## What you need to run this

This skill does not know which agent is reading it, so it names the capabilities it needs rather than assuming them:

- **Run shell commands** and read their output.
- **Read and write files.**
- **Hold a back-and-forth with the user.** Phase 1 is an interview, and the identity decision is theirs.
- **Fetch a web page.** The tracker's REST API documentation is not bundled here. `curl` does the same job if there is no fetch tool.

uv is the preferred runner because it resolves the latest SDK on every run. Without uv, build one virtual environment for the session (`python3 -m venv`, then `pip install --upgrade 'roboto[analytics]'`) and use its interpreter wherever this file says `uv run`.

Do not test through a tracker tool only you can call, such as an MCP server in your harness: the action calls the tracker from inside its container, and nothing outside it proves that works.

`references/` throughout means the directory alongside this file. Read `references/sync-api.md` and `references/authoring-rules.md` before Phase 1.

## The request

The user's description of what should become issues, and where, is the argument to this skill. Strip a `--yolo` flag from anywhere in it; what remains is the description. If the description is empty, ask the user which findings should reach which tracker and stop.

`--yolo` suppresses the Phase 1 interview and nothing else. The preflight, the verification gates, the Phase 5 edit pass, and the recording of decisions all stand: every ambiguity resolved by judgment lands in `SPEC.md` with its rationale, so the user audits the decisions after the fact instead of before.

`--yolo` never authorizes a write to the user's organization or tracker. Creating a secret, a run without `--dry-run`, deploying, and invoking on hosted compute stay the user's call: give the exact command and wait for a yes.

A request to bring issue state back into Roboto (close an issue, clear a tag) is a different action that reads the tracker on a schedule. Say so and stop, unless the user wants the one-way sync. Having Roboto's AI file issues itself is an MCP connection (the docs page "Connect MCP Servers to Roboto"), not an action.

## Sources, in order of authority

Three sources outrank every file in this skill. They are numbered by authority: when two disagree, the lower number wins. Start with the source whose Answers column fits the question, and stop at the first source that answers it.

| Source | What | How | Answers |
|---|---|---|---|
| 1 | The latest released SDK and CLI, resolved fresh from PyPI | `uv run --no-project --isolated --refresh-package roboto --with 'roboto[analytics]' python -c "import inspect, roboto; print(inspect.signature(roboto.InvocationContext.get_optional_parameter))"`; for CLI flags, `uv run --no-project --isolated --refresh-package roboto --with roboto python -m roboto.cli actions invoke-local --help` | Exact signatures, parameter names, defaults, enum members, docstrings, CLI flags |
| 2 | The Roboto docs at www.roboto.ai/docs | Fetch `https://www.roboto.ai/docs/<path>.md`; see "Docs lookups" | Concepts, how-tos, RoboQL fields, REST endpoints |
| 3 | The SDK CHANGELOG and GitHub releases | Fetch https://raw.githubusercontent.com/roboto-ai/roboto-python-sdk/refs/heads/main/CHANGELOG.md and https://api.github.com/repos/roboto-ai/roboto-python-sdk/releases/latest | Which release added or changed a behavior; the latest version number |

Every lookup of the latest release runs with `--no-project --isolated`, so that a `uv run` started inside a Python project or virtual environment neither uses the `roboto` installed there (an older pinned release, for example) nor writes a `uv.lock` into the project, and with `--refresh-package roboto`, so that it does not reuse PyPI's answer from up to ten minutes earlier and miss a new release.

The files under `references/` rank below all three. The `metadata` block in this file's frontmatter records the SDK release (`verified-sdk`) and date (`verified-on`) they were last checked against. When Phase 0 finds a newer release, re-check anything you take from them against source 1 before using it. Cite the live source, not the reference file.

**Docs lookups.** To find a page, fetch `https://www.roboto.ai/docs/llms.txt`, which lists every page with its URL. To read one, fetch its Markdown copy by adding `.md` to the URL (`https://www.roboto.ai/docs/learn/actions.md`); without a fetch tool, `curl -sL <url>`. To find where an SDK symbol is documented, search `https://www.roboto.ai/docs/reference/python-sdk/objects.json` for its dotted name. For REST endpoints, read `https://www.roboto.ai/docs/reference/rest-api/openapi.json`. These files are large, so read them through a search (`grep`, or a Python one-liner) rather than printing them whole. If the agent runtime can start a subagent, run lookups in one and return only the answer.

The tracker has its own order. Its API responses, from the instance the user named, outrank its documentation: cloud and self-hosted versions, API versions, and plan tiers differ, so a documented field can be absent or rejected on the instance in front of you. Fetch the documentation this session to shape the first request, then trust what comes back.

- **The installed CLI and SDK are not authoritative.** They are whatever version the user last installed, and `roboto <command> --help` describes that version and nothing else. If the CLI is behind the latest release, say so and point to `roboto upgrade` (CLI 0.58.0 and later); on an older CLI, `brew upgrade roboto`, or replacing the binary or `.deb` from the latest release.
- **A copy that will run is the authority on what it does.** After Phase 2, the SDK in the project's `.venv` is the code that runs in the container. Read its version with `.venv/bin/python -c "from roboto.version import roboto_version; print(roboto_version())"` and record it in `SPEC.md`. If it is behind source 1, say what differs; never lower source 1 to match it.
- **A docs page can be ahead of the release, or wrong about it.** When source 2 describes something source 1 lacks, source 3 says whether it is released. Build against the release, and tell the user what is coming. The secrets page, for example, shows `from roboto import Secret`, which raises `ImportError` in the release recorded as `verified-sdk`; the import that works is `from roboto.domain.secrets import Secret`.
- **Recommend the API that fits the task.** Sessions are imported from `roboto.experimental.sessions`; that import path is not a reason to sync from datasets instead. When the findings are about a flight, drive, or run, the session is the entity to read and stamp.

Where a source cannot be reached, say which one, and tell the user what you could not check. When there is no fetch tool and no `curl`, ask the user to paste the page.

## Phase 0 — Preflight

Run this before the interview. Every check below guards a step that would otherwise fail after the user has spent time answering questions and you have written the whole action.

```bash
uname -s                                             # platform; decides the Phase 4 pty form
roboto --version                                     # installed CLI; compare with the latest release below
uv --version                                         # runner for source 1
docker info                                          # daemon reachable, not merely installed
git --version                                        # roboto actions init needs Git
roboto --suppress-upgrade-check users orgs           # credentials valid; one JSON object per org
curl -s https://pypi.org/pypi/roboto/json | python3 -c 'import json,sys; print(json.load(sys.stdin)["info"]["version"])'
```

- **`users orgs`** fails without valid credentials and otherwise prints one JSON object per organization. With more than one, every `invoke-local` and the deploy need `--org`; carry the list forward. Never read `~/.roboto/config.json` to check credentials, and never print a token.
- **The latest release.** If it is newer than `verified-sdk`, tell the user the references predate it.
- **The platform.** macOS and Linux; Windows is untested.

Then the checks specific to syncing:

- **A scratch project in the target tracker**, writable and watched by nobody. Every gate in Phase 4 files real issues.
- **A token that can create and edit issues there**, held in an environment variable. A read-only token passes the read call below and fails only on create.
- **One real read call** to confirm the base URL, the project identifier form, and the token together, with the auth header and list endpoint from the tracker's documentation:

  ```bash
  curl -sS -o /dev/null -w '%{http_code}\n' -H "<auth header>: $TRACKER_TOKEN" "<issue-list endpoint for the scratch project>"
  ```

  Fix a non-2xx status now. It usually separates a bad token (401), a missing permission or hidden project (403 or 404), and a wrong base URL.
- **The findings exist.** Pick a real session or dataset with the user and print its findings with the read-only script in `references/sync-api.md` ("Where findings come from"). An action that syncs findings nothing produces cannot be verified.
- **The link form.** Build one link as `references/sync-api.md` ("Links") describes and open it in a browser, or ask the user to. If it does not land on the entity's page, ask for their web app's address.

If a check fails, stop and tell the user exactly what to install or run. Do not begin the interview.

## Phase 1 — Decompose and resolve

### Step 1: State the mapping

Before asking anything, write the mapping in one sentence: *one `<session | dataset | file | event>` with `<finding>` becomes one issue in `<project>`, titled `<pattern>`, carrying `<content>`, labelled `<labels>`.* If you cannot write it, the gap is in the mapping, and it is Step 2's first question.

### Step 2: Find the ambiguities

Resolve an axis that turns on a platform capability against the sources, not by asking the user.

| Axis | What is undetermined | Consequence of guessing wrong |
|---|---|---|
| **Identity** | What makes an issue the same issue next run: one session, one dataset, one file, one event? | Every re-analysis files a duplicate (rule 5) |
| Stamp location | Which entity's metadata records the issue | Decides whether the link survives and is visible from Roboto |
| Input | How the invocation reaches that entity: a session input, a dataset, a file, an event | `context.dataset` raises under a session input (rule 4) |
| Finding source | Tags, AI summary, events, metadata, or a mix | Decides the SDK calls; a summary can still be generating (rule 15) |
| Content | Which findings go in the body, and as prose or a table | An issue nobody reads is worse than none |
| Labels | Which findings become labels, under what naming scheme | Trackers differ on unknown labels (rule 14) |
| Clean result | What a run with no findings produces | Three defensible answers with very different issue lists (rule 9) |
| State | Close when a finding clears, reopen when it returns? | Decides whether the open-issue list means anything |
| Assignment | Assignee, milestone, or project field | Often the reason the team asked for the sync |
| Unconfigured | What happens when the tracker parameters are absent | Degrading keeps the action testable without a tracker (rule 16) |
| Failure posture | Tracker unreachable or rejecting: fail the invocation, or log and continue? | Decides whether a tracker outage fails every triggered run |
| Invocation mode | Manual, or a trigger on which platform event | A trigger on a metadata-updated event can fire on the action's own stamp (rule 19) |

### Step 3: Resolve

**Without `--yolo`:** interview the user on identity, clean result, content, and failure posture; the other axes usually follow from those. Batch the questions, lead each with your recommendation, and use a multiple-choice prompt where your harness offers one. Ask only what changes the build.

**With `--yolo`:** resolve every axis yourself. Identity at the coarsest entity the findings describe (the session when the findings are about a run), the stamp on that entity's metadata, a closed record for a clean result, state kept in sync on re-runs, a logged preview when unconfigured, and log-and-continue on tracker failure. Mark each as a default in `SPEC.md`.

Settle the action name too. It becomes the Roboto identifier and the directory name, so make it a verb phrase: `file-triage-issues`, not `tracker-tool`.

### Step 4: Confirm the plan

State the mapping sentence, each resolved axis, the file-by-file plan, and the verification you will run, including that Phase 4 files real issues in the scratch project and writes the stamp onto a real entity. Under `--yolo`, present it and continue; otherwise wait for the go-ahead.

## Phase 2 — Scaffold

Never hand-write the project layout. `roboto actions init` downloads Roboto's action template from GitHub and reads four answers from stdin: name, description, input type (`1` files, `2` topics), and whether to initialize git. Answer `1`, since you replace the example body, and `y`:

```bash
printf '%s\n' '<Action Name>' '<description>' '1' 'y' \
  | roboto --suppress-upgrade-check actions init <existing-parent-dir>
```

Do not scaffold into a directory that holds an unrelated project. From the new project root, run `./scripts/setup.sh`, read the generated `DEVELOPING.md` (the authority on the project's own workflow), and record the `.venv` SDK version.

## Phase 3 — Implement

List every SDK member the plan depends on and check each against the `.venv` SDK with `inspect.signature` before writing the call. Then write, following `references/sync-api.md` ("The tracker client" and "The sync decision"):

1. **`action.json`**: the tracker parameters (base URL, project, the token, labels, the web app address for links), each with `required` and `default` per Phase 1, and `requires_downloaded_inputs: false`, since the action reads records, not file contents (rule 22). A parameter has only `name`, `required`, `description`, and `default`; there is no secret flag. The token parameter is an ordinary one with no default, and a `roboto-secret://` URI is passed as its value at invocation (rule 11).
2. **A tracker client module**: create, fetch one, update, and set state, each with a timeout and each returning a result instead of raising (rules 17 and 20).
3. **A rendering module**: plain values in, title and body out, with every `roboto://` reference rewritten to a link (rule 13).
4. **`main.py`**: set the log level, read and validate parameters, resolve the entity from the input, read the findings, read the stamp, decide, then call the client and write the stamp, both gated on `not context.is_dry_run` (rule 2). Keep `main` an orchestrator; the decisions live in functions that take plain values.
5. **`pyproject.toml`**: the HTTP client library in the runtime dependencies, not `dev`.
6. **`test/test_main.py`**: keep the shipped signature test and add one test per branch of the sync decision, each with a fake client and no network (rule 23).
7. **`SPEC.md`**: first the identity rule (what makes an issue the same issue, where the stamp lives, what a clean result produces), then the mapping sentence, the resolved axes with their rationale, the failure behavior, and a verification table left pending for Phase 4.
8. **`README.md`**: what the action does, its parameters, how to store the token, and how to invoke it. Point to `SPEC.md` for intent.

Apply every rule in `references/authoring-rules.md`. The generated project documents itself and never mentions this skill, its phases, or `--yolo` (rule 21).

## Phase 4 — Verify

Run three steps from the project root. The property under test is that **two runs leave exactly one issue**.

### Step 1: Lint and tests

If Phase 3 touched `pyproject.toml`, re-run `./scripts/setup.sh` first. Then run `./scripts/verify.sh`, and fix what it reports until it passes.

### Step 2: A local dry run

`invoke-local` attaches its container to a terminal, so from a non-interactive shell supply one with `script`, whose arguments differ by platform:

```bash
case "$(uname -s)" in
  Darwin)
    script -q /dev/null \
      roboto --suppress-upgrade-check --log-level=info actions invoke-local --dry-run <args>
    ;;
  *)
    script -qec \
      "roboto --suppress-upgrade-check --log-level=info actions invoke-local --dry-run <args>" \
      /dev/null
    ;;
esac
```

`<args>` is `--session-id se_...` or `--dataset ds_...` (alone, it sets the dataset with no file input), each parameter as `-p name=value`, the token as `-p tracker_token=roboto-secret://<secret-name>`, and `--org` for a multi-org user. The secret must exist first; `references/sync-api.md` ("Parameters and secrets") creates it without putting the token in `argv`, and running that is the user's call. Read the log: the action found the entity, read the findings, took the expected branch, and logged the issue it would file, writing nothing (rule 2). Judge every `invoke-local` run by its log, not its exit status: it exits 0 when the action raises, and also when the container never starts, as it does without a terminal ("cannot attach stdin to a TTY-enabled container because stdin is not a terminal").

### Step 3: Real runs against the scratch project

These write the stamp and file issues, so show the user the exact command (Step 2's, without `--dry-run`) and wait for a yes. After each step, read the tracker's issue list, not the log; the log records what the action believed, which is what is under test.

1. **First run.** One issue exists, with the title pattern, the findings, the link back to the entity, the labels, and the state the clean-result posture requires.
2. **The stamp.** The entity's metadata carries the issue identifier and URL. Read it with a script; the CLI has no command that shows a session.
3. **Second run, nothing changed.** Still exactly one issue, updated in place. This is the gate.
4. **A changed finding.** With the user's agreement, change one finding on the entity, run, and confirm the body, labels, and state follow it.
5. **Deleted issue.** Delete the issue in the tracker and run. A new issue exists, the stamp points at it, and nothing raised.
6. **Unconfigured.** Run without the tracker parameters. The action does what Phase 1 decided (rule 16).
7. **Bad token.** Point the token parameter at a second secret holding an invalid value (creating it is the user's call). The failure posture holds, and the token appears nowhere in the log (rule 12). A URI naming a secret that does not exist fails before the action starts, with "Failed to retrieve secret"; that tests the secret store, not the action.

`invoke-local` runs under the placeholder invocation ID `inv_LOCAL_DOCKER_INVOCATION`, so the link to the invocation in the issue body can be checked only on the first hosted run. Say so in `SPEC.md`.

Record each run in `SPEC.md`'s verification table with the command, the entity, and the issue it produced. Then delete the test issues, or tell the user where they remain. If a gate cannot run, stop and say what blocks it. Do not report an unverified action as working.

## Phase 5 — Edit pass

Review the files you wrote in Phase 3, not the template's `bin/entrypoint.py`, `logger.py`, or `scripts/`:

1. **API truth.** Every SDK call matches the `.venv` signature, and every tracker field matches a response you saw in Phase 4.
2. **No literals.** No token, project identifier, instance URL, or org ID is written into the repository; `grep` for the scratch project's identifier and the tracker host.
3. **Names and comments.** Function names say what they decide; comments say why, not what.
4. **The diff.** Read `git diff` once from the top and confirm every change belongs to the Phase 1 plan.

Fix what you find rather than listing it, then re-run Phase 4 Step 1. Escalate only a fix that would contradict a user decision.

## Phase 6 — Hand off

Report:

1. **What the action does**: the mapping sentence and the path to the project.
2. **The identity rule**: what makes an issue the same issue, and where the stamp lives.
3. **Decisions made**: each resolved axis, marked as a user answer or a `--yolo` judgment.
4. **Verification**: each gate with its command, the entity used, and the issue it produced, and whether the scratch project was cleaned up. Name any gate that did not run and why.
5. **The credential**: which permission it needs, which secret holds it, and that rotating it means updating the secret, not redeploying.
6. **Open items**: anything escalated from Phase 5, the hosted-only invocation link check, and that nothing flows back from the tracker into Roboto.

Then give, without running them, the deploy command, `./scripts/deploy.sh [ROBOTO_ORG_ID]`, which pushes an image and creates or updates the action in the user's org, and a first hosted run on one entity the user picks, in the real project: `roboto actions invoke <action-name> --session-id se_... -p ...` (or `--dataset ds_...`). Keep that run to one entity: the cleanup after a wrong first run is somebody closing issues by hand.

To run the action automatically, the `create-roboto-trigger` skill creates and verifies the trigger; the number of entities the trigger matches is the number of issues that will appear. For a session-keyed action the next command, created disabled and unrun, has this shape:

```bash
roboto triggers create --name <action-name>-on-ingest --on session.ingested --once-per occurrence --disabled \
  --targets-json '[{"type": "invoke_action", "target_id": "sync", "action": {"name": "<action-name>"}, "invocation_input": {"sessions": {"ids": ["{{session.session_id}}"]}}, "parameter_values": {"tracker_token": "roboto-secret://<secret-name>"}}]'
```

End with one or two lines naming the sources verified against (page URLs, the `.venv` SDK version, the tracker instance) and anything not verified.
