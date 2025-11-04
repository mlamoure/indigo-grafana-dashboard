# Grafana Home Dashboard Plugin for Indigo

[![GitHub release](https://img.shields.io/github/release/mlamoure/indigo-grafana-dashboard.svg)](https://github.com/mlamoure/indigo-grafana-dashboard/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

An Indigo plugin that logs device and variable states to InfluxDB for visualization with Grafana. Create beautiful time-series dashboards to track your home automation data over time.

## Features

* **InfluxDB Client**: Connects to your external InfluxDB 1.7 or 1.8 server
* **Granular Control**: Advanced inclusion/exclusion criteria to control which devices and states are logged
* **Data Filtering**: Prevent erroneous values from being logged with min/max ranges and percentage change thresholds
* **Smart Updates**: Configurable minimum update frequency to avoid gaps in graphs
* **Utility Functions**: Device and state exploration tools to help configure your dashboards

## Requirements

### Indigo Requirements
* Indigo 2025.1 or higher
* macOS with Python 3.11+

### External Server Requirements
* **InfluxDB 1.7 or 1.8** (NOT compatible with 2.x)
  - Docker: `docker run -p 8086:8086 -v /path/to/data:/var/lib/influxdb influxdb:1.8`
  - Homebrew: `brew install influxdb@1`
  - Download: https://portal.influxdata.com/downloads/
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
* **InfluxDB HTTP Port**: HTTP API port (default: 8086)
* **InfluxDB User**: Username for authentication
* **InfluxDB Password**: Password for authentication
* **InfluxDB Database**: Database name (will be created if it doesn't exist)
* **Retention Policy**: How long to keep data (6 months, 1 year, 2 years, 5 years, or forever)

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

**Minimum Update Frequency**: Configure how often to send updates even if values haven't changed. This prevents gaps in graphs for infrequently changing devices. Options: 5, 10, 15, 30, or 60 minutes.

## Advanced Features

### Data Filters

Create sophisticated filtering rules to prevent bad data from reaching InfluxDB:

* **Min/Max Value Filtering**: Only log values within a specific range
* **Percentage Change Filtering**: Only log values if they haven't changed by more than a specified percentage
* **Per-Device or Global Rules**: Apply filters to specific devices or all devices
* **Lock Minimum Updates**: Pause minimum frequency updates for devices that fail filters

Access via: **Plugins → Grafana Home Dashboard → Configure data filters (advanced)**

### Device Exploration

Utility tools to help you understand what data is available:

* **Explore Device**: Print all states for a specific device to the Indigo Event Log
* **Explore State**: Find all devices that have a specific state

Access via: **Plugins → Grafana Home Dashboard → Explore device/state**

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
- **Fields**: All device states (based on inclusion criteria)

### Variable Changes
- **Measurement**: `variable_changes`
- **Tags**: `varname`
- **Fields**: `name`, `value`, `value.num` (if numeric)

## Version History

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

This plugin is provided as-is with no warranty. While it has been tested with Indigo 2025.1, use at your own risk. Always backup your Indigo database before installing plugins.
