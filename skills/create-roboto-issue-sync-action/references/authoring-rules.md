# Issue sync authoring rules

Each rule below names either a failure mode that keeps an issue-sync action from working on its first invocation or a convention the generated repository must follow. Apply every rule that bears on the action being written; cite the rule number when a requirement forced a choice.

The SDK behavior these rules name was checked against the SDK release recorded as `verified-sdk` in the `metadata` block of `SKILL.md`, by the methods the first paragraph of `references/sync-api.md` describes, on the date recorded as `verified-on`. Tracker behavior is stated as something to check, not as fact. Where a rule and a live source disagree, the live source wins.

## Runtime contract

1. **Leave `bin/entrypoint.py` and `main`'s signature alone, and set the log level from the context at the top of `main`.** The entrypoint calls `main(context)` with one `roboto.InvocationContext`, and the shipped `test/test_main.py` checks that signature. The template's `logger.py` sets no level on the action's logger, so without the `logger.setLevel(context.log_level)` line the template's `main` starts with, every run logs nothing below `WARNING`.

2. **Gate the tracker writes and the stamp together on `not context.is_dry_run`, and log what each would have done.** Gating the create but not the stamp makes a dry run write a stamp for an issue that was never filed, so the next real run starts from a stamp that names no issue. Tracker reads stay ungated, so the dry run still exercises the existence check.

3. **Read and validate every parameter at the top of `main`.** Values arrive as strings. Check the tracker base URL parses as a URL and that no value still reads as an unfilled `{{ }}` placeholder; treat such a value as unset, rather than sending it to a request builder that fails later with a less useful message.

4. **Reach the entity through the input the invocation mode provides.** `context.dataset` raises `ActionRuntimeException` when no dataset is associated, which is the case for a session input, a selector query, and a schedule. A session-keyed action reads `context.get_input().sessions`, and logs and returns when the list is empty.

## Identity

5. **Record the issue on the Roboto entity that defines identity, and read that record before every sync.** A tracker cannot tell which Roboto entity an issue came from, so without the stamp every re-analysis and trigger retry files another issue.

6. **When the existence check fails, assume the issue exists.** A timeout, a rate limit, or a 5xx says nothing about the issue. Treating it as "deleted" files a duplicate each time the network fails. Only a definite not-found response means create.

7. **After a create, confirm the stamp landed, and log the issue identifier at `ERROR` if it did not.** If the create succeeds and the stamp write fails, every later run finds no record and files another issue. Retry the write once; the logged identifier lets a person restore the stamp by hand.

8. **Expect two runs for one entity at the same time.** Trigger delivery is at least once per target, and an operator can re-invoke while a run is in progress, so two runs can both read no stamp and both create. Put the entity's `roboto://` URI in the issue body as a marker, and when the stamp is absent, search the tracker for it before creating. Where the tracker's search lags behind its creates, this narrows the window without closing it; say so in `SPEC.md`.

9. **Decide what a clean result produces, and write it in `SPEC.md`.** File nothing, file a closed issue as a record, or close an existing issue. If issues follow the data, a finding that clears closes its issue and a returning finding reopens it, so the open-issue list means one thing.

10. **Link in both directions.** The issue body links to the entity and to the invocation; the entity's stamp holds the issue URL. Locally the invocation ID is the placeholder `inv_LOCAL_DOCKER_INVOCATION`, so the invocation link resolves only on hosted runs.

## Credentials

11. **Take the tracker token as a secret parameter, never as a literal.** Pass `roboto-secret://<name>` at invocation or in the trigger's parameter values; the runtime resolves it. A literal in `action.json`, the repository, or a trigger is readable by everyone who can read those, and rotating it means redeploying.

12. **Never log the token, and prove it.** A logged request object, header dict, or exception that carries the request writes the token into the invocation log of every failed run. Phase 4 runs with an invalid token and reads the log for it.

## Content

13. **Rewrite every `roboto://` reference into a web link before posting.** In a tracker, `roboto://` text renders as plain text that opens nothing. AI summaries are full of these references. Use the `/open` form from `references/sync-api.md` ("Links"), confirmed in Phase 0.

14. **Find out what the tracker does with an unknown label, by trying it on the scratch project.** A tracker may create the label, reject the request, or drop the label and create the issue anyway. The third leaves the issue without the information it was filed to carry. If labels must exist first, create them or put the finding in the body.

15. **Bound every wait on an AI summary.** `StreamingAISummary.complete_text` waits with no limit while a summary is still generating. Use `await_completion(timeout_s=...)`, catch `TimeoutError` and `RobotoFailedToGenerateException`, and catch `RobotoNotFoundException` from `get_summary()` for an entity never summarized. A summary that had already failed comes back with `status` `failed` instead of raising, so check `status` before posting `text`.

## Failure

16. **When the tracker parameters are absent, degrade instead of failing.** Log the issue that would be filed (title, labels, body) at `INFO`, write it to `context.output_dir`, and exit cleanly. This keeps the action useful before a tracker is set up and testable without one.

17. **Give every tracker call a timeout, and have it return a result instead of raising.** A request with no timeout runs until the invocation's own timeout kills it, with no useful log. A result the caller inspects puts the failure posture (fail the invocation, or log and continue) in one place instead of four.

18. **Read the stamp from a fresh copy of the entity.** The entities in `get_input()` are built from records captured when the invocation was set up, and the stamp may have been written since. Re-read with `Session.from_id`, `refresh()`, or `get_metadata()`.

19. **Do not let the stamp write start this action again.** Writing the stamp is a metadata update. A trigger subscribed to `dataset.metadata_updated` or `file.metadata_updated` that runs this action can fire again for the stamp; its condition must exclude that change, or the trigger should subscribe to the event that produces the findings, such as `invocation.completed` of the analysis action or `session.ingested`. Write the stamp only when it changes.

## Structure

20. **Keep tracker specifics inside the client module.** Endpoint shapes, identifier encoding, auth headers, label behavior, and state changes belong in one module. The rest of the action and its tests then run against a fake client, and a second tracker is a new module.

21. **Open `SPEC.md` with the identity rule, and never mention this skill in the project.** What makes an issue the same issue, where the stamp lives, and what a clean result produces are what the next person will change. `SPEC.md`, `README.md`, and comments describe the action, not the skill, its phases, or `--yolo`.

## Packaging and tests

22. **Set `requires_downloaded_inputs: false`, and put the HTTP client in the runtime dependencies.** The action reads records over the API, so downloading input files only costs time and storage. A runtime import left in the `dev` dependencies imports locally and raises `ImportError` in the container. `requests` is the exception that hides this: it reaches the container through `roboto`'s own dependency on `cookiecutter`, so leaving it out of the runtime list goes unnoticed until that chain changes. Declare it anyway.

23. **Never let a test reach the network.** `./scripts/verify.sh` runs `ruff` and `pytest` wherever the repository is checked out, including CI without credentials. Test each branch of the sync decision with a fake client: stamp absent; stamp present and the issue exists, with no create call; stamp present and the issue gone; stamp present and the check failed, with no create call; a clean result; a finding that clears and returns.
