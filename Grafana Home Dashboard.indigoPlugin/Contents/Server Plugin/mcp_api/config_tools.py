"""
The influxlog_* tools: what the Grafana Home Dashboard plugin logs to InfluxDB,
and why.  Advertised in Contents/Resources/mcp-manifest.json.

Every tool reads the plugin's live state.  Nothing here writes to InfluxDB or
reads time-series data (the MCP Server's history tools do that), and no output
ever contains the InfluxDB password or token: the config store's plain form has
no secrets, and the connection section reports only `password_set`.
"""

import datetime
import sys

import indigo

from config_store import ConfigError, RESTORABLE
from influx_filter import SCOPES, InfluxFilter
from influx_settings import (FREQUENCY_CHOICES, RETENTION_CHOICES, describe_retention,
							 validate_connection_settings)

from .errors import ToolError
from .filter_log import read_records
from .resolvers import device_ref, resolve_device, resolve_devices, suggestions
from .tool_dispatcher import AsyncResult

# connection tool argument -> PluginConfig.xml field id
CONNECTION_ARGS = {'host': 'InfluxHost', 'port': 'InfluxHTTPPort', 'ssl': 'InfluxSSL', 'version': 'InfluxVersion',
				   'database': 'InfluxDB', 'user': 'InfluxUser', 'password': 'InfluxPassword'}
FIELD_TO_ARG = {field: arg for arg, field in CONNECTION_ARGS.items()}
DEVICE_MODES = ('default', 'all_states', 'excluded')
FILTER_STRATEGIES = ('min_max', 'percent_changed')
MAX_FILTER_DEVICES = 500


def _is_number(value):
	import math
	return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def iso(value):
	if value is None:
		return None
	if isinstance(value, datetime.datetime):
		if value.tzinfo is None:
			value = value.astimezone()
		return value.isoformat(timespec="seconds")
	return str(value)


def _bool_arg(value, name):
	if not isinstance(value, bool):
		raise ToolError("validation", f"{name} must be true or false")
	return value


def _revision_arg(value):
	if value is None:
		return None
	if isinstance(value, bool) or not isinstance(value, int):
		raise ToolError("validation", "expected_revision must be an integer (the revision get_config returned)")
	return value


def _string_list(value, name):
	if value is None:
		return []
	if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
		raise ToolError("validation", f"{name} must be a list of non-empty strings")
	return [item.strip() for item in value]


def _int_arg(value, name, low, high, default):
	if value is None:
		return default
	if isinstance(value, bool) or not isinstance(value, int):
		raise ToolError("validation", f"{name} must be an integer from {low} to {high}")
	if not low <= value <= high:
		raise ToolError("validation", f"{name} must be from {low} to {high} (got {value})")
	return value


