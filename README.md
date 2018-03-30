This plugin builds a time-series dashboard for Indigo (indigodomo.com) home automation software. It uses two components to make this happen: a time series database called InfluxDB, and a data visualization tool called Grafana.

This plugin includes both InfluxDB and Grafana within it. Previous plugins that worked to do this required steps for installation outside of Indigo. This plugin does not, thus simplifying the installation and management.

Both InfluxDB and Grafana are included within the plugin, nothing is installed outside of the plugin directory. The plugin config asks for a location to put the Influx and Grafana data only. This is so that your historical data and dashboards are not wiped during each plugin update.

# Documentation #
[https://github.com/mlamoure/indigo-grafana-dashboard/wiki]

# Requirements #
Be aware of the system requirements for InfluxDB.

InfluxDB System Requirements - [https://docs.influxdata.com/influxdb/v1.5/guides/hardware_sizing/]

# Support#
Indigo forums - [http://forums.indigodomo.com/viewforum.php?f=279&sid=8325f6e661b0bea59f44b6989402f6c5]