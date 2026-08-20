# Action authoring rules

Each rule below names either a failure mode that keeps a generated action from working on the first invocation or a convention the generated repository must follow. Apply every rule that bears on the action being written; cite the rule number when a requirement forced a choice.

## Runtime contract

1. **Leave `bin/entrypoint.py` and `main`'s signature alone.** The entrypoint imports `main` from the package's `__init__.py`, builds the context with `roboto.InvocationContext.from_env()`, and calls `main(context)`. `test/test_main.py` introspects the signature: it fails if `main` takes anything other than one positional parameter, if that parameter carries an annotation other than `roboto.InvocationContext`, or if the return is annotated as anything but `None`.

   The test reads annotations, not behavior, so two mistakes slip past it. A `main` annotated `-> None` that returns a value still passes, and the entrypoint discards the value. Dropping `main`'s re-export from the package `__init__.py` also passes, because the test imports from `<package>.main` directly; the container imports from the package and breaks.

2. **Set the log level from the context, once, at the top of `main`:** `logger.setLevel(context.log_level)`. Without it, the level the invoker asked for has no effect: the module logger stays at the root default of `WARNING` (the template's `logging.basicConfig` sets only a format), so a failed hosted invocation lacks the INFO/DEBUG detail needed to diagnose it. Never `print`; use the module logger from `logger.py` so output carries level and source line.

   Locally, `--log-level` is a top-level CLI flag and has to precede the subcommand (`roboto --log-level=info actions invoke-local ...`, not `roboto actions invoke-local --log-level=info`). It defaults to `ERROR`, so a local run that omits it prints nothing below error even when the `setLevel` call is present.

3. **Gate every side effect on `not context.is_dry_run`:** uploads, metadata and tag writes, event creation, and non-idempotent external calls. A dry run must traverse the same code path and log what it would do, because `invoke-local --dry-run` is the only pre-deploy check against real data. An action that silently no-ops under dry run cannot be verified; one that writes under dry run corrupts real data during development.

4. **Parse and validate every parameter at the top of `main`, before any work.** Parameters arrive as strings (`action-api.md`). Convert them, range-check them, and raise `ValueError` naming the parameter and the accepted range; that message is what the operator sees in `roboto invocations logs`. Failing fast beats failing halfway through a long invocation.

5. **Read runtime facts through `InvocationContext`, never through `ROBOTO_*` environment variables.** The variables are an implementation detail that changes between SDK versions; the context properties are the supported surface.

## Input handling

6. **Match `requires_downloaded_inputs` to how the action reads data.** File-content actions need `true` (the default) and get a populated `local_path`. Topic-driven actions should set `false`: they fetch over the API, and the flag then guarantees no file is downloaded on their behalf — a safeguard against wasted downloads, not a correctness requirement. The flag matters only when the invocation selects files (`--file-query`, or `--dataset` with `--file-path`); a topic-query invocation resolves no files, so `true` downloads nothing anyway. Setting it `false` while indexing `local_path` dereferences `None`.

7. **Handle empty input explicitly.** `get_input()` can return no files and no topics: a trigger's glob matched nothing, or a query returned an empty set. Log the fact and return cleanly. Do not raise. A trigger firing on an unrelated upload is normal operation, not a failure, and a raise marks the invocation as failed and pages whoever owns the alarm.

8. **Never assume a file has been ingested.** `file.get_topics()` is a generator that yields nothing for a file Roboto has not ingested, and `file.get_topic("<name>")` raises `RobotoNotFoundException` on un-ingested input. Check first, and log which topic was missing from which file.

9. **Guard `get_data_as_df` against absent message paths.** A topic's schema may not carry the column the action wants. Check membership in `df.columns` before indexing, and report the topic name alongside the missing column. `get_data_as_df` requires the `roboto[analytics]` extra.

## Output

10. **Write outputs only to `context.output_dir`.** The container discards anything written elsewhere when it exits. Build paths as `context.output_dir / name`, never by string concatenation onto a hardcoded root.

11. **Stage output tags and metadata through the file changeset manager.** Use `put_tags` / `put_fields` / `set_description` for files the action produces; each takes the path relative to `context.output_dir` as its first argument, and the runtime applies the staged changes after the upload. Fetching and mutating an output file during the invocation cannot work: the upload has not happened, so the file does not yet exist in Roboto and the lookup fails.

12. **Do not touch `context.dataset` unless the invocation is guaranteed to have one.** It raises `ActionRuntimeException` when no dataset is associated, which is the case under a scheduled trigger, under query-based input (`--file-query` / `--topic-query`), and during local runs without `--dataset`. An action whose only output is `context.dataset.put_tags(...)` works under a file-upload trigger and crashes under a scheduled one. When the invocation mode permits an unspecified dataset, either derive the dataset from an input file instead of the context, or guard the call and log that dataset-level output was skipped. Match that choice to the invocation modes the action is specified to run under (settled by the Invocation mode axis of SKILL.md Phase 1).

13. **Make the action idempotent.** Triggers retry, and operators re-invoke. Re-running over the same input should converge to the same result rather than appending a second copy of every event or duplicating tags.

## Packaging

14. **Split dependencies between the runtime and dev tables.** Python runtime imports go in `[project].dependencies`; tools used only by `verify.sh` go in `[project.optional-dependencies].dev`. A runtime import left in `dev` imports fine locally and raises `ImportError` inside the container.

15. **Declare system packages in the `Dockerfile`.** `apt-get install` anything a wheel shells out to or links against (`ffmpeg`, codec libraries, compilers) under the `# -- INSTALL SYSTEM DEPENDENCIES --` marker. Workstation-installed packages are not in the image.

16. **Keep the Python version in sync across all three places that state it.** `.python-version`, the `Dockerfile`'s `PYTHON_MAJOR`/`PYTHON_MINOR` build args, and `requires-python` in `pyproject.toml` are independent settings; drift means local tests and the container run different interpreters.

17. **Size `compute_requirements` against the real workload, and say why.** The cookiecutter template that `roboto actions init` scaffolds from (source linked in `action-api.md`) defaults to 512 vCPU units, 1024 MiB of memory, and 21 GiB of storage, which covers light file inspection. Loading a large topic into a DataFrame, decoding video, or downloading a multi-gigabyte input needs more memory or storage, and when `requires_downloaded_inputs` is `true`, `storage` must exceed the total downloaded input size. Stay inside the allowed values in `action-api.md`: `vCPU` is an enum; `memory` is restricted to a discrete set that depends on the `vCPU` chosen (whole GiB steps below 8192 vCPU units, 4 GiB steps at 8192, 8 GiB steps at 16384, and 512 MiB only at 256); `storage` has a 21 GiB floor. An out-of-range or mismatched value fails at action-create time, after the image has been built and pushed. Record the reasoning in the spec so a future reader can revisit it.

## Tests

18. **Keep the shipped signature test.** `test/test_main.py` is the guard on rule
    1. Add to it; do not replace it.

19. **Test the extracted logic, not the platform.** Pull decisions worth testing (threshold comparisons, parsing, summary math) into module-level functions that take plain values, and test those directly. A test that stands up an `InvocationContext` and asserts on what it returns verifies the fixture rather than the action. When a code path genuinely cannot be lifted out of the context, drive the SDK directly: `InvocationContext(...)` takes its state as constructor arguments, and `roboto.testing.StubRobotoClient` stands in for the HTTP client. Use that approach only after extraction has failed.

20. **Never let a test reach the network.** `verify.sh` runs `ruff` and `pytest` and nothing else, wherever the repo is checked out, including CI, where Roboto credentials may be absent. Real-data confidence comes from `invoke-local --dry-run`, not from `pytest`.

## Documentation

21. **Write the spec for a reader who lacks the conversation that produced the action.** The generated project's spec is the only place the intent behind the code survives. State the requirement, the resolved ambiguity, and the reason a number or a threshold has the value it does. A future agent asked to extend the action reads that file to learn what it is allowed to change.

22. **Do not describe the generating process in the project's own docs.** No references to this skill, its phases, an interview, or `--yolo`. The action repository stands alone: it documents the action, its parameters, its inputs and outputs, and how to run it. Attribute decisions to their rationale, not to where in a workflow they were made.
