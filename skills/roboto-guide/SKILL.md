---
name: roboto-guide
description: >-
  Answer questions about Roboto (the robotics data platform at roboto.ai) and
  write roboto CLI commands or ad hoc Python SDK scripts against it. Use this
  skill whenever the user mentions Roboto, RoboQL, the roboto CLI, "import
  roboto", or Roboto datasets, files, topics, message paths, sessions, events,
  actions, invocations, triggers, collections, devices, or agents, and whenever
  they ask how to search, upload, download, tag, annotate, or analyze robotics
  logs stored in Roboto. Not for building a new Roboto Action end to end; hand
  that to the create-roboto-action skill.
license: MPL-2.0
compatibility: >-
  Needs a shell and network access to docs.roboto.ai, pypi.org,
  files.pythonhosted.org, raw.githubusercontent.com, and api.github.com.
  uv is recommended for running scripts against the latest SDK. The roboto CLI
  and Roboto credentials are needed only to run commands or scripts against a
  Roboto organization.
metadata:
  verified-sdk: "0.55.0"
  verified-on: "2026-09-09"
argument-hint: <question about Roboto, or a task to do with the roboto CLI or SDK>
---

Give correct, current answers about Roboto, and produce CLI commands or SDK scripts that run on the first try against the latest release. The documentation and the SDK change faster than any file in this skill, so look things up.

## What you need to run this

This skill does not know which agent is reading it, so it names capabilities rather than tools:

- **Run shell commands** and read their output, for the docs lookup script and for `uv` or a Python virtual environment.
- **Read files**, for the references alongside this file.
- **Write files**, when the user wants a script saved.
- **Fetch a web page**, optionally. The bundled script covers docs.roboto.ai without a fetch tool; a fetch tool helps for GitHub and PyPI.

Nothing else is required. `uv` is the preferred runner because it resolves the latest SDK on every run and supplies a new enough Python when the system lacks one. Without it, build one virtual environment for the session as `references/sdk-cookbook.md` ("Without uv") shows, and use its interpreter wherever this file says `uv run`. If neither `uv` nor Python 3.11 is available, install `uv` first; the cookbook lists the one-line installers.

If your agent runtime can start a subagent, run the lookups in one and return only the answer, so fetched page text stays out of the main conversation. If it cannot, keep lookups small with the script's `--max-chars` flag.

Throughout, `references/` and `scripts/` mean the directories alongside this file.

## Learn the machine first

Run `python3 scripts/roboto_docs.py env` once per session before anything else (on Windows, `py -3 scripts\roboto_docs.py env`). It prints the platform and shell, the Python that ran it and whether the SDK can use it, whether `uv` and the `roboto` CLI are on `PATH` with their versions, whether credentials are present, and the runner to use, without printing a secret. Then run `versions` (under "Sources, in order of authority"). Decide from that output:

- **Runner.** `uv run` when `uv` is present; otherwise the virtual environment the cookbook's "Without uv" section builds, at the path `env` prints.
- **Command form.** Every command in this skill is written for a POSIX shell. On Windows, read `python3` as `py -3`, `bin/` as `Scripts\`, and check quoting before running; `references/platforms.md` translates the commands for PowerShell and cmd and says where the credentials file and caches live on each platform.
- **Credentials.** If `env` reports none and the task needs them, go to "Get started" step 2 now rather than failing at the first API call.

## Sources, in order of authority

Three sources outrank every file in this skill. They are numbered by authority: when two disagree, the lower number wins. Start with the source whose Answers column fits the question, and stop at the first source that answers it.

| Source | What | How | Answers |
|---|---|---|---|
| 1 | The latest released SDK, resolved fresh from PyPI | `uv run --refresh-package roboto --with 'roboto[analytics]' python -c "import inspect, roboto; print(inspect.signature(roboto.Dataset.upload_file))"` | Exact signatures, parameter names, defaults, enum members, docstrings |
| 2 | docs.roboto.ai | `python3 scripts/roboto_docs.py search <term>` then `fetch <page or symbol>` | Concepts, how-tos, RoboQL fields, CLI options for the latest release, REST endpoints with their parameters and schemas (`python3 scripts/roboto_docs.py restapi <term>`, then `restapi --path <path>`) |
| 3 | The SDK README and GitHub releases | Fetch https://raw.githubusercontent.com/roboto-ai/roboto-python-sdk/refs/heads/main/README.md and https://api.github.com/repos/roboto-ai/roboto-python-sdk/releases/latest | Install instructions, extras, latest version numbers, the command that connects the Roboto MCP server (`claude mcp add --transport http roboto https://mcp.roboto.ai/mcp`) |

