# Spec template

Write this to `SPEC.md` in the delivered trigger directory. Replace every angle-bracket slot; delete sections that do not apply rather than leaving them empty.

The audience is an engineer or agent opening the directory with no other context. Per rule 20 of `authoring-rules.md`, say nothing about how the file came to exist.

---

```markdown
# <trigger-name> — specification

<One paragraph: what event this trigger responds to, which action it invokes, over
what data, and why that automation exists. Write it so a reader who knows Roboto but
not this trigger can decide whether it is the rule they are looking for.>

## Requirements

| # | Requirement | Satisfied by |
|---|---|---|
| R1 | <Single testable behavior, in the present tense: "invokes X once per Y uploaded to a dataset tagged Z".> | `<field>` |
| R2 | ... | ... |

## Trigger

- **Type**: <event-driven | scheduled>
- **Action invoked**: `<action-name>` <owned by this org | owned by `<org>`>
- **Action version**: <pinned to digest `<digest>` | tracks latest — and why>
- **Causes**: <the configured causes, or "server default" — and, either way, the causes
  the created trigger reported back>
- **For-each**: <dataset | dataset_file> — because <reason>
- **Required inputs**: <the glob patterns, and what they are expected to match. State
  whether the all-versus-any reading of this list follows from the for-each
  granularity chosen above.>
- **Additional inputs**: <patterns downloaded but not matched, or "none">
- **Condition**: <the condition, in words and as JSON, or "none" — and if none, why an
  org-wide trigger is correct here>
- **Parameter values**: <what is passed to the action, and which of the action's
  required parameters each one satisfies, or "none">
- **Overrides**: <compute, container, or timeout overrides and the workload that
  justifies them, or "the action's own defaults">

## Scope

- **Blast radius at authoring time**: <how many datasets or files in the org matched
  this trigger's condition and patterns when it was written>
- **Expected invocation rate**: <roughly how often this is expected to fire in normal
  operation>
- **Re-run behavior**: <what happens when the same data is uploaded again>

## Non-goals

<What this trigger deliberately does not cover, so a future reader does not "fix" it
into scope. E.g. does not fire on metadata edits; does not cover datasets from other
sources; does not reprocess historical data.>

## Verification

SDK version: `<version>`

| Path | Event produced | Evaluation outcome | Invocation | Result |
|---|---|---|---|---|
| Positive | <e.g. uploaded sample.bag to scratch dataset ds_...> | <outcome and cause> | `<iv_...>` | <what the invocation's logs confirmed> |
| Negative | <e.g. uploaded notes.txt, which matches no pattern> | <outcome and skip reason> | none | <why this is the expected reason> |

## Operations

- **Current state**: <enabled | disabled>
- **Enable**: `roboto triggers update <trigger-name> --enabled --org <org-id>`
- **Disable**: `roboto triggers update <trigger-name> --disabled --org <org-id>`
- **Inspect**: `roboto triggers get <trigger-name> --org <org-id>`
- **Reapply this spec**: `python create_trigger.py --org <org-id>`
```
