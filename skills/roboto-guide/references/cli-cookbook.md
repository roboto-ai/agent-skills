# roboto CLI cookbook

Worked commands for the `roboto` CLI. Every command and flag below was checked against the CLI bundled with the roboto wheel from PyPI at the release recorded as `verified-sdk` in the `metadata` block of `SKILL.md` (`uv run --with 'roboto[analytics]' python -m roboto.cli <group> <command> --help`) and against the CLI source in that wheel. Output shapes were confirmed from the source and, for some commands, from a read-only run.

The installed CLI's `--help` describes the version the user is running. The docs page `reference/cli` is generated from the latest release's argument parser and describes that release. When the two disagree, the user's CLI is out of date (see "Version check" below).

## Conventions

- **Output is usually JSON, but the shape varies.** `datasets show`, `datasets create`, `actions show`, `invocations show`, `triggers get`, `collections show`, and `orgs show` print one JSON object. `datasets search`, `actions search`, `actions list-invocations`, and `invocations status` (the status log) print a JSON array; `invocations status --tail` prints one JSON object per new status as it arrives. `users orgs`, `orgs members`, `collections list`, `triggers search`, `tokens list`, `secrets list`, and `devices list` print one JSON object per item rather than an array. `jq -r .org_id` works on that stream; `python -m json.tool` does not, because it parses a single document, and `jq '.[]'` fits only the array-shaped commands. `datasets list-files` prints one dataset-relative path per line. `actions invoke`, `upload-files`, `download-files`, `tokens create`, `secrets write`, `invocations logs`, and `invocations cancel` print human-readable text. Progress bars and the upgrade notice go to stderr.
- **Global flags work before or after the subcommand.** `roboto --log-level INFO datasets show ...` and `roboto datasets show ... --log-level INFO` are equivalent because the entry point re-parses leftover arguments. The global flags are `--log-level {ERROR,WARNING,INFO,DEBUG}` (case-insensitive, default ERROR), `--profile <name>`, `--config-file <path>`, `--cache-dir <path>`, `--suppress-upgrade-check`, `--version`, and `--verbose`/`-v`, which the help text marks DEPRECATED in favor of `--log-level`. The exception is a subcommand that defines a flag with the same name: the subcommand takes the trailing form. `devices register` and `devices generate-creds` have their own `-f`/`--config-file` (the output file for device credentials), and `collections show` has its own `-v` (`--collection-version`), so put the global `--config-file` or `-v` before those subcommands.
- **Org selection.** A user in one org never needs `--org`. A user in several orgs must pass `--org <og_...>` on org-scoped commands (create, search, invoke, list) or set `ROBOTO_ORG_ID`. List the org IDs with `roboto users orgs`.
- **IDs are prefixed.** Datasets `ds_`, invocations `iv_`, and collections `cl_` per the `learn/concepts` page; organizations `og_` (printed by `users orgs`) and files `fl_` (the `file_id` field of file records). Actions are addressed by name, optionally qualified: `<name>`, `<name>@<digest>`, `<org_id>/<name>`, `<org_id>/<name>@<digest>`. The `<org_id>` part is the owning org's ID; Roboto's public Action Hub actions are owned by `roboto-public`, so `roboto-public/ros_ingestion`. An unqualified name resolves in the calling org (`--org`, or the user's only org), so Action Hub actions owned by another org must be qualified. Digests are the 32 hex characters printed in the `digest` field of `actions search` output, not `sha256:...`.
- **Short flags differ per command.** `-d` is `--dataset-id` on `datasets` commands but `--description` on `datasets create`. Check `--help` before reusing a short flag.
- **`datasets search` does not take RoboQL.** It filters on `--tag` and `--metadata key=value` only. The CLI accepts RoboQL only as `--file-query`, `--topic-query`, and `--session-query` on `actions invoke` and `invoke-local`; for any other RoboQL query, use the SDK.
- **Most destructive commands run without confirmation.** `datasets delete`, `datasets delete-files`, `actions delete`, `collections delete`, `triggers delete`, `devices delete`, `tokens delete`, `secrets delete`, `images delete-image`, `images delete-repository`, `invocations cancel`, `invocations cancel-all`, `orgs remove-user`, and `orgs remove-role` have no prompt. The exceptions: `orgs delete` and `users delete` ask for y/n confirmation (skip it with `--ignore-prompt`), and `actions create` asks before overwriting an existing action of the same name (skip it with `--yes`). Show the user the exact command and get an explicit yes before running a destructive command.

## Version check

```bash
roboto --version
# Latest release:
curl -s https://api.github.com/repos/roboto-ai/roboto-python-sdk/releases/latest | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"])'
```

The CLI also prints an upgrade notice on stderr when a newer version exists. To upgrade, per the SDK README: `brew upgrade roboto` on macOS; on Linux and Windows, download the new binary or `.deb` from the latest release and replace the old one.

## Identity

```bash
roboto users whoami        # who the token belongs to, org memberships, token id
roboto users orgs          # every org the user belongs to, printed as one JSON object per org (not an array)
roboto orgs show --org og_xxx
roboto orgs members --org og_xxx
```

## Datasets

```bash
# Create, with optional name, description, tags, metadata, device
roboto datasets create --name "Run 42" -t nightly -t px4 -m vehicle_id=sn_1234 --org og_xxx

# Look up
roboto datasets show -d ds_xxx
roboto datasets search --tag px4 --metadata vehicle_id=sn_1234 --org og_xxx

# Update tags and metadata (JSON values parse; dotted keys nest)
roboto datasets update -d ds_xxx --put-tags reviewed --put-metadata 'release=2.4.0' 'stats.max_alt=120'
roboto datasets update -d ds_xxx --remove-tags nightly --remove-metadata stats.max_alt

# Files
roboto datasets list-files -d ds_xxx -i '**/*.ulg'
roboto datasets upload-files -d ds_xxx -p ./logs/            # a file or a directory
roboto datasets upload-files -d ds_xxx -p ./logs/ -x '**/*.tmp'
roboto datasets download-files -d ds_xxx -p ./out -i '**/*.mcap'
roboto datasets rename-file -d ds_xxx -f fl_xxx -p new/relative/path.ulg
roboto datasets import-external-file -d ds_xxx -f s3://bucket/key.ulg -p logs/key.ulg   # from a registered S3 bucket; -p defaults to the filename at the dataset root
```

Include and exclude filters are glob patterns. `upload-files` has `-x` only; `list-files`, `download-files`, and `delete-files` have both `-i` and `-x`. On `upload-files` and `download-files`, the filters apply when `-p` points to a directory.

`--metadata` on `search` and `-m` on `create` try to parse each value as JSON and fall back to a string, so `serial=1234` becomes the number 1234 and `serial=sn_1234` stays a string. To store or match a string that looks like a number, wrap it in JSON quotes inside the shell quotes: `--metadata 'serial="1234"'`.

## Actions and invocations

```bash
# Discover
roboto actions search --org og_xxx
roboto actions search --actionhub                 # published to the Action Hub
roboto actions show ros_ingestion                 # resolves in the calling org only
roboto actions show roboto-public/ros_ingestion  # Action Hub action, qualified by the owning org's ID
roboto actions show roboto-public/ros_ingestion@<digest>   # pinned to one version; digest is 32 hex chars

# Invoke on hosted compute against a dataset
roboto actions invoke roboto-public/ros_ingestion --dataset ds_xxx --file-path '**/*.bag' --org og_xxx   # Action Hub action, qualified by the owning org's ID
roboto actions invoke my-action --dataset ds_xxx -p threshold=0.8 -p mode=fast
roboto actions invoke my-action --file-query 'dataset.tags CONTAINS "nightly" AND path LIKE "%.ulg"'
roboto actions invoke my-action --topic-query 'name = "cpuload" AND msgpaths[cpuload.load].mean > 0.8'
roboto actions invoke my-action --dataset ds_xxx --output-dataset-id ds_yyy --vcpu 2048 --memory 8192 --timeout 120

# Follow an invocation (ids start with iv_)
roboto invocations status --tail iv_xxx
roboto invocations logs --tail iv_xxx
roboto invocations show iv_xxx
roboto actions list-invocations my-action --org og_xxx
roboto invocations cancel iv_xxx
```

`-p` / `--parameter` values are raw strings; the action parses them. `--file-path` takes a dataset-relative path or glob and can be repeated; it requires `--dataset`. The selector flags (`--file-query`, `--topic-query`, `--session-query`, `--session-id`) are mutually exclusive with `--dataset` and `--file-path`. `--memory` (MiB) must be one of the values allowed for the chosen `--vcpu`; the `learn/compute` page lists them. `--timeout` is in minutes.

For local invocation and authoring (`roboto actions init`, `invoke-local`, deploy scripts), use the `create-roboto-action` skill; it covers the Docker workspace, where `--log-level` goes, and the terminal that `invoke-local` needs in non-interactive shells.

## Triggers

```bash
roboto triggers create --name ingest-bags --action roboto-public/ros_ingestion \
  --required-inputs '**/*.bag' --for-each dataset_file --required-tag ros --org og_xxx
roboto triggers get ingest-bags
roboto triggers search --org og_xxx
roboto triggers update ingest-bags --disabled            # or --enabled; other fields update the same way
roboto triggers delete ingest-bags
```

`--parameter-value` on triggers parses JSON, unlike `-p` on `actions invoke`, which takes raw strings. Cron-scheduled triggers exist only in the SDK (`ScheduledTrigger`).

## Collections

```bash
roboto collections create --name "Crash candidates" --dataset-id ds_a ds_b --tag triage --org og_xxx
roboto collections list --org og_xxx
roboto collections show cl_xxx --content-mode references
roboto collections update cl_xxx --add-dataset-id ds_c --remove-dataset-id ds_a --add-tag reviewed
roboto collections changelog cl_xxx
```

## Secrets, tokens, devices, images

```bash
roboto secrets write my-api-key "$(cat key.txt)"   # name and value as positionals
roboto secrets list
roboto tokens create --name ci-token --expiry-days 30
roboto devices register <device_id> --org og_xxx     # also writes the device's credentials to ./config.json (-f to choose the path); errors if that file exists
roboto devices generate-creds <device_id> --org og_xxx  # new credentials file for an existing device
roboto devices list --org og_xxx
roboto images login --repository-uri <uri>          # Docker login to Roboto's registry, valid for 12 hours and scoped to that repository; --permissions {ReadOnly,ReadWrite}
```

Never print a secret value or the contents of `~/.roboto/config.json` into the conversation.

## Chat

```bash
roboto chat start      # interactive terminal session with Roboto's AI agent; --org selects the org
```

## Patterns

Pick fields out of JSON output with `jq`:

```bash
roboto datasets search --tag px4 --org og_xxx | jq -r '.[] | "\(.dataset_id)\t\(.name)"'
```

Invoke and wait for a terminal status in a script. `actions invoke` prints text rather than JSON, a single line of the form `Queued invocation of '<action ref>'. Invocation ID: '<iv_...>'`, so extract the ID with `grep`:

```bash
iv=$(roboto actions invoke my-action --dataset ds_xxx --org og_xxx | grep -o "iv_[A-Za-z0-9]*")
roboto invocations status --tail "$iv"
roboto invocations logs "$iv"
```

Run the same commands without the standalone binary from any Python environment that has the SDK installed:

```bash
python -m roboto.cli users whoami
```
