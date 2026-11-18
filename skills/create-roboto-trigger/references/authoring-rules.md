# Trigger authoring rules

Each rule below names either a failure mode that keeps a trigger from firing on the data it should, or a convention the delivered trigger directory must follow. Apply every rule that bears on the trigger being built; cite the rule number when a requirement forced a choice.

## The deliverable

1. **Deliver the trigger as a script, not as a command typed once.** A trigger created by a command someone typed once exists only in the org, with no record of why it is shaped that way. Deliver `trigger.py`, written so a second run converges instead of failing: `update` the trigger when one with its name exists, `create` it when none does.

2. **Import the trigger model from `roboto.domain.triggers`.** `from roboto import Trigger` gives the legacy `roboto.domain.actions.Trigger`, which raises `DeprecationWarning`, speaks `causes` and `for_each`, and cannot read a trigger with several targets or one an ingestion rule owns. `roboto.domain.actions.ScheduledTrigger` is the legacy schedule model. Use neither.

3. **No org IDs, dataset IDs, or tokens as literals.** The org comes from `--org` or `ROBOTO_ORG_ID`, and the test subject from `--guard`. A script with an org ID in it cannot be reused, and one with a token in it cannot be committed.

4. **Keep each `target_id` stable.** The once-per history is kept per `target_id`, so a renamed target fires again for every file, dataset or invocation the old id already handled. An update must also keep every `target_id` that existing dispatches reference.

5. **Name the trigger as the rule it encodes, with letters, digits, `_` and `-` only, at most 256 characters.** Any other character raises `pydantic.ValidationError` before the request is sent. `summarize-mcap-on-ingest` tells the next reader what the trigger does; `trigger1` does not.

## Firing source

6. **Match the event to what the action reads.** An action that reads topic data needs `file.ingested` (one file) or `session.ingested` (a whole run); on `file.uploaded` it starts before ingestion and finds no topics. An action that reads raw bytes can run on `file.uploaded`, and one that needs a whole upload batch fits `dataset.upload_completed`.

7. **Choose `once_per` from what one invocation processes, and make the action safe to run twice.** `file` runs once per file, even when the file is uploaded again; `dataset` runs once per dataset; `occurrence` runs every time. Delivery is at-least-once, so a target can run twice for one event.

8. **Subscribe to events about one kind of entity.** A trigger on `file.uploaded` and `dataset.created` together is refused when saved; make one trigger per kind.

9. **Write a schedule as a five-field cron expression in UTC.** A schedule cannot name a time zone, so "9 am in Munich" must be converted, and the conversion changes with daylight saving time. A minute missed while the scheduler is unavailable is skipped, not run late.

10. **Expect `session.ingested` to fire more than once per session.** It offers only `once_per=occurrence`, and a session is announced again each time its ingestable files change and are all ingested again. The action must produce the same result when it runs again on the same session.

## Inputs

11. **Give a file-event target at least one `required_inputs` pattern unless `once_per` is `dataset`.** At `file` or `occurrence` the event's file is the input and must match a pattern, so the validator refuses a target without one. `'**/*'` matches any file.

12. **Know how the patterns match.** They are Git wildmatch patterns on the file's path within its dataset (`**/*.bag` matches `x.bag` and `a/b/x.bag`). A per-file target fires for a file matching any pattern. A dataset target waits until each pattern has a file of its own, so overlapping patterns can keep waiting even when the dataset has enough files; on `file.ingested`, each pattern is instead checked on its own, so one file can satisfy several, and every matching file must also be ingested. Triggers ignore a file whose path has any part starting with a dot (`.cache/x.bag`, `logs/.x.bag`); `roboto.paths.is_dotfile_path(path)` tests a path.

13. **On an event that names no dataset, select inputs with `invocation_input`.** `session.ingested`, `session_event.created`, invocation events, `event.created` and schedules have no dataset files to match, so `required_inputs` and `additional_inputs` are refused there. Use `InvocationInput.from_session_id("{{session.session_id}}")` for a session, or a query selector.

14. **Put a placeholder inside a quoted value in a RoboQL query.** `dataset_id = "{{dataset.dataset_id}}"` saves; `dataset_id = {{dataset.dataset_id}}` is refused.

15. **Do not expect a trigger to process data that predates it.** A file trigger at `once_per` `file` or `occurrence` ignores files uploaded before the trigger was created, and a dry run on such a file says so. To process existing data, invoke the action on it directly; the `roboto-guide` skill writes that command.

## Conditions and templates

16. **Qualify every condition field with its root.** An unqualified field binds to the event's default root, the dataset on file events, so `tags CONTAINS "x"` on `file.uploaded` reads the dataset's tags, not the file's. Conditions on topics or message paths are refused.

17. **Check every condition field and placeholder against `roboto triggers sample <event> --paths`.** The validator checks only the root, so `dataset.tag` for `dataset.tags` saves cleanly. A leaf whose path resolves to nothing never matches, and a placeholder that does not resolve cannot be filled in when the trigger fires.

18. **Read a value fixed at the event from `envelope.data`, not from the entity's root.** A condition reads an entity as it is when the trigger evaluates, not as it was when the event happened, so `file.version` can be newer than `envelope.data.file_version`, the version that fired the trigger.

19. **Put every scope the description names in the condition.** A trigger without a condition covers the whole org. When the description names any scope (a project, a robot, a campaign), the scope belongs in the condition, and the lack of one belongs in `SPEC.md` as a deliberate choice.

## Invocation

20. **Check `parameter_values` against the action's parameters yourself.** Do not count on the save to reject a missing required parameter. Invoking the action without one is refused, as a manual invocation is, so a trigger that saves cleanly then records a `failed` dispatch, and starts no invocation, every time it fires.

21. **Decide whether to pin the action's digest, and record why.** Without one, the trigger runs the action's latest version, so redeploying the action changes what the trigger runs.

22. **Size overrides to what the trigger feeds the action, and name an output dataset where the event names none.** An action sized for one file can time out on a whole dataset; `timeout` is in minutes, capped by an org limit (`RobotoLimitExceededException`). An invocation from an event that names no dataset has no data source, so an action that writes output files needs `upload_destination`.

## Verification

23. **Verify a guarded trigger, never a disabled one.** A dry run of a disabled trigger fails the `enabled` gate and evaluates nothing after it. Pin the trigger to one test subject with `--guard`, verify it enabled, and remove the guard only with the user's yes.

24. **Read `enabled` back after every create and enable.** A create past the org's active-trigger limit can save the trigger disabled instead of failing, and an enable past it raises `RobotoLimitExceededException`.

25. **Read the dispatch, then the invocation, and report them separately.** A `dispatched` dispatch whose invocation failed is a working trigger and a broken pipeline. A `failed` dispatch carries the error in `status_detail`.

26. **Run the negative path and check the reason.** A trigger verified only on data it should fire for may fire on everything. A path that matches no pattern and a condition leaf that misses are different findings; a negative path skipped for the wrong reason has verified nothing.

## Documentation

27. **Write `SPEC.md` for a reader who lacks the conversation that produced the trigger.** State each requirement, each resolved ambiguity, and why the event, grain, patterns and condition have the values they do.

28. **Do not describe the generating process in the delivered files.** No references to this skill, its phases, an interview, or `--yolo`. Attribute each decision to its rationale.
