# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Indigo plugin (current version in `Contents/Info.plist`) that provides InfluxDB data logging for Indigo home automation. It connects to an external InfluxDB server and logs device/variable state changes for time-series visualization (typically used with Grafana).

**Bundle ID**: `com.vtmikel.grafana`

**Key Architecture Decision**: This plugin is an InfluxDB client only - it does NOT bundle or manage server processes. Users must provide their own InfluxDB (1.7/1.8, or 3 via its v1 API) and Grafana servers.

**Repos**: Gitea `lamoureux-household/indigo-grafana-dashboard` (branch `master`, full history) is the source of truth. GitHub `mlamoure/indigo-grafana-dashboard` is the public copy and is **squash-only since 2026.11.0**: one commit per release, private history stays on Gitea.

## Plugin Structure

```
Grafana Home Dashboard.indigoPlugin/
├── Contents/
│   ├── Info.plist                    # Plugin metadata (PluginVersion, API 3.6)
│   ├── Resources/                    # Plugin icon, mcp-manifest.json
│   └── Server Plugin/
│       ├── plugin.py                 # Main plugin class: connection, writer thread, filters, config UI
│       ├── influx_client.py          # In-house InfluxDB client: line-protocol encoder + HTTP calls
│       ├── influx_settings.py        # Settings validation shared by the dialog, connect() and tools
│       ├── influx_filter.py          # InfluxFilter (data filter rule), prefs record and dict form
│       ├── config_store.py           # ConfigStore: every configuration change goes through apply()
│       ├── mcp_api/                  # MCP tool provider (influxlog_* tools), imported lazily; history.py = query_history
│       ├── Actions.xml               # hidden mcp_tool_invoke action only
│       ├── json_adaptor.py           # Converts Indigo objects to InfluxDB format
│       ├── PluginConfig.xml          # Two-panel config UI (Connection + Inclusion/Exclusion)
│       └── MenuItems.xml             # Advanced features (filters, device exploration)
├── requirements.txt                  # dev/test only (pytest, influxdb==5.3.2 for the encoder comparison)
├── tests/                            # pytest suite + tests/live (InfluxDB 1.8 + 3 container matrix)
├── .gitea/workflows/test.yml         # CI: pytest on Python 3.13
└── README.md                         # User documentation
```

There is no `Server Plugin/requirements.txt`: the plugin uses the `requests` Indigo installs, so Indigo creates no `Contents/Packages`. Don't add one back.

## Core Components

### plugin.py
The main plugin class extends `indigo.PluginBase` and manages:
- **InfluxDB connection**: Connects to external InfluxDB 1.7/1.8 or 3 server (`connect()` serialized by `connectionLock`, never on the callback thread - `requestReconnect()` runs it on a worker)
- **Data pipeline**: Device/variable state changes → InfluxDB writes
- **Filtering system**: Advanced filtering to prevent bad data (value ranges, percentage changes)
- **Configuration**: Two-panel config (Connection settings + Inclusion/Exclusion criteria)
- **Connection management**: Retry logic, auto-recovery

**Important Classes**:
- `Plugin`: Main plugin class with InfluxDB client
- `InfluxFilter`: Data filtering rules (min/max values, percentage change thresholds)

**Key State Variables**:
- `connection`: `InfluxClient` instance (`influx_client.py`)
- `connected` / `connectionState` (`connected`, `connecting`, `retrying`, `stopped_auth_failure`, `invalid_config`) / `lastConnectError`
- `stats`: `WriteStats` - points written, dropped by reason (`queue_full`, `rejected`, `shutdown`, `gave_up`), last success, last error
- `deviceLastUpdated` / `variableLastUpdated`: heartbeat clocks for the minimum update frequency, dicts **keyed by `dev.id` / `var.id` — never by name**. In-memory only; cleared on restart.
- `deviceLocks`: devices a `percentChanged` filter locked out of heartbeats, `{dev id: {since, filter, state}}`. Logged once when taken and once when released (never per poll).
- `DeviceLastWrittenValues` / `PercentChangedStates`: Baseline for `percentChanged` filters on the polling path (which has no `origDev`). Populated **after** filtering, so a blocked value never becomes the baseline that lets its successor through. Deliberately *not* the adaptor's cache — see below.
- `FilterList`: Array of `InfluxFilter` objects for data validation. **Copy-on-write**: edits build a new list and assign it, so `DeviceToInflux` can iterate a snapshot without a lock
- `StatesIncludeList` / `DeviceIncludeList` / `DeviceExcludeList`: guarded by `configLock` (RLock) - the concurrent thread rebuilds and persists them every 15 min while ConfigUI callbacks edit them
- `dialog`: the plugin config dialog's working copy of the include lists; its buttons edit the copy, `closedPrefsConfigUi` commits it unless cancelled
- `stateCatalog` (`{state: device count}`) / `deviceNames`: rebuilt by `BuildConfigurationLists`; the UI list generators compute from these

