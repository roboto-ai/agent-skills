# Map of docs.roboto.ai

Read this before fetching anything. It says which page answers which kind of question, so you fetch one page instead of several. Page paths are relative to `https://docs.roboto.ai/`; pass them to `scripts/roboto_docs.py fetch <path>`. The page list was generated from the site's index on the date recorded as `verified-on` in the `metadata` block of `SKILL.md`. If a path here returns an error, run `scripts/roboto_docs.py search <term>` and use what the live inventory says. The inventory also has four table-of-contents pages this map leaves out because they hold only links: `index`, `learn/index`, `reference/index`, and `roboql/index`.

## How the site is organized

| Section | Path prefix | Answers |
|---|---|---|
| Get Started | `getting-started/` | Creating an account, personal access tokens, `~/.roboto/config.json` |
| Learn Roboto | `learn/` | What each concept is and how it behaves: datasets, files, topics, events, actions, triggers, agents |
| User Guides | `user-guides/` | Step-by-step tasks. Four of the pages are hubs that mostly link to sub-guides; the User guides table below marks each one |
| RoboQL | `roboql/` | The query language: syntax, every queryable field, worked examples |
| References | `reference/` | Generated API docs for the Python SDK, the CLI, the REST API, and `action.json` |

## Getting started and access

| Page | Title | Fetch it when the question is about |
|---|---|---|
| `getting-started/index` | Get Started | Onboarding overview |
| `getting-started/account` | Account | Sign-up, choosing an Individual or Team account, and a tour of the web app's main pages (Home, Search, Collections, Actions, Action Hub, Settings) |
| `getting-started/programmatic-access` | Programmatic Access | Personal access tokens, the exact `~/.roboto/config.json` layout, device tokens, and a pointer to the REST API |

## Concepts and platform behavior

| Page | Title | Fetch it when the question is about |
|---|---|---|
| `learn/concepts` | Concepts | Definitions of every key term: Action, Agent, Collection, Dataset, Device, Event, File, Goal, Image, Ingestion, Invocation, MCP, Secret, Skill, Thread, Topic, Trigger. Start here for "what is a ..." |
| `learn/sdk` | SDK & CLI | How the SDK and CLI relate, install pointers, first examples, eventual consistency, and the retry pattern |
| `learn/actions` | Actions | What actions are; the lifecycle (develop, test, deploy, invoke); `action.json` basics; invocations; and triggers (types, for-each mode, required inputs, conditions) |
| `learn/collections` | Collections | Curated, versioned groups of datasets, files, or events; sharing and deletion. The page does not mention sessions, which can also belong to a collection (`find_sessions` filters on `collection.collection_id`) |
| `learn/compute` | Compute | Compute credits: the credit formula, representative profiles, and every vCPU and RAM combination an invocation can request |
| `learn/devices` | Devices | Registering robots, device access tokens, device-attributed uploads |
| `learn/formats` | Formats | The supported log formats (ROS 1 and 2, PX4, ArduPilot, Parquet, CSV, video, journal) and the action that ingests each |
| `learn/secrets` | Secrets | Storing third-party API keys and passing them to actions |
| `learn/storage` | Storage | Where files live, bring-your-own S3 bucket, import from external storage |
| `learn/ai/index` | Agents | Overview of Roboto's AI features |
| `learn/ai/agents` | Agents and Threads | Starting agent threads, streaming their events, forking a thread, client tools |
| `learn/ai/goals` | Goals | Structured outcomes attached to one turn of a thread, which the AI must achieve before the turn completes; the three goal types (dataset summary, dataset triage, create events), how to declare them, and how to read their results |
| `learn/ai/skills` | Skills | Roboto's stored, versioned Markdown procedures for its AI. These are not Agent Skills for coding agents |
| `learn/ai/mcp` | MCP Connections | Connecting external MCP servers into Roboto's agents |
| `learn/ai/mcp-server` | Roboto MCP Server | What `mcp.roboto.ai` exposes to Claude Code, Cursor, and other clients |
| `learn/ai/slack` | Roboto in Slack | What the `@Roboto` Slack app does in both directions (asking Roboto from a channel, agents posting to approved channels) and how it decides who can do what |

## User guides