The files under `references/` rank below all three. One is a map of the docs site; the others are condensed copies of doc pages and worked commands. The `metadata` block in this file's frontmatter records the SDK release (`verified-sdk`) and date (`verified-on`) they were last checked against; each file's first paragraph gives the method. Run `python3 scripts/roboto_docs.py versions` once per session: it compares that stamp with the latest release on PyPI and GitHub and prints the installed CLI version. When a newer release exists, re-check anything you take from these files against source 1 before using it. They tell you what to look up and how to phrase it. Cite the live source, not the reference file.

Three rules follow:

- **The installed CLI and SDK are not authoritative.** They are whatever version the user last installed, and `roboto <command> --help` describes that version and nothing else. `python3 scripts/roboto_docs.py versions` prints the installed CLI version next to the latest release tag (the CLI itself also prints a "new release of roboto is available" notice on stderr when it is behind). If it is behind, say so and point to the SDK README's "Upgrade CLI" section (`brew upgrade roboto` for Homebrew installs; elsewhere, download the new binary or `.deb` and replace the old one). Write scripts against the latest release, and tell the user when a call needs a newer version than they have.
- **Verify every SDK call against source 1 before handing over a script.** `references/sdk-cookbook.md` alone is not enough; check every signature you used in this session. A parameter name the release does not accept fails the script at that call.
- **Recommend the API that fits the task, and describe it by what it does.** Some newer APIs, sessions among them, raise `ExperimentalWarning` on first use. Every script ignores it at the top, as the cookbook template shows, and the warning is not a reason to steer the user elsewhere. A session is the right starting point for any question about a flight, drive, or run rather than a file, so lead with it when it fits instead of reconstructing the run from files.

If the Roboto MCP server (`mcp.roboto.ai`) is connected in the agent runtime, its tools can search the user's data and answer questions from the documentation. Prefer it for questions about the user's own datasets.

The MCP server's tools do not modify or delete existing data. The ones that write only add new records, such as visualizer layouts or thread forks, acting as the signed-in user. The one exception is sending a message to a thread: Roboto's AI then answers as the user and can do anything it can do in AI Chat, so treat that tool as a write. The MCP server never replaces the CLI or SDK for writes.

## Classify the request

Decide which of these you are doing, because the procedure differs:

1. **Get started**: "How do I install Roboto?", "How do I set this up?", "I just signed up, what now?"
2. **Explain**: "What is a message path?", "How do triggers evaluate?", "Which formats ingest?"
3. **Do it with the CLI**: "Upload this directory", "Tail the logs of that invocation."
4. **Write a script**: anything that loops, filters, joins entities, touches topic data, or needs pandas.
5. **Answer about the user's data**: "Which of my datasets have a cpuload topic above 0.8?" This needs the user's credentials.

A request to build a reusable, deployable action ("an action that tags every dataset where...") belongs to the `create-roboto-action` skill. Say so and stop, unless the user asks for a one-off script instead.

## Get started

1. Read `references/getting-started.md`. It orders the onboarding path: account, access token and `~/.roboto/config.json`, CLI install per platform, SDK install with extras, first upload and ingestion, first look at the data, optional MCP connection.
2. Fetch the SDK README (source 3) and confirm that the install commands and the latest release still match the reference before quoting them. The README changes with each SDK release.
3. The `env` output names the operating system; ask whether they want the CLI, the SDK, or both, and give only the steps for that platform and that answer. `references/platforms.md` has the per-platform install table.
4. When you can run commands on their machine, verify each step as you go: `roboto --version` after the install, `roboto users whoami` after the token. Report the output you saw. If `whoami` reports that no config file was found, the error names the path it looked in (`~/.roboto/config.json` unless `ROBOTO_CONFIG_FILE` overrides it); check that path first.
5. Finish with the next step, usually the first upload and ingestion for their log format, and the docs page for that format.

## Explain

