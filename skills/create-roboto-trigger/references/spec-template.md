# Spec template

The structure of `SPEC.md`, which Phase 2 writes into the trigger directory and Phase 4 completes. Replace every angle-bracket slot, and delete sections that do not apply rather than leaving them empty.

The audience is an engineer or agent opening the directory with no other context. Per rule 28 of `authoring-rules.md`, say nothing about how the file came to exist.

---

```markdown
# <trigger-name>

<One paragraph: which event or schedule fires this trigger, which action it runs, on
what data, and why that automation exists. Write it so a reader who knows Roboto but
not this trigger can tell whether it is the rule they are looking for.>

## Requirements

| # | Requirement | Satisfied by |
|---|---|---|
| R1 | <One testable behavior in the present tense: "runs X once per .mcap file ingested into a dataset tagged production".> | `<field>` |
| R2 | ... | ... |

## Trigger

- **Fires on**: <event types and `once_per`, or the cron expression in UTC and what it
  means in the user's local time>, because <reason>
- **Action**: `<action-name>` <owned by this org | owned by `<org>`>, <pinned to digest
  `<digest>` | latest version>, because <reason>
- **Condition**: <in words and as JSON, or "none", and if none, why an org-wide
  trigger is correct here>
- **Required inputs**: <patterns and what they are expected to match, or "none (the event
  names no dataset)">
- **Additional inputs**: <patterns, or "none">
- **Invocation input**: <selectors with their placeholders, or "none">
- **Parameter values**: <each value, and which of the action's required parameters it
  satisfies, or "none">
- **Overrides and output**: <compute, timeout, `upload_destination` and the workload
  that justifies them, or "the action's own defaults">
- **Target ID**: `<target_id>`. Do not rename it: the once-per history is stored under it.

## Scope

- **Expected rate**: <how often this is expected to fire, from the count measured when
  it was written>
- **Re-runs**: <what happens when the same file is uploaded again, or a session is
  announced ingested again>
- **Existing data**: <not processed by the trigger; how to process it if needed>

## Non-goals

<What this trigger deliberately does not cover, so a later reader does not widen it.>

## Verification

SDK version: `<version>`. Test subject: `<ds_... | session ID | invocation ID | minute>`,
pinned with `--guard <FIELD=VALUE>`.

| Path | What was done | Dry-run verdict and failing gate | Dispatch | Invocation result |
|---|---|---|---|---|
| Condition, match | dry run on `<real entity>` | <leaves and actual values> | none | none |
| Condition, miss | dry run on `<real entity>` | <the leaf that missed and its value> | none | none |
| Positive | <e.g. uploaded run.mcap to the test dataset> | <would fire> | `dispatched`, `<iv_...>` | <what the invocation's logs showed> |
| Negative | <e.g. uploaded notes.txt> | <`target_prefilter`: matches no pattern> | none | none |

## Operations

- **State**: <guarded and disabled | live>
- **Go live**: `uv run trigger.py --org <org-id>`
- **Disable**: `roboto triggers disable <trigger-name> --org <org-id>`
- **Inspect**: `roboto triggers get <trigger-name> --org <org-id>`
- **Explain a firing or a miss**: `roboto triggers dry-run <trigger-name> --file-id <id> --org <org-id>`
```
