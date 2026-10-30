# Grafana Home Dashboard Plugin for Indigo

[![GitHub release](https://img.shields.io/github/release/mlamoure/indigo-grafana-dashboard.svg)](https://github.com/mlamoure/indigo-grafana-dashboard/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

An Indigo plugin that logs device and variable states to InfluxDB for visualization with Grafana. Create beautiful time-series dashboards to track your home automation data over time.

## Features

* **InfluxDB Client**: Connects to your external InfluxDB 1.7/1.8 server, or InfluxDB 3 via its v1 compatibility API. Nothing to install: the plugin uses the Python packages that come with Indigo
* **Granular Control**: Advanced inclusion/exclusion criteria to control which devices and states are logged
* **Data Filtering**: Prevent erroneous values from being logged with min/max ranges and percentage change thresholds
* **Smart Updates**: Configurable minimum update frequency to avoid gaps in graphs
* **Utility Functions**: Device and state exploration tools to help configure your dashboards

## Requirements

### Indigo Requirements
* Indigo 2025.1 or higher
* macOS with Python 3.11+
* No extra Python packages. Since 2026.11.0 the plugin talks to InfluxDB through `requests`, which Indigo installs itself, so Indigo installs nothing for it (no `Contents/Packages` folder)

### External Server Requirements
* **InfluxDB 1.7 or 1.8** (NOT compatible with 2.x)
  - Docker: `docker run -p 8086:8086 -v /path/to/data:/var/lib/influxdb influxdb:1.8`
  - Homebrew: `brew install influxdb@1`
  - Download: https://portal.influxdata.com/downloads/
* **or InfluxDB 3** (Core/Enterprise) reached through its v1 compatibility API
  - Select "InfluxDB 3" in the plugin's InfluxDB Version dropdown
  - The credentials/token must have write access to the database (and read access too for the AI history tool, [`influxlog_query_history`](#history-influxlog_query_history)) — the plugin does not create databases or retention policies on InfluxDB 3 (retention is managed server-side; InfluxDB 3 creates a missing database on the first write when the token allows it)
  - For token auth, leave the username as configured on your server and supply the token as the password (v1-compat convention)
* **Grafana** (for visualization, optional but recommended)
  - Docker: `docker run -p 3000:3000 grafana/grafana`
  - Homebrew: `brew install grafana`
  - Download: https://grafana.com/grafana/download

## Installation

1. Download the latest release from [GitHub Releases](https://github.com/mlamoure/indigo-grafana-dashboard/releases)
2. Double-click the `.indigoPlugin` file to install
3. Configure your InfluxDB connection in the plugin configuration

## Configuration

### InfluxDB Connection

Configure the connection to your InfluxDB server in the plugin configuration:

* **InfluxDB Server Host**: Hostname or IP address of your InfluxDB server (e.g., `localhost`, `192.168.1.100`)
* **Use SSL**: Enable if your InfluxDB server uses HTTPS
* **InfluxDB Version**: InfluxDB 1.7/1.8 (default) or InfluxDB 3 (v1 compatibility API)
* **InfluxDB HTTP Port**: HTTP API port (default: 8086)
* **InfluxDB User**: Username for authentication
* **InfluxDB Password**: Password for authentication
* **InfluxDB Database**: Database name (created on InfluxDB 1.x when the user has admin rights; a user without them can log to a database created for it)
* **Retention Policy**: How long to keep data (6 months, 1 year, 2 years, 5 years, or forever) — InfluxDB 1.x only; InfluxDB 3 retention is managed server-side. See [Retention on InfluxDB 1.x](#retention-on-influxdb-1x)

The dialog checks these settings before it closes (host, a port from 1 to 65535, the version, the database), and a connection change is applied in the background, so saving never freezes the plugin.

#### Retention on InfluxDB 1.x

The plugin applies the retention setting through a retention policy named `indigo_policy`, which it makes the database's **default** policy so that data is written there.

Plugin versions before 2026.11.0 created `indigo_policy` but never made it the default, so all data went to InfluxDB's `autogen` policy (kept forever) and the setting never took effect. On such a database the plugin now leaves your data where it is, because switching the default would hide all existing history from Grafana panels that don't name a retention policy, and logs a warning with the one command that applies the setting from then on:

```sql
ALTER RETENTION POLICY "indigo_policy" ON "indigo" DURATION 720d DEFAULT
```

After that, new data goes to `indigo_policy` and expires as configured; older data stays in `autogen` (query it as `"autogen"."device_changes"`). A database the plugin creates itself gets `indigo_policy` as its default straight away. A database that already existed without `indigo_policy` (for example one other tools write to as well) keeps its default policy too; the warning then shows the `CREATE RETENTION POLICY ... DEFAULT` command instead, because every writer that doesn't name a policy would use it. Changing the retention setting later alters the policy's duration. Managing retention needs an InfluxDB user with admin rights; without them the plugin logs a warning and keeps logging data.

### Inclusion / Exclusion Criteria

Control which devices and states are logged:

**How it works:**
1. **Excluded devices** will never have any information sent to InfluxDB
2. **Included devices** will have ALL states sent to InfluxDB
3. **All other devices** will have only the global include states sent

**Global Include States**: These states will be logged for all devices (unless excluded). Default states include:
- `onState`, `state.onOffState`
- `energyCurLevel`, `energyAccumTotal`
- `sensorValue`, `value.num`
- `batteryLevel`
- HVAC states (`coolSetpoint`, `heatSetpoint`, `state.hvac_state`)

**Minimum Update Frequency**: Configure how often to send updates even if values haven't changed. This prevents gaps in graphs for infrequently changing devices. Options: 5, 10, 15, 30, or 60 minutes, or Disabled (no repeated updates; only real changes are sent).

Changes made with the include/exclude buttons take effect when you click **Save**; **Cancel** discards them.

If the global include list is empty, devices that are not in the include-devices list send nothing (only included devices are logged). Use **reset to default states** to restore the defaults.

## Advanced Features

### Data Filters

Create sophisticated filtering rules to prevent bad data from reaching InfluxDB:

* **Min/Max Value Filtering**: Only log values within a specific range
* **Percentage Change Filtering**: Only log values if they haven't changed by more than a specified percentage
* **Per-Device or Global Rules**: Apply filters to all devices, to specific devices, or to all devices except some (for example an all-device setpoint range that a cooler's 34 °F setpoint would otherwise trip)
* **Lock Minimum Updates**: Pause minimum frequency updates for devices that fail filters
* **Order matters**: filters are evaluated in order and a value stops at the first filter it fails, so the order decides which filter's logging and lock settings apply

Blocked values are recorded in `filter.log` in the plugin's log folder (`/Library/Application Support/Perceptive Automation/Indigo <version>/Logs/com.vtmikel.grafana/`); **Print filter blocks to Event Log** shows the latest ones. Filter names the plugin generated (for example `heatSetpoint (all devices) min: 30.0, max: 80.0`) follow the filter's settings when you edit it; a name you typed is kept.

Access via: **Plugins → Grafana Home Dashboard → Configure data filters (advanced)**

### Device Exploration

Utility tools to help you understand what data is available:

* **Explore Device**: Print all states for a specific device to the Indigo Event Log
* **Explore State**: Find all devices that have a specific state

Access via: **Plugins → Grafana Home Dashboard → Explore device/state**

## AI Configuration (MCP Advanced Tools)

With the [MCP Advanced Tools](https://github.com/mlamoure/indigo-mcp-server) plugin (formerly MCP Server; 2026.8.1 or later) installed, an AI assistant can read and change what this plugin logs. The plugin contributes tools prefixed `influxlog_`; nothing changes for users without MCP Advanced Tools.

| Tool | What it does |
|---|---|
| `influxlog_get_status` | Connection state, server version, write counters (points written / dropped by reason), last write error, queue depth, devices locked by a filter |
| `influxlog_get_config` | Every setting except the password (reported only as set / not set), the include and exclude lists with device names, the filters in order with their real scope, and the config revision |
| `influxlog_explain_device` | For one device: which of its states are sent and why, which filters apply and whether the current value passes them |
| `influxlog_search_states` | Find state keys, or the devices that have a given state and whether it is sent for each |
| `influxlog_get_filter_blocks` | The latest values the filters blocked, parsed from `filter.log` |
| `influxlog_query_history` | What devices and variables did over a time window, read back from InfluxDB (see [History](#history-influxlog_query_history)) |
| `influxlog_set_device_mode` | Exclude a device, include all its states, or return it to the global include list |
| `influxlog_update_included_states` | Add or remove global include states, or reset them to the defaults |
| `influxlog_update_settings` | Minimum update frequency, retention (InfluxDB 1.x), debug flags |
| `influxlog_update_connection` | Host, port, SSL, version, database, user and password/token — tested before it is saved |
| `influxlog_reconnect` | Reconnect with the current settings (for example after a token was rotated) |
| `influxlog_list_snapshots` / `influxlog_restore_snapshot` | Undo: every change is snapshotted first |
| `influxlog_create_filter` / `influxlog_update_filter` / `influxlog_delete_filter` | Manage the data filters, including the "all devices except" scope; a filter is addressed by its position plus its expected name, so a filter that moved is never changed by mistake |

Every change made through a tool can be dry-run first and can be checked against the configuration revision the AI read (`expected_revision`, so it can't overwrite a change it hasn't seen); it takes effect immediately, is snapshotted (the last 20 are kept, in `Preferences/Plugins/com.vtmikel.grafana.snapshots/` in the Indigo folder) and is recorded with one line in the Indigo Event Log (`MCP: ...`). MCP Advanced Tools's "Allow plugin-provided tools to make changes" setting switches all of them off.

**The password/token** is write-only: no tool returns it and it is never logged or snapshotted. A connection change is tested (ping and a write-permission check that writes no data) before it is saved, and a failing test leaves the working settings in place. Setting the password through a tool does pass it through the AI conversation and its model provider; set it in the plugin's config dialog instead if that matters to you.

### History (`influxlog_query_history`)

Reads back what the plugin logged, so an AI assistant can answer "how cold did the porch get last night?", "how many hours was the heat on each day this week?" or "when did the garage door open?". It only reads.

* **What it covers**: devices (`device_changes`), thermostats (`thermostat_changes`), weather stations (`weather_changes`) and variables (`variable_changes`) - up to 5 devices and 5 variables per call
* **Numbers** (temperatures, setpoints, power): current, first, minimum and maximum with the times they happened, the time-weighted mean, the change and the trend (rising / falling / steady), and a warning when the value never moved in the window, with the last time it was different - a sign of a stuck or offline sensor
* **On/off and text states** (lights, doors, locks, HVAC mode, variables): the value at the start of the window, every change with its time, and the time spent in each value
* **Over time** (optional `bucket`): minimum / mean / maximum per 15 minutes, hour or day for numbers, or the time in each value per bucket ("hours on per day"); hour and day buckets start on the Indigo server's local hour and midnight
* **Outages**: per device or variable, the stretches longer than twice the minimum update frequency in which nothing at all was written (the device, the plugin or InfluxDB was silent). A single state that doesn't change is normally written only on that heartbeat, and every change of another state postpones it, so the tool never reads a quiet state as an outage
* **No data**: says why - the device is excluded, the state isn't in the include list, a data filter blocks its value, the device is locked - and gives the last value logged before the window
* **Window**: the last hours or days (default 24 hours), or a start and end time, up to 366 days. Without a list of states, a device returns up to six of the states the plugin logs for it
* **InfluxDB 1.x**: data in both `autogen` and `indigo_policy` (see [Retention on InfluxDB 1.x](#retention-on-influxdb-1x)) is read and merged

The credentials in the plugin's connection settings must be allowed to **read** the database as well as write to it: an InfluxDB 1.x user with `ALL` privileges on it (not only `WRITE`), or an InfluxDB 3 token with read and write on it. With write-only credentials the tool says so and logging is unaffected. History is stored under a device's name at the time it was written, so after a rename the older history is under the old name.

## Grafana Dashboard Setup

1. Install Grafana on your network
2. Add InfluxDB as a data source:
   - URL: `http://your-influxdb-host:8086`
   - Database: Same as configured in the plugin
   - User/Password: Same as configured in the plugin
3. Create dashboards or import community dashboards
4. Query the `device_changes` measurement for device data
5. Query the `variable_changes` measurement for variable data

### Example Query

```sql
SELECT "energyCurLevel" FROM "device_changes"
WHERE "name" = 'Living Room Light'
AND time >= now() - 24h
```

## Data Structure

### Device Changes
- **Measurement**: `device_changes`
- **Tags**: `name`, `folderId`, `folder` (if in a folder)
- **Fields**: All device states (based on inclusion criteria), plus the device liveness fields below

### Device Liveness Fields

Every device point also carries, automatically and regardless of your inclusion criteria:

| Field | Meaning |
|---|---|
| `lastSuccessfulComm` | Unix timestamp of the device's last successful communication |
| `secondsSinceLastSuccessfulComm` | How long ago that was, in seconds |
| `lastChanged` | Unix timestamp of the device's last state change |
| `secondsSinceLastChanged` | How long ago that was, in seconds |

These let you tell a device that has **stopped communicating** from one that is merely **quiet**.
Without them, a device that dropped off the network months ago looks identical in Grafana to a
thermostat holding steady overnight — both are a flat line, because the plugin keeps re-sending the
last known value as a heartbeat so your graphs don't gap.

Alert on `secondsSinceLastSuccessfulComm`, not `lastChanged` — a quiet-but-healthy device also has
a frozen `lastChanged`. A useful "offline device" panel:

```sql
SELECT last("secondsSinceLastSuccessfulComm") FROM "device_changes"
WHERE $timeFilter GROUP BY "name"
```

Sort descending and set the unit to seconds. Anything much larger than a few times your
**Minimum Update Frequency** is worth investigating.

#### What these fields do *not* catch

A device can keep communicating normally while one of its readings is stuck — a sensor that still
answers polls but always reports the same temperature, for example. Indigo considers such a device
healthy, so both timestamps stay current and the liveness fields will not flag it.

That failure mode is a *value* problem, not a *communication* problem, and it is best detected in
Grafana by asking whether a reading has moved at all over a long window:

```sql
SELECT spread("sensorValue") FROM "device_changes"
WHERE time > now() - 24h GROUP BY "name"
```

A spread of exactly `0` over 24 hours, for a reading that ought to vary, means the value is stuck
even though the device looks alive. Use the liveness fields for "is it there?" and a spread check
for "is it still telling me anything?".

Two things to get right before alerting on this, or it will cry wolf and be ignored:

- **Compare each device against its own history, not against zero.** A flat reading is only
  suspicious if that device has varied before. Plenty of readings are legitimately constant — a
  closet luminance sensor that always reads 0, a setpoint, a battery level, a relay. Flag a device
  only when `spread` over 24h is 0 *and* its spread over the previous 30 days was greater than 0.
- **It misses a value stuck with dither.** A sensor alternating 69.1 / 69.2 has a spread of 0.1,
  not 0, so a comparison against zero will not catch it. Comparing today's spread against the
  device's own historical spread does.

Scope it to readings that physically vary — `sensorValue` on sensors, for example. Across 31
temperature sensors over 24 hours on the author's system, exactly one was flat while every other
swung 1.2–21.7 °F, so the separation is clean where the check applies.

> ⚠️ **Do not add `lastChanged` or `lastSuccessfulComm` to your include-states list.** They are
> already sent on every point. Adding them to the include list makes every change to them generate
> its own data point, which can multiply your write volume dramatically. For this reason they are
> hidden from the include-states picker.

Devices that have never communicated (virtual devices, device groups, some plugin-backed devices)
simply omit these fields rather than reporting as maximally stale.

### Variable Changes
- **Measurement**: `variable_changes`
- **Tags**: `varname`
- **Fields**: `name`, `value`, `value.num` (if numeric)

## Version History

### v2026.12.1 (Stable release)
Tested against InfluxDB 1.8.10 and InfluxDB 3 Core 3.12.0.

- **Stable release** of the 2026.12.0 beta, alongside the Indigo 2026.1 release and MCP Advanced Tools 2026.11.2. No code changes since 2026.12.0

### v2026.12.0 (History for AI assistants)
Tested against InfluxDB 1.8.10 and InfluxDB 3 Core 3.12.0.

- **New**: `influxlog_query_history` reads back what devices and variables did over a time window - numbers with their minimum, maximum, mean and trend, on/off and text states with their changes and the time in each value, optional per-hour or per-day series, outages, and why a state has no data (see [History](#history-influxlog_query_history)). It needs credentials that can read the database as well as write to it; everything else works as before without them

### v2026.11.0 (Own InfluxDB client + fixes)
Tested against InfluxDB 1.8.10 and InfluxDB 3 Core 3.12.0.

- **Changed**: the plugin no longer uses the archived `influxdb` Python client (archived in 2024). It writes through a small client of its own built on the `requests` that ships with Indigo, so Indigo installs **no** packages for the plugin any more. Data is encoded exactly as before (verified byte for byte against the old client), so existing InfluxDB columns keep their types
- **Fixed**: filter **Edit** has not worked since v2025.0.1 — the edit fields stayed disabled
- **Fixed**: on InfluxDB 1.x a field type conflict was never recovered, so the affected device's points were dropped on every write
- **Fixed**: on InfluxDB 1.x the retention setting never applied (see [Retention on InfluxDB 1.x](#retention-on-influxdb-1x)), and "Disabled (keep forever)" turned into a 30-day policy
- **Fixed**: a revoked or wrong password/token was only noticed at debug level while every point was retried one by one and dropped; the plugin now logs an error and pauses until the credentials are corrected
- **Fixed**: InfluxDB 1.x users without admin rights could never connect
- **Fixed**: a lost connection no longer throws queued data away: points are kept (up to 10,000) and written once InfluxDB is back
- **Fixed**: NaN or infinite values (for example a device address such as `2e928278`, which reads as a number) no longer make InfluxDB reject the device's whole point
- **Fixed**: "Disabled" minimum update frequency sent an update for every device on every poll
- **Fixed**: Cancel in the plugin config dialog did not undo include/exclude button changes
- **Fixed**: an empty global include list sent every state of every device, and after a restart stopped the plugin from connecting
- **Fixed**: a blank or non-numeric port crashed the plugin; the config dialog now validates the connection settings
- **Fixed**: `filter.log` was always written under an `Indigo 2025.1` folder in your home folder; it now lives in Indigo's log folder for the plugin (an existing file is moved)
- **Fixed**: deleting several filters at once could delete the wrong ones; "insert at" past the end placed a new filter second-to-last; editing a percent-change filter re-enabled its lock option
- **Fixed**: a briefly missing state (a device offline) was removed from the include list for good
- **Fixed**: a change only in letter case, or to an empty text, waited for the next heartbeat
- **Fixed**: the change-detection cache was capped below the size of a large Indigo database, re-sending unchanged states
- **Changed**: a locked device is logged when it is locked and when it is released, instead of every minute; much less debug output in `plugin.log`
- **Removed**: settings left over from plugin version 2.x, including a stored Grafana admin password
- **New**: AI configuration through the Indigo MCP Server: 15 `influxlog_*` tools (see [AI Configuration](#ai-configuration-mcp-advanced-tools))
- **New**: filters can apply to "all devices except" the ones you pick (stored with the existing filter format, so going back to an older release keeps every filter; an "all devices except" filter then applies to all devices again)
- **Changed**: if the configuration changes elsewhere (for example through an MCP tool) while the plugin config dialog is open, saving the dialog applies your changes on top instead of overwriting the other ones

### v2026.8.0 (Filter Fixes + Device Liveness)
- **New**: device liveness fields on every point — tell a dead sensor from a quiet one (see [Device Liveness Fields](#device-liveness-fields))
- **Fixed**: "percent changed" filters were ignored during the periodic minimum-frequency update, so a bad value the filter had blocked could still reach InfluxDB on the next heartbeat
- **Fixed**: the "lock minimum frequency updates after filter failure" option could leave a device locked permanently, silently stopping all of its data
- **Fixed**: "percent changed" filters on states written as `state.<name>` or `<name>.num`, and filters where the previous value was zero, silently passed everything through
- **Fixed**: filter blocks that lock a device now say so in the filter log, and a locked device announces itself in the Indigo event log instead of only under debug logging — a locked device sends nothing at all for any of its states, which otherwise looks exactly like a device that is simply quiet
- **Fixed**: the filter property dropdown accumulated duplicate entries over time

### v2026.7.0 (InfluxDB 3 Support)
- **InfluxDB Version dropdown**: choose InfluxDB 1.7/1.8 or InfluxDB 3 (v1 compatibility API) in the connection settings
- **Asynchronous batched writes**: state changes are queued and written in batches on a background thread, so the plugin (and its config dialog) stays responsive even against servers with slow write acknowledgments
- **Better type-conflict handling**: InfluxDB 3 error responses are now understood, so fields with a mismatched column type are converted instead of the data point being dropped

### v2025.0.0 (Modernization Release)
**BREAKING CHANGES:**
- Removed bundled InfluxDB and Grafana servers
- Plugin now requires external InfluxDB 1.7/1.8 server
- Updated to Indigo SDK 2025.1 (Python 3.11+)

**Improvements:**
- Upgraded all Python dependencies to latest versions
- Simplified architecture: InfluxDB client only
- Removed ~500 lines of server management code
- Switched to pip requirements.txt for dependency management
- Calendar versioning adopted (2025.0.0)

### v2.0.1 (Previous Version)
- Bundled InfluxDB 1.7 and Grafana servers
- Python 3 compatibility
- Server management and auto-recovery

## Migration from v2.x

**Important**: Version 2025.0.0 is a breaking change that removes the bundled InfluxDB and Grafana servers. You must set up external servers before upgrading.

1. **Install InfluxDB 1.8** on your network (see Requirements section)
2. **Migrate existing data** (if you have existing data from v2.x):
   ```bash
   # On your Indigo server, export data from old plugin location
   influxd backup -portable -database indigo /path/to/backup

   # On new InfluxDB server, restore data
   influxd restore -portable -db indigo /path/to/backup
   ```
3. **Install Grafana** separately (see Requirements section)
4. **Update plugin** to v2025.0.0
5. **Configure connection** to your external InfluxDB server
6. **Reconfigure Grafana** to point to new InfluxDB server

## Support & Documentation

* **Documentation**: [Wiki](https://github.com/mlamoure/indigo-grafana-dashboard/wiki)
* **Support Forum**: [Indigo Forums](http://forums.indigodomo.com/viewforum.php?f=279)
* **Example Dashboards**: [Forum Thread](http://forums.indigodomo.com/viewtopic.php?f=279&t=20472)
* **Issues**: [GitHub Issues](https://github.com/mlamoure/indigo-grafana-dashboard/issues)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits

- Original author: Mike Lamoureux
- JSON Adaptor: Dave Brown (Copyright 2017, 2018)
- InfluxDB: InfluxData Inc.
- Grafana: Grafana Labs

## Disclaimer

This plugin is provided as-is with no warranty. While it has been tested with Indigo 2025.2, use at your own risk. Always backup your Indigo database before installing plugins.