1. Read `references/docs-map.md` and pick the one or two pages that answer the question. `learn/concepts` covers definitions; the user guides cover tasks; `roboql/` covers queries.
2. Fetch them: `python3 scripts/roboto_docs.py fetch learn/concepts --max-chars 8000`. To fetch one section instead of a page, use an anchor (`learn/concepts#topics-section`) or a symbol name (`roboto.domain.topics.Topic.get_data`).
3. If the map has no page for it, search the site's index: `python3 scripts/roboto_docs.py search trigger --role doc`. Roles: `doc`, `label`, `cli`, `module`, `class`, `function`, `attribute`.
4. For the objects the web app saves (visualizer layouts and workspaces, saved views, dashboards, AI Chat threads), the docs pages describe the UI only. Answer what they contain and what can be read or written from the SDK record types and the REST endpoints: `python3 scripts/roboto_docs.py restapi layout` (or `viz`, `view`, `dashboard`, `thread`), then `--path` for a schema. The cookbook's "Layouts, views, dashboards, workspaces, and AI threads" section has the read pattern.
5. Answer in your own words, then give the URL you used so the user can read further. If two pages disagree, or a page reads as stale against source 1, say which you trusted and why.

Do not summarize a page you did not fetch. If the lookup fails (no network, page missing), say what you could not check and answer with that caveat.

## Do it with the CLI

1. Read `references/cli-cookbook.md` for the conventions (JSON output, where global flags may go, `--org` for multi-org users, ID prefixes) and a worked command close to the task.
2. Confirm the exact flags against the user's installed version with `roboto <group> <command> --help`, since that is the version that will run. If a flag exists only in a newer release, tell the user to upgrade; do not guess.
3. Give the command in a fenced block. Write placeholders literally as `ds_xxx` and `og_xxx`, and add a line saying what each stands for. When you run the command yourself, read the JSON output back before reporting the result.

Do not run a `delete`, `delete-files`, `delete-image`, `delete-repository`, `cancel`, `cancel-all`, `remove-user`, or `remove-role` subcommand until the user has confirmed the exact command; only `orgs delete` and `users delete` prompt on their own. Do not print the contents of `~/.roboto/config.json`, a token, or a secret value into the conversation.

## Write a script

1. Read `references/sdk-cookbook.md` for the script template, authentication, and the pattern nearest the task (search, datasets and files, topics, sessions, events, actions, agents, layouts and threads).
2. Verify each call against source 1. One `uv run` invocation can print several signatures.
3. Write the script with the inline-metadata header from the cookbook so `uv run script.py` resolves the latest SDK (without `uv`, the session's virtual environment runs the same file). Put the SDK version you verified against in the docstring.
4. Make it read-only unless the user asked for a write. A script that creates, uploads, tags, invokes, or deletes says so at the top and takes `--dry-run` when the user did not ask for the write outright.
5. Run it, or at least `uv run script.py --help`, when you can run commands and the script is read-only. Report the output you saw. Do not claim it runs if you did not run it.
6. Bound every search with a `LIMIT` clause or `itertools.islice`. Print IDs next to names.
7. For topic data and analytics, index before you fetch. Build the index the cookbook describes under "Index a dataset before analyzing it" (files, topics, message paths with types and precomputed statistics) and save it under `roboto-index/`. Choose topics, message paths, and time windows from that file, fetch only those, and reread the file for follow-up questions instead of rebuilding it. For a run that spans files or devices, work from a session and its session-scoped topics.

RoboQL is the search language for datasets, files, topics, message paths, events, collections, and sessions; `references/roboql.md` has the syntax and every field. The CLI accepts RoboQL only as `--file-query`, `--topic-query`, and `--session-query` on `actions invoke` and `invoke-local`; `datasets search` does not, so a RoboQL search from the command line means writing a script.

## Answer about the user's data

Data questions need the user's credentials and touch their org, so make the access explicit:

1. Check identity first: `roboto users whoami` or `User.for_self()` in a script. If the user belongs to several orgs, ask which one, or use the one they named. If the org names or data look unfamiliar, print `RobotoClient.from_env().endpoint` from a script: a profile can point at a deployment other than `api.roboto.ai`, and IDs, Hub listings, and behavior differ between deployments.
2. Scope every org-scoped call to that org. On the CLI, pass `--org`. In a script the parameter name depends on the call: query and lookup methods such as `Dataset.query` and `Action.from_name` take `owner_org_id`, create methods such as `Dataset.create` take `caller_org_id`, RoboQL searches are scoped with `RobotoSearch.for_roboto_client(client, org_id=...)`, `Session.for_org` takes `org_id`, and the raw client's layout and thread endpoints take `caller_org_id`. The names are not interchangeable, so check each one against source 1.
3. Prefer the Roboto MCP server when connected; its tools do not modify or delete existing data (see the thread-message exception under "Sources, in order of authority").
4. Otherwise write a read-only script as described under "Write a script", show it, run it, and report the results with IDs.

## Hand off

End with the answer or the artifact, then add one or two lines naming the source you verified against (page URL, SDK version) and anything you could not verify. Do not restate the procedure.
