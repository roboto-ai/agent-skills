# RoboQL quick reference

RoboQL is the query language for searching datasets, files, topics, message paths, events, collections, and sessions in Roboto. This file condenses the three pages under https://docs.roboto.ai/roboql/ (`roboql/overview`, `roboql/fields`, `roboql/example_queries`) so you can write a first query without fetching them. The field lists were copied from the live docs on the date recorded as `verified-on` in the `metadata` block of `SKILL.md`. When a query fails on a field name, fetch `roboql/fields` with `scripts/roboto_docs.py` and trust that page.

## Where RoboQL runs

| Surface | How |
|---|---|
| Python SDK | `from roboto import RobotoSearch` (a top-level import; `roboto.query` does not export it), then `RobotoSearch.from_env().find_datasets(q)`, `find_files(q)`, `find_topics(q)`, `find_message_paths(q)`, `find_events(q)`, `find_collections(q)`, `find_devices(q)`, or `find_sessions(q)`. `from_env` reads `ROBOTO_ORG_ID`; the bare `RobotoSearch()` constructor passes no org and fails for users in more than one org |
| Actions | `--file-query`, `--topic-query`, and `--session-query` on `roboto actions invoke` and `invoke-local`. These flags are mutually exclusive with dataset and file-path input |
| Web app | The search bar |
| CLI `datasets search` | Does not take RoboQL; it filters by `--tag` and `--metadata` only. Use the SDK to run RoboQL from a script |

## Syntax

```
<condition> [AND|OR <condition> ...] [SORT BY <field> ASC|DESC] [LIMIT <n>]
```

- A condition is `field <comparator> value`. Values are quoted strings, numbers, or the Boolean literals `true` / `false`. A quoted `"true"` is the string, not the Boolean.
- Group with parentheses: `(a = "x" AND b > 1) OR c = "y"`.
- `*` means "no conditions": `* SORT BY created DESC LIMIT 10`.
- The docs advise pairing `LIMIT` with `SORT BY`; without a sort, the returned subset is arbitrary.
- Metadata keys use a dotted path: `metadata.vehicle_id = "sn_1234"`. Bracket syntax such as `metadata["release"]` is not valid.
- `created` and `modified` on every entity compare as ISO 8601 strings: `created >= "2024-05-01"`. Event `start_time` and `end_time` accept either an ISO 8601 string or Unix epoch nanoseconds: `start_time > "2024-09-09T16:38:26.941-07:00"`. Topic `start_time` and `end_time` are epoch nanosecond timestamps; compare them to integers, not date strings.

### Comparators

| Comparator | Applies to |
|---|---|
| `=`, `!=` | Every field except `tags` and `msgpaths` |
| `<`, `<=`, `>`, `>=` | Timestamps and numbers: `size`, `message_count`, `schema_version` |
| `CONTAINS`, `NOT_CONTAINS` | Strings (substring match), including IDs such as `dataset_id`; `tags` (membership), which accepts no other comparators |
| `LIKE`, `NOT_LIKE` | Strings; SQL-style patterns with `%` |
| `IS_NULL`, `IS_NOT_NULL` | The docs list these only for file `ingestion_status` |

Which comparators `metadata.<key>` accepts depends on the type of the stored value.

### Entity references

An entity reference groups several conditions onto one related entity. `files[0]` and `files[1]` refer to two different files. A label in the brackets works the same way, and the docs offer it for readability:

```
(files[bag].path CONTAINS ".bag" AND files[bag].size > 2000000000) AND
files[video].path CONTAINS "takeoff.mp4"
```

The available references depend on the entity type being queried:

| Query type | References available |
|---|---|
| datasets | `files[i]`, `topics[i]` |
| files | `dataset`, `topics[i]` |
| topics | `dataset`, `file`, `msgpaths[<topic>.<path>]` |
| message paths | `dataset`, `topic`, `file` |
| events | `collection.collection_id` (alias `collection.id`), which filters to events in one collection |
| collections | None |

`msgpaths[...]` requires the log to have been ingested by a format action (ROS, PX4, and others from the Action Hub), and the reference must end in a statistic. The statistic suffixes are `count`, `max`, `mean`, `median`, `min`, `p25`, `p75`, `p95`, `p99`, and `stddev` (the members of `roboto.domain.topics.MessagePathStatistic`), plus `true_count` and `false_count` on Boolean paths. Check any other suffix against `roboql/fields` or a test query. Example: `topics[0].msgpaths[cpuload.load].mean > 0.8`.

## Fields by entity

Sortable fields are marked with an asterisk.

**Datasets:** `created`\*, `created_by`\*, `dataset_id` (alias `id`), `description`, `device_id`, `metadata.<key>`, `modified`\*, `modified_by`, `name`, `org_id`, `tags`.

**Files:** `association_id` (aliases `dataset_id`, `collection_id`)\*, `created`\*, `created_by`\*, `description`, `device_id`, `file_id` (alias `id`)\*, `ingestion_status`, `metadata.<key>`, `modified`\*, `modified_by`\*, `name`\*, `org_id`, `origination`, `relative_path` (alias `path`)\*, `size`\*, `status`, `tags`, `upload_id`, `uri`.

