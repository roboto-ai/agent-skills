# Edit passes

This file defines the post-implementation edit protocol of `create-roboto-action` (SKILL.md Phase 5): five passes over the files you authored during implementation (SKILL.md Phase 3) — `main.py`, any sibling modules, `test/test_main.py`, `SPEC.md`, and the project `README.md` — each pass carrying its result into the next.

You are editing your own work, so you already hold what an outside reviewer would lack: the requirements table and the resolved decisions from SKILL.md Phase 1, and `SPEC.md`, which records both. Fix what you find rather than list it. Escalate to the final report's Open items section (SKILL.md Phase 6) only when a fix would contradict a decision the user made or would take the action beyond the scope `SPEC.md` records: its requirements, resolved decisions, and non-goals.

## Invariants — hold these through every pass

The invariants below are properties of the Roboto action runtime, not of the generated code, so nothing in the files under edit will remind you of them:

- `bin/entrypoint.py` is fixed template machinery; do not edit it. It imports `main` through the package `__init__.py` re-export, so keep that re-export even though no test covers it.
- `main`'s signature is a runtime contract, annotations included: one positional parameter annotated `roboto.InvocationContext`, and a return type of `None`.
- The shipped signature test in `test/test_main.py` guards that contract, loosely: it checks each annotation only when one is present, so a dropped annotation passes the test yet still breaks this invariant. Add to it; never weaken or delete it.
- Tests never reach the network, and a hand-built `InvocationContext` is a last resort, permitted only for logic that cannot be extracted into a module-level function taking plain values, and only on `roboto.testing.StubRobotoClient` (`authoring-rules.md`, rules 18–20). Real-data confidence comes from the `invoke-local --dry-run` verification (SKILL.md Phase 4), not from these tests.
- No new dependencies. The container builds its environment from `pyproject.toml` (the venv itself never ships), and Phase 4's verification covered only the dependencies that file already lists; adding one invalidates that verification.
- `SPEC.md` is the contract. Code contradicting it is a bug; a spec decision you disagree with calls for a spec change, made deliberately and recorded, rather than a silent code change.

## Pass 1 — API truth

Treat every SDK call, `action.json` field, and CLI invocation in both the code and the docs as written from memory until you confirm each against the SDK installed under `.venv/` (rung 1 of SKILL.md's Ground truth ladder). Check argument order, required versus optional parameters, return types, and which exceptions propagate.

Then check stated-against-actual: wherever a comment, `SPEC.md` row, or `README.md` line says what a block accomplishes, trace the code and confirm it does that. A snippet can use every API correctly and still not do what the sentence above it claims: a missing step, an inverted condition, an option left off.

## Pass 2 — Naming and shape

This pass has two halves; naming is the substance.

**Shape.** Remove dead code, unused imports, unnecessary wrappers, and intermediate variables that name nothing. Break up a `main` long enough to lose the thread. Delete flexibility no current caller needs: a parameter with one possible value, a hook nothing calls, an abstraction over a single case. If the only thing justifying a construct is a comment about what might be needed later, the construct goes.

**Naming.** Describe the behavior; do not point at your own context. A name earns its place by making a claim a reader can check against the code in view. A *deictic* name instead points into context the reader does not have — the session that produced this action, the description it was generated from, the layer next door — and resolves to nothing once that context is gone. It reads as precise to you now for the same reason it will read as empty later. Rename:

- **Coined vocabulary** — a name that labels a thing by pointing at your mental model rather than stating what it holds or does. `WorkItem` becomes `FileTopicPair`; `DamageState` becomes `MissingRowState`; a bare `budget` or `the walk` becomes the quantity it actually tracks. Defining the coined name in a docstring is not a fix; it documents the problem instead of removing it.
- **Writing-time pointers** — `new_handler`, `v2_parser`, `legacy_*`. Each decays the moment the thing it contrasts with is gone.
- **Technique labels** — `lockfree_queue`, `memoized_lookup`. Filing the code under outside literature says less than naming the specific fact.
- **Contrast adjectives** — `simple_parse`, `special_case`, `plain_read`. The whole meaning is a comparison whose other side is not on the page.
- **Storage names standing in for concepts** — a table, column, or file-format name used as the name of the relationship itself rather than of the thing that records it.
- **Vocabulary borrowed from an adjacent layer**, where a term from the name's own layer would be clearer. A name is correctly scoped when a reader of the surrounding code would reach for that word unprompted.

Also rename identifiers that contradict what the code does (`get_x` that also writes, `is_valid` that mutates) and vague ones (`data`, `result`, `tmp`, `val`) where a specific name exists.

The bar for every rename: the new name gains a claim a reader can check. Swapping in a more fluent synonym is not a fix. Keeping a name and documenting its meaning in a docstring instead of renaming is reserved for names outside this project's control: `main`'s signature, `action.json` field names, SDK symbols.

After renaming, grep the project for the old name. `SPEC.md`'s "Satisfied by" column, `README.md`, and the tests all reference symbols by name, and a rename that stops at the module boundary leaves the spec describing code that no longer exists.

## Pass 3 — Comments

Explain why the code exists, what user-visible outcome it produces, or what invariant it defends, never what the next line does mechanically. Delete any comment recoverable from the code below it.

- Cut comment-shaped filler: "Note that", "Basically", "In other words", "Here we". Lead with the fact.
- Give each fact one home. A sentence the docstring already carries is a paraphrase when it reappears inline, and the two copies will drift.
- No author-relative language, which is Pass 2's rule applied to comments: no importance claims ("critical", "load-bearing") with the mechanism omitted, no names for regions of your own mental map ("the fast path", "the happy path"), no writing-time markers ("now", "previously", "this change", "refactored to").
- Where the code catches an exception, say which exceptions are swallowed, which propagate, and why for each.
- Delete comments that no longer match the code.

A comment whose job is to translate a coined identifier is a Pass 2 rename you missed: go back and rename rather than explain the name. The same holds for a comment that anchors a writing-time pointer or expands a technique label sitting in a symbol name.

Rule 22 of `authoring-rules.md` binds here and in the docs: the project documents itself, never the process that produced it. No comment, `SPEC.md` row, or `README.md` line may mention this skill, its phases, an interview, or `--yolo`.

## Pass 4 — Verify script

```bash
./scripts/verify.sh
```

The project ships its own verify script; use it rather than a linter. Fix what it reports on code you wrote and re-run until it passes.

## Pass 5 — Final diff review

Read the complete diff of Passes 1–4 in one sitting and confirm each of the following:

- No change altered observable behavior unless a requirement called for it. Behavior-preserving restructuring is the expected output of these passes; do not undo a good refactor to shrink the diff.
- Every invariant above still holds, especially the signature test and the `__init__.py` re-export.
- Renames are complete across code, tests, `SPEC.md`, and `README.md`.
- The code still does what `SPEC.md` says it does.

Then re-run `./scripts/verify.sh`. If any fix touched action logic, also re-run the `invoke-local --dry-run` verification (SKILL.md Phase 4); `SPEC.md`'s verification table records the exact commands and inputs to repeat. A pass that changed behavior without re-running the dry run has verified nothing.

Where a fix revealed a gap a test can pin — two copies of a value that must agree, a requirement satisfied jointly by `action.json` and `main.py`, an invariant nothing currently checks — close it with the test rather than a paragraph in `SPEC.md`. Prose decays; a test does not. Then prove the test fails for the right reason: mutate the thing it guards, watch it fail, restore. A test never seen red is a gap still open.

Update `SPEC.md` for anything that changed a decision or a requirement.
