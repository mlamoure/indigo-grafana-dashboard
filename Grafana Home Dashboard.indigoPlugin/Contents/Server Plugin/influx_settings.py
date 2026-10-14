#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""Validation and parsing of the plugin's settings.  One implementation, used by
the config dialog (validatePrefsConfigUi), by connect(), and by the MCP tools,
so all three accept and reject exactly the same values."""

INFLUX_VERSIONS = ('1', '3')

# months; -1 = keep forever (InfluxQL INF)
RETENTION_CHOICES = ('6', '12', '24', '60', '-1')

# minutes; -1 = no heartbeats.  'smart' is a legacy value (option commented out of
# PluginConfig.xml): heartbeats only around midnight.
FREQUENCY_CHOICES = ('5', '10', '15', '30', '60', '-1')
DEFAULT_FREQUENCY = 5


def to_bool(value):
	"""Convert a string representation to a real boolean ('False' -> False)."""
	return str(value).strip().lower() in ('true', 't', '1', 'yes', 'on')


def validate_connection_settings(values):
	"""values: a mapping using the PluginConfig.xml field ids (InfluxHost,
	InfluxHTTPPort, InfluxSSL, InfluxVersion, InfluxDB, InfluxUser,
	InfluxPassword).  Returns (settings, errors): settings is a normalized dict,
	errors maps field id -> message and is empty when everything is valid."""
	errors = {}

	host = str(values.get('InfluxHost') or '').strip()
	if not host:
		errors['InfluxHost'] = "enter the InfluxDB server's host name or IP address"
	elif '://' in host or '/' in host or any(ch.isspace() for ch in host):
		errors['InfluxHost'] = "enter only the host name or IP address (no http://, path or spaces); use the SSL checkbox for https"

	port = None
	port_text = str(values.get('InfluxHTTPPort') or '').strip()
	try:
		port = int(port_text)
		if not 1 <= port <= 65535:
			raise ValueError(port_text)
	except ValueError:
		port = None
		errors['InfluxHTTPPort'] = "the port must be a whole number from 1 to 65535"

	version = str(values.get('InfluxVersion') or '').strip()
	if version not in INFLUX_VERSIONS:
		errors['InfluxVersion'] = "select InfluxDB 1.7 / 1.8 or InfluxDB 3"

	database = str(values.get('InfluxDB') or '').strip()
	if not database:
		errors['InfluxDB'] = "enter the database name"

	settings = {
		'host': host,
		'port': port,
		'ssl': to_bool(values.get('InfluxSSL', False)),
		'version': version,
		'database': database,
		'username': str(values.get('InfluxUser') or ''),
		'password': str(values.get('InfluxPassword') or ''),
	}
	return settings, errors


def parse_retention(value):
	"""Retention months as an int (-1 = forever).  Raises ValueError."""
	months = int(float(str(value).strip()))
	if months != -1 and months <= 0:
		raise ValueError(f"retention must be a positive number of months or -1, got {value!r}")
	return months


def retention_spec(value):
	"""(InfluxQL duration literal, seconds) for a retention pref; forever is
	('INF', 0) - InfluxDB reports an infinite duration as 0."""
	months = parse_retention(value)
	if months == -1:
		return 'INF', 0
	days = months * 30
	return f"{days}d", days * 86400


def describe_retention(value):
	months = parse_retention(value)
	return "forever" if months == -1 else f"{months} months"


def parse_frequency(value, default=DEFAULT_FREQUENCY):
	"""Minimum update frequency pref -> int minutes (-1 = disabled) or 'smart'."""
	text = str(value).strip()
	if text == 'smart':
		return 'smart'
	try:
		return int(float(text))
	except ValueError:
		return default


def validate_other_settings(values):
	"""Retention and minimum update frequency.  Returns an errors dict."""
	errors = {}
	if str(values.get('InfluxRetention', '24')).strip() not in RETENTION_CHOICES:
		errors['InfluxRetention'] = "select a retention period from the list"
	frequency = str(values.get('MinimumUpdateFrequency', DEFAULT_FREQUENCY)).strip()
	if frequency not in FREQUENCY_CHOICES and frequency != 'smart':
		errors['MinimumUpdateFrequency'] = "select a minimum update frequency from the list"
	return errors
