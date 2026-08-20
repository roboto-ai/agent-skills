# Triage

The fault-localization tree that SKILL.md Phase 2 executes. Two inputs drive it: **the last status the invocation reached**, and **the exit code** where one was reported. Take both from Phase 0 before using this file.

Everything here is diagnosable from what the invocation itself records — its status history, its configuration, and its logs. If a hypothesis cannot be confirmed from those three, it is not a hypothesis this skill can settle; say so rather than speculating about platform internals you cannot observe.

## Step 1 — Is there a verdict to reach?

An invocation moves through preparation, execution, and upload before completing, and reaches a terminal state on success, on cancellation, or on failure. Confirm terminality against the installed enum rather than by eye: `InvocationStatus` exposes predicates for whether a status is running and whether it is terminal, and those predicates are the check.

Two states are commonly mistaken for verdicts:

- **A live status.** Reporting "it failed" about an invocation still in progress is the most embarrassing available error. Report what it is doing.
- **A failed status that is not the last word.** The status model permits a failed invocation to return to the queue, and distinguishes an ordinary failure from the state an invocation lands in once it will not be retried. Read the transition rules in the enum (`can_transition_to`) rather than assuming failure is final, and prefer the later, harder state when both appear in the history.

## Step 2 — Where did it stop?

The status the invocation reached last localizes the fault before any log is read.

| Stopped at | Fault domain | What to check first |
|---|---|---|
| Never scheduled — still queued | The invocation was never placed on compute | Organization limits and quotas; whether the invocation is queued for scheduling. Not an action defect, and not something logs will explain, because the action never ran |
| Preparing inputs | The invocation's input specification, or the data | The input selection in `invocations show`: did it resolve to anything? Storage sized below the total input. Files that no longer exist |
| Running the action | The action's own code, its dependencies, or its resource sizing | The exit code (Step 3), then the end of the logs. This is the only branch where the action's source is the likely culprit |
| Uploading outputs | What the action wrote, or where it was to be written | Whether the action wrote anything at all; whether an upload destination exists for this invocation's data source |
| Completed, but wrong | The action's logic, its inputs, or the expectation | Nothing is broken from the platform's perspective. Go to Step 4 |
| Cancelled | A person or a process cancelled it | Who and why. This is not a defect. Check whether a bulk cancellation caught it incidentally |

Two absences carry information at this step:

- **No logs and a stop before the action ran** confirms the fault is in preparation, not in the action.
- **Logs that stop mid-work with no error** point at a limit rather than a defect. Compare elapsed time against the configured timeout, and read the last status detail.

## Step 3 — What did the exit code say?

The action runtime reports a defined set of exit codes adapted from `sysexits.h`. Read them from the installed `roboto.action_runtime.exit_codes` enum; the set below is a map, not a citation, and the enum settles both the numbers and their meanings.

| Class | Means | Where the fix goes |
|---|---|---|
| Success | The action completed | If the result is still wrong, go to Step 4 |
| Usage error | The action was invoked incorrectly — a bad or missing parameter, a bad value | The invocation, or the trigger that produced it. Sometimes the action's validation message, if it did not name the parameter and its accepted range |
| Data error | **The action behaved correctly and the input was bad** — wrong format, corrupted, empty | Upstream of Roboto. See the antipattern below |
| Internal error | A defect in the action's own code | The action's source |
| Configuration error | The action or its environment is misconfigured | The action's configuration, its image, or its declared dependencies |

An exit code the enum does not define came from the process itself rather than from the runtime. Treat it as an unhandled failure in the action's code and read the end of the logs for the traceback.

## Step 4 — Completed, but wrong

The platform reports success when the action exits cleanly, whatever the action did or did not do. Four causes, in the order worth checking:

1. **It processed nothing.** The most common case, and it looks identical to success. The input specification selected no files, or selected files the action skipped. Read the logs for what it reported finding, and the input specification in `invocations show` for what it was given. A clean exit that processed zero inputs is a failure wearing a success status.
2. **It processed the wrong thing.** The input specification resolved to more, or other, data than intended — an over-broad pattern, or a trigger firing on data nobody meant to include.
3. **Its outputs went somewhere unexpected.** Files written outside the action's designated output directory are discarded when the container exits. Files written correctly still need a destination that this invocation's data source provides.
4. **It did what it was told, and the expectation was wrong.** A real outcome. Say it plainly rather than hunting for a defect that is not there.

## Step 5 — When the logs are uninformative

An action that logs nothing below error level may not have set its log level from the invocation context, in which case the silence says nothing about this failure. Check whether the action sets its logger level from the context at startup, and whether the invocation requested a level below error at all.

This is a finding in its own right: an action that cannot be diagnosed from its hosted logs will need debugging again. Report it under "what else this surfaced" even when it was not the cause, and note that a local invocation takes its log level from a top-level CLI flag that must precede the subcommand.

## Antipatterns

Each of these is a wrong turn that produces a confident, incorrect verdict.

1. **"Fixing" a data error in the action.** The runtime distinguishes bad input from an action defect precisely so this does not happen. Changing the action to accept input it correctly rejected makes the symptom disappear and the corruption propagate. The finding belongs to the data.

2. **Pattern-matching a traceback before reading the status history.** The status history is cheaper, is often decisive on its own, and tells you whether the traceback you are about to read is even from the relevant phase.

3. **Re-running against easier input.** A fix proven against one small clean file has not been proven against the input that failed. Use the original input, taken from `invocations show`.

4. **Forgetting to redeploy before re-running.** A hosted invocation runs the deployed image. An unredeployed fix re-fails identically, which reads as "the fix didn't work" and sends the diagnosis back to the start.

5. **Reading a timeout as a bug.** An invocation stopped at its configured limit did not necessarily do anything wrong; it may simply be sized for less work than it was given. The fix may be the timeout or the compute sizing rather than the code — and if the input is unbounded, the fix is in how the invocation selects input.

6. **Diagnosing from the action's source alone.** The source is authority on what the action intended. Only the invocation's own record is authority on what happened.

7. **Treating a bulk cancellation as a failure.** A cancelled invocation was stopped by someone. Find out who and why before looking for a defect.
