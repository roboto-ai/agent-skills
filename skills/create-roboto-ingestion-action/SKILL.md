---
name: create-roboto-ingestion-action
description: >-
  Build and verify a Roboto Action that ingests a custom or unsupported log format,
  turning raw recordings into topics whose data can actually be read back. Use this
  skill whenever Roboto does not understand a file format the user has even if they
  only describe the symptom ("my logs upload but there's nothing to plot", "Roboto
  doesn't know my robot's format", "how do I get my proprietary logs into topics").
  Covers format decomposition, choosing between the DataFrame and low-level ingestion
  paths, implementation, and verification by reading the ingested data back as a
  dataframe. Not for formats Roboto already supports out of the box, and not for
  post-ingestion analysis.
license: MPL-2.0
compatibility: Requires the roboto CLI (authenticated), Docker, and a real sample file of the format being ingested
argument-hint: <description of the format to ingest, ideally with a path to a sample file> [--yolo]
---

Turn a format Roboto does not understand into topics, message paths, and data that `get_data_as_df` returns rows for — with the last clause being the whole difficulty.

## Read this first: what makes ingestion different

An ingestion action is an ordinary Roboto Action, so everything about scaffolding, authoring, local verification, and deployment is already covered by **`create-roboto-action`**. This skill does not repeat that machinery. It supplies the three things that are specific to ingestion:

1. **The interview that decomposes a file format** into topics, message paths, timestamps, and units.
2. **The ingestion contract** — which SDK path to write through, and the failure mode that makes an ingestion action look successful while producing nothing readable.
3. **A verification gate that reads the data back**, which is stronger than any gate a general action can offer.

**Use both skills together.** Where a phase below says "delegate", follow the corresponding phase of `create-roboto-action` and return here. If that skill is not installed, this one still works: the delegated phases are ordinary action authoring, and you can carry them out with the platform's own scaffolder and the generated `DEVELOPING.md`. Say which you did.

Before anything else, check whether the format is already supported. Roboto ships ingestion actions for several common robotics formats, and the current list is on the formats page linked in `references/ingestion-api.md`. Building a second ingestion action for a supported format wastes the user's time; if a supported action exists and merely failed, that is `debug-roboto-invocation`'s job, not this one's.

## What you need to run this

- **Run shell commands** and read their output.
- **Read and write files.**
- **Hold a back-and-forth with the user.** Phase 1 is an interview about their data.
- **Fetch a web page.** Used to check the SDK against `docs.roboto.ai` before the project exists.

No plugins, no external tool servers (such as MCP servers), no sub-agents.

**You also need a real sample file.** Not a description of one, not a spec — a file. Every phase of this skill reads it, and the verification gate compares ingested values against it. If the user has no sample file to hand, stop and ask for one; an ingestion action written against a format document and never run against real bytes is not verifiable, and format documents are wrong more often than they are right.

`references/` throughout means the directory alongside this file. Read `references/ingestion-api.md` and `references/authoring-rules.md` before Phase 1.

## Ground truth

Never write an SDK call from memory. The ladder is the same as `create-roboto-action`'s — the action's own venv first, then the generated `DEVELOPING.md`, then `docs.roboto.ai`, then this skill's `references/` last — with one addition specific to ingestion:

**The sample file outranks every document about the format.** Vendor specs, format documentation, and the user's recollection all describe what the format is supposed to contain. The file describes what it does contain. Where they disagree, the file wins, and the disagreement is worth reporting: it usually means the user's data differs from what they believe they have.

Record the SDK version you built against in `SPEC.md`:

```bash
.venv/bin/python -c "from roboto.version import roboto_version; print(roboto_version())"
```

## Phase 0 — Preflight

Delegate the standard action preflight (platform, CLI, Docker daemon, credentials, org inventory). Then add two ingestion-specific checks:

- **The sample file exists and is readable**, and you can open it with whatever library the format needs. If that library does not exist, the ingestion action cannot be written in Python without one, and that is a finding to surface now rather than in Phase 3.
- **The format is not already supported.** Check the formats page, and check the org's action hub for an existing ingestion action.

Note also that the DataFrame ingestion path needs the SDK's ingestion extra, which is distinct from the analytics extra used for reading topic data back. Phase 2 decides whether you need it; `references/authoring-rules.md` covers declaring it.

## Phase 1 — Decompose the format

This is the interview, and it is about the user's data rather than about software. Read the sample file while you conduct it; answers you can extract from the file are answers you should not spend a question on.

### Step 1: Inventory what is in the file

Open the sample and produce a table: what streams does it contain, how are they named, what fields does each carry, what types are those fields, and how many records are in each. Show it to the user. This table is the requirements table for the rest of the skill, and it is frequently the first time anyone has seen their format laid out this way.

### Step 2: Resolve the ambiguities

| Axis | What is undetermined | Consequence of guessing wrong |
|---|---|---|
| Topic granularity | What becomes one topic — a stream, a message type, a device, the whole file? | Determines everything downstream. Too coarse and unrelated signals share a timeline; too fine and a plot needs ten topics |
| Topic naming | What are topics called, and is the name stable across files? | Names are how every later query, trigger, and analysis finds the data. A name carrying a per-file id makes fleet-wide comparison impossible |
| Timestamps | Which field is time, in what unit, and against what epoch? | The single most common ingestion defect. See rules 2 and 3 |
| Clock integrity | Is time monotonic? Are there resets, gaps, or per-stream clocks? | Determines whether one timeline is honest, and whether the action must repair or reject |
| Field selection | Every field, or a subset? | Ingesting everything is usually right, but wide records may need a decision |
| Canonical types | Which fields are numbers, strings, timestamps, images, arrays? | Drives visualization and cross-format reads. Defaulting everything to unknown quietly disables platform features (rule 4) |
| Units | What unit is each numeric field in? | Not recoverable later without re-ingesting. The one piece of metadata users always wish they had captured |
| Nesting | Are records flat or nested, and how should nested fields be named? | Decides message-path naming and whether the source path must be preserved separately (rule 10) |
| Non-tabular data | Are there images, video, point clouds, or large binaries? | Decides the ingestion tier in Phase 2. These do not fit a DataFrame |
| Scale | How large is the largest expected file, and how many records? | Drives compute sizing, and whether the action can hold the file in memory at all |
| Bad-input posture | What should happen for a corrupt, truncated, or empty file? | Determines the exit code the action reports, which determines whether an operator debugging it looks at the action or at the data (rule 8) |
| Partial-failure posture | If one stream fails to parse, ingest the rest or fail the file? | A trigger firing on every upload makes this decision visible daily |

**Without `--yolo`**, interview the user on the axes the file cannot answer — units above all, plus naming conventions and the two failure postures. Lead with your recommendation. Do not ask about anything you can read out of the sample.

**With `--yolo`**, resolve them yourself: prefer one topic per named stream, preserve the source's own names, ingest every field, infer canonical types from the source types, carry units where the format records them and say so where it does not, tolerate a failed stream and report it rather than failing the file, and report bad input as bad input rather than crashing. Mark each as a default in `SPEC.md`.

### Step 3: Confirm the plan

State the inventory table, each resolved ambiguity, the ingestion tier chosen in Phase 2, and the action name. An ingestion action's name should say what it ingests: `acme-telemetry-ingestion`, not `parser`.

## Phase 2 — Choose the ingestion tier

Two stable paths write topics, and they differ in how much of the contract you are responsible for. Confirm both against the installed SDK before choosing; `references/ingestion-api.md` maps the surface.

**Tier 1 — from a DataFrame.** Parse the format into a pandas DataFrame per topic and hand it to the file, naming the timestamp column and its unit. The platform infers the schema, derives the message paths and their statistics, serializes the data, and registers the representation. This is one call, and it is the right default whenever the data is tabular.

**Tier 2 — topic, message paths, representation.** Create the topic, add each message path with its native and canonical type, and register a representation pointing at stored data in a supported storage format. You are responsible for every step, including the last one, which is the step that gets forgotten (rule 1).

Choose Tier 2 only when Tier 1 genuinely cannot express the data: images, video, point clouds, or other large binary payloads that do not belong in a DataFrame; data that is already written in a supported storage format and should be pointed at rather than rewritten; or records too large to hold in memory as a frame. A format with both tabular signals and image streams needs both tiers in the same action, and that is normal.

State the chosen tier and its justification in `SPEC.md`. Under `--yolo`, prefer Tier 1 and use Tier 2 only for the parts that force it.

### A note on the forward path

The SDK carries a declarative schema description under its experimental namespace, aimed at stating a recording's contents in one declaration. It is worth reading to understand where the platform is heading, and it is explicitly not for long-lived production code — the SDK says so itself, and parts of it are still in motion. An ingestion action a user will run for years is long-lived production code. Build on the stable surface, and mention the experimental one in the final report as something to revisit when it graduates.

## Phase 3 — Implement

Delegate scaffolding to `create-roboto-action` Phase 2, then implement with these differences:

- **The parser is the substance, and it is testable without the platform.** Keep format parsing in module-level functions that take a path and return frames or plain values. Those functions get real unit tests against a checked-in fixture — a small, redistributable sample. Everything that touches Roboto stays in a thin layer above them.
- **Never assume the file is well-formed.** Rule 8: a corrupt, truncated, or empty input is a data error the action reports as such, not a traceback.
- **Ingestion writes to the platform, so it is a side effect.** Gate it on the dry-run flag like any other, and log what would have been ingested: topic names, message-path counts, record counts, time ranges. Those logs are what makes a dry run worth reading.
- **Make it idempotent.** Rule 6 covers what the DataFrame path does for you here, and what Tier 2 does not.

Declare the SDK extra the chosen tier needs, as a runtime dependency rather than a dev one.

## Phase 4 — Verify

Delegate the standard gates — the project's verify script, then local invocation against real data. Then add the gate that is specific to this skill, and that no general action can offer.

**Ingestion is verified by reading the data back, not by watching the action exit cleanly.**

Run the action against the sample file for real, then, from a Python environment with the SDK's analytics extra:

1. **The topics exist.** List the file's topics. Compare against Phase 1's inventory table: same names, same count, nothing missing, nothing invented.
2. **The message paths exist**, with the canonical types and units Phase 1 settled. A message path typed unknown that should have been a number is a defect even though nothing failed.
3. **The data reads back.** For each topic, fetch its data as a dataframe and confirm it returns rows.

   **This is the step the whole skill exists for.** A topic created without a registered representation is a metadata-only container: it appears in listings, it looks ingested, and it returns nothing to any data-access call. An action that creates topics and stops there passes every other check and has ingested nothing usable. See rule 1.

4. **The columns match** the message paths, and the values are right. Spot-check at least three: first record, last record, and one in the middle, compared against the source file read independently. Values that are plausible are not values that are correct.
5. **The timestamps are sane.** In nanoseconds, monotonically non-decreasing, and spanning the range the source file covers. An off-by-a-thousand unit error produces data that looks perfect until someone tries to align two topics.
6. **Re-running converges.** Ingest the same file twice and confirm the second run does not duplicate topics or double the record count.

Then run the **bad-input path**: a truncated or empty file, and confirm the action reports it as a data error rather than crashing, with a message naming the file and the problem.

Record every check in `SPEC.md`'s verification table with what it showed. A gate you did not run is a gate to name in the final report.

If the data does not read back, do not adjust the verification to pass. Return to Phase 2 and 3: on Tier 2 the cause is almost always a missing representation, and on Tier 1 it is almost always the timestamp column or its unit.

## Phase 5 — Edit pass

Delegate to `create-roboto-action` Phase 5, with one addition to its API-truth pass: confirm every canonical type and storage format you named exists in the installed enum. These are the values most easily invented from memory, and a wrong one fails at ingestion time rather than at import time.

## Phase 6 — Hand off

Delegate the standard report and the unrun deploy command, and add:

1. **The format inventory** from Phase 1, since it is often the most valuable artifact produced and may be the only written description of the user's format that exists.
2. **The ingestion tier** and why.
3. **What reads back** — the verification results, stated as what the user can now do: which topics, which signals, over what time range.
4. **What was not ingested** — every field, stream, or record type deliberately left out, and why. This is the list someone will come back to.
5. **Anything the sample file contradicted** about the format documentation or the user's expectations.
6. **Units not captured**, if the format did not record them, flagged as needing a decision before a fleet's worth of data is ingested without them.

Then point at the automation, unrun: an ingestion action earns its value when every upload is ingested without anyone asking. That is a trigger on file upload, and `create-roboto-trigger` builds and verifies it. Say so; do not create it here.
