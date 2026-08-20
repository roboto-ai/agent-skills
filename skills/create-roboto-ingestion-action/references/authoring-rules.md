# Ingestion authoring rules

These supplement the general action authoring rules in `create-roboto-action`; they do not replace them. Every rule there about the runtime contract, dry-run gating, output handling, packaging, and tests still applies. The rules below are the ones specific to writing topics.

Cite the rule number when a requirement forced a choice.

## The ingestion contract

1. **A topic without a registered representation is invisible to every data-access call.** Creating a topic and adding message paths produces a metadata-only container: it appears in listings, it has a schema, it looks ingested — and fetching its data returns nothing. This is the defining failure mode of hand-written ingestion, because nothing errors. The DataFrame path registers the representation for you; the low-level path does not, and you must do it explicitly. Verify by reading the data back (SKILL.md Phase 4, step 3), never by listing topics.

2. **Timestamps are nanoseconds since the UNIX epoch.** Whatever the source format uses — seconds, milliseconds, microseconds, a boot-relative counter, a vendor epoch — convert it. A format whose clock is relative to power-on has no UNIX timestamp at all, and the offset has to come from somewhere; find it, or record in the spec that the timeline is relative and what that costs.

3. **A numeric timestamp column needs its unit stated explicitly.** The DataFrame path can infer a timestamp column when it is a timezone-aware datetime, but a column of numbers is ambiguous by construction, and the SDK requires the unit rather than guessing. Passing seconds while declaring milliseconds produces data that ingests cleanly and is wrong by three orders of magnitude — visible only when someone tries to align two topics.

4. **Choose each field's canonical type deliberately.** The canonical type is Roboto's normalized type, and it is what enables the platform's typed features — plotting numbers, rendering images, reading timestamps, handling arrays. The enum includes an explicit fallback for genuinely unknown types; the SDK's own documentation says to use it sparingly. Typing a column of floats as unknown because it was easier is a silent feature loss that only re-ingestion fixes. Read the enum for the current members.

5. **Topic names are unique within a file, and should be stable across files.** A name that embeds a per-file identifier, a timestamp, or a session id makes fleet-wide querying impossible: the same signal from two recordings becomes two unrelated topics. Preserve the source's own stream names when it has them, and put the varying part in metadata rather than in the name.

6. **Make ingestion idempotent, and know which tier gives it to you.** The DataFrame path updates an existing topic of the same name on the same file in place, so re-running converges. The low-level path has no such guarantee: creating a topic that already exists conflicts, and adding a message path that already exists conflicts. Handle both, because triggers retry and operators re-invoke. Verify by ingesting the same file twice and confirming the record count did not double.

7. **Capture units at ingestion time or lose them.** A unit belongs on the message path where it is declared. It is not recoverable afterwards without re-ingesting every file, and a fleet's worth of unlabelled radians-or-degrees is a problem that compounds daily. Where the source format does not record units, ask the user; where the user does not know, record that gap in the spec explicitly rather than leaving the field bare and unremarked.

## Input handling

8. **Bad input is a data error, not a crash.** A corrupt, truncated, empty, or wrong-format file is not a defect in the action, and the runtime has a defined exit code that says exactly that. Report it, with a message naming the file and what was wrong. This is what lets whoever debugs the invocation later look at the data instead of at your code — and it is the distinction `debug-roboto-invocation` is built around.

9. **The sample file outranks the format documentation.** Vendor specs describe intent; the file describes fact. Field orders differ, optional fields are absent, versions drift, and endianness surprises. Parse defensively, and report every place the file contradicted the document — that discrepancy is often the most useful thing the user learns from this work.

10. **Name nested fields carefully, and preserve the source path.** Message paths use dots to express nesting, which means a source field whose own name contains a dot is ambiguous under that convention. The SDK accepts the source path as a separate list precisely for this, so the platform can address the attribute correctly regardless of how the display name reads. Use it whenever the source schema is nested or its names are not dot-safe.

11. **Decide what happens when one stream fails to parse.** Ingesting the remaining streams and reporting the failure is usually right for a trigger-driven action, since one malformed stream should not cost the whole file. Failing the whole file is right when partial data would be misleading. Whichever you choose, log which streams were skipped and why — a silently partial ingestion is worse than either option.

## Packaging

12. **Declare the extra the chosen tier needs, as a runtime dependency.** The DataFrame path needs the SDK's ingestion extra; reading topic data back needs the analytics extra. They are different extras, and an action that ingests through frames and also reads data back needs both. An extra left in the dev dependency table works locally and raises an import error inside the container.

13. **Declare the parsing library's system packages in the Dockerfile.** Format parsers routinely link against system libraries or shell out to binaries that are present on a workstation and absent from a container image. This fails only in the container, which is the most expensive place to discover it.

14. **Size compute against the largest expected file, not the sample.** The sample is small because samples are small. Ask what the largest real recording is, and size memory and storage for it. A DataFrame holds the whole stream in memory, so a format that streams comfortably can still exhaust an under-sized container.

## Tests

15. **Test the parser, not the platform.** Format parsing is the substance of an ingestion action and is testable without any network: keep it in module-level functions taking a path and returning frames or plain values, and test those against a small fixture checked into the repository. Choose a fixture you are permitted to redistribute — a truncated real recording is often fine, a customer's full log usually is not. The platform-facing layer above the parser stays thin enough not to need its own tests.

## Documentation

16. **Record the format inventory in the spec.** The table produced in Phase 1 — streams, fields, types, units, record counts — is frequently the only written description of the user's format that exists anywhere. It belongs in the delivered repository, alongside what was deliberately not ingested and why.

17. **Do not describe the generating process in the project's own docs.** No references to this skill, its phases, an interview, or `--yolo`. The repository documents the ingestion action: what format it reads, what topics it produces, and how to run it.
