# Trigger authoring rules

Each rule names either a failure mode that keeps a trigger from firing correctly or a convention the delivered artifact must follow. Apply every rule that bears on the trigger being built; cite the rule number when a requirement forced a choice.

## Reproducibility

1. **The script is the trigger.** A trigger created by a command someone typed once exists only in the org, and the next person to change it has no record of why it is shaped that way. Deliver `create_trigger.py`, and write it so a second run converges rather than fails: look the trigger up by name, `update(...)` it when it exists, `create(...)` it when it does not. The file is the source of truth; the org holds a copy.

2. **Create disabled; enable last, and only with the user's word.** A trigger created live begins evaluating before it has been verified, against whatever data arrives in the meantime. Create with the disabled flag, verify against a scratch dataset, and leave the enable command for the user to run. This is the only rule in this file that `--yolo` does not relax.

3. **No identifiers or credentials as literals.** Org ids, dataset ids, and tokens come from an argument or the environment. A script with an org id baked in cannot be used by the next org, and one with a token in it cannot be committed at all.

## Cause and timing

4. **Know what `required_inputs` means for your `for_each`, because it changes.** The two granularities read the same list differently: a dataset-level trigger looks for a set of files that together satisfy **all** the patterns, while a file-level trigger looks for files matching **any** of them. A three-pattern list that a dataset trigger treats as "all three must be present" is treated by a file trigger as "any one of these". Confirm the current semantics against the skip-reason documentation in `trigger-api.md`, and state in `SPEC.md` which reading the trigger relies on.

5. **Match the cause to what the action reads.** An action that reads ingested topic data must be caused by ingestion completing, not by upload; on upload it runs against a file Roboto has not ingested yet, finds no topics, and either fails or silently does nothing. An action that reads raw file bytes can run on upload. This is the single most consequential decision in the interview.

6. **Never pass the recurring-schedule cause to an event-driven trigger.** It is reserved for the platform's own use with `ScheduledTrigger` and is documented as an error on create or update. A recurring schedule needs the other class, not this cause.

7. **Read the causes back after creating.** Omitting `causes` accepts a server-side default this skill does not specify. Print the created trigger's causes, compare them to what the interview settled, and report any difference rather than assuming the default matched your intent.

8. **Decide whether to pin the action's version.** Omitting the digest is documented as tracking the action's latest version, which means redeploying the action silently changes what the trigger runs. That is usually what a user wants and occasionally a surprise. Record the choice.

## Matching and scope

9. **Use the narrowest glob the requirement supports.** `**/*` matches every file at every depth and is a decision to state in the spec, never a default to fall into. Patterns match a file's path within its dataset, so a pattern anchored to a directory that only some datasets use is a scoping decision too.

10. **A trigger without a condition is org-wide.** It will evaluate against every data source in the organization that produces its cause. When the description scopes the work at all — a project, a robot, a data campaign — that scope belongs in a condition, and the absence of one belongs in the spec as a deliberate choice.

11. **`additional_inputs` are downloaded but never matched.** Files the action needs for context, but whose absence should not stop the trigger, go there. Putting them in `required_inputs` makes the trigger wait for files it only wants to read.

## Invocation

12. **Check the action's parameters at author time.** Read the target action's parameter list, and confirm that `parameter_values` supplies every required parameter that has no default. Do not assume trigger creation validates this for you; a trigger that creates cleanly and then fails on every invocation is the expensive version of this mistake.

13. **Size overrides against what the trigger will actually feed the action.** An action sized for a manual invocation over one file can time out or run out of memory when a trigger feeds it a whole dataset. When the for-each granularity or the input patterns imply larger inputs than the action's defaults assume, override compute or timeout, and say why in the spec.

14. **Re-running over the same data is skipped, by design.** Roboto records that the action already ran for a dataset or file and skips subsequent evaluations for it. A user who expects a re-upload to reprocess should hear this during the interview, not discover it from a skipped evaluation.

## Verification

15. **Verify by evaluation record, never by reading the trigger back.** A trigger that reads back exactly as authored has proven only that the create call worked. The gate is: produce the cause event, wait for evaluations to complete, and read the resulting record's outcome.

16. **Run the negative path.** Produce an event that should not invoke the action, and confirm the skip reason is the one you expect. A trigger verified only on the positive path may be firing on everything.

17. **An invoked action that then failed is a verified trigger and a broken pipeline.** Read the invocation's status and logs, and report the two facts separately. Reporting only "the trigger fired" hides the failure; reporting only "it failed" hides that the automation works.

18. **Diagnose from the skip reason.** Each reason names its own fix:

    | Skip reason | What to change |
    |---|---|
    | `NoMatchingFiles` | The `required_inputs` patterns, or the `for_each` granularity whose all-versus-any semantics you assumed (rule 4). Confirm the file's path within the dataset is what you think it is |
    | `ConditionNotMet` | The condition, or the tags and metadata on the test data. Confirm which entity the condition is evaluated against before rewriting it |
    | `AlreadyRun` | Nothing, usually — use fresh data. If a re-run is genuinely required, that is a requirement the interview missed (rule 14) |
    | `TriggerDisabled` | Enable it. Expected during verification, since rule 2 creates it disabled |

    A failed evaluation, as opposed to a skipped one, carries its exception in the record's status detail. That is a platform-side or configuration error, not a matching decision, and it is worth reporting verbatim.

## Documentation

19. **Write the spec for a reader who lacks the conversation that produced the trigger.** State the requirement, the resolved ambiguity, and why a glob, cause, or condition has the value it does. A future agent asked to change the trigger reads that file to learn what it is allowed to change.

20. **Do not describe the generating process in the delivered artifact.** No references to this skill, its phases, an interview, or `--yolo`. The directory stands alone: it documents the trigger, what it fires on, what it invokes, and how it was verified. Attribute decisions to their rationale, not to where in a workflow they were made.