### influx_client.py
Replaces the archived `influxdb` 5.3.2 client (2026.11.0). The encoder reproduces 5.3.2's `make_line` **byte for byte** (`tests/test_line_protocol.py`; also checked against all ~1,900 production devices/variables) except: NaN/±inf fields are skipped, and a point with no fields is skipped. 5.3.2 escapes tag values like keys (its trailing-space `_escape_tag_value` helper is never called) - keep it that way. Errors: `InfluxConnectionError` (no response), `InfluxHTTPError` (status + decoded message; on InfluxDB 3 parse errors `point_index` names the bad point), `InfluxQueryError` (statement error inside a 200). `check_write_access()` is an empty write: 204 on 1.x; on 3 the token is checked and the empty body refused with 400 (= accepted). On InfluxDB 3 that empty write creates a missing database, as any write would.

### config_store.py — the one owner of configuration changes (#11)
The configuration still lives on the Plugin object (the write pipeline reads it on every device change), but **every change goes through `ConfigStore.apply(source, mutate, dry_run, expected_revision)`**: lock → revision check → mutate a plain copy (`current()`, which has **no secrets**) → diff → `load()` into the plugin → `persistConfig()` → revision + 1 (persisted as the `configRevision` pref). Sources: the plugin config dialog (`commitDialog`), the filters dialog, housekeeping (pruning deleted devices from lists and filter scopes), and the MCP tools. Never assign `StatesIncludeList` / `FilterList` / settings directly from new code.
- The plugin config dialog records `dialogBase()` (revision + the config it opened with) and on save **three-way merges** its changes onto the current config, so an AI edit made while the dialog was open survives; the password is merged the same way by hand (it is never in the store).
- `persistConfig()` writes every plugin-owned pref, connection settings only once `configured` (their presence is what marks the plugin as configured).
- The filters dialog's Edit records `filterEditGuard` (position, name); a save refuses if that position no longer holds that filter.
- **Snapshots**: `beforeCommit` writes the config being replaced to `<Indigo>/Preferences/Plugins/com.vtmikel.grafana.snapshots/<revision>.json` (last 20 kept). `restore_snapshot` restores states/lists/filters/settings, **never the connection**.
- **Password changes** bump `connection.credentials_version` (an in-memory counter in the secret-free config), so a password-only change is still a revision and a snapshot without the store ever holding the secret.

