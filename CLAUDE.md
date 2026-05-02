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
- `DeviceLastUpdatedList` / `VariableLastUpdatedList`: Track update times for minimum frequency updates
- `FilterList`: Array of `InfluxFilter` objects for data validation

### json_adaptor.py
Converts Indigo device objects to InfluxDB-compatible JSON format:
- Smart type conversion (strings → floats where possible)
- Datetime → Unix timestamps
- Enum → string conversion
- Caching to reduce redundant writes

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
**IMPORTANT**: This plugin supports InfluxDB **1.7 and 1.8 only**. It is **NOT compatible** with InfluxDB 2.0+. The API and authentication changed significantly in version 2.0.

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