class InfluxLogTools:
	TOOLS = ("get_status", "get_config", "explain_device", "search_states", "get_filter_blocks",
			 "set_device_mode", "update_included_states", "update_settings", "update_connection", "reconnect",
			 "list_snapshots", "restore_snapshot", "create_filter", "update_filter", "delete_filter")

	def __init__(self, plugin):
		self.plugin = plugin
		self.store = plugin.store
		# plugin.py's module, whatever name Indigo loaded it under
		self.constants = sys.modules[type(plugin).__module__]

	# ------------------------------------------------------------------
	# shared helpers

	def _filters_view(self, config, include_devices):
		catalog = self.plugin.stateCatalog
		filters = []
		for position, f in enumerate(config["filters"], start=1):
			entry = {
				"position": position,
				"name": InfluxFilter.fromDict(f).name,
				"name_is_generated": not f["name"],
				"state": f["state"],
				"state_device_count": catalog.get(f["state"], 0),
				"strategy": f["strategy"],
				"scope": f["scope"],
				"log_to_event_log": f["log_to_event_log"],
			}
			if f["strategy"] == "min_max":
				entry.update({"min": f["min"], "max": f["max"]})
			else:
				entry.update({"max_percent": f["max_percent"], "lock_on_failure": f["lock_on_failure"]})
			if f["scope"] == "devices" and not f["devices"]:
				entry["applies_to_no_devices"] = True
			if f["scope"] != "all":
				entry["device_count"] = len(f["devices"])
				listed = f["devices"] if include_devices else f["devices"][:10]
				entry["devices"] = [device_ref(dev_id) for dev_id in listed]
				if len(listed) < len(f["devices"]):
					entry["devices_truncated"] = True
			filters.append(entry)
		return filters

	def _mode(self, dev_id):
		if dev_id in self.plugin.DeviceExcludeList:
			return "excluded"
		if dev_id in self.plugin.DeviceIncludeList:
			return "all_states"
		return "global_states"

	def _send_decision(self, mode, key):
		"""(sent, reason) for one key of a device, before filters."""
		p = self.plugin
		if mode == "excluded":
			return False, "device is excluded"
		if key in self.constants.ALWAYS_SENT_STATES:
			if p.InfluxV3Compat and key == "name":
				return True, "always sent (as the 'name' tag on InfluxDB 3)"
			return True, "always sent"
		if mode == "all_states":
			return True, "device is included: all its states are sent"
		if key in p.StatesIncludeList:
			return True, "in the global include list"
		return False, "not in the global include list"

	def _write(self, tool, mutate, dry_run, expected_revision, summary, log=True):
		"""One configuration change through the store: dry run, revision guard,
		snapshot, one Event Log line (log=False: the caller writes it).  Returns
		the store's result."""
		dry_run = _bool_arg(dry_run, "dry_run")
		expected_revision = _revision_arg(expected_revision)
		return self.store.apply(f"mcp: {tool}", mutate, dry_run=dry_run, expected_revision=expected_revision,
								summary=summary, log=f"MCP: {tool} {summary}" if log else None)

	def _keys_count(self, state):
		"""Devices that have a state and are not excluded."""
		excluded = set(self.plugin.DeviceExcludeList)
		return sum(1 for dev_id, keys in self.plugin.deviceKeys.items() if state in keys and dev_id not in excluded)

	# ------------------------------------------------------------------
	# tools

	def get_status(self):
		p = self.plugin
		stats = p.stats.snapshot()
		info = p.serverInfo or {}
		last_error = stats["last_error"]
		if last_error:
			last_error = dict(last_error, time=iso(last_error["time"]))
		locks = [
			dict(device_ref(dev_id), since=iso(lock["since"]), filter=lock["filter"], state=lock["state"])
			for dev_id, lock in sorted(dict(p.deviceLocks).items())
		]
		return {
			"plugin_version": p.pluginVersion,
			"connection": {
				"state": p.connectionState,
				"host": p.InfluxHost,
				"port": str(p.InfluxHTTPPort),
				"ssl": bool(p.InfluxSSL),
				"influxdb_version_mode": str(p.InfluxVersion),
				"database": p.InfluxDB,
				"user": p.InfluxUser,
				"server_version": info.get("version"),
				"server_build": info.get("build"),
				"last_connect_error": p.lastConnectError,
			},
			"writes": {
				"counting_since": iso(stats["started"]),
				"points_written": stats["points_written"],
				"batches_written": stats["batches_written"],
				"points_dropped": stats["points_dropped"],
				"last_success": iso(stats["last_success"]),
				"last_error": last_error,
				"queue_depth": p.write_queue.qsize(),
				"queue_capacity": self.constants.INFLUX_QUEUE_MAX,
			},
			"locked_devices": locks,
			"config_revision": self.store.revision,
		}

	def get_config(self, include_filter_devices=False):
		p = self.plugin
		config = self.store.current()
		catalog = p.stateCatalog
		settings = config["settings"]
		retention = settings["retention"]
		return {
			"revision": self.store.revision,
			"connection": dict(config["connection"], password_set=bool(p.InfluxPassword)),
			"settings": {
				"minimum_update_frequency": settings["minimum_update_frequency"],
				"retention": "forever" if retention == "-1" else int(retention),
				"retention_description": describe_retention(retention),
				"retention_applies": config["connection"]["version"] == "1",
				"debug": settings["debug"],
			},
			"included_states": [{"state": state, "devices": catalog.get(state, 0)} for state in config["states"]],
			"included_devices": [device_ref(dev_id) for dev_id in config["include"]],
			"excluded_devices": [device_ref(dev_id) for dev_id in config["exclude"]],
			"filters": self._filters_view(config, bool(include_filter_devices)),
			"state_catalog": {"states": len(catalog), "built": iso(p.catalogBuilt)},
		}

	def explain_device(self, device):
		p = self.plugin
		dev = resolve_device(device)
		mode = self._mode(dev.id)

		# to_json, never diff_to_json: explaining a device must not touch the
		# adaptor's change-detection cache
		values = p.adaptor.to_json(dev)
		measurement = values.pop("measurement", "device_changes")

		states, sent_count, blocked = [], 0, 0
		for key in sorted(values):
			value = values[key]
			if isinstance(value, dict):
				continue
			sent, reason = self._send_decision(mode, key)
			checks = []
			for position, f in enumerate(p.FilterList, start=1):
				if f.state != key or not f.appliesTo(dev.id):
					continue
				passed, previous, change = p.evaluateFilter(f, None, dev, key, value)
				check = {"position": position, "name": f.name, "passes": bool(passed)}
				if f.filterStrategy == "percentChanged":
					check["baseline"] = previous
					check["percent_change"] = None if change is None else round(change, 3)
				checks.append(check)
				if sent and not passed:
					sent = False
					blocked += 1
					reason = f"blocked by filter {position} '{f.name}'"
					break
			entry = {"key": key, "value": value, "sent": sent, "reason": reason}
			if checks:
				entry["filters"] = checks
			sent_count += sent
			states.append(entry)

		lock = p.deviceLocks.get(dev.id)
		return {
			"device": device_ref(dev.id),
			"mode": mode,
			"measurement": measurement,
			"locked": dict(lock, since=iso(lock["since"])) if lock else None,
			"last_point_or_heartbeat": iso(p.deviceLastUpdated.get(dev.id)),
			"summary": {"keys": len(states), "sent": sent_count, "blocked_by_filters": blocked},
			"note": ("A key is written only when its value changes (or on the minimum-frequency heartbeat); "
					 "points also carry secondsSinceLastChanged / secondsSinceLastSuccessfulComm."),
			"states": states,
		}

	def search_states(self, query=None, state=None, limit=None, offset=None):
		p = self.plugin
		limit = _int_arg(limit, "limit", 1, 200, 50)
		offset = _int_arg(offset, "offset", 0, 100000, 0)
		if (query is None) == (state is None):
			raise ToolError("validation", "give exactly one of query (substring search) or state (exact key)")

		self.store.ensureCatalog()
		catalog = p.stateCatalog

		if query is not None:
			text = str(query).lower()
			matches = sorted((key for key in catalog if text in key.lower()), key=lambda k: (-catalog[k], k))
			page = matches[offset:offset + limit]
			return {
				"total": len(matches), "offset": offset, "limit": limit,
				"results": [{"state": key, "devices": catalog[key], "included": key in p.StatesIncludeList,
							 "always_sent": key in self.constants.ALWAYS_SENT_STATES} for key in page],
			}

		key = str(state)
		if key not in catalog:
			raise ToolError("not_found", f"no device has the state {key!r}",
							{"did_you_mean": suggestions(key, list(catalog))})
		holders = sorted((dev_id for dev_id, keys in p.deviceKeys.items() if key in keys),
						 key=lambda dev_id: (p.deviceNames.get(dev_id) or "").lower())
		results = []
		for dev_id in holders[offset:offset + limit]:
			try:
				dev = indigo.devices[dev_id]
			except KeyError:
				continue
			value = p.adaptor.to_json(dev).get(key)
			mode = self._mode(dev_id)
			sent, reason = self._send_decision(mode, key)
			results.append(dict(device_ref(dev_id), value=value, mode=mode, sent=sent, reason=reason))
		return {"state": key, "included": key in p.StatesIncludeList, "total": len(holders), "offset": offset,
				"limit": limit, "results": results}

	def get_filter_blocks(self, limit=None, device=None, state=None):
		p = self.plugin
		limit = _int_arg(limit, "limit", 1, 200, 50)
		device_name = None
		if device is not None:
			device_name = resolve_device(device).name
		records, scanned = read_records(p.FilterLogFileLoc, limit, device=device_name,
										state=None if state is None else str(state))
		return {"file": p.FilterLogFileLoc, "lines_scanned": scanned, "count": len(records),
				"newest_first": True, "entries": records}

	# ------------------------------------------------------------------
	# write tools: inclusion, settings, connection (phase 2)

	def set_device_mode(self, devices, mode, dry_run=False, expected_revision=None):
		if mode not in DEVICE_MODES:
			raise ToolError("validation", f"mode must be one of {', '.join(DEVICE_MODES)}")
		resolved = resolve_devices(devices, limit=50)
		ids = [dev.id for dev in resolved]
		target = 'global_states' if mode == 'default' else mode
		previous = {dev_id: self._mode(dev_id) for dev_id in ids}

		def mutate(config):
			config['include'] = [dev_id for dev_id in config['include'] if dev_id not in ids]
			config['exclude'] = [dev_id for dev_id in config['exclude'] if dev_id not in ids]
			if mode == 'all_states':
				config['include'] += ids
			elif mode == 'excluded':
				config['exclude'] += ids
			return [f"{dev.name} is already '{mode}'" for dev in resolved if previous[dev.id] == target]

		names = ", ".join(dev.name for dev in resolved)
		result = self._write("set_device_mode", mutate, dry_run, expected_revision, f"{mode}: {names}")
		result['affected_devices'] = [
			dict(device_ref(dev_id), previous_mode=previous[dev_id], mode=target,
				 keys=len(self.plugin.deviceKeys.get(dev_id, ())))
			for dev_id in ids if previous[dev_id] != target]
		if mode == 'all_states':
			many = [d for d in result['affected_devices'] if d['keys'] > 50]
			if many:
				result['warnings'].append("including a device sends every one of its states: " + ", ".join(
					f"{d['name']} ({d['keys']} keys)" for d in many))
		return result

	def update_included_states(self, add=None, remove=None, reset_to_defaults=False, allow_unknown=False,
							   dry_run=False, expected_revision=None):
		add = _string_list(add, "add")
		remove = _string_list(remove, "remove")
		reset_to_defaults = _bool_arg(reset_to_defaults, "reset_to_defaults")
		allow_unknown = _bool_arg(allow_unknown, "allow_unknown")
		if not (add or remove or reset_to_defaults):
			raise ToolError("validation", "give add, remove and/or reset_to_defaults")

		self.store.ensureCatalog()
		catalog = self.plugin.stateCatalog
		errors, did_you_mean = [], {}
		for index, state in enumerate(add):
			if state in self.constants.ALWAYS_SENT_STATES:
				errors.append({"path": f"add[{index}]", "message": (
					f"{state!r} is already sent on every point; adding it to the include list would send a point "
					f"every time it changes and multiply the write volume")})
			elif state not in catalog and not allow_unknown:
				errors.append({"path": f"add[{index}]", "message": f"no device has the state {state!r} "
																   f"(pass allow_unknown=true to add it anyway)"})
				did_you_mean[state] = suggestions(state, list(catalog))
		if errors:
			details = {"errors": errors}
			if did_you_mean:
				details["did_you_mean"] = did_you_mean
			raise ToolError("validation", "some states cannot be added", details)

		def mutate(config):
			warnings = []
			if reset_to_defaults:
				config['states'] = list(self.constants.DEFAULT_STATES)
			for state in remove:
				if state in config['states']:
					config['states'].remove(state)
				else:
					warnings.append(f"{state!r} was not in the include list")
			for state in add:
				if state in config['states']:
					warnings.append(f"{state!r} is already included")
				else:
					config['states'].append(state)
			if not config['states']:
				raise ConfigError('validation', "that would leave the global include list empty, so every device "
												"not in the include-devices list would stop logging",
								  [{"path": "remove", "message": "the include list cannot be emptied"}])
			return warnings

		parts = (["reset to defaults"] if reset_to_defaults else []) + \
				([f"add {', '.join(add)}"] if add else []) + ([f"remove {', '.join(remove)}"] if remove else [])
		result = self._write("update_included_states", mutate, dry_run, expected_revision, "; ".join(parts))
		before = set(result['before'].get('states', []))
		after = set(result['after'].get('states', []))
		result['affected_devices'] = {
			'added': {state: self._keys_count(state) for state in sorted(after - before)},
			'removed': {state: self._keys_count(state) for state in sorted(before - after)},
		}
		return result

	def update_settings(self, minimum_update_frequency=None, retention=None, debug=None, dry_run=False,
						expected_revision=None):
		if minimum_update_frequency is None and retention is None and debug is None:
			raise ToolError("validation", "give minimum_update_frequency, retention and/or debug")

		frequency = None
		if minimum_update_frequency is not None:
			text = str(minimum_update_frequency).strip().lower()
			if isinstance(minimum_update_frequency, bool):
				text = ''
			if text in ('disabled', '-1'):
				frequency = 'disabled'
			elif text in FREQUENCY_CHOICES:
				frequency = int(text)
			else:
				raise ToolError("validation", "minimum_update_frequency must be 5, 10, 15, 30, 60 or 'disabled'")

		months = None
		if retention is not None:
			text = '' if isinstance(retention, bool) else str(retention).strip().lower()
			months = '-1' if text in ('forever', '-1') else text
			if months not in RETENTION_CHOICES:
				raise ToolError("validation", "retention must be 6, 12, 24, 60 (months) or 'forever'")

		if debug is not None:
			if not isinstance(debug, dict) or not debug:
				raise ToolError("validation", "debug must be an object such as {\"transport\": true}")
			unknown = [key for key in debug if key not in ('plugin', 'config', 'transport', 'transport_l2', 'json')]
			bad = [key for key, value in debug.items() if not isinstance(value, bool)]
			if unknown or bad:
				raise ToolError("validation", "debug keys are plugin, config, transport, transport_l2 and json, "
											  "each true or false")

		def mutate(config):
			warnings = []
			settings = config['settings']
			if frequency is not None:
				settings['minimum_update_frequency'] = frequency
			if months is not None:
				settings['retention'] = months
				if config['connection']['version'] != '1':
					warnings.append("retention applies to InfluxDB 1.x only; InfluxDB 3 manages retention on the server")
			if debug:
				settings['debug'].update(debug)
			return warnings

		summary = ", ".join(f"{key}={value}" for key, value in (
			("minimum_update_frequency", frequency),
			("retention", describe_retention(months) if months else None),
			("debug", debug)) if value is not None)
		result = self._write("update_settings", mutate, dry_run, expected_revision, summary)
		retention_changed = (result['before'].get('settings', {}).get('retention')
							 != result['after'].get('settings', {}).get('retention'))
		if result['changed'] and not result['dry_run'] and retention_changed and self.plugin.InfluxVersion == '1':
			self.plugin.applyRetentionInBackground()
			result['warnings'].append("the retention policy is being updated on the server in the background; "
									  "see get_status and the Event Log")
		return result

	def update_connection(self, host=None, port=None, ssl=None, version=None, database=None, user=None,
						  password=None, force=False, dry_run=False, expected_revision=None):
		p = self.plugin
		given = {arg: value for arg, value in (('host', host), ('port', port), ('ssl', ssl), ('version', version),
											   ('database', database), ('user', user), ('password', password))
				 if value is not None}
		if not given:
			raise ToolError("validation", "give at least one of host, port, ssl, version, database, user, password")
		force = _bool_arg(force, "force")
		dry_run = _bool_arg(dry_run, "dry_run")
		expected_revision = _revision_arg(expected_revision)
		if ssl is not None and not isinstance(ssl, bool):
			raise ToolError("validation", "ssl must be true or false")
		if password is not None and not isinstance(password, str):
			raise ToolError("validation", "password must be a string")

		proposed = {'InfluxHost': p.InfluxHost, 'InfluxHTTPPort': p.InfluxHTTPPort, 'InfluxSSL': p.InfluxSSL,
					'InfluxVersion': p.InfluxVersion, 'InfluxDB': p.InfluxDB, 'InfluxUser': p.InfluxUser,
					'InfluxPassword': p.InfluxPassword}
		for arg, value in given.items():
			proposed[CONNECTION_ARGS[arg]] = str(value) if arg in ('port', 'version') else value
		settings, errors = validate_connection_settings(proposed)
		if errors:
			raise ToolError("validation", "invalid connection settings",
							{"errors": [{"path": FIELD_TO_ARG.get(field, field), "message": message}
										for field, message in errors.items()]})

		password_changed = password is not None and password != p.InfluxPassword
		new_connection = {'host': settings['host'], 'port': str(settings['port']), 'ssl': settings['ssl'],
						  'version': settings['version'], 'database': settings['database'], 'user': settings['username']}
		current = {'host': p.InfluxHost, 'port': str(p.InfluxHTTPPort), 'ssl': bool(p.InfluxSSL),
				   'version': str(p.InfluxVersion), 'database': p.InfluxDB, 'user': p.InfluxUser}

		def mutate(config):
			config['connection'].update(new_connection)
			if password_changed:
				config['connection']['credentials_version'] += 1

		changes = [f"{arg} {current[arg]!r} -> {new_connection[arg]!r}" for arg in new_connection
				   if new_connection[arg] != current[arg]]
		if password_changed:
			changes.append("password changed")
		summary = ", ".join(changes) or "no change"

		def strip_counter(result):
			for section in ('before', 'after'):
				result[section].get('connection', {}).pop('credentials_version', None)
			return result

		if dry_run:
			result = strip_counter(self.store.apply("mcp: update_connection", mutate, dry_run=True,
													expected_revision=expected_revision))
			result.update(committed=False, password_changed=password_changed)
			return result

		if not changes:
			# the current settings: test them, change nothing
			def test_only():
				result = strip_counter(self.store.apply("mcp: update_connection", mutate, dry_run=True,
														expected_revision=expected_revision))
				test = p.testConnection(settings)
				result.update(dry_run=False, committed=False, password_changed=False, test=test)
				result['warnings'] = ["these are the current settings: tested, nothing changed"] + test['warnings']
				return result

			return AsyncResult(test_only)

		def work():
			test = p.testConnection(settings)
			if not test['passed'] and not force:
				raise ToolError("validation", f"connection test failed ({test['error']}); the current settings stay "
											  f"in force. Fix the settings, or pass force=true to save them anyway.",
								{"test": test})
			with self.store.lock:
				# the first connection settings ever saved make the plugin configured
				# (persistConfig only writes connection prefs once it is)
				was_configured = p.configured
				p.configured = True
				try:
					result = self.store.apply("mcp: update_connection", mutate, expected_revision=expected_revision,
											  summary=summary)
				except Exception:
					p.configured = was_configured
					raise
				if password_changed:
					p.InfluxPassword = settings['password']
				p.persistConfig()
			p.logger.info(f"MCP: update_connection {summary} (revision {self.store.revision})")
			p.requestReconnect("InfluxDB connection settings changed (MCP), reconnecting...")
			strip_counter(result)
			result.update(committed=True, password_changed=password_changed, test=test)
			if not test['passed']:
				result['warnings'].append("saved despite a failed connection test (force=true)")
			result['warnings'] += test['warnings']
			return result

		return AsyncResult(work)

	def reconnect(self):
		p = self.plugin
		if not p.configured:
			raise ToolError("conflict", "the plugin has not been configured yet; set the connection first")
		previous = p.connectionState
		p.requestReconnect("MCP: reconnect requested")
		return {"requested": True, "previous_state": previous,
				"note": "the connection is retried in the background; check get_status for the result"}

	def list_snapshots(self):
		return {"revision": self.store.revision, "snapshots": self.store.listSnapshots()}

	def restore_snapshot(self, revision, dry_run=False, expected_revision=None):
		if isinstance(revision, bool) or not isinstance(revision, int):
			raise ToolError("validation", "revision must be an integer from list_snapshots")
		snapshot = self.store.readSnapshot(revision)
		if snapshot is None:
			raise ToolError("not_found", f"no snapshot of revision {revision}",
							{"available": [s['revision'] for s in self.store.listSnapshots()]})
		saved = snapshot['config']

		def mutate(config):
			for section in RESTORABLE:
				config[section] = saved[section]
			warnings = []
			theirs = {k: v for k, v in saved.get('connection', {}).items() if k != 'credentials_version'}
			mine = {k: v for k, v in config['connection'].items() if k != 'credentials_version'}
			if theirs != mine:
				warnings.append("connection settings are not restored (the snapshot had "
								+ ", ".join(f"{k}={v!r}" for k, v in theirs.items() if mine.get(k) != v)
								+ "); use update_connection to change them")
			gone = [dev_id for dev_id in config['include'] + config['exclude'] if dev_id not in indigo.devices]
			if gone:
				warnings.append(f"{len(gone)} devices in the snapshot no longer exist; housekeeping drops them")
			return warnings

		result = self._write("restore_snapshot", mutate, dry_run, expected_revision,
							 f"to revision {revision} ({snapshot.get('summary')})")
		result['restored_from'] = {"revision": revision, "time": snapshot.get('time'),
								   "summary": snapshot.get('summary')}
		retention_changed = (result['before'].get('settings', {}).get('retention')
							 != result['after'].get('settings', {}).get('retention'))
		if result['changed'] and not result['dry_run'] and retention_changed and self.plugin.InfluxVersion == '1':
			self.plugin.applyRetentionInBackground()
		return result

	# ------------------------------------------------------------------
	# filter CRUD (phase 3)

	def _scope_devices(self, refs, path):
		if refs is None:
			return None
		return [dev.id for dev in resolve_devices(refs, path=path, limit=MAX_FILTER_DEVICES)]

	def _check_filter(self, f, allow_unknown, allow_empty_scope=False):
		"""Validation errors ({path, message}) and suggestions for a complete filter
		dict.  allow_empty_scope: a device scope that is already empty (its devices
		were deleted) may stay empty while other fields are edited."""
		errors, did_you_mean = [], {}
		catalog = self.plugin.stateCatalog
		state = f.get('state')
		if not isinstance(state, str) or not state.strip():
			errors.append({"path": "state", "message": "give the state key the filter checks"})
		elif state not in catalog and not allow_unknown:
			errors.append({"path": "state", "message": f"no device has the state {state!r} "
													   f"(pass allow_unknown=true to use it anyway)"})
			did_you_mean[state] = suggestions(state, list(catalog))
		if f.get('strategy') not in FILTER_STRATEGIES:
			errors.append({"path": "strategy", "message": "strategy must be min_max or percent_changed"})
		elif f['strategy'] == 'min_max':
			for key in ('min', 'max'):
				if not _is_number(f.get(key)):
					errors.append({"path": key, "message": f"{key} must be a number"})
			if _is_number(f.get('min')) and _is_number(f.get('max')) and not f['min'] < f['max']:
				errors.append({"path": "min", "message": "min must be smaller than max"})
		elif not _is_number(f.get('max_percent')) or not f['max_percent'] > 0:
			errors.append({"path": "max_percent", "message": "max_percent must be a number greater than 0"})
		if f.get('scope') not in SCOPES:
			errors.append({"path": "scope", "message": "scope must be all, devices or all_except"})
		elif f['scope'] == 'all' and f.get('devices'):
			errors.append({"path": "devices", "message": "devices only go with scope 'devices' or 'all_except'"})
		elif f['scope'] != 'all' and not f.get('devices') and not allow_empty_scope:
			errors.append({"path": "devices", "message": f"scope {f['scope']!r} needs at least one device"})
		if len(f.get('devices') or []) > MAX_FILTER_DEVICES:
			errors.append({"path": "devices", "message": f"at most {MAX_FILTER_DEVICES} devices"})
		for key in ('lock_on_failure', 'log_to_event_log'):
			if not isinstance(f.get(key), bool):
				errors.append({"path": key, "message": f"{key} must be true or false"})
		if not isinstance(f.get('name'), str):
			errors.append({"path": "name", "message": "name must be a string ('' = generated)"})
		return errors, did_you_mean

	@staticmethod
	def _raise_invalid(errors, did_you_mean, message="invalid filter"):
		details = {"errors": errors}
		if did_you_mean:
			details["did_you_mean"] = did_you_mean
		raise ConfigError('validation', message, errors, details)

	def _state_sent_warnings(self, state, config):
		"""A filter only sees values that are sent: say so when few or none are."""
		if state in self.constants.ALWAYS_SENT_STATES or state in config['states']:
			return []
		senders = [dev_id for dev_id in config['include'] if state in self.plugin.deviceKeys.get(dev_id, ())]
		if not senders:
			return [f"{state!r} is not sent for any device (not in the global include list, and no included device "
					f"has it), so this filter has no effect until it is"]
		return [f"{state!r} is not in the global include list: the filter only sees the {len(senders)} included "
				f"device(s) that have it"]

	def _filter_view(self, f, position):
		rule = InfluxFilter.fromDict(f)
		view = {"position": position, "name": rule.name, "state": f['state'], "strategy": f['strategy'],
				"scope": f['scope'], "log_to_event_log": f['log_to_event_log']}
		if f['strategy'] == 'min_max':
			view.update(min=f['min'], max=f['max'])
		else:
			view.update(max_percent=f['max_percent'], lock_on_failure=f['lock_on_failure'])
		if f['scope'] != 'all':
			view['devices'] = [device_ref(dev_id) for dev_id in f['devices'][:20]]
			view['device_count'] = len(f['devices'])
		return view

	def _filter_impact(self, f):
		"""Which logged devices have the state and fall in the filter's scope,
		and - for a min/max filter - which of their current values it would block."""
		p = self.plugin
		rule = InfluxFilter.fromDict(f)
		excluded = set(p.DeviceExcludeList)
		covered = [dev_id for dev_id, keys in p.deviceKeys.items()
				   if f['state'] in keys and dev_id not in excluded and rule.appliesTo(dev_id)]
		impact = {"devices_with_state_in_scope": len(covered)}
		if f['strategy'] == 'min_max':
			blocked = []
			for dev_id in covered:
				try:
					value = p.adaptor.to_json(indigo.devices[dev_id]).get(f['state'])
				except KeyError:
					continue
				number = self.constants.numeric_value(value)
				if number is not None and not rule.minValue <= number <= rule.maxValue:
					blocked.append(dict(device_ref(dev_id), value=value))
			impact["current_values_blocked"] = blocked[:50]
			impact["current_values_blocked_count"] = len(blocked)
		return impact

	def create_filter(self, state, strategy, min=None, max=None, max_percent=None, scope='all', devices=None,
					  lock_on_failure=True, log_to_event_log=False, name=None, position=None, allow_unknown=False,
					  dry_run=False, expected_revision=None):
		allow_unknown = _bool_arg(allow_unknown, "allow_unknown")
		self.store.ensureCatalog()
		f = {'state': state.strip() if isinstance(state, str) else state, 'strategy': strategy,
			 'min': min if min is not None else 0.0, 'max': max if max is not None else 0.0,
			 'max_percent': max_percent if max_percent is not None else 0.0, 'scope': scope,
			 'devices': self._scope_devices(devices, "devices") or [], 'lock_on_failure': lock_on_failure,
			 'log_to_event_log': log_to_event_log, 'name': name if name is not None else ''}
		errors, did_you_mean = self._check_filter(f, allow_unknown)
		if position is not None and (isinstance(position, bool) or not isinstance(position, int)):
			errors.append({"path": "position", "message": "position must be an integer (1 = first)"})
		if errors:
			self._raise_invalid(errors, did_you_mean)
		for key in ('min', 'max', 'max_percent'):
			f[key] = float(f[key])
		f['devices'] = sorted(set(f['devices']))
		inserted = {}

		def mutate(config):
			filters = config['filters']
			at = len(filters) + 1 if position is None else position
			if not 1 <= at <= len(filters) + 1:
				raise ConfigError('validation', f"position must be from 1 to {len(filters) + 1}",
								  [{"path": "position", "message": f"1 to {len(filters) + 1}"}])
			filters.insert(at - 1, dict(f))
			inserted['position'] = at
			return self._state_sent_warnings(f['state'], config)

		rule_name = InfluxFilter.fromDict(f).name
		result = self._write("create_filter", mutate, dry_run, expected_revision,
							 f"'{rule_name}'" + (f" at position {position}" if position else ""))
		result['filter'] = self._filter_view(f, inserted.get('position'))
		result['affected_devices'] = self._filter_impact(f)
		return result

	def update_filter(self, position, expected_name, state=None, strategy=None, min=None, max=None,
					  max_percent=None, scope=None, devices=None, add_devices=None, remove_devices=None,
					  lock_on_failure=None, log_to_event_log=None, name=None, new_position=None, allow_unknown=False,
					  dry_run=False, expected_revision=None):
		allow_unknown = _bool_arg(allow_unknown, "allow_unknown")
		if isinstance(position, bool) or not isinstance(position, int):
			raise ToolError("validation", "position must be an integer from get_config (1 = first)")
		if not isinstance(expected_name, str):
			raise ToolError("validation", "expected_name is required: the name get_config shows for that position")
		if new_position is not None and (isinstance(new_position, bool) or not isinstance(new_position, int)):
			raise ToolError("validation", "new_position must be an integer")
		self.store.ensureCatalog()
		replace = self._scope_devices(devices, "devices")
		add = set(self._scope_devices(add_devices, "add_devices") or [])
		remove = set(self._scope_devices(remove_devices, "remove_devices") or [])
		given = {key: value for key, value in (('state', state), ('strategy', strategy), ('min', min), ('max', max),
											   ('max_percent', max_percent), ('lock_on_failure', lock_on_failure),
											   ('log_to_event_log', log_to_event_log), ('name', name)) if value is not None}
		if not given and scope is None and replace is None and not add and not remove and new_position is None:
			raise ToolError("validation", "give at least one field to change")
		outcome = {}

		def mutate(config):
			filters = config['filters']
			if not 1 <= position <= len(filters):
				raise ConfigError('not_found', f"there is no filter {position} (there are {len(filters)})")
			current = filters[position - 1]
			current_name = InfluxFilter.fromDict(current).name
			if current_name != expected_name:
				raise ConfigError('conflict', f"filter {position} is {current_name!r}, not {expected_name!r}: positions "
											  f"shift when filters change - read get_config again and retry")
			f = dict(current, **given)
			if scope is not None and scope != current['scope']:
				f['scope'] = scope
				f['devices'] = []  # a new scope's list is never the old one's (it would invert its meaning)
			if replace is not None:
				f['devices'] = replace
			f['devices'] = sorted((set(f['devices']) | add) - remove)
			if f['scope'] == 'all' and (add or replace):
				raise ConfigError('validation', "devices only go with scope 'devices' or 'all_except'",
								  [{"path": "scope", "message": "set scope to 'devices' or 'all_except'"}])
			untouched_empty_scope = (f['scope'] == current['scope'] and not current['devices'] and not f['devices'])
			errors, did_you_mean = self._check_filter(f, allow_unknown or f['state'] == current['state'],
													  allow_empty_scope=untouched_empty_scope)
			if errors:
				self._raise_invalid(errors, did_you_mean)
			warnings = []
			if f['scope'] == 'devices' and not f['devices']:
				warnings.append("this filter applies to no devices (its devices no longer exist); give it devices "
								"or delete it")
			for key in ('min', 'max', 'max_percent'):
				f[key] = float(f[key])

			target = position if new_position is None else new_position
			if not 1 <= target <= len(filters):
				raise ConfigError('validation', f"new_position must be from 1 to {len(filters)}",
								  [{"path": "new_position", "message": f"1 to {len(filters)}"}])
			del filters[position - 1]
			filters.insert(target - 1, f)
			outcome.update(filter=f, position=target, old_name=current_name, old=current)
			return warnings

		result = self._write("update_filter", mutate, dry_run, expected_revision, f"{position} '{expected_name}'", log=False)
		f, old = outcome['filter'], outcome['old']
		changes = [f"{key} {old[key]!r} -> {f[key]!r}" for key in ('state', 'strategy', 'min', 'max', 'max_percent',
																  'scope', 'lock_on_failure', 'log_to_event_log', 'name')
				   if old[key] != f[key]]
		if old['devices'] != f['devices']:
			names = [device_ref(dev_id)['name'] for dev_id in f['devices'][:5]]
			changes.append(f"devices -> {len(f['devices'])} ({', '.join(str(n) for n in names)}"
						   + (", ..." if len(f['devices']) > 5 else "") + ")")
		if outcome['position'] != position:
			changes.append(f"moved to position {outcome['position']}")
		if result['changed'] and not result['dry_run']:
			self.plugin.logger.info(f"MCP: update_filter {position} '{outcome['old_name']}': {'; '.join(changes)} "
									f"(revision {result['revision']})")
		result['changes'] = changes
		result['filter'] = self._filter_view(f, outcome['position'])
		result['affected_devices'] = self._filter_impact(f)
		return result

	def delete_filter(self, position, expected_name, dry_run=False, expected_revision=None):
		if isinstance(position, bool) or not isinstance(position, int):
			raise ToolError("validation", "position must be an integer from get_config (1 = first)")
		if not isinstance(expected_name, str):
			raise ToolError("validation", "expected_name is required: the name get_config shows for that position")
		removed = {}

		def mutate(config):
			filters = config['filters']
			if not 1 <= position <= len(filters):
				raise ConfigError('not_found', f"there is no filter {position} (there are {len(filters)})")
			current_name = InfluxFilter.fromDict(filters[position - 1]).name
			if current_name != expected_name:
				raise ConfigError('conflict', f"filter {position} is {current_name!r}, not {expected_name!r}: positions "
											  f"shift when filters change - read get_config again and retry")
			removed['filter'] = filters.pop(position - 1)
			return []

		result = self._write("delete_filter", mutate, dry_run, expected_revision, f"{position} '{expected_name}'")
		result['deleted'] = self._filter_view(removed['filter'], position)
		return result
