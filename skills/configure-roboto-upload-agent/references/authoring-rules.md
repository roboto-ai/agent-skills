# Upload agent configuration rules

Each rule names either a failure mode that keeps data from reaching Roboto, or one that destroys it on the way. Cite the rule number when a requirement forced a choice.

## The two files

1. **Two config files, two scopes. Do not conflate them.** The **agent config** is one per machine and says where to look: the directories to scan, the marker filename to look for, and the machine-wide deletion settings. The **per-directory marker** is one per recording, and its presence is what marks a directory as a dataset to upload; it carries that dataset's own name, description, metadata, tags, device id, collections, and per-directory include and exclude patterns. Putting a dataset's tags in the agent config, or a search path in a marker, silently does nothing — the models ignore unknown structure differently than you expect, and neither field takes effect.

2. **The completion marker is the agent's memory.** Once a directory has been uploaded, the agent writes a completion file into it naming the dataset the data went to, and every later run skips that directory on sight. This is what makes a continuously running agent safe, and it is the answer to "why won't it re-upload": delete that file and it will. A completion file that cannot be parsed is still treated as a reason to skip, deliberately, so a corrupted marker looks exactly like a finished upload.

## Deletion — the rules that destroy data

3. **Deleting uploaded files removes the local copy, and on a robot that is often the only copy.** The agent deletes after its own notion of a successful upload. Never enable it before a full round trip has been verified against the live platform, never enable it without the user's explicit word — including under `--yolo` — and verify it separately, on data the user can afford to lose. Confirm the dataset is complete in Roboto **before** confirming the files are gone locally; the other order teaches you nothing you want to learn that way.

4. **Empty-directory cleanup is narrower than it sounds, and is still deletion.** A directory is removed only when it is empty or holds nothing but the completion marker; anything else left behind stops it. That makes it safe against surprises and also means it will quietly not fire whenever a stray file remains, which is a support question waiting to happen. It is most useful paired with file deletion, and inherits every caution in rule 3.

## Scanning and markers

5. **An in-progress marker means resume, not restart.** A directory carrying one is picked up again and uploaded into the dataset that marker names, rather than into a new one. This is what makes an interrupted upload safe, and it is worth testing deliberately (SKILL.md Phase 3 step 7) rather than discovering during an outage. Deleting an in-progress marker by hand orphans its dataset and causes the next run to create a second one.

6. **Auto-creation of markers looks exactly one level under each search path.** Directories nested more deeply are not considered, and neither is the search path itself. A layout that nests recordings two levels down gets no markers and uploads nothing, with a log that reports finding no markers rather than an error. Check the depth of the real layout against this before relying on auto-creation.

7. **Never let the agent see a directory that is still being written.** It will upload what exists at that moment and write a completion marker, and that marker means it will never revisit the directory. The reliable pattern is for whatever ends a recording to write the marker as its last act — which makes the marker mean "this recording is finished" rather than "this directory exists". Where that is impossible, the search paths must exclude the directory a recording is written into until it is done.

8. **The concurrency lock makes a second instance a silent no-op — and an orphaned lock stops everything just as silently.** Overlapping runs are harmless by design: the second exits without uploading, so a scheduler firing during a long upload is fine. The cost is that a lock left behind by a killed process makes every subsequent run do nothing while logging that the agent appears to already be running. This belongs in the runbook, because it presents as "uploads just stopped" with no error anywhere.

## Credentials and operation

9. **Credentials must be non-interactive and must survive a reboot.** The agent reads them from the environment, and a headless machine has nobody to complete an interactive login. A credential exported in an interactive shell profile works during setup and is absent under a service manager — which is the single most common reason an agent that worked yesterday is not running today. Put it where the service unit can see it, and record its expiry in the spec.

10. **Merge mode resolves collisions last-write-wins, in a non-deterministic order.** Merging every upload into one dataset applies each marker's dataset properties as sequential updates, so two markers with different descriptions, or different values for the same metadata key, produce whichever the traversal happened to reach last. Do not use merge mode where the dataset's properties matter; use it where the grouping matters and the properties are uniform.

11. **Environment variables interpolate in the default marker template.** The template used for auto-created markers resolves environment variable references, which is how a fleet distinguishes machines without a per-machine config file — a hostname, a robot id, or a software version can land in dataset metadata that way. The values come from the environment the agent runs in, which under a service manager is not the user's interactive environment.

12. **Never put a secret in a marker file.** It lives on the machine's disk, inside the directory being uploaded, and it is uploaded along with everything else unless excluded. It is for identifying and describing a dataset, not for credentials.

13. **Collection membership is best-effort.** A marker can ask for its dataset to be added to collections; a failure there is logged and does not fail the upload. The data arrives and the curation silently does not, so check collection membership as part of verifying the round trip rather than assuming it followed.

## Delivery

14. **Verify before automating, and verify on the machine that will run it.** A configuration proven by one manual run, one repeat run, and one interrupted run is a configuration a service manager can be trusted with. One that has never uploaded anything is a hypothesis about paths that may not exist on that host. Deliver both config files, the service unit, and the runbook as a directory under version control rather than as edits made in place, so the next machine is a copy rather than a re-derivation.
