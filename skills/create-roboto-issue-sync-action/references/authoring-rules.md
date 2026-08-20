# Issue-sync authoring rules

These supplement the general action authoring rules in `create-roboto-action`; they do not replace them. Every rule there about the runtime contract, dry-run gating, parameter validation, packaging, and tests still applies. The rules below are the ones specific to writing into a system outside Roboto.

Cite the rule number when a requirement forced a choice.

## Identity

1. **Identity is a decision, and it must be recorded on the Roboto side.** An issue tracker has no idea which Roboto entity an issue came from, so the link has to be stored by you: stamp the created issue's identifier onto the entity the issue represents — a dataset's metadata, a file's metadata, an event — and read that stamp before every sync to decide create-or-update. Without the stamp there is no correct behavior available: searching the tracker by title is guesswork, and creating unconditionally files a duplicate on every re-analysis. Decide *which* entity carries the stamp deliberately, because that choice is the definition of "the same issue".

2. **When the existence check fails, assume the issue exists.** Before updating a stamped issue you must confirm it is still there, because people delete issues. That check can also fail for reasons that have nothing to do with the issue: a timeout, a rate limit, a proxy. Treating those as "gone" files a duplicate every time the network hiccups, which is the worst failure mode this action has — it is silent, it compounds, and it is discovered by a human scrolling a polluted issue list. Fail toward "exists"; a missed update is recoverable, a duplicate is manual cleanup.

3. **Decide what a clean result produces, and say so.** Three answers are defensible and they produce very different issue lists: file nothing; file an issue in the closed state as a record that the analysis ran; or update an existing issue to closed. The third is not optional if you chose either of the first two and also want state to track reality — a finding that clears should close its issue, and a finding that returns should reopen it. Whatever the choice, the open-issue list should mean exactly one thing, and the spec should say what.

4. **Link in both directions.** The issue body carries links back to the dataset and to the invocation that produced it; the Roboto entity carries the issue's URL alongside its identifier. Someone reading the issue can reach the data, and someone looking at the data can reach the issue. Half of this is easy to forget, and the missing half is always the one somebody needs.

## Credentials

5. **Credentials arrive as secrets, never as literals.** Store the token in Roboto's secret store and pass its secret URI as a parameter; the runtime resolves it at invocation time. Never a literal token in `action.json`, in the repository, on a command line, or in a trigger's parameter values. Rotating a credential should mean updating the secret, not redeploying the action.

## Content

6. **Rewrite platform-internal URIs into browser-openable links.** Findings frequently reference data using Roboto's own URI scheme, which renders in an issue as inert text. Rewrite those into ordinary web URLs before posting, so a reader can click from the issue straight into the visualizer at the referenced signal and time. An issue whose evidence cannot be opened is a paragraph of assertions.

7. **Know what your tracker does with an unknown label.** Providers differ, and the difference is not cosmetic: some create a label on first use, some reject the request, some silently drop the unknown ones and apply the rest. That third behavior is the dangerous one, because the issue is created successfully and is missing exactly the information it was filed to convey. Verify empirically against the scratch project, and if labels must pre-exist, either provision them or degrade to putting the finding in the body.

## Failure and degradation

8. **Unconfigured degrades; it does not fail.** When the tracker parameters are absent, the action should still do its job on the Roboto side and persist the rendered report where the user can read it. This keeps the action useful for someone who has not set up a tracker yet, and it makes the whole action testable without any tracker at all.

9. **Tracker calls return results; they do not raise into the sync path.** Wrap each call, log what failed with the status and the response body, and return an outcome the caller decides on. The failure posture — fail the invocation, or log and continue — is then a decision made in one place rather than an exception escaping from four.

10. **Every tracker call has a timeout.** An HTTP client with no timeout can hang until the invocation's own timeout kills it, turning a slow tracker into a failed action with no useful log. Set one explicitly on every request.

11. **Stamp before you can lose the stamp.** If the create call succeeds and the write of the stamp then fails, the next run has no record of the issue and files a second one. Treat create-and-stamp as an operation that must not be half-done: confirm the stamp landed, retry it on failure, and if it still fails, log the issue's identifier at error level so the link can be restored by hand. This is the one place where a silent partial failure produces duplicates indefinitely.

12. **Never log the credential, and check that you don't.** It is easy to log a request object, a header dict, or an exception carrying the whole request. Verify with a deliberately invalid token (SKILL.md Phase 4, step 7) and read the resulting log: if the token appears, the action leaks it into the invocation logs of every failed run, where it is durable and readable by anyone who can read invocations.

13. **Treat a placeholder-looking parameter value as unset.** A parameter whose value came from templating can arrive as the literal placeholder text rather than as absent, when whatever should have substituted it did not. A tracker base URL that is obviously not a URL should be handled like a missing one rather than sent to a request builder that will fail confusingly much further along.

14. **Never let a tracker failure lose the findings.** The findings are the valuable part; the tracker is a destination for them. Write the report to the Roboto side first, then sync. If the sync fails, the work survives and the run can be repeated. The reverse order means a tracker outage discards an analysis.

15. **Dry run cannot preview an external write.** Gate the sync on the dry-run flag like any other side effect, and log the issue that would have been created or updated, with its title, labels, state, and target. Be honest in the spec that the dry-run path exercises everything except the call itself, so local verification does not substitute for the real gate.

## Structure

16. **Keep provider specifics inside the client.** Endpoint shapes, identifier encoding, auth header names, label semantics, and how state is changed all belong in one thin module. The rest of the action should not know which tracker it is talking to. This is what makes the sync logic testable with a fake, and what makes adding a second provider a new module rather than a rewrite.

17. **Write the spec so the identity rule is the first thing a reader learns.** What makes an issue the same issue, where that is recorded, and what a clean result produces. Someone changing this action later will change one of those three, and the spec is where they find out what the current answer is and why.