| Page | Title | Fetch it when the question is about |
|---|---|---|
| `user-guides/index` | User Guides | The list of guides plus links to blog walkthroughs |
| `user-guides/get-started-ros` | Get Started | Uploading and ingesting a ROS log (`.bag` for ROS 1; `.mcap` or `.db3` for ROS 2) in the web app |
| `user-guides/get-started-px4` | Get Started | Uploading and ingesting a `.ulg` log in the web app |
| `user-guides/working-with-ros-logs` | Working with ROS Logs | Hub page only: preparation steps and links to the ROS get-started, visualize, search, and trigger guides. Fetch the sub-guide, not this page |
| `user-guides/working-with-px4-logs` | Working with PX4 Logs | Hub page only: preparation steps and links to the PX4 get-started, visualize, auto-tag, search, trigger, and flight review guides. Fetch the sub-guide, not this page |
| `user-guides/search-ros` / `user-guides/search-px4` | Search Data | Searching ROS or PX4 datasets and files with RoboQL by metadata, tags, and message path statistics (min, max, mean, median, boolean counts) |
| `user-guides/visualize-ros` / `user-guides/visualize-px4` | Visualize Data | The visualizer's panel types (plot, log, map, raw; image for ROS), console log search, sharing a workspace by URL, and, for ROS, comparing multiple logs. UI walkthrough only: for what a layout or workspace holds as data, see `domain/layouts` below and the cookbook's layouts section |
| `user-guides/trigger-ros` / `user-guides/trigger-px4` | ROS Triggers / PX4 Triggers | Enabling or creating the ingestion trigger (`ros_ingestion` or `ulog_ingestion`) in the web app so uploads ingest automatically |
| `user-guides/auto-tag-px4` | Auto-Tag Logs | Running the `roboto-public/tag_ulog` Action Hub action, which tags ULog files with `ERROR_<module>` from console log errors |
| `user-guides/create-events-on-data` | Create Events on Data | Creating events that link datasets, files, topics, or message paths to a timespan, and retrieving them with the SDK |
| `user-guides/plot-transform-functions` | Plot Transform Functions | Transforming signals in plots, and when to use a derived topic instead |
| `user-guides/working-with-collections` | Working with Collections | Building and versioning collections |
| `user-guides/running-your-first-action-cli` | Run Your First Action (CLI) | Creating a dataset, uploading a bag, invoking an Action Hub action with `roboto actions invoke`, and following it with `roboto invocations status --tail`. Take the invoke flags and the action name from `references/cli-cookbook.md` or `roboto actions invoke --help` rather than from this page |
| `user-guides/running-your-first-action-ui` | Run Your First Action (UI) | The same first-action walkthrough in the web app |
| `user-guides/creating-your-own-action` | Create Your Own Action | Scaffolding, building, and deploying an action. To build one end to end, use the `create-roboto-action` skill instead of this page |
| `user-guides/process-data-actions` | Process Data with Actions | Hub page only: links to the two run-your-first-action guides and create-your-own-action |
| `user-guides/process-data-agents` | Process Data with Agents | Hub page only: how agents differ from actions, then links to the auto-triage and auto-curate guides |
| `user-guides/auto-triage-robotics-data` | Auto-Triage Your Data | Building skills that define triage labels and an agent with goals that tags each new flight log, marks events on its timeline, and writes a triage report as the dataset summary |
| `user-guides/auto-curate-skills-agents` | Auto-Curate Your Data | Building a skill that defines an event of interest and an agent with a goal that creates those events and adds them to a collection |
| `user-guides/flight-review-reports` | Flight Review Reports | Generating, viewing, and sharing a PX4 Flight Review HTML report by invoking the `px4_flight_review` action on a ULog file |
| `user-guides/using-ai-chat` | Using AI Chat | The AI chat sidebar in the web app: opening it, its context awareness, and example prompts. To read or search threads from code, see `ai` below |
| `user-guides/use-roboto-mcp-server` | Use the Roboto MCP Server | Per-client setup for `mcp.roboto.ai` |
| `user-guides/connect-mcp-servers` | Connect MCP Servers to Roboto | Adding third-party MCP servers to Roboto's agents |
| `user-guides/use-roboto-in-slack` | Use Roboto in Slack | Connecting a Slack workspace to an organization, linking your Slack account, asking Roboto from a channel, and approving channels for agents to post into |

## RoboQL

| Page | Title | Fetch it when the question is about |
|---|---|---|
| `roboql/overview` | RoboQL Overview | Syntax, operators, sort and limit, entity references |
| `roboql/fields` | Query Fields | Every queryable field per entity type (datasets, files, topics, message paths, events, collections) with its comparators and whether it sorts |
| `roboql/example_queries` | Example Queries | Worked queries for datasets, files, topics, message paths, events |

`references/roboql.md` in this skill condenses all three. Fetch the live pages when a field name is in doubt.

## References

| Page | Title | Fetch it when the question is about |
|---|---|---|
| `reference/cli` | CLI | Every `roboto` command and option, generated from the CLI's argument parser, so it is complete. The page is large: pass `--max-chars`, or find the option with `search --role cli` |
| `reference/python-sdk` | Python SDK | A table of the eight key classes and a link to the module tree at `reference/python-sdk/roboto/index` |
| `reference/rest-api` | REST API | A one-line stub that links to `https://docs.roboto.ai/restapi.html`, a page too large to fetch as text. Use `python3 scripts/roboto_docs.py restapi <term>` to list matching endpoints and `restapi --path /v1/... [--method get]` to print one endpoint's parameters, request body, and response schema. An endpoint's description says when its reads are eventually consistent |
| `reference/action-json` | Action Configuration | The `action.json` schema |

### Python SDK module pages

Each module has a page at `reference/python-sdk/roboto/<module path>/index`. The public classes you will use most are re-exported from the top-level `roboto` package, so `from roboto import Dataset` works even though the class's page lives under `domain/datasets`. To get one class's section rather than the whole module page, fetch the symbol: `scripts/roboto_docs.py fetch roboto.domain.datasets.Dataset`.

