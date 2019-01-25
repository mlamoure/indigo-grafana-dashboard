This plugin gives you the tools to build a time-series dashboard for Indigo (indigodomo.com) home automation software. It uses and includes within the plugin two components to make this happen: a time series database called InfluxDB (https://influx.com), and a data visualization tool called Grafana (https://grafana.com).

This plugin includes both InfluxDB and Grafana within it. Previous plugins that worked to do this required steps for installation outside of Indigo. This plugin does not, thus simplifying the installation and management.

Both InfluxDB and Grafana are included within the plugin, nothing is installed outside of the plugin directory. The plugin config asks for a location to put the Influx and Grafana data only. This is so that your historical data and dashboards are not wiped during each plugin update.

# Features #
* Built-in InfluxDB and Grafana servers
* Latest Influx client libraries
* Granular control of inclusion and exclusion criteria to control which devices, and what states, are sent to InfluxDB and Grafana (dependency on Global Property Manager from previous versions is removed)
* Filtering - advanced configuration allows the creation of filters to prevent values outside of ranges, or sudden changes, from being sent to Influx and messing up your pretty graphs.
* Utility functions to output the JSON of any device, or to investigate which devices are publishing any particular property.  This takes the guessing work out of your Grafana queries.
* Improved error handling, logging over previous plugins working with Influx

# Documentation #
[https://github.com/mlamoure/indigo-grafana-dashboard/wiki]

# Requirements #
* OS X 10.8 or higher
Be aware of the system requirements for InfluxDB.
* InfluxDB System Requirements - [https://docs.influxdata.com/influxdb/v1.5/guides/hardware_sizing/]

# Support #
* Indigo forums - [http://forums.indigodomo.com/viewforum.php?f=279&sid=8325f6e661b0bea59f44b6989402f6c5]
* Example dashboards - [http://forums.indigodomo.com/viewtopic.php?f=279&t=20472]
