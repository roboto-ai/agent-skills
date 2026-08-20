---
name: create-roboto-trigger
description: >-
  Create a verified Roboto Trigger that invokes an existing action automatically when
  data arrives or on a schedule. Use this skill whenever the user wants data processed
  without manual invocation even if they only describe the outcome ("ingest every bag as
  it lands", "run the diagnostic once a file finishes ingesting", "summarize the fleet
  nightly") without saying "trigger". Covers decomposition, an ambiguity-resolving
  interview (skipped under --yolo), authoring the trigger as a reproducible script,
  and verification by reading real trigger evaluation records. Not for writing the
  action itself (use create-roboto-action) and not for debugging a trigger that already
  fires correctly.
license: MPL-2.0
compatibility: Requires the roboto CLI (authenticated) and a Python environment with the roboto SDK installed
argument-hint: <natural-language description of what should run automatically, and when> [--yolo]
---

Turn "this should happen by itself" into a trigger that provably fires on the data it should, provably skips the data it should not, and is reproducible from a file in version control rather than from a command someone typed once.

## What you need to run this

This skill does not know which agent is reading it, so it names the capabilities it needs rather than assuming them:

- **Run shell commands** and read their output.
- **Read and write files.**
- **Hold a back-and-forth with the user.** Phase 1 is an interview.
- **Fetch a web page.** Used to check the trigger surface against `docs.roboto.ai`. Without it, say so and use the fallback described under Ground truth.

Nothing beyond that. No plugins, no external tool servers (such as MCP servers), no sub-agents, no symbol-level code intelligence. Where a step below reads like it names a specific tool, it names the capability; use whatever your harness provides for it.

`references/` throughout means the directory alongside this file. Read `references/trigger-api.md` and `references/authoring-rules.md` before Phase 1. They carry the API surface, the evaluation-outcome vocabulary that Phase 4 reads, and the failure modes that Phase 1's questions exist to prevent.

## The request

The user's description of what should happen automatically is the argument to this skill. Strip a `--yolo` flag from anywhere in it; what remains is the description. If the description is empty, ask the user what should run automatically and stop.

`--yolo` suppresses the Phase 1 interview and nothing else. The preflight, the verification gate, the review pass, and the recording of decisions all stand: every ambiguity resolved by judgment lands in `SPEC.md` with its rationale, so the user audits the decisions after the fact instead of before.

`--yolo` never skips Phase 6's confirmation. Enabling a trigger is the one irreversible-in-effect step in this skill, and it stays the user's call.

## A trigger is not an action

This skill assumes the action already exists and is deployed. If the user is describing work no action performs yet, say so and point them at `create-roboto-action`; a trigger for an action that does not exist cannot be created, let alone verified.

Two distinct platform objects answer to the word "trigger", and picking the wrong one is not recoverable by editing fields:

- **`Trigger`** — event-driven. Roboto evaluates it when something happens to your data (a file is uploaded, a file finishes ingesting, metadata changes). This is what `roboto triggers` manages.
- **`ScheduledTrigger`** — time-driven. It fires on a cron schedule regardless of data activity, and it is a separate SDK class with its own fields (`schedule`, `next_occurrence`, `invocation_input`). The `roboto triggers` CLI commands do not manage it.

Phase 1's Timing axis settles which one you are building. Everything from Phase 2 on is written for the event-driven `Trigger`; when the answer is a schedule, follow the same phases but read `ScheduledTrigger` in `references/trigger-api.md` for the surface, and adapt Phase 4's gate as that section describes.

## Ground truth

The Roboto SDK moves faster than any file in this skill. Never write an SDK call, a CLI flag, or an enum member from memory. Confirm each against a live source in this session.

| Rung | Source | How | When it wins |
|---|---|---|---|
| 1 | The installed SDK | `python -c "import roboto, inspect; from roboto.domain.actions import Trigger; print(inspect.signature(Trigger.create))"`, or read its source under `site-packages/roboto/domain/actions/` | Highest authority: it is the code that will run |
| 2 | The CLI's own help | `roboto triggers create --help`, `roboto triggers update --help` | Authoritative for which flags exist, which are required, and what each defaults to |
| 3 | `docs.roboto.ai` | Fetch the durable URLs listed in `references/trigger-api.md` | Authoritative for concepts, causes, and worked examples |
| 4 | `references/trigger-api.md` | Read it | Lowest authority: a map for running the interview, not a citation |

Unlike an action project, a trigger has no scaffold and therefore no project venv. Rung 1 means the Python environment that will run the script you write in Phase 3. Establish which one that is during Phase 0 and use it consistently; a trigger authored against one interpreter and run under another is a version mismatch waiting to surface as a `TypeError` on an argument that does not exist.

**A docstring is prose, not code.** Rung 1 outranks the other rungs because it is the executable truth, but the docstrings inside it are neither executed nor tested, and the trigger surface has at least one example that references members which do not exist. Confirm every enum member you rely on by reading the enum, not by trusting an example that uses it. `references/trigger-api.md` lists the members that exist at the time of writing; the enum in the installed SDK settles it.

If you have no way to fetch a web page, rung 3 is unavailable. Rungs 1 and 2 are both local and answer most questions here, so this is a milder constraint than it is for an action. Tell the user which concept pages you could not read and continue.

Record in `SPEC.md` the SDK version you built against:

```bash
python -c "from roboto.version import roboto_version; print(roboto_version())"
```

`roboto.__version__` does not exist; reaching for it wastes a lookup.

## Phase 0 — Preflight

Run this before the interview. Every check guards a step that would otherwise fail after the user has spent time answering questions.

```bash
command -v roboto                                    # CLI on PATH
roboto --suppress-upgrade-check users orgs           # credentials valid; enumerates your orgs
python -c "from roboto.domain.actions import Trigger; print('sdk ok')"   # SDK importable
roboto --suppress-upgrade-check actions search       # the target action exists and is deployed
```

Three results need more than the comments carry:

- **`users orgs`** doubles as the credential check and the org inventory. If the user belongs to more than one organization, every later command needs `--org` or `caller_org_id`; carry the list forward rather than rediscovering it. Do not read `~/.roboto/config.json` to check credentials; it holds a plaintext token.
- **The SDK import** establishes rung 1. Note which interpreter answered, and use that same one in Phase 3.
- **`actions search`** must show the action the description implies, in an org the user can invoke it from. A trigger names its action by name, so a typo or an undeployed action produces a trigger that is created successfully and then never does anything useful. Confirm the exact name, and note whether the action is owned by the user's org or another one — the latter needs the owner's org id alongside the name.

Also read the target action's parameters now, since Phase 1's Parameter axis needs them:

```bash
roboto --suppress-upgrade-check actions show <action-name> --org <org-id>
```

Organizations cap the number of active triggers. A create can therefore fail on a quota rather than on anything wrong with the trigger. Do not quote a number; if a create fails that way, point the user at their organization settings.

If a check fails, stop and tell the user exactly what to install or run. Do not begin the interview.

## Phase 1 — Decompose and resolve

### Step 1: Decompose the description

Turn the description into a requirements table before asking anything. Each row is one testable behavior in the present tense: "invokes `ros_ingestion` once per `.bag` file uploaded to a dataset tagged `production`", not "handles bags".

Write the rows so Phase 4 can test them. A requirement that cannot be stated as "given this data event, the trigger fires / does not fire" is not a trigger requirement; it belongs to the action.

Then classify each requirement as **stated**, **implied** (the goal is unreachable without it, and only one reading is plausible — record the inference), or **ambiguous** (more than one reading changes what gets built).

### Step 2: Find the ambiguities

Walk these axes. Each is a decision that changes the created trigger, so an unresolved one becomes a guess that fires — or fails to fire — in the user's org.

| Axis | What is undetermined | Consequence of guessing wrong |
|---|---|---|
| Timing | Data event or recurring schedule? | Picks `Trigger` or `ScheduledTrigger`; the wrong one cannot be edited into the other |
| Cause | Which events evaluate the trigger — upload, ingest, dataset metadata, file metadata? | The single most common failure. An action that reads topic data must wait for `FileIngest`; on `FileUpload` it runs before ingestion and finds no topics |
| For-each | One invocation per dataset, or one per file? | Changes invocation count, cost, and the meaning of `required_inputs` (rule 4) |
| Required inputs | Which glob patterns must match? | `NoMatchingFiles`, the second most common failure. Patterns are matched against the file's path within the dataset |
| Additional inputs | Which files should be downloaded but not affect matching? | Context files the action reads but should not wait for |
| Condition | Which datasets are in scope, by tag or metadata? | No condition means the trigger runs on everything that matches the globs, across the whole org |
| Parameters | What values does the action need at invocation time? | The trigger fires and the action runs wrong, which is harder to notice than a trigger that never fires |
| Re-run posture | Should re-uploading the same data run it again? | Roboto skips with `AlreadyRun`; if the user expects reprocessing, that expectation is wrong and they should hear it now |
| Overrides | Different compute, or a longer timeout, than the action's defaults? | An action sized for manual use can time out under a trigger that feeds it larger inputs |
| Blast radius | How many datasets and files in the org match this today? | Determines whether enabling it is a quiet change or a large batch of invocations |

The Blast radius axis is a question you answer, not one you ask. Before Phase 6, run a search that approximates the trigger's own matching so the user learns the scale before the trigger is live:

```bash
roboto --suppress-upgrade-check datasets search --tag <tag> --metadata <key>=<value> --org <org-id>
```

Confirm those flags against `roboto datasets search --help` before running it, and note that this approximates the trigger's condition only — it does not apply the input globs, so treat the count as an upper bound and say so. Report it. Whether enabling a trigger causes Roboto to evaluate data that already exists is not something this skill asserts; Phase 4 settles it empirically for the case in front of you, and Phase 6 reports what was observed.

Also settle the trigger name if the description does not imply one. It is unique within the organization and is how every later command addresses the trigger, so it should read as the rule it encodes: `ingest-bags-on-upload`, not `trigger1`.

### Step 3: Resolve

**Without `--yolo`:** interview the user. Where your harness offers a structured multiple-choice prompt, use it for the axes with a small fixed set of answers (timing, cause, for-each, re-run posture); otherwise ask in prose. Use free-form questions for values only the user holds: glob patterns, tag and metadata keys, parameter values, the action name if Phase 0 found more than one candidate.

Batch related questions, and lead each with your own recommendation so the user confirms rather than composes. Carry anything the description already answered as a stated guess to confirm or correct, never as a settled fact.

Two answers deserve a warning the first time they come up, stated once with the concrete failure mode:

- An action that reads topic data, paired with the `FileUpload` cause, will run before ingestion finishes and find nothing.
- No condition, paired with a broad glob like `**/*`, makes the trigger fire on every matching upload anywhere in the org.

Then record whatever the user decides.

**With `--yolo`:** resolve every ambiguity yourself. Choose the option that keeps the trigger narrow and its misfires cheap: prefer the most specific glob the description supports over `**/*`, prefer a condition over none when the description names any scoping property, prefer `FileIngest` over `FileUpload` whenever the action reads topic data, and take the action's own compute defaults unless a requirement needs more. Mark each such choice as a default rather than a requirement when you record it.

### Step 4: Confirm the plan

State, compactly: the trigger name, the requirements table, each resolved ambiguity with its resolution, the blast-radius count, and the file you are about to write. Under `--yolo`, present this as what you are about to build and continue without waiting. Otherwise, get the user's go-ahead.

## Phase 2 — Choose the authoring surface

The CLI and the SDK do not expose the same trigger. Confirm the current state of both against rungs 1 and 2 rather than trusting this table, then choose:

| Need | CLI | SDK |
|---|---|---|
| Set `causes` explicitly | Not exposed by any flag | `causes=[...]` on `Trigger.create` |
| Create in a disabled state | Not exposed on `create` | `enabled=False` on `Trigger.create` |
| Conditions, globs, parameters, overrides, for-each | Yes | Yes |
| Reproducible from version control | Only as a shell command | A script that is the artifact |

**Default to the SDK.** Phase 4's gate requires creating the trigger disabled, and the Cause axis is the most consequential decision in Phase 1; a surface that cannot express either one turns both into whatever the server defaults to. Use the CLI only for a trigger whose cause genuinely does not matter, and say in `SPEC.md` that you accepted the default.

Whichever surface creates the trigger, **read the causes back** after creating it. The default set is a server-side decision this skill does not assert:

```python
print(trigger.record.causes)
```

If the returned set is not the set Phase 1 settled on, that is a finding for the final report, not something to paper over.

## Phase 3 — Author

The deliverable is a directory, not a command someone typed. Create it alongside the action's project when there is one, otherwise wherever the user keeps infrastructure:

```
triggers/<trigger-name>/
├── create_trigger.py       # idempotent: creates, or updates in place if it exists
├── <trigger-name>.json     # the trigger as the server returned it, from trigger.to_dict()
└── SPEC.md                 # from references/spec-template.md
```

Write `create_trigger.py` so that running it twice is safe and running it after an edit converges the live trigger to the file (rule 1). Create disabled (rule 2). Take the org id from an argument or the environment, never a literal. Apply every rule in `references/authoring-rules.md` that bears on this trigger.

Leave the verification rows in `SPEC.md` pending; Phase 4 fills them.

`<trigger-name>.json` is written after Phase 4, from the live trigger, so it records what the server actually built rather than what you asked for.

## Phase 4 — Verify

This is the difference between a trigger that looks right and one that fires. A trigger is not verified by reading it back; it is verified by making an event happen and reading the evaluation record Roboto wrote in response.

Every evaluation carries a `status`, an `outcome`, and — when the outcome is `Skipped` — an `outcome_reason` that names the misconfiguration precisely. That vocabulary is the whole gate. Read it in `references/trigger-api.md` and confirm the members against the installed enums (Ground truth).

### The positive path

1. **Create a scratch dataset.** Verifying against a dataset the user cares about means invoking a real action on real data.

   ```bash
   roboto --suppress-upgrade-check datasets create --org <org-id>
   ```

2. **Enable the trigger**, now that its blast radius is one empty dataset you just made.

3. **Produce the cause event.** Match it to the Cause axis: upload a matching file for `FileUpload`; upload and let ingestion finish for `FileIngest`; set a tag or metadata field for the metadata causes.

   ```bash
   roboto --suppress-upgrade-check datasets upload-files -d <ds_id> -p ./sample.bag
   ```

4. **Wait for evaluation to complete**, rather than sleeping a guessed interval:

   ```python
   trigger.wait_for_evaluations_to_complete()
   ```

5. **Read the evaluation.** `trigger.latest_evaluation()` returns the most recent record, and `Trigger.get_evaluations_for_dataset(dataset_id)` returns every evaluation any trigger performed for that dataset — the better call when you need to know whether your trigger was evaluated at all.

   A verified positive path is: `status` is the completed status, `outcome` is the action-invoked outcome, and `cause` is the cause you configured. Anything else is a failure to diagnose, not a result to report.

6. **Confirm the invocation exists and did the right thing.** `trigger.get_invocations()` yields the invocations this trigger produced. Take the newest, then:

   ```bash
   roboto --suppress-upgrade-check invocations status <invocation_id>
   roboto --suppress-upgrade-check invocations logs <invocation_id>
   ```

   An evaluation that invoked an action which then failed is a verified trigger and a broken pipeline. Report both facts separately.

### The negative path

Run it. A trigger that fires is half-verified; a trigger that fires on everything is a bug that only the negative test finds.

Produce an event that should **not** invoke the action — a file that matches no required input, or a dataset that fails the condition — and confirm the evaluation was skipped for the reason you expect. `NoMatchingFiles` and `ConditionNotMet` are different findings: the first means your globs are wrong, the second means your condition is. A negative path that skips for the wrong reason has verified nothing.

### When the gate fails

The `outcome_reason` names the fix. `references/authoring-rules.md` maps each reason to what to change; the mapping is what makes this skill's gate cheap to run and worth running more than once.

If the gate cannot run — no credentials, no invocable action, no way to produce the cause event — stop and tell the user what is blocking it and exactly what to run. Do not report an unverified trigger as working.

### Teardown

Delete the scratch dataset, and disable the trigger again if Phase 6 has not yet had the user's go-ahead to leave it live. Record every run in `SPEC.md`'s verification table: the event produced, the evaluation's outcome and reason, and the invocation id where one exists. One row per path exercised, including the negative one.

## Phase 5 — Review pass

Scope: `create_trigger.py` and `SPEC.md`. Three passes, in order.

1. **API truth.** Treat every SDK call, enum member, and CLI flag in the script and the spec as written from memory until confirmed against rung 1. Check that each enum member you named exists in the installed enum, since a plausible-looking member is exactly the failure mode the docstrings model.

2. **Spec-against-live.** Read `<trigger-name>.json`, the server's own record, and confirm every claim in `SPEC.md` matches it: causes, for-each, globs, condition, parameters, overrides. This is where a server default you did not intend becomes visible.

3. **Naming and idempotency.** The trigger name should state the rule it encodes; the script should converge rather than duplicate on a second run; no org id, dataset id, or token should be a literal in the file.

Fix what you find rather than listing it. Escalate to the final report only when a fix would contradict a decision the user made.

## Phase 6 — Enable and hand off

Verification ran against a scratch dataset. Going live is a separate decision, and it is the user's.

Report:

1. **What the trigger does** — one paragraph, and the path to the directory.
2. **Requirements coverage** — the Phase 1 table, each row mapped to the field that implements it.
3. **Decisions made** — every resolved ambiguity, marked as a user answer or (under `--yolo`) a judgment call.
4. **Server defaults observed** — anything the server returned that Phase 1 did not specify, `causes` above all.
5. **Verification** — the positive and negative paths, with outcomes and reasons. Name any gate that did not run and why.
6. **Blast radius** — the count from Phase 1, restated as what will likely happen when this goes live.
7. **Open items** — anything escalated from Phase 5.

Then give the enable command without running it:

```bash
roboto --suppress-upgrade-check triggers update <trigger-name> --enabled --org <org-id>
```

Enabling a trigger changes what happens to the user's data without further input from them, and its effects reach real datasets and real compute spend. Do not run it on the user's behalf, including under `--yolo`. Tell them the trigger is created, verified, and disabled, and that this command turns it on.