| Module | Main classes | What it covers |
|---|---|---|
| `domain/datasets` | `Dataset` | Creating, looking up, tagging, uploading to, and downloading from a dataset; listing its files and topics |
| `domain/files` | `File`, `IngestionStatus`, `FileStatus` | Per-file metadata, download, and the topics on a file |
| `domain/topics` | `Topic`, `MessagePath`, `RepresentationSelector`, `CanonicalDataType` | Time-series access: `get_data`, `get_data_as_df`, message path statistics |
| `domain/events` | `Event` | Time-range annotations on datasets, files, topics, message paths |
| `domain/collections` | `Collection`, `CollectionResourceType` | Curated groups of resources |
| `domain/actions` | `Action`, `Invocation`, `Trigger`, `ScheduledTrigger`, `ComputeRequirements`, `InvocationSource` | Invoking actions, reading invocation status and logs, event and cron triggers |
| `domain/devices` | `Device` | Robot registration and device tokens |
| `domain/orgs` | `Org`, `OrgRoleName` | Organization membership and administration |
| `domain/users` | `User` | The calling user |
| `domain/secrets` | `Secret` | Secrets for actions |
| `domain/tokens` | `Token` | Access tokens |
| `domain/comments` | `Comment` | Comments on entities |
| `domain/metrics` | `Metric`, `MetricDefinition` | Publishing and aggregating custom metrics |
| `domain/custom_fields` | `CustomField` | Org-defined typed fields on entities |
| `domain/skills` | `Skill` | Roboto's AI skills |
| `domain/views`, `domain/layouts`, `domain/dashboards` | record and request types only | Saved views, visualizer layouts, and metric dashboards. No domain class: read and write them with `RobotoClient` against the endpoints `restapi layout` (or `view`, `dashboard`, and `viz` for workspaces) lists; the cookbook's layouts section has the pattern |
| `roboto_search` | `RobotoSearch` | The RoboQL entry point: `find_datasets`, `find_files`, `find_topics`, `find_message_paths`, `find_events`, `find_collections`, `find_devices`, and `find_sessions` |
| `query` | `QuerySpecification`, `Condition`, `ConditionGroup`, `Comparator`, `QueryClient` | Structured (non-RoboQL) queries accepted by `Dataset.query`, `File.query`, `Action.query`, `Invocation.query`, and `Trigger.query` |
| `ai` | `AgentThread`, `AISummary`, `ClientTool` | Starting agent threads from code, streaming their events, and reading an existing thread (`AgentThread.from_id`, then `transcript`, `messages`, `status`) |
| `analytics` | `find_similar_signals`, `Match` | Signal similarity search; needs the `analytics` extra |
| `action_runtime` | `InvocationContext`, `ActionInput` | Code that runs inside an action; the `create-roboto-action` skill covers it in depth |
| `time` | `to_epoch_nanoseconds`, `TimeUnit` | Converting seconds, `"<sec>.<nsec>"` strings, ISO 8601, and datetimes to epoch nanoseconds |
| `http` | `RobotoClient` | The HTTP client: `from_env`, `for_profile`, raw `get`/`post` for endpoints without a domain class |
| `config`, `env` | `RobotoConfig`, `RobotoEnv` | How credentials and `ROBOTO_*` environment variables resolve |
| `exceptions` | `RobotoNotFoundException`, `RobotoUnauthorizedException`, and others | Error types to catch |
| `experimental/sessions`, `experimental/topics`, `experimental/video` | `Session`, session-scoped `Topic`, frame extraction | Newer APIs that live under `roboto.experimental`. Import with `from roboto.experimental.sessions import Session`; the module form `import roboto.experimental.sessions as x` fails. They raise `ExperimentalWarning` on first use; scripts ignore it at the top, as the cookbook template shows. `experimental/video` needs the `video` extra |
| `formats/mcap`, `formats/parquet` | | Low-level readers used by ingestion actions |

## Outside docs.roboto.ai

| Resource | URL | Use |
|---|---|---|
| SDK README | https://raw.githubusercontent.com/roboto-ai/roboto-python-sdk/refs/heads/main/README.md | The install instructions that the SDK & CLI page on docs.roboto.ai defers to: SDK (pip, extras), CLI (Homebrew, `.deb`, standalone binaries), and the command that connects the Roboto MCP server |
| SDK source | https://github.com/roboto-ai/roboto-python-sdk | The implementation, for when a docstring is not enough |
| Latest CLI release | https://github.com/roboto-ai/roboto-python-sdk/releases/latest | Binaries for Linux, macOS, and Windows, and the version number to compare against `roboto --version` |
| Example notebooks | https://github.com/roboto-ai/roboto-python-sdk/tree/main/examples | `fetch-topic-data`, `analyze-px4-topic-data`, `analyze-1000-px4-flights`, `similarity-search`, `agent_thread_client_tools.py` |
| PyPI | https://pypi.org/project/roboto/ | The latest SDK version |
| Action Hub | https://app.roboto.ai/actions/hub | Ingestion actions per format and other published actions |
| Web app | https://app.roboto.ai | Where tokens are created: Settings, then Tokens |