### MCP tool provider (`mcp_api/`, #11)
Contract: `docs/mcp-provider-manifest.md` in indigo-mcp-server. `Contents/Resources/mcp-manifest.json` (prefix `influxlog` → ContextForge `indigo-influxlog-*`), hidden action `mcp_tool_invoke` in `Actions.xml`, `handle_mcp_tool_invoke` imports `mcp_api` **lazily**, `broadcastToSubscribers("mcp_tools_updated")` at startup. `tests/test_mcp_manifest.py` keeps the manifest, `InfluxLogTools.TOOLS`, the handler signatures and Actions.xml in sync. Tools resolve devices by id or exact name (close-match suggestions), put the name next to every id, and use `adaptor.to_json` - **never `diff_to_json`**, which updates the change-detection cache. The InfluxDB password/token never appears in any output (`test_no_secret_anywhere` sweeps replies, log records and snapshot files).
**`query_history` (`mcp_api/history.py`, 2026.12.0)** is the one tool that reads InfluxDB. `prepare()` validates and resolves on the callback thread; the queries run on an `InfluxToolWorker` thread (`AsyncResult`) with a **client of its own** (`newClient(settings)`, 20 s per request, 50 s budget per call; manifest timeout 60 s) - never the writer's session. Every InfluxQL statement is built in `HistoryReader` (epoch seconds; `"name"::tag` because 1.x stores the device name as tag *and* field); `tests/fake_influx.FakeHistoryClient` answers only those statement shapes and `tests/live/test_live_history.py` runs them on both servers - change all three together. Gotchas, verified live:
- InfluxDB 3 (3.10-3.12) refuses a **double quote inside a string literal** ("invalid escape sequence"), so a name containing `"` (e.g. `TV 65"`) is matched with an anchored regex `=~ /^...$/`; InfluxDB 1.x keeps the encoder's escaped `\` as **two** backslashes in a tag, so 1.x lookups double them.
- **Gaps are per device, never per state**: they come from the `id` field (on every device point; `value` for variables). An unchanged state is re-sent only on the heartbeat, and `deviceUpdated` restarts the heartbeat clock whenever *any* state was sent, so a quiet state on a busy device has hour-long holes that are not outages (a lamp's `onState` had 13 h without a point while the lamp wrote every 5 min).
- 1.x reads every retention policy (`autogen` + `indigo_policy`) and merges; InfluxDB 3 has none (and `SHOW RETENTION POLICIES` is refused to a read token). Over `RAW_POINT_CAP` points a series falls back to InfluxDB aggregates (`mean_of_points`, no change list); the raw path's `mean` is time-weighted.
- Read access: 401/403 on a read becomes a `conflict` naming the fix.

Write tools go through `InfluxLogTools._write` → `store.apply` (dry_run, expected_revision, snapshot, one `MCP: <tool> <summary> (revision N)` INFO line). `update_connection` returns an `AsyncResult`: `handle_mcp_tool_invoke` takes `indigo.acquireCallbackCompleteHandler()` and finishes on an `InfluxToolWorker` thread, because its test-then-commit (`Plugin.testConnection`: ping + empty-write access check) does network I/O. A failed test leaves the settings in force unless `force`.

### json_adaptor.py
Converts Indigo device objects to InfluxDB-compatible JSON format:
- Smart type conversion (strings → floats where possible)
- Datetime → Unix timestamps
- Enum → string conversion
- Caching to reduce redundant writes. **This cache is "last seen", not "last written"** — it is updated with the full device *before* `DeviceToInflux`'s filter loop runs, so it records values the filters then block. Never use it as a filter baseline.
- Device liveness fields (`lastChanged`, `lastSuccessfulComm`, `secondsSince*`), emitted on every device point

**Author**: Dave Brown (Copyright 2017, 2018)

### Configuration System

**Two-panel configuration** (`PluginConfig.xml`):

1. **InfluxDB Connection Panel** (`listConfigurationSelector="connection"`):
   - InfluxDB server host, SSL, HTTP port
   - Username/password for InfluxDB connection
   - Database name
   - Retention policy (6mo, 1yr, 2yr, 5yr, disabled)
   - Debug levels: Plugin, Config, Transport (L1/L2), JSON

2. **Inclusion/Exclusion Panel** (`listConfigurationSelector="device"`):
   - Global include states (applies to all devices)
   - Include specific devices (all states sent)
   - Exclude specific devices (never sent)
   - Minimum update frequency (5/10/15/30/60 min to avoid gaps in graphs)

### Advanced Features (MenuItems.xml)

- **Data Filters**: Complex filtering rules to prevent bad values from reaching InfluxDB
  - Min/max value filtering
  - Percentage change thresholds
  - Per-device or global rules
  - Lock minimum frequency updates after filter failure
- **Device Exploration**: Print device JSON to Event Log
- **State Exploration**: Find all devices with a specific state
- **Reset Data Filters**: Clear all filter rules
- **Rebuild Config Dialog**: Refresh configuration lists

## Important Constraints

### InfluxDB Version
**IMPORTANT**: This plugin supports InfluxDB **1.7/1.8** and **InfluxDB 3** (via its v1 compatibility API, selected with the "InfluxDB Version" dropdown in the connection config). It is **NOT compatible** with InfluxDB 2.x. In InfluxDB 3 mode the plugin skips database/retention DDL (servers are pre-provisioned and token-scoped) and drops fields that duplicate tag keys (IOx requires a column to be tag XOR field).

### Write Pipeline (v2026.7.0+)
Writes are asynchronous: producers (`deviceUpdated`, `variableUpdated`, `UpdateAll`) enqueue points with client-side timestamps; a single background writer thread batches them into one `write_points()` call per ~1s flush window (`influxWriterLoop` in plugin.py). This matters because InfluxDB 3 acknowledges each HTTP write only after its WAL flush (~1s default), so synchronous per-point writes cap at ~1 point/sec and back up Indigo's callback queue — which is what made the config dialog unresponsive. Never reintroduce network I/O into Indigo callback methods (that includes `connect()`: startup and `closedPrefsConfigUi` leave it to the concurrent thread / `requestReconnect()`).

**Error classification (2026.11.0, `writeBatch`)** - by HTTP status, never by retrying point by point first:
- **401/403** → credentials refused: `onAuthFailure` (ERROR once, `StopConnectionAttempts`), batch kept, producers stop (`acceptingPoints()` false) until the settings change.
- **404 / 5xx / network** → transient: batch kept, `markDisconnected` → reconnect worker; the writer **pauses** (never drains the queue) while disconnected, and producers keep buffering into the 10,000-point queue once a connection has been made. A batch failing `MAX_BATCH_ATTEMPTS` times is dropped (`gave_up`).
- **400** → data problem: type conflicts are corrected from the **decoded** message (1.x `input field "x" ... already exists as type y`; 3 `column 'x', expected iox::column_type::field::y`) and the typecache learns. 1.x `partial write` means the valid points were stored (only re-send points with the corrected field). InfluxDB 3 rejects the whole batch and names the first bad line → drop that point, retry the rest. Only a 1.x whole-batch 400 without a line falls back to per-point.

**InfluxDB 1.x retention (decision 2026-10-14)**: `indigo_policy` is created as the database **DEFAULT** only on a database the plugin itself just created (`createDatabase` compares `SHOW DATABASES` before its `CREATE DATABASE`); ALTERed when it is the default and the duration differs; `-1` = `INF`. Every other database is left alone with one WARNING and the opt-in command: an install from before 2026.11.0 (non-default `indigo_policy`, data in `autogen`) gets `ALTER ... DEFAULT`, a pre-existing database without the policy (possibly shared with other writers) gets `CREATE ... DEFAULT`. Switching a default would hide history from Grafana panels that don't name a policy and put other writers' data on this plugin's schedule. `CREATE DATABASE` and retention are best effort (non-admin users connect fine).

### Device Liveness Fields (v2026.8.0+)
`diff_to_json` emits `lastChanged`, `lastSuccessfulComm` and derived `secondsSinceLastChanged` / `secondsSinceLastSuccessfulComm` on **every** device point, so a flat line from a *dead* device is distinguishable from a flat line from a merely *quiet* one.

These are **enrichment-only and must never reach the include-states gate.** They are added after the `if not hasUpdate: return None` early-return, so they ride along on points that were already going to be written and add zero new points. Anything in `StatesIncludeList` sets `hasUpdate`, and `lastChanged` moves on every device change — routing them through the include list would emit a point per change per device. For that reason they are deliberately absent from `DEFAULT_STATES` and hidden from the include-states picker (`ALWAYS_SENT_STATES` in plugin.py), though still offered in the filter property picker.

The age fields exist because InfluxQL cannot express `now() - field` in a `SELECT` projection and Grafana's Math expressions have no wall-clock function, so a staleness alert cannot be built from the absolute epochs alone. Note that `lastChanged` alone does not discriminate — a quiet-but-alive device and an offline one both have a frozen `lastChanged`; alert on `secondsSinceLastSuccessfulComm`.

**Scope limit — these detect a device that stopped *communicating*, not one whose *value* is stuck.** Verified on production 2026-08-08: `Living Room Temperature` (the device in issue #7) has had `sensorValue` frozen at exactly 69.1 for 7 days, yet Indigo reports both `lastSuccessfulComm` and `lastChanged` as minutes old — the Z-Wave node still answers, it just never reports a different reading. A healthy sensor polled less recently can therefore look *staler* than this one. Detecting a stuck value is a dashboard-side query (`SELECT spread("sensorValue") ... GROUP BY "name"`, where exactly `0` over 24h means stuck), not something the plugin can flag.

`LIVENESS_SENTINEL_FLOOR` is `2000-01-02T00:00Z`, not `2000-01-01T00:00Z`. Indigo's never-communicated placeholder is 2000-01-01 in **local** time, so on any server west of UTC it lands above a UTC-midnight floor and those devices report as ~26 years stale.

### Python Compatibility
- Python 3.11+ (Indigo 2025.1); production runs Indigo 2025.2 on Python 3.13 - the suite runs on 3.13
- **No third-party packages of its own.** `requests` is part of Indigo's own install set (`IndigoPluginHost3.app/Contents/Resources/installer_requirements.txt`: requests 2.32.5 on 2025.2; 2.31.0 on 2025.1's Python 3.11). Before 2026.11.0 a `Server Plugin/requirements.txt` made Indigo pip-install `influxdb` plus msgpack/pytz/dateutil/six/requests into `Contents/Packages`, ahead of Indigo's own packages on the import path.

### Plugin prefs
- `InfluxRetention` and `MinimumUpdateFrequency` are stored as **strings** (`'24'`, `'15'`, `'-1'`); parse with `influx_settings` (`parse_frequency`, `retention_spec`). Frequency `-1` = no heartbeats; legacy `'smart'` = heartbeats only 23:45-00:15.
- Never configured = no `InfluxHost` pref (the dialog has never been saved). An empty `listIncStates` is a valid configuration (only included devices are logged), not "unconfigured".
- Indigo stores the dialog's **whole** valuesDict on save, including the stale copies of plugin-owned keys (`listFilterList`, the include lists) from when it opened - `closedPrefsConfigUi` re-asserts them via `persistConfig()`.
- `OBSOLETE_PREFS` (v2.x leftovers incl. a plaintext `GrafanaAdminPassword`) are deleted at startup. **Never print prefs without redacting `*Password*`.**
- `filter.log` lives in `indigo.server.getLogsFolderPath(pluginId)`; releases before 2026.11.0 wrote to `~/Library/.../Indigo 2025.1/Logs/...` and the file is moved once.

## Development Workflow

### Tests
```bash
uv venv --python 3.13 .venv && uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/pytest tests/ -q              # offline suite (fake indigo, see tests/README.md)
tests/live/run_influx_matrix.sh         # live influxdb:1.8 + influxdb:3-core matrix (Docker)
```
`conftest.py`'s fake `indigo.Dict` rejects sets/None like the real one - keep it strict. **Every release must pass the live matrix first**, and the README's release notes name the versions it printed. InfluxDB 3 Core allows 5 databases per server: live v3 tests share one database and use unique measurements.

### Deploying to production
```bash
/home/mike/programming/mike-local-development-scripts/deploy_indigo_plugin_to_server.sh \
    "Grafana Home Dashboard.indigoPlugin" /home/mike/programming/indigo-grafana-dashboard
ssh mike@indigo.home.mikelamoureux.net 'bash -c "/usr/local/indigo/indigo-restart-plugin com.vtmikel.grafana"'
```
Check `/Library/Application Support/Perceptive Automation/Indigo 2025.2/Logs/com.vtmikel.grafana/plugin.log` afterwards.

### Releasing
Merge on Gitea first, pass the live matrix, then (the first argument is the **clone's folder name**):
```bash
/home/mike/programming/mike-local-development-scripts/release_indigo_plugin_to_github.sh \
    indigo-grafana-dashboard ~/programming -y --squash --notes-file /path/to/notes.md
```
`--squash` publishes one commit to GitHub (`Release <version>`) and pushes the tag there; the script also creates the annotated Gitea tag and the Gitea release with the same notes and the zip. It finds the Gitea remote by host (`origin` via the `gitea:` alias works) and stops before pushing anything if the Gitea side can't be done. Grep the notes for family names first - the GitHub copy is public. Alignment check: `git rev-parse origin/master^{tree}` vs `github/master^{tree}` (commit SHAs differ in squash mode).

## Common Constants (plugin.py)

```python
DEFAULT_POLLING_INTERVAL = 60          # Main loop polling
FAST_POLLING_INTERVAL = 5              # When connecting to InfluxDB
LONG_POLLING_INTERVAL = 60 * 15        # After many failed connections
UPDATE_STATES_LIST = 15                # Minutes between state list updates
DEFAULT_UPDATE_FREQUENCY = 24          # Hours between update checks
MAX_LOG_FILE_OUTPUT_LINES = 50         # Filter log pruning
LOG_PRUNE_FREQUENCY = 24               # Hours between log pruning

# Default states sent to InfluxDB for all devices
DEFAULT_STATES = [
    "state.onOffState", "onState", "onState.num",
    "model", "subModel", "deviceTypeId", "state.hvac_state",
    "energyCurLevel", "energyAccumTotal", "value.num",
    "sensorValue", "coolSetpoint", "heatSetpoint",
    "batteryLevel", "batteryLevel.num"
]
```

## Known Issues & Technical Debt

### Connection Management
- Connection retry logic with exponential backoff
- After 10 failed attempts, switches to 15-minute retry interval
- Authorization failures stop connection attempts (requires config fix)

### Filter System
The data filtering system (`filterValues` menu item, `influx_filter.py`) is complex:
- Filters are ordered and processed sequentially; a value stops at the first filter it fails (order decides whose lock/log applies)
- Can lock minimum frequency updates after failures
- Silent logging to `filter.log` + optional Event Log logging (the `filter.log` line format is parsed by `mcp_api/filter_log.py` - change both together, including the `threshhold` typo)
- Scope: `all`, `devices` (appliedDevices) or `all_except` (exceptDevices). The prefs record stays format **2.0.0**, with the except list as an optional 11th element: releases before 2026.11.0 read item[0..9] and ignore it, so a rollback keeps every filter (all_except reads as all). Don't bump the format number for additive fields - an older release then loads no filters at all, silently. 1.0.0 (and the pre-release "3.0.0") migrate on load. An unreadable format leaves `listFilterList` untouched in the prefs (`filtersUnreadable`) until the filters are edited explicitly
- Generated names follow the settings (`GENERATED_FILTER_NAME`); a typed name is kept

### Inclusion/Exclusion Logic (plugin.py)
1. **Excluded devices**: Never sent to InfluxDB (highest priority)
2. **Included devices**: All states sent (`diff_to_json(dev, None)` - `None` means all)
3. **All other devices**: Only global include states sent (`diff_to_json(dev, list)` - an **empty** list sends nothing; before 2026.11.0 `[]` meant "all")

Include states missing from every device right now (a device offline) are kept, not pruned. Deleted devices are pruned from the include/exclude lists, the adaptor cache (keyed by device id, no size cap) and the heartbeat/lock dicts.

## Version History

### v2026.12.0 (history tool)
- `influxlog_query_history` (`mcp_api/history.py`): numbers, on/off and text states, time in state, buckets, per-device gaps, no-data reasons; devices, thermostats, weather stations and variables; 1.x retention policies merged
- `InfluxClient.query(..., epoch=)`; `resolve_variable`
- Test fix: `test_legacy_smart_frequency` no longer depends on the real date (it failed from 2026-10-16)

### v2026.11.0 (Own InfluxDB client + code-review fixes, issue #12)
- Archived `influxdb` client replaced by `influx_client.py` on Indigo's `requests`; `Server Plugin/requirements.txt` removed. Encoder byte-identical to 5.3.2 except NaN/inf and field-less points skipped
- Write errors classified by status (see Write Pipeline); queued data survives an outage; writer thread can't die silently
- 1.x: type-conflict recovery works again (decoded message), retention per the 2026-10-14 decision, non-admin users connect
- Filter Edit fixed (set → list); edit keeps the lock flag; multi-delete sorts as numbers; insert-at clamps to last; non-numeric values pass min/max filters silently; generated filter names follow the settings
- Config dialog: working copy (Cancel cancels), `validatePrefsConfigUi`, reconnect on a worker thread, `configLock`
- Disabled heartbeat (-1) sends none; legacy 'smart' no longer raises
- Empty include list no longer means "all states" nor "unconfigured"
- filter.log in Indigo's log folder; obsolete v2.x prefs removed; adaptor cache keyed by id without the 1000 cap (production evicted ~12,000 entries/day); no process-wide JSONEncoder patch; exact string change detection; lock logged on take/release only; noisy debug lines gated behind TransportDebug

### v2026.8.0 (Filter Lock Fixes + Device Liveness)
- **Fixed**: `DeviceLastUpdatedList` / `VariableLastUpdatedList` were keyed by id in `UpdateAll()` and by name in `deviceUpdated()` / `variableUpdated()`. The unlock was dead code, so a device locked by a `percentChanged` filter would have stayed locked for the life of the plugin process and silently stopped reaching InfluxDB. Latent — no `percentChanged` filter had ever blocked a value
- **Fixed**: `deviceUpdated()` would have immediately undone a lock the same update had just taken; `DeviceToInflux()` now returns `(somethingWasSent, deviceWasLocked)`
- **Fixed**: `percentChanged` filters could not evaluate on the `UpdateAll()` polling path (no `origDev`), so a spike blocked on the event path leaked into InfluxDB on the next heartbeat. Polling now falls back to `DeviceLastWrittenValues`
- **Fixed**: `percentChanged` filters on `state.*` / `*.num` keys raised `KeyError` and were silently passed; zero baselines raised `ZeroDivisionError` and were silently passed
- **Fixed**: `BuildConfigurationLists()` never reset `AllStatesUI`, so the filter property dropdown gained a duplicate copy of every state name every 15 minutes
- **Added**: device liveness fields on every point (see Device Liveness Fields above). Verified on production: coverage 6 → 874 of 977 devices, point rate unchanged (~6,000/hr before and after). The ~100 uncovered devices have no key intersecting the include-states list, so no point is written for them at all — a pre-existing gap, not a regression
- **Added**: locks are now recorded in `filter.log`, and `UpdateAll` logs a locked device at `info` rather than behind `TransportDebug`. A locked device emits nothing for any of its states, which is indistinguishable from a healthy quiet device unless something says so out loud — deliberately a one-line visibility change rather than a watchdog, since the lock has never fired in this plugin's history
- Filter evaluation log line no longer prints `with a range (0.0, 0.0)` for `percentChanged` filters

### v2026.7.0 (InfluxDB 3 + Async Writer)
- "InfluxDB Version" dropdown (1.7/1.8 vs 3) replaces the v2025.1.0 `InfluxV3Compat` checkbox; old pref is migrated and persisted automatically
- Asynchronous batched write pipeline (background writer thread, client-side timestamps) — fixes the plugin-saturation/unresponsive-config-dialog issue against InfluxDB 3's ~1s WAL-flush write acks
- Type-conflict recovery now parses InfluxDB 3 (IOx) error responses in addition to 1.x, so conflicting fields are coerced instead of the whole point being dropped
- Version changes in the config dialog now take effect on close (no plugin restart needed)
- InfluxDB 3 connections are validated with a ping at connect time

### v2025.1.0 (InfluxDB 3 opt-in)
- Optional InfluxDB 3 (v1-compat API) support behind a checkbox: skips DDL on connect, drops fields that duplicate tag keys

### v2025.0.0 (Modernization Release)
- **BREAKING**: Removed bundled InfluxDB and Grafana servers
- **BREAKING**: Plugin now requires external InfluxDB 1.7/1.8 server
- Updated to Indigo SDK 2025.1 (ServerApiVersion 3.6)
- Upgraded all Python dependencies to latest versions
- Simplified architecture: InfluxDB client only
- Removed ~500 lines of server management code
- Switched to pip requirements.txt for dependency management
- Calendar versioning adopted (2025.0.0)

### v2.0.1 (Previous Version)
- Bundled InfluxDB 1.7 and Grafana servers
- Python 3 compatibility
- Server management and auto-recovery

## Documentation

- **Wiki**: https://github.com/mlamoure/indigo-grafana-dashboard/wiki
- **Example Dashboards**: http://forums.indigodomo.com/viewtopic.php?f=279&t=20472
- **Support Forum**: http://forums.indigodomo.com/viewforum.php?f=279

## Indigo Plugin Development References

- **Docs**: https://docs.indigodomo.com/2025.2/ - fetch `https://docs.indigodomo.com/llms.txt` (index) or grep `llms-full.txt`; the HTML pages 403 automated fetches
- **PluginBase source** (authoritative for callback contracts, e.g. `getPrefsConfigUiValues` returns the live `pluginPrefs`): `/Library/Application Support/Perceptive Automation/Indigo 2025.2/IndigoPluginHost3.app/Contents/Resources/PlugIns/plugin_base.py` on the Indigo Mac

## InfluxDB Setup Requirements

Users must have an external InfluxDB 1.7/1.8 or InfluxDB 3 server. On 1.x the plugin will:
1. Create the database if it doesn't exist (when the user has admin rights)
2. Manage the `indigo_policy` retention policy (see Write Pipeline → retention)
3. Automatically connect and handle reconnections

**Recommended InfluxDB Installation Methods**:
- Docker: `docker run -p 8086:8086 influxdb:1.8`
- Homebrew: `brew install influxdb@1`
- Official packages: https://portal.influxdata.com/downloads/

**Grafana Setup** (separate from plugin):
- Users must install Grafana separately
- Configure InfluxDB as data source
- Import dashboards or create custom visualizations
