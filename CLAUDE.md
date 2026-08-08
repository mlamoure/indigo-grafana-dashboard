# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Indigo plugin (v2025.0.0) that provides InfluxDB data logging for Indigo home automation. It connects to an external InfluxDB server and logs device/variable state changes for time-series visualization (typically used with Grafana).

**Bundle ID**: `com.vtmikel.grafana`

**Key Architecture Decision**: This plugin is an InfluxDB client only - it does NOT bundle or manage server processes. Users must provide their own InfluxDB (1.7 or 1.8) and Grafana servers.

## Plugin Structure

```
Grafana Home Dashboard.indigoPlugin/
├── Contents/
│   ├── Info.plist                    # Plugin metadata (version 2025.0.0, API 3.6)
│   ├── Resources/                    # Plugin icon
│   ├── Packages/                     # Auto-installed dependencies (excluded from git)
│   └── Server Plugin/
│       ├── plugin.py                 # Main plugin class (~1100 lines, client-only)
│       ├── json_adaptor.py           # Converts Indigo objects to InfluxDB format
│       ├── PluginConfig.xml          # Two-panel config UI (Connection + Inclusion/Exclusion)
│       ├── MenuItems.xml             # Advanced features (filters, device exploration)
│       └── requirements.txt          # Python dependencies (auto-installed by Indigo)
├── requirements.txt                  # Python dependencies (development reference)
└── README.md                         # User documentation
```

## Core Components

### plugin.py
The main plugin class extends `indigo.PluginBase` and manages:
- **InfluxDB connection**: Connects to external InfluxDB 1.7/1.8 server
- **Data pipeline**: Device/variable state changes → InfluxDB writes
- **Filtering system**: Advanced filtering to prevent bad data (value ranges, percentage changes)
- **Configuration**: Two-panel config (Connection settings + Inclusion/Exclusion criteria)
- **Connection management**: Retry logic, auto-recovery

**Important Classes**:
- `Plugin`: Main plugin class with InfluxDB client
- `InfluxFilter`: Data filtering rules (min/max values, percentage change thresholds)

**Key State Variables**:
- `connection`: InfluxDBClient instance
- `connected`: Boolean connection status
- `DeviceLastUpdatedList` / `VariableLastUpdatedList`: Track update times for minimum frequency updates. **Keyed by `dev.id` / `var.id` — never by name.** Element 2 of a device row is the `lockMinimumUpdates` lock. In-memory only; cleared on restart.
- `DeviceLastWrittenValues` / `PercentChangedStates`: Baseline for `percentChanged` filters on the polling path (which has no `origDev`). Populated **after** filtering, so a blocked value never becomes the baseline that lets its successor through. Deliberately *not* the adaptor's cache — see below.
- `FilterList`: Array of `InfluxFilter` objects for data validation

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
Writes are asynchronous: producers (`deviceUpdated`, `variableUpdated`, `UpdateAll`) enqueue points with client-side timestamps; a single background writer thread batches them into one `write_points()` call per ~1s flush window (`influxWriterLoop` in plugin.py). This matters because InfluxDB 3 acknowledges each HTTP write only after its WAL flush (~1s default), so synchronous per-point writes cap at ~1 point/sec and back up Indigo's callback queue — which is what made the config dialog unresponsive. Never reintroduce network I/O into Indigo callback methods.

### Device Liveness Fields (v2026.8.0+)
`diff_to_json` emits `lastChanged`, `lastSuccessfulComm` and derived `secondsSinceLastChanged` / `secondsSinceLastSuccessfulComm` on **every** device point, so a flat line from a *dead* device is distinguishable from a flat line from a merely *quiet* one.

These are **enrichment-only and must never reach the include-states gate.** They are added after the `if not hasUpdate: return None` early-return, so they ride along on points that were already going to be written and add zero new points. Anything in `StatesIncludeList` sets `hasUpdate`, and `lastChanged` moves on every device change — routing them through the include list would emit a point per change per device. For that reason they are deliberately absent from `DEFAULT_STATES` and hidden from the include-states picker (`ALWAYS_SENT_STATES` in plugin.py), though still offered in the filter property picker.

The age fields exist because InfluxQL cannot express `now() - field` in a `SELECT` projection and Grafana's Math expressions have no wall-clock function, so a staleness alert cannot be built from the absolute epochs alone. Note that `lastChanged` alone does not discriminate — a quiet-but-alive device and an offline one both have a frozen `lastChanged`; alert on `secondsSinceLastSuccessfulComm`.

