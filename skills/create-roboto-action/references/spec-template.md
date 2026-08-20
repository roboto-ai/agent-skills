# Spec template

Write this to `SPEC.md` in the generated action project. Replace every angle-bracket slot; delete sections that do not apply rather than leaving them empty.

The audience is an engineer or agent opening the repository with no other context. Per rule 22 of `authoring-rules.md` ("Do not describe the generating process in the project's own docs"), say nothing about how the file came to exist.

---

```markdown
# <action-name> — specification

<One paragraph: what this action does, to what input, producing what output. Write
it so a reader who knows Roboto but not this action can decide whether it is the
right tool.>

## Requirements

| # | Requirement | Satisfied by |
|---|---|---|
| R1 | <Single testable behavior, in the present tense.> | `<file>:<symbol>` |
| R2 | ... | ... |

## Input

- **Shape**: <files | topics | none>
- **Selection**: <how an invoker or trigger picks the input: glob, RoboQL, dataset.
  When the shape is none, say so and state that the action ignores any selection
  passed to it.>
- **Downloaded**: <yes/no> — `requires_downloaded_inputs` is `<value>` because <reason>
- **Invocation modes**: <which of dataset-and-path, query-based, scheduled trigger,
  and local this action supports. `context.dataset` raises when the invocation
  carries no dataset id, which rules out query-based input, scheduled triggers, and
  a local run without `--dataset`; an action that writes dataset tags or metadata
  therefore supports only dataset-and-path and `invoke-local --dataset`.>
- **Assumptions**: <e.g. files are MCAP and already ingested; topic carries message path X>

## Output

- **Files**: <name and format of everything written to `context.output_dir`, or "none">
- **Tags and metadata**: <what the action stages through the file changeset manager, or "none">
- **Events**: <which time ranges the action marks, and on which entity, or "none">
- **Upload destination**: <the explicit output dataset if the invocation was given
  one, otherwise the single input dataset; input spanning multiple datasets skips
  the automatic upload. State which case this action relies on, or "none"
  if it writes no files.>

## Parameters

Every parameter arrives as a string; "Type after parsing" is what `main` coerces it
to. Secrets follow the same rule: `get_secret_parameter` returns `str`, and
`get_parameter` and `get_optional_parameter` resolve a `roboto-secret://` value to
that same `str`. For a secret, fill in both columns: "Secret" says how `main` reads
the value, "Type after parsing" what the value becomes. `action.json` declares only
`name`, `required`, `default`, and `description`.

| Name | Required | Default | Type after parsing | Secret | Meaning |
|---|---|---|---|---|---|
| `<name>` | <yes/no> | `<default>` | <int / float / bool / str / json> | <no, or yes — read with `get_secret_parameter`> | <what it controls; valid range> |

## Dependencies

- **Python**: <runtime packages added to `[project].dependencies`, and why. Note
  `roboto[analytics]` if the action reads topic data as a DataFrame.>
- **System**: <apt packages added to the `Dockerfile`, or "none". A package the
  workstation already provides but this list omits breaks the action inside the
  container, never on the workstation.>

## Failure behavior

| Condition | Behavior |
|---|---|
| No input matched | <log and exit 0, which is normal for a trigger whose glob missed> |
| Input not ingested | <log the file and the missing topic, skip the file, and exit 0 if nothing remains> |
| Parameter out of range | <raise `ValueError` before any work> |
| <domain-specific failure> | <...> |

## Compute sizing

The `compute_requirements` and `timeout` keys of `action.json`:

- `vCPU <n>` — CPU units, not vCPUs: 1024 units = 1 vCPU. One of 256, 512, 1024,
  2048, 4096, 8192, 16384.
- `memory <n>` MiB — the discrete values the chosen `vCPU` allows, not a free range
  (256 permits 512/1024/2048; 512 permits 1024–4096 in 1024 steps; the ceiling
  rises with `vCPU` up to 122880). Raise `vCPU` to unlock more memory.
- `storage <n>` GiB — 21 to 200. Storage bounds how much input an invocation can
  hold on disk; 21 GiB is the minimum.
- `timeout <n>` minutes.

The SDK validates these bounds; the platform separately enforces per-org tier
limits at invocation time. A free-tier org caps out at 4096 CPU units, 8192 MiB
memory, 50 GiB storage, and a 30-minute timeout; the ranges above those caps
(up to 16384 units, 122880 MiB, 200 GiB, and a 720-minute timeout) require a
premium-tier org. Note when the chosen sizing assumes one.

<Why these numbers: the largest expected input, peak in-memory representation, and
the headroom left. State what would force a revision.>

## Resolved decisions

Choices the requirements did not settle, the option taken, and why. A future change
to this action should revisit these rather than rediscover them.

| Question | Decision | Rationale |
|---|---|---|
| <ambiguity> | <what was chosen> | <why; note if this was a default rather than a stated requirement> |

## Non-goals

What this action deliberately leaves undone, and why. A future change should respect
these bounds rather than drift past them.

- <Something a reader might expect this action to do, and the reason it does not.>

## Verification

Built and verified against `roboto` `<version>` (from `.venv/bin/python -c "from
roboto.version import roboto_version; print(roboto_version())"`). A later SDK may
have moved the APIs this action calls.

| Check | Command | Status |
|---|---|---|
| Lint and unit tests | `./scripts/verify.sh` | <result> |
| Dry-run against real data | `roboto actions invoke-local --dry-run <args>` | <result, or "not run — reason"> |

<For the dry run, record the exact input used and what the output confirmed. If it
did not run, say what a reader must do to close the gap.>

## Open questions

- <Anything a human still needs to decide, with the reason the requirements did not
  settle it. Omit the section when there are none.>
```