**Topics:** `association_id` (alias `file_id`)\*, `association_type`\*, `created`\*, `created_by`\*, `end_time`\* (epoch nanoseconds), `message_count`\*, `metadata.<key>`, `modified`\*, `modified_by`\*, `msgpaths` (alias `fields`)\*, `org_id`, `schema_checksum`, `schema_name`, `schema_version`, `start_time`\* (epoch nanoseconds), `topic_id` (alias `id`)\*, `topic_name` (alias `name`)\*.

**Message paths:** `canonical_data_type`, `created`\*, `created_by`\*, `data_type`, `message_path` (aliases `name`, `path`, `field`)\*, `message_path_id` (alias `id`)\*, `metadata.<key>` (pre-computed statistics are stored here, for example `metadata.max` and `metadata.mean`), `modified`\*, `modified_by`\*, `topic_id`\*.

**Events:** `created` (alias `created_at`)\*, `created_by`\*, `description`, `end_time`\*, `event_id` (alias `id`; `=` and `!=` only), `metadata.<key>`, `modified` (aliases `modified_at`, `updated_at`)\*, `modified_by`\*, `name` (alias `event_name`)\*, `org_id` (`=` and `!=` only), `start_time`\*, `tags`.

**Collections:** `collection_id` (alias `id`; `=` and `!=` only)\*, `created`\*, `created_by`\*, `description`, `name`\*, `resource_type` (`file`, `dataset`, or `event`; `=` and `!=` only), `tags`, `updated`\*, `updated_by`\*. The modification timestamp is `updated`, not `modified`.

**Sessions** (from the `RobotoSearch.find_sessions` docstring; the RoboQL docs pages do not list them): `session_id` (alias `id`)\*, `name`, `min_timestamp_ns` (alias `start_time`)\*, `max_timestamp_ns` (alias `end_time`), `duration`\* (`max_timestamp_ns - min_timestamp_ns`; integer nanoseconds only), `dataset.dataset_id` (alias `dataset.id`; `=` and `!=` only; sessions that include a file from that dataset), `device.device_id` (alias `device.id`; `=` and `!=` only), `collection.collection_id` (alias `collection.id`; `=` and `!=` only), `metric.<name>` (alias `metrics.<name>`; dots are part of the metric name, as in `metric.cpu.load.max`). On `metric.<name>`, the value comparators need a number and match only sessions that have the metric; `IS_NOT_NULL` and `EXISTS` match sessions that have it at any value, `IS_NULL` and `NOT_EXISTS` those that lack it. The four time fields accept epoch nanoseconds, `<sec>.<nsec>` strings, ISO 8601, or a `datetime`.

**Devices:** the RoboQL docs pages list no fields. `RobotoSearch.find_devices` exists, but the docs do not say which fields it filters on; fetch `roboto.RobotoSearch.find_devices` with `scripts/roboto_docs.py` to read its docstring.

## Examples from the docs

Datasets:

```
* SORT BY created DESC LIMIT 5
created >= "2024-05-01" AND created < "2024-05-31" AND metadata.vehicle_id = "sn_1234"
(files[0].size > 2000000000 AND files[0].path CONTAINS ".bag") AND files[1].path CONTAINS "takeoff.mp4"
topics[0].msgpaths[cpuload.load].mean > 0.8 AND tags CONTAINS "Night"
```

Files:

```
* SORT BY size DESC LIMIT 10
dataset.tags CONTAINS "Rainy" AND path CONTAINS ".ulg"
topics[0].msgpaths[vehicle_air_data.baro_alt_meter].max > 1000 AND topics[1].msgpaths[cpuload.load].mean < 0.4
metadata.release = "2.4.0"
```

Topics:

```
name = "vehicle_angular_velocity" AND created >= "2024-04-28T11:00-07:00" AND created < "2024-04-28T12:00-07:00"
file.size < 10000000 AND message_count > 10000
msgpaths[battery_status.connected].false_count > 0 AND msgpaths[battery_status.connected].true_count > 0
dataset.metadata.softwareVersion = "3.14" AND name CONTAINS "camera"
```

Message paths:

```
data_type = "uint8[]" AND created > "2024-09-25"
topic.name = "/camera/front/image" AND file.tags CONTAINS "crash"
```

Events:

```
name CONTAINS "spike" AND start_time > "2024-09-09T16:38:26.941-07:00"
name = "Lane Change" AND tags CONTAINS "London"
```

## Eventual consistency

Search reads (`RobotoSearch.find_*` and the results or counts of submitted queries) are eventually consistent. The docs (`learn/sdk`, "Handling Eventual Consistency") say replication lag is typically under one second and that most data replicates within one to two seconds. A script that creates or tags something and then searches for it immediately may not see it. Retry with a brief delay. When you already know the ID and need guaranteed consistency, use a direct lookup such as `Dataset.from_id`, which the docs recommend over search.
