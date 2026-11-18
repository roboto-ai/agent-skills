# Script template

The skeleton of `trigger.py`, the script Phase 2 writes into the trigger directory and Phases 3 and 4 run.

The skeleton below was run against the SDK release recorded as `verified-sdk` in the `metadata` block of `SKILL.md`, on the date recorded as `verified-on`, with `--check` and `--help` only (no request was sent to Roboto), and it passed `ruff check`. A newer release can change any call in it: re-check what you use against source 1 of SKILL.md's "Sources, in order of authority". Where this file and a live source disagree, the live source wins.

## Skeleton

Run with no flags, the script creates the trigger, or updates it in place when one named `NAME` exists, enabled and with its real condition: that is the go-live command, and it is the user's to run. `--guard FIELD=VALUE` ANDs `FIELD EQUALS VALUE` onto the condition (Phase 4), `--check` validates locally and sends nothing (Phase 3), and the script exits non-zero when the saved `enabled` differs from the one requested (rule 24).

Replace `NAME`, `FIRES_ON`, `CONDITION`, `TARGETS` and the docstring's first line, which `--help` prints, with the Phase 1 decisions. Keep the rest as it is.

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["roboto"]
# ///
"""Create or update the summarize-mcap-on-ingest trigger: run summarize-mcap on each ingested MCAP file.

SPEC.md, next to this file, records why the trigger is shaped this way.
"""

import argparse
import json
import os
import sys
import warnings

from roboto.warnings import ExperimentalWarning

warnings.filterwarnings("ignore", category=ExperimentalWarning)

from roboto.domain.actions import ActionReference, InvocationInput  # noqa: E402,F401
from roboto.domain.platform_events import OncePer, PlatformEventType  # noqa: E402
from roboto.domain.triggers import (  # noqa: E402
    CreateTriggerRequest,
    EventSubscription,
    InvokeActionTarget,
    Schedule,  # noqa: F401
    Trigger,
    TriggerValidator,
)
from roboto.exceptions import RobotoNotFoundException  # noqa: E402
from roboto.query import Comparator, Condition, ConditionGroup, ConditionOperator  # noqa: E402

NAME = "summarize-mcap-on-ingest"

FIRES_ON = EventSubscription(events=[PlatformEventType.FileIngested], once_per=OncePer.File)
# A schedule instead: FIRES_ON = Schedule(cron="0 6 * * *")  # 06:00 UTC every day

CONDITION = Condition(field="dataset.tags", comparator=Comparator.Contains, value="production")
# No condition: CONDITION = None

TARGETS = [
    InvokeActionTarget(
        target_id="summarize",  # keep stable: the once-per history is stored under this id
        action=ActionReference(name="summarize-mcap"),
        required_inputs=["**/*.mcap"],
        parameter_values={"threshold": 0.8},
    ),
]
# On session.ingested, no file patterns; select the session instead:
#     invocation_input=InvocationInput.from_session_id("{{session.session_id}}"),


def condition_with(guard):
    """The trigger's condition, ANDed with a guard that pins it to one test subject."""
    if guard is None:
        return CONDITION
    field, _, value = guard.partition("=")
    pin = Condition(field=field, comparator=Comparator.Equals, value=value)
    if CONDITION is None:
        return pin
    return ConditionGroup(operator=ConditionOperator.And, conditions=[pin, CONDITION])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--org", default=os.environ.get("ROBOTO_ORG_ID"), help="org ID (default: ROBOTO_ORG_ID)")
    parser.add_argument("--guard", metavar="FIELD=VALUE", help="pin the trigger to one test subject")
    parser.add_argument("--disabled", action="store_true", help="save the trigger disabled")
    parser.add_argument("--check", action="store_true", help="validate locally and print the request; send nothing")
    args = parser.parse_args()

    enabled = not args.disabled
    condition = condition_with(args.guard)
    TriggerValidator().validate(fires_on=FIRES_ON, condition=condition, targets=TARGETS)
    request = CreateTriggerRequest(name=NAME, fires_on=FIRES_ON, condition=condition, targets=TARGETS, enabled=enabled)
    if args.check:
        print(request.model_dump_json(indent=2, exclude_none=True))
        return

    try:
        trigger = Trigger.from_name(NAME, owner_org_id=args.org)
    except RobotoNotFoundException:
        trigger = Trigger.create(
            NAME, TARGETS, fires_on=FIRES_ON, condition=condition, enabled=enabled, caller_org_id=args.org
        )
    else:
        # Outside the try: an update that names a missing action also raises RobotoNotFoundException.
        trigger.update(fires_on=FIRES_ON, condition=condition, targets=TARGETS, enabled=enabled)

    print(json.dumps(trigger.to_dict(), indent=2))
    if trigger.enabled != enabled:
        print(f"Asked for enabled={enabled}, saved as enabled={trigger.enabled}.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

Without uv, the inline metadata block is a comment, and the same file runs under the session's virtual environment (`<venv>/bin/python trigger.py`).
