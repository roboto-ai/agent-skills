# The sync contract

The mechanics of keeping a Roboto entity and a tracker issue in one-to-one correspondence. Rung 5 of SKILL.md's Ground truth ladder — the lowest. Confirm the Roboto calls against the SDK in the action's venv, and the tracker calls against the tracker's own responses.

## The Roboto side

### Reading findings

An issue-sync action does not analyze anything; it reads results that already exist. Confirm the accessors against the installed SDK. The usual sources:

- **Dataset or file metadata and tags** — the flat, queryable findings.
- **The dataset's AI summary**, if one was generated or an action wrote one. The getter returns a streaming handle rather than a string, and **raises when the dataset has never been summarized** rather than returning `None` — catch that instead of checking for absence.
- **Events** — findings that have a time range, which render well as a timeline table in an issue body.
- **Output files from a prior action** — when an analysis wrote a report rather than structured fields.
- **An agent's goal results** — but only when the thread id reaches the action as a parameter, or the action starts the thread itself. The SDK resolves a thread by id alone; there is no call that lists the threads attached to a dataset, so an action cannot discover a pre-existing one for the data it is running on.

Whichever it is, confirm it exists for a real dataset during Phase 0. An action that syncs findings nothing produces cannot be verified.

### Parameters and secrets

Confirm these against the installed `InvocationContext`:

- An accessor for an **optional** parameter, returning the default you pass (`None` if you pass none) when the parameter is unset.
- An accessor for a **required** parameter, which raises when it has no value at all.
- An accessor for a **secret** parameter, which raises when the secret cannot be resolved.

Both the optional and required accessors detect a secret URI in a parameter's value and resolve it; the required one only adds the raise-when-absent.

That combination means the degradation posture (sync rule 8) needs **two** checks, not one. An absent parameter is not an exception — the optional accessor hands back your default. The exception arrives one step later, when a parameter *is* set to a secret URI that cannot be resolved: the optional accessor delegates to the secret accessor and the runtime exception escapes. So handle unconfigured with a `None` check, and half-configured with a `try`/`except` around the same read.

Every parameter value arrives as a string. Validate before use, and see sync rule 13 about values that look like unsubstituted placeholders.

Pass the value as `roboto-secret://<secret-name>` for the caller's org, or `roboto-secret://<secret-name>@<org_id>` to name one. `roboto secrets --help` lists only the verbs and does not document the URI; the secrets page on `docs.roboto.ai` does.

**Mind how the secret gets stored.** The CLI's write verb takes the value as a required positional argument, so `roboto secrets write <name> <value>` puts the credential in `argv` — visible in the process list and in shell history, which is exactly what sync rule 5 forbids. Prefer the web UI's secrets settings or the SDK's create call. If the CLI is genuinely the only option, say so out loud and treat it as the one sanctioned exception.

### The stamp

The stamp is what makes the sync idempotent (sync rule 1). Write it with the entity's metadata accessor — available on datasets, files, and events alike, though they differ in ways that matter for confirming the write. The dataset's returns nothing, so confirm by re-reading its metadata (which refetches); the file's and event's return the updated instance, and a file's cached metadata will not show the stamp until you re-read from that return value or refresh. Dots in a metadata key create nested fields rather than a flat key, so pick a stamp key without them. Store two things:

- **The issue's identifier**, in whatever form the tracker's update endpoint takes.
- **The issue's URL**, so the link works from the Roboto side without reconstructing it.

Read it back before syncing. A stamp that is absent means create; a stamp that is present means update, subject to the existence check below.

Note the asymmetry that produces sync rule 11: creating the issue is a remote write and stamping is a second remote write, and nothing makes them atomic. The window between them is small and it is the only way this action produces permanent duplicates.

## The tracker side

### The four calls

A sync client needs exactly four operations. Keeping it to four is what makes a second provider a new module rather than a rewrite (sync rule 16):

| Operation | Purpose |
|---|---|
| **Create** | File a new issue with title, body, and labels. Returns the identifier and URL to stamp |
| **Fetch one** | Confirm a stamped issue still exists. A not-found response means create fresh; **any other failure means assume it exists** (sync rule 2) |
| **Update** | Overwrite an existing issue's body and labels |
| **Set state** | Close or reopen |

Each takes a timeout (sync rule 10) and returns a result rather than raising (sync rule 9).

### Differences between providers

Verify every row against the tracker in front of you rather than trusting a table. These are the axes on which trackers actually differ, and each has produced a surprise:

- **Authentication.** The header name and token format differ. So does what an insufficient scope looks like: sometimes a clear 403, sometimes a 404 that reads as "no such project".
- **Project identity.** A numeric id, a slug, a `group/project` path, a key. Path forms usually need URL-encoding, including the separator.
- **Unknown labels.** Created on first use, rejected, or silently dropped (sync rule 7). The third is the one to actually test for.
- **State on create.** Some trackers cannot create an issue in a closed state, so a closed record requires create-then-close — two calls, with the window between them visible to anyone watching the project.
- **Body format.** Markdown flavors differ in table support, in how links render, and in what they do with unrecognized syntax.
- **Rate limits.** Differ by provider and by plan, and matter as soon as a trigger fires this action across a backlog.
- **Idempotency support.** Most issue-tracker APIs have no idempotency key for issue creation; do not design around one existing. If yours does — or accepts a client-supplied issue id — use it, since it narrows the sync rule 11 window considerably. Confirm against your instance first.
- **Self-hosted versus cloud.** Same product, different version, different available fields. Check the instance, not the vendor's current documentation.

### Rendering the body

The body is the deliverable a human reads. Include:

- A **header** naming the entity, linking to it, and linking to the invocation that produced the issue (sync rule 4).
- The **findings**, as prose where an analysis produced prose.
- A **table** for structured findings — labels with their justifications, events with their times — since a bare list of tags does not explain itself.
- **Openable links.** Rewrite Roboto's internal URI scheme into web URLs (sync rule 6). The pattern is a regular substitution: find the `roboto://` references, percent-encode each URI, and pass it to the web app's open endpoint as a query parameter. Neither the SDK nor the public docs specify that endpoint — it lives in the web app — so confirm the current form against the app before relying on it.

Keep rendering in functions that take plain values and return a string. They are the easiest thing in this action to test and the most likely thing to be wrong.

## The sync decision, in order

```
read the stamp from the entity
├─ absent                       -> create, then stamp (sync rule 11)
└─ present
   └─ does the issue exist?
      ├─ yes                    -> update body + labels, then set state
      ├─ no (definitively)      -> create, then re-stamp
      └─ check failed           -> assume yes, update (sync rule 2)
```

State follows the clean-result posture (sync rule 3): a run with no findings closes, a run with findings reopens, and both are no-ops when the issue is already in that state.

## What "verified" means here

The property is not that an issue appeared. It is that **running twice leaves exactly one issue**. Establish it by listing the project's issues, not by reading the action's log — the log records what the action believed, and the belief is what is under test.

The deleted-issue path deserves its own run because it is the one nobody stages by hand: delete the issue in the tracker, run again, and confirm a fresh issue is created and re-stamped without raising. Issue boards get tidied; a stamp pointing at a deleted issue is a matter of when.

## Out of scope

Nothing in this contract flows from the tracker back into Roboto. Closing an issue does not clear a tag, and a comment on an issue does not reach the dataset. If a user wants that, it is a different action reading the tracker on a schedule, and it should be scoped as such rather than bolted onto this one.