**Scope limit — these detect a device that stopped *communicating*, not one whose *value* is stuck.** Verified on production 2026-08-08: `Living Room Temperature` (the device in issue #7) has had `sensorValue` frozen at exactly 69.1 for 7 days, yet Indigo reports both `lastSuccessfulComm` and `lastChanged` as minutes old — the Z-Wave node still answers, it just never reports a different reading. A healthy sensor polled less recently can therefore look *staler* than this one. Detecting a stuck value is a dashboard-side query (`SELECT spread("sensorValue") ... GROUP BY "name"`, where exactly `0` over 24h means stuck), not something the plugin can flag.

`LIVENESS_SENTINEL_FLOOR` is `2000-01-02T00:00Z`, not `2000-01-01T00:00Z`. Indigo's never-communicated placeholder is 2000-01-01 in **local** time, so on any server west of UTC it lands above a UTC-midnight floor and those devices report as ~26 years stale.

### Python Compatibility
- Requires Python 3.11+ (Indigo 2025.1)
- Uses pip requirements from `requirements.txt`
- Dependencies are auto-installed by Indigo to `Contents/Packages/` directory

### Python Dependencies
The plugin requires these packages (see `Server Plugin/requirements.txt`):
- `influxdb==5.3.2` - InfluxDB 1.x client library
- `requests==2.32.5` - HTTP library (required by influxdb)
- `msgpack==1.1.2` - MessagePack serialization
- `pytz==2025.2` - Timezone support

**Dependency Management**:
- `requirements.txt` in `Server Plugin/` directory is read by Indigo
- Indigo automatically installs packages to `Contents/Packages/` on plugin load
- `Contents/Packages/` is excluded from git (auto-generated)
- Root `requirements.txt` is kept for development reference only

**No manual installation required** - Indigo handles this automatically!

## Development Workflow

### Testing Locally
```bash
# Deploy to production Indigo server (requires mounted network share)
# IMPORTANT: Ensure /Volumes/Perceptive Automation is mounted first
cd /Users/mike/Mike_Sync_Documents/Programming/mike-local-development-scripts
source .venv/bin/activate.fish  # or .venv/bin/activate for bash
./deploy_indigo_plugin_to_server.sh "Grafana Home Dashboard.indigoPlugin"

# After deployment, manually restart the plugin in Indigo

# For local testing (if Indigo installed locally at /usr/local/indigo/)
python restart_indigo_plugin.py "/path/to/Grafana Home Dashboard.indigoPlugin"
# or
python restart_indigo_plugin.py com.vtmikel.grafana
```

### Releasing
```bash
cd /Users/mike/Mike_Sync_Documents/Programming/mike-local-development-scripts
source .venv/bin/activate.fish

# Generate release notes to file (recommended for Claude Code)
cat > /tmp/release_notes.md << 'EOF'
## What's New
- List changes here

## Bug Fixes
- List fixes here
EOF

# Create release on BOTH GitHub and Gitea (auto-detected if 'local_gitea' remote exists)
./release_indigo_plugin_to_github.sh "Grafana Home Dashboard.indigoPlugin" -y --notes-file /tmp/release_notes.md

# GitHub only (skip Gitea)
./release_indigo_plugin_to_github.sh "Grafana Home Dashboard.indigoPlugin" -y --no-gitea --notes-file /tmp/release_notes.md

# Gitea only (skip GitHub)
./release_indigo_plugin_to_github.sh "Grafana Home Dashboard.indigoPlugin" -y --gitea-only --notes-file /tmp/release_notes.md

# Recover from a botched release: re-attach the zip to an existing tag
# without re-creating the tag, push, or release notes
./release_indigo_plugin_to_github.sh "Grafana Home Dashboard.indigoPlugin" -y --attach-only v2026.1.0

# Draft for review first
./release_indigo_plugin_to_github.sh "Grafana Home Dashboard.indigoPlugin" --draft --notes-file /tmp/release_notes.md -y
```

**Release Script Features** (as of 2026-05-02):
- Auto-extracts version from `Info.plist` via the shared `lib/plist.sh` helper
- Creates git tag (v{version})
- Packages plugin using `package_indigo_plugin_for_release.sh`
- Removes `Contents/Packages` and `.gitignore` files from release zip
- Auto-detects `local_gitea` remote and publishes there alongside GitHub
- `--attach-only <tag>` recovery mode for re-uploading without re-creating the release
- `--dry-run` to preview without executing
- Gitea token is pulled from Vault (`claude/api-tokens/gitea`) automatically;
  override with `GITEA_TOKEN` env var if you need a one-off
- Override `GITEA_API_BASE` env var to point at a non-default Gitea host
- Override package destination with `INDIGO_RELEASE_DIR` env var

**New exit code**: `6` — Gitea-specific failure (network, API, or token).

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
The data filtering system (`filterValues` menu item) is complex:
- Filters are ordered and processed sequentially
- Can lock minimum frequency updates after failures
- Silent logging to `filter.log` + optional Event Log logging
- Supports both global (all devices) and specific device rules

### Inclusion/Exclusion Logic (plugin.py)
1. **Excluded devices**: Never sent to InfluxDB (highest priority)
2. **Included devices**: All states sent
3. **All other devices**: Only global include states sent

## Version History

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

- **Plugin Guide**: https://wiki.indigodomo.com/doku.php?id=indigo_2025.1_documentation:plugin_guide
- **Object Model**: https://wiki.indigodomo.com/doku.php?id=indigo_2025.1_documentation:object_model_reference
- **Local SDK**: `/Users/mike/Mike_Sync_Documents/Programming/IndigoSDK-2025.1`

## InfluxDB Setup Requirements

Users must have an external InfluxDB 1.7 or 1.8 server configured. The plugin will:
1. Create the database if it doesn't exist
2. Set retention policy based on plugin configuration
3. Automatically connect and handle reconnections

**Recommended InfluxDB Installation Methods**:
- Docker: `docker run -p 8086:8086 influxdb:1.8`
- Homebrew: `brew install influxdb@1`
- Official packages: https://portal.influxdata.com/downloads/

**Grafana Setup** (separate from plugin):
- Users must install Grafana separately
- Configure InfluxDB as data source
- Import dashboards or create custom visualizations
