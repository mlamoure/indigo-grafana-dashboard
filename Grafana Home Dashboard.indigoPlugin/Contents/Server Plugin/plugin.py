#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2018 Mike Lamoureux
# Modernized 2025 - InfluxDB client only (no bundled servers)

import indigo
import datetime
import json
import logging
import time
import os
import queue
import re
import shutil
import threading
from json_adaptor import JSONAdaptor, LIVENESS_FIELDS, TYPE_CONVERTERS
from influx_client import (InfluxClient, InfluxError, InfluxConnectionError, InfluxHTTPError,
						   InfluxQueryError, parse_duration_seconds)
from influx_settings import (to_bool, validate_connection_settings, validate_other_settings,
							 retention_spec, describe_retention, parse_frequency)
from influx_filter import InfluxFilter, GENERATED_FILTER_NAME, FILTER_PREFS_VERSION
from config_store import ConfigStore, ConfigError, frequency_label

WAIT_POLLING_INTERVAL = 5 # used ocassionally to wait for a sequantal process to happen
FAST_POLLING_INTERVAL = 5
DEFAULT_POLLING_INTERVAL = 60  # number of seconds between each poll
LONG_POLLING_INTERVAL = 60 * 15
UPDATE_STATES_LIST = 15 # how frequently (in minutes) to update the state list
DEFAULT_UPDATE_FREQUENCY = 24 # frequency of update check, in hours
MAX_LOG_FILE_OUTPUT_LINES = 50
LOG_PRUNE_FREQUENCY = 24 # how frequently to prune the logs to the MAX_LOG_FILE_OUTPUT_LINES length
MAX_INFLUX_WRITE_RETRIES = 5  # Maximum type corrections per batch
MAX_CONNECTION_RETRIES = 10  # Switch to long polling interval after this many connection failures
INFLUX_BATCH_MAX = 500  # maximum points per write_points() call
INFLUX_QUEUE_MAX = 10000  # bounded pending-write queue; new points are dropped when full
INFLUX_FLUSH_INTERVAL = 1.0  # seconds the writer coalesces points before flushing a batch
WRITER_PAUSE_INTERVAL = 1.0  # seconds the writer waits between checks while disconnected
MAX_BATCH_ATTEMPTS = 10  # a batch failing this many times for transient reasons is dropped
QUEUE_FULL_WARNING_INTERVAL = 15 * 60  # seconds between "queue is full" warnings

# writeBatch() outcomes
WRITE_OK = 'ok'          # written, or dropped because InfluxDB rejected the data itself
WRITE_RETRY = 'retry'    # transient failure (network, 5xx, missing database): keep the batch
WRITE_HALT = 'halt'      # credentials refused: keep the batch, stop until reconfigured

RETENTION_POLICY_NAME = 'indigo_policy'

DEFAULT_STATES = ["state.onOffState", "onState", "onState.num", "model", "subModel", "deviceTypeId", "state.hvac_state", "energyCurLevel", "energyAccumTotal", "value.num", "sensorValue", "coolSetpoint", "heatSetpoint", "batteryLevel", "batteryLevel.num"]

# States the JSON adaptor sends on every point regardless of the include list.  The
# liveness fields must NOT be added to DEFAULT_STATES or the include list: anything
# in that list sets hasUpdate, and lastChanged moves on every device change, so it
# would emit a point per change per device.  They are offered for building filters
# but hidden from the include-states picker so they can't be added by accident.
ALWAYS_SENT_STATES = {'name', 'id'} | {key for pair in LIVENESS_FIELDS for key in pair}

# Prefs left behind by plugin versions 2.x (bundled InfluxDB/Grafana servers) and
# by fields since removed from PluginConfig.xml.  GrafanaAdminPassword is a
# plaintext password nothing reads any more.  Removed on startup.
OBSOLETE_PREFS = (
	'GrafanaAdminPassword', 'GrafanaAnonymous', 'GrafanaAnonymousInstruction', 'GrafanaDataLocation',
	'GrafanaDisableInstruction', 'GrafanaPort', 'DisableGrafana', 'ExternalDB', 'InfluxDataLocation',
	'InfluxDisableInstruction', 'InfluxPort', 'InfluxPortInstruction', 'InfluxUsePasswordInstruction',
	'DirectoriesInstruction', 'DirectoriesInstruction2', 'DirectoriesInstruction3', 'SortInstruction',
	'listIncStatesSort', 'listAvailableDevices', 'listAvailableExcludedDevices', 'menuAvailableExcludedDevices',
	'addDeviceExcludedButton', 'removeDeviceExcludedButton', 'section1', 'blank1', 'simpleSeparator2',
)

def numeric_value(value):
	"""Coerce a value from the JSON adaptor to a float, or None when it is not
	numeric.  Bools are deliberately rejected: a False -> True flip is a
	divide-by-zero, not a percentage change."""
	if isinstance(value, bool):
		return None

	try:
		return float(value)
	except (TypeError, ValueError):
		return None

def percent_changed(previousValue, newValue):
	"""Percent change from previousValue to newValue, or None when it cannot be
	computed - either side non-numeric, or a zero baseline.  Callers treat None
	as 'no opinion' and let the value through."""
	previous = numeric_value(previousValue)
	current = numeric_value(newValue)

	if previous is None or current is None or previous == 0:
		return None

	return ((current - previous) / previous) * 100.0

def bumpCredentials(config):
	"""Mark a password change in the store's secret-free configuration."""
	config['connection']['credentials_version'] += 1


def ui_name(name):
	"""Indigo's dynamic lists reject commas and semicolons in option labels."""
	return str(name).replace(",", " ").replace(";", " ")

# InfluxDB 3 (IOx) column types as they appear in v1-compat error messages
IOX_TYPE_MAP = {
	'string': 'str',
	'float': 'float',
	'integer': 'int',
	'unsigned': 'int',
	'boolean': 'bool'
}

class WriteStats:
	"""Write-path counters, updated by the writer thread and read by the status
	reporting.  Points are counted when they reach InfluxDB or are given up on."""

	def __init__(self):
		self.lock = threading.Lock()
		self.started = datetime.datetime.now()
		self.pointsWritten = 0
		self.batchesWritten = 0
		self.dropped = {'queue_full': 0, 'rejected': 0, 'shutdown': 0, 'gave_up': 0}
		self.lastSuccess = None
		self.lastError = None

	def written(self, count):
		with self.lock:
			self.pointsWritten += count
			self.batchesWritten += 1
			self.lastSuccess = datetime.datetime.now()

	def drop(self, reason, count=1):
		with self.lock:
			self.dropped[reason] = self.dropped.get(reason, 0) + count

	def error(self, err):
		with self.lock:
			self.lastError = {
				'time': datetime.datetime.now(),
				'status': getattr(err, 'status_code', None),
				'message': str(getattr(err, 'message', err))[:300],
			}

	def snapshot(self):
		with self.lock:
			return {
				'started': self.started,
				'points_written': self.pointsWritten,
				'batches_written': self.batchesWritten,
				'points_dropped': dict(self.dropped),
				'last_success': self.lastSuccess,
				'last_error': dict(self.lastError) if self.lastError else None,
			}

class Plugin(indigo.PluginBase):
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		indigo.devices.subscribeToChanges()
		indigo.variables.subscribeToChanges()
		self.connection = None
		self.adaptor = None
		self.configured = True

		# connectionLock serializes connect(): the concurrent thread, a reconnect
		# requested by the config dialog and the writer can all trigger one.
		# configLock guards the include/exclude/filter lists, which the concurrent
		# thread rebuilds and persists while ConfigUI callbacks edit them.
		self.connectionLock = threading.Lock()
		self.configLock = threading.RLock()

		self.ConnectionRetryCount = 0
		self.QuietConnectionError = False
		self.StopConnectionAttempts = False
		self.connectionState = 'starting'
		self.lastConnectError = None
		self.everConnected = False
		self.serverInfo = {}
		self.retentionNoticeLogged = False

		# Heartbeat clocks for the minimum update frequency, keyed by id - never by
		# name.  In memory only; cleared on restart.
		self.deviceLastUpdated = {}
		self.variableLastUpdated = {}
		# Devices a percentChanged filter locked out of heartbeats until they report
		# a change: dev id -> {'since', 'filter', 'state'}
		self.deviceLocks = {}

		# Last value this plugin actually WROTE, per device, for the states some
		# percentChanged filter watches.  UpdateAll() has no origDev to compare
		# against, so this is its baseline.  Deliberately NOT the JSON adaptor's
		# cache: that one is updated with the full device before the filters run,
		# so it records values the filters then block - a blocked spike would
		# become its own baseline and sail through on the next heartbeat.
		self.DeviceLastWrittenValues = {}
		self.PercentChangedStates = set()

		self.StatesIncludeList = []
		self.DeviceIncludeList = []
		self.DeviceExcludeList = []
		self.FilterList = []
		self.filtersUnreadable = False

		# {state key: number of devices that have it} and {dev id: UI label},
		# rebuilt every UPDATE_STATES_LIST minutes by BuildConfigurationLists
		self.stateCatalog = {}
		self.deviceNames = {}
		self.deviceKeys = {}  # dev id -> frozenset of its keys, for search_states
		self.catalogBuilt = None

		# Working copy of the include lists while the plugin config dialog is
		# open.  Its buttons edit this copy; closedPrefsConfigUi commits it
		# through the store unless the user cancelled.
		self.dialog = None
		self.dialogPassword = None
		self.filterEditGuard = None  # (position index, name) the filters dialog is editing
		self.filterListShown = None  # filter names as the filters dialog last listed them

		# every configuration change goes through the store (config_store.py)
		self.credentialsVersion = 0
		self.store = ConfigStore(self)
		self._tool_dispatcher = None  # MCP tool provider, built on first call

		self.folders = {}
		self.pollingInterval = DEFAULT_POLLING_INTERVAL
		self.connected = False

		# Pending InfluxDB writes: producers (device/variable callbacks,
		# UpdateAll) enqueue and never touch the network; a single writer
		# thread batches them into write_points() calls (influxWriterLoop)
		self.write_queue = queue.Queue(maxsize=INFLUX_QUEUE_MAX)
		self.writer_thread = None
		self.writer_stop = threading.Event()
		self.lastQueueFullWarning = None
		self.stats = WriteStats()
		self.lastErrorLog = {}

		self.FilterLogFileLoc = None

		self.LastConfigRefresh = datetime.datetime.now()

		self.lastUpdateCheck = None
		self.lastLogPrune = None

	def startup(self):
		try:
			self.migratePrefs()
			self.loadSettings()
			self.loadLists()
			self.loadFilters()
			self.adaptor = JSONAdaptor(self.logger, self.TransportDebug, self.TransportDebugL2, self.JSONDebug)

		except Exception as e:
			self.logger.exception(e)
			self.logger.error("missing proper configuration to start up.")
			self.configured = False

		self.FilterLogFileLoc = self.prepareFilterLog()

		self.writer_thread = threading.Thread(target=self.influxWriterLoop, name="InfluxWriter", daemon=True)
		self.writer_thread.start()

		# the first connect() and UpdateAll() run at the top of runConcurrentThread,
		# so an unreachable server can't hold up plugin startup
		self.BuildConfigurationLists()
		self.pruneFilterBlocksEventLog()

		# Tell MCP Advanced Tools (if installed) to read our
		# mcp-manifest.json.  Harmless no-op when nobody subscribes.
		try:
			indigo.server.broadcastToSubscribers("mcp_tools_updated")
		except Exception as e:
			self.logger.debug(f"mcp_tools_updated broadcast failed: {e}")

	def migratePrefs(self):
		# InfluxDB version selection: "1" = InfluxDB 1.7/1.8 (default), "3" =
		# InfluxDB 3 via its v1-compat API. Migrates the pre-2026.7.0
		# InfluxV3Compat checkbox pref and persists the result so the config
		# dialog shows the migrated selection.
		version = str(self.pluginPrefs.get('InfluxVersion', ''))
		if version not in ('1', '3'):
			self.pluginPrefs['InfluxVersion'] = '3' if to_bool(self.pluginPrefs.get('InfluxV3Compat', False)) else '1'

		removed = [key for key in OBSOLETE_PREFS + ('InfluxV3Compat',) if key in self.pluginPrefs]
		for key in removed:
			del self.pluginPrefs[key]
		if removed:
			self.logger.info(f"removed {len(removed)} obsolete settings left by older plugin versions: {', '.join(removed)}")
			self.savePrefs()

	def loadSettings(self):
		prefs = self.pluginPrefs
		# never configured = the config dialog has never been saved; don't try to
		# reach the 'localhost' default until the user has said where InfluxDB is
		self.configured = 'InfluxHost' in prefs
		if not self.configured:
			self.connectionState = 'not_configured'
		self.InfluxHost = prefs.get('InfluxHost', 'localhost')
		self.InfluxSSL = to_bool(prefs.get('InfluxSSL', False))
		self.InfluxHTTPPort = str(prefs.get('InfluxHTTPPort', '8086'))
		self.InfluxUser = prefs.get('InfluxUser', 'indigo')
		self.InfluxPassword = prefs.get('InfluxPassword', 'indigo')
		self.InfluxDB = prefs.get('InfluxDB', 'indigo')
		self.InfluxRetention = str(prefs.get('InfluxRetention', '6'))
		self.InfluxVersion = str(prefs.get('InfluxVersion', '1'))
		self.InfluxV3Compat = self.InfluxVersion == '3'

		self.minimumUpdateFrequency = parse_frequency(prefs.get("MinimumUpdateFrequency", 5))

		# Debug Preferences
		self.debug = to_bool(prefs.get("ServerDebug", False))
		self.ConfigDebug = to_bool(prefs.get("ConfigDebug", False))
		self.TransportDebug = to_bool(prefs.get("TransportDebug", False))
		self.TransportDebugL2 = to_bool(prefs.get("TransportDebugL2", False))
		self.JSONDebug = to_bool(prefs.get("JSONDebug", False))

	def loadLists(self):
		prefs = self.pluginPrefs
		if 'listIncStates' in prefs:
			self.StatesIncludeList = self.cleanStateList(prefs['listIncStates'])
			if not self.StatesIncludeList:
				self.logger.warning("the global include-states list is empty, so only devices in the include-devices list are logged. Use 'reset to default states' in the plugin config to restore the defaults.")
		else:
			# never configured: start from the defaults
			self.StatesIncludeList = DEFAULT_STATES[:]

		self.DeviceIncludeList = self.cleanDeviceList(prefs.get("listIncDevices", []))
		self.DeviceExcludeList = self.cleanDeviceList(prefs.get("listExclDevices", []))

	@staticmethod
	def cleanStateList(states):
		cleaned = []
		for state in states or []:
			state = str(state).strip()
			if state and state not in cleaned:
				cleaned.append(state)
		return cleaned

	@staticmethod
	def cleanDeviceList(devices):
		cleaned = []
		for item in devices or []:
			try:
				dev_id = int(item)
			except (TypeError, ValueError):
				continue
			if dev_id not in cleaned:
				cleaned.append(dev_id)
		return cleaned

	def loadFilters(self):
		preferencesFilterList = self.pluginPrefs.get("listFilterList", [])
		preferencesFilterVersion = self.pluginPrefs.get("preferencesFilterVersion", "1.0.0")

		filters = []
		try:
			if preferencesFilterVersion not in ("1.0.0", "2.0.0", "3.0.0"):
				raise ValueError(f"unknown filter format {preferencesFilterVersion}")
			for item in preferencesFilterList:
				filters.append(InfluxFilter.fromPrefs(item, preferencesFilterVersion))

		except (IndexError, KeyError, ValueError, TypeError) as e:
			self.logger.error(f"there was an error loading/upgrading your filters: {e}. Please check the filters configuration to correct.")
			self.logger.debug(f"Filter list data: {preferencesFilterList}")
			# keep the stored filters untouched (persistConfig skips them) until
			# the filters are edited explicitly
			self.filtersUnreadable = True
			self.FilterList = []
			self.RebuildFilterIndex()
			return

		self.FilterList = filters
		if preferencesFilterVersion != FILTER_PREFS_VERSION and filters:
			# 1.0.0 -> 2.0.0 (and pre-release 3.0.0 -> 2.0.0): every filter is kept
			self.logger.info(f"upgraded {len(filters)} data filters from format {preferencesFilterVersion} to {FILTER_PREFS_VERSION}")
			self.SaveFiltersToPreferences()
		self.RebuildFilterIndex()

	def prepareFilterLog(self):
		"""filter.log lives in Indigo's own log folder for this plugin.  Releases
		before 2026.11.0 hard-coded a path under ~/Library/.../Indigo 2025.1, so
		an existing file there is moved over once."""
		try:
			log_dir = indigo.server.getLogsFolderPath(self.pluginId)
		except Exception:
			log_dir = os.path.join(indigo.server.getInstallFolderPath(), "Logs", self.pluginId)

		try:
			os.makedirs(log_dir, exist_ok=True)
		except OSError as e:
			self.logger.error(f"could not create the filter log folder {log_dir}: {e}")

		path = os.path.join(log_dir, "filter.log")

		legacy_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'Perceptive Automation',
								  'Indigo 2025.1', 'Logs', self.pluginId)
		legacy = os.path.join(legacy_dir, 'filter.log')
		if os.path.abspath(legacy) != os.path.abspath(path) and os.path.isfile(legacy):
			try:
				if not os.path.exists(path):
					shutil.move(legacy, path)
					self.logger.info(f"moved filter.log from {legacy_dir} to {log_dir}")
					try:
						os.rmdir(legacy_dir)  # only succeeds when empty
					except OSError:
						pass
				else:
					self.logger.debug(f"an older filter.log remains at {legacy}")
			except OSError as e:
				self.logger.warning(f"could not move the old filter.log from {legacy}: {e}")

		return path

	def savePrefs(self):
		try:
			indigo.server.savePluginPrefs()
		except Exception as e:
			self.logger.debug(f"savePluginPrefs failed: {e}")

	# called after runConcurrentThread() exits
	def shutdown(self):
		self.writer_stop.set()
		if self.writer_thread is not None:
			self.writer_thread.join(timeout=10)
		if self.connection:
			self.connection.close()
		self.connected = False

	def logRateLimited(self, key, level, message, interval=60 * 15):
		"""Log a recurring error at most once per interval (seconds)."""
		now = time.monotonic()
		last = self.lastErrorLog.get(key)
		if last is None or now - last >= interval:
			self.lastErrorLog[key] = now
			self.logger.log(level, message)
		else:
			self.logger.debug(message)

################### InfluxDB connection #########################################################

	def connectionSettings(self):
		"""The current connection settings, validated.  Raises ValueError."""
		settings, errors = validate_connection_settings({
			'InfluxHost': self.InfluxHost, 'InfluxHTTPPort': self.InfluxHTTPPort, 'InfluxSSL': self.InfluxSSL,
			'InfluxVersion': self.InfluxVersion, 'InfluxDB': self.InfluxDB, 'InfluxUser': self.InfluxUser,
			'InfluxPassword': self.InfluxPassword,
		})
		if errors:
			raise ValueError("; ".join(f"{field}: {message}" for field, message in errors.items()))
		return settings

	def newClient(self, settings):
		return InfluxClient(settings['host'], settings['port'], ssl=settings['ssl'], username=settings['username'],
							password=settings['password'], database=settings['database'],
							user_agent=f"Indigo-{self.pluginId}/{self.pluginVersion}")

	def connect(self, force=False):
		"""Connect unless already connected.  force reconnects anyway - a settings
		change must not be lost to a connect() with the old settings that was
		already in flight."""
		with self.connectionLock:
			if self.connected and not force:
				return
			self._connect()

	def _connect(self):
		self.logger.debug("running connect()")

		if self.StopConnectionAttempts:
			self.logger.debug("   halting connect(); StopConnectionAttempts = true")
			return

		if not self.configured:
			self.logger.debug("   halting connect(); configured = false")
			return

		try:
			settings = self.connectionSettings()
		except ValueError as e:
			self.connected = False
			self.connectionState = 'invalid_config'
			self.lastConnectError = str(e)
			if not self.QuietConnectionError:
				self.logger.error(f"the InfluxDB connection settings are not valid ({e}). Correct them in the plugin config.")
				self.QuietConnectionError = True
			return

		if not self.QuietConnectionError or self.debug:
			self.logger.info(f"connecting to InfluxDB... {settings['host']}:{settings['port']} (InfluxDB {settings['version']}) using user account: {settings['username']}")

		self.connectionState = 'connecting'
		client = self.newClient(settings)
		v3 = settings['version'] == '3'

		try:
			# InfluxDB 1.x answers /ping without checking credentials; InfluxDB 3
			# checks the token.  The empty write below settles credentials and
			# write permission on both without writing a point.
			info = client.ping()
			newDatabase = False
			if not v3:
				newDatabase = self.createDatabase(client)
			client.check_write_access()
			if not v3:
				self.ensureRetentionPolicy(client, newDatabase)

		except InfluxHTTPError as e:
			client.close()
			if e.is_auth_error:
				self.onAuthFailure(e)
			else:
				self.onConnectFailure(e)
			return
		except InfluxError as e:
			client.close()
			self.onConnectFailure(e)
			return
		except Exception as e:
			client.close()
			self.logger.exception(e)
			self.onConnectFailure(e)
			return

		self.warnOnVersionMismatch(info, v3)

		previous = self.connection
		self.connection = client
		self.serverInfo = info
		self.ConnectionRetryCount = 0
		self.QuietConnectionError = False
		self.StopConnectionAttempts = False  # these credentials work
		self.pollingInterval = DEFAULT_POLLING_INTERVAL
		self.lastConnectError = None
		self.connectionState = 'connected'
		self.everConnected = True
		self.connected = True

		server = f" ({info.get('build') or 'InfluxDB'} {info.get('version')})" if info.get('version') else ""
		self.logger.info(f"######## connected to InfluxDB successfully{server}... plugin will now resume logging data to InfluxDB ########")

		if previous is not None and previous is not client:
			previous.close()

		self.logger.debug("completed connect()")

	def onAuthFailure(self, error):
		"""Credentials refused (401) or not allowed to write (403): stop until the
		settings change - retrying a revoked token only fills the server's log."""
		self.connected = False
		self.connectionState = 'stopped_auth_failure'
		self.lastConnectError = str(error)
		self.StopConnectionAttempts = True
		self.QuietConnectionError = True
		self.logger.error(f"InfluxDB refused the plugin's credentials ({error}). Logging to InfluxDB is paused until the user name / password (token) is corrected in the plugin config.")

	def onConnectFailure(self, error):
		self.ConnectionRetryCount = self.ConnectionRetryCount + 1
		self.connected = False
		self.connectionState = 'retrying'
		self.lastConnectError = str(error)

		self.logger.debug(f"   connection attempt {self.ConnectionRetryCount}: error while connecting to InfluxDB: {error}")

		if not self.QuietConnectionError:
			self.logger.error(f"error while connecting to InfluxDB ({error}), will continue to try silently in the background.")
			self.QuietConnectionError = True
		elif self.ConnectionRetryCount > MAX_CONNECTION_RETRIES:
			self.pollingInterval = LONG_POLLING_INTERVAL
			self.logger.error(f"error while connecting to InfluxDB after {self.ConnectionRetryCount} attempts, will now attempt silently every 15 minutes.  Most recent connection error: {error}")

	def warnOnVersionMismatch(self, info, v3):
		version = str(info.get('version') or '')
		if not version:
			return
		if v3 and version.startswith('1.'):
			self.logger.warning(f"the server reports InfluxDB {version}, but the plugin is set to InfluxDB 3. Select 'InfluxDB 1.7 / 1.8' in the plugin config.")
		elif not v3 and version.startswith('3'):
			self.logger.warning(f"the server reports InfluxDB {version}, but the plugin is set to InfluxDB 1.7 / 1.8. Select 'InfluxDB 3' in the plugin config, or InfluxDB 3 will reject points that use a name as both a tag and a field.")

	def createDatabase(self, client):
		"""InfluxDB 1.x: create the database when the user is allowed to.  A user
		without admin rights can still log to a database created for it, so a
		refusal is not an error; a missing database surfaces on the write check.
		Returns True only when this call created the database."""
		try:
			existing = set(client.databases())
		except InfluxError as e:
			if getattr(e, 'status_code', None) == 401:
				raise
			existing = None  # unknown: never treat the database as new
		try:
			client.create_database(self.InfluxDB)
		except InfluxHTTPError as e:
			if e.status_code != 403:
				raise
			self.logger.debug(f"   the InfluxDB user may not create databases ({e}); assuming '{self.InfluxDB}' exists")
			return False
		except InfluxQueryError as e:
			self.logger.debug(f"   CREATE DATABASE failed: {e}")
			return False
		created = existing is not None and self.InfluxDB not in existing
		if created:
			self.logger.info(f"created InfluxDB database '{self.InfluxDB}'")
		return created

	def ensureRetentionPolicy(self, client, newDatabase=False):
		"""InfluxDB 1.x retention, applied through the 'indigo_policy' retention
		policy.  Best effort: a failure here never stops logging.

		Before 2026.11.0 the policy was created without DEFAULT, so every install
		wrote to 'autogen' (kept forever) and the setting never applied.  Decision
		2026-10-14: only a database the plugin has just created gets it as the
		default.  Any database that already existed - an older install with a
		non-default 'indigo_policy', or a database other tools share - keeps its
		default policy, and the user is told how to opt in: switching the default
		would hide all history from Grafana panels that don't name a retention
		policy, and would put other writers' data on this plugin's schedule."""
		try:
			duration, seconds = retention_spec(self.InfluxRetention)
		except ValueError as e:
			self.logger.warning(f"invalid retention setting {self.InfluxRetention!r} ({e}); retention is not managed")
			return

		try:
			policies = {policy.get('name'): policy for policy in client.retention_policies(self.InfluxDB)}
			current = policies.get(RETENTION_POLICY_NAME)

			if current is None and newDatabase:
				client.create_retention_policy(RETENTION_POLICY_NAME, self.InfluxDB, duration, default=True)
				self.logger.info(f"created InfluxDB retention policy '{RETENTION_POLICY_NAME}' ({describe_retention(self.InfluxRetention)}) as the default for database '{self.InfluxDB}'")

			elif current is None:
				if not self.retentionNoticeLogged:
					self.retentionNoticeLogged = True
					self.logger.warning(
						f"InfluxDB retention is not applied to database '{self.InfluxDB}': it existed before the plugin "
						f"connected, so the plugin leaves its default retention policy alone. To apply the retention "
						f"setting to this plugin's data from now on, run in the influx CLI:  CREATE RETENTION POLICY "
						f"\"{RETENTION_POLICY_NAME}\" ON \"{self.InfluxDB}\" DURATION {duration} REPLICATION 1 DEFAULT  - "
						f"note that every writer that doesn't name a retention policy then uses it.")

			elif not current.get('default'):
				if not self.retentionNoticeLogged:
					self.retentionNoticeLogged = True
					self.logger.warning(
						f"InfluxDB retention is not applied to database '{self.InfluxDB}': its data is stored in the "
						f"'autogen' retention policy (kept forever), because plugin versions before 2026.11.0 never made "
						f"'{RETENTION_POLICY_NAME}' the default. Existing data is left where it is. To apply the "
						f"retention setting from now on, run in the influx CLI:  ALTER RETENTION POLICY "
						f"\"{RETENTION_POLICY_NAME}\" ON \"{self.InfluxDB}\" DURATION {duration} DEFAULT  - new data "
						f"then goes to {RETENTION_POLICY_NAME}, and older data stays readable as \"autogen\".\"device_changes\".")

			elif parse_duration_seconds(current.get('duration', '')) != seconds:
				client.alter_retention_policy(RETENTION_POLICY_NAME, self.InfluxDB, duration, default=True)
				self.logger.info(f"changed InfluxDB retention policy '{RETENTION_POLICY_NAME}' to {describe_retention(self.InfluxRetention)}")

		except InfluxHTTPError as e:
			if e.status_code == 401:
				raise
			if not self.retentionNoticeLogged:
				self.retentionNoticeLogged = True
				self.logger.warning(f"could not manage the InfluxDB retention policy ({e}); the InfluxDB user needs admin rights for that. Logging continues.")
		except InfluxQueryError as e:
			if not self.retentionNoticeLogged:
				self.retentionNoticeLogged = True
				self.logger.warning(f"could not manage the InfluxDB retention policy ({e}). Logging continues.")

	def requestReconnect(self, reason="", resetErrors=True):
		"""Reconnect on a worker thread: connect() makes network calls (up to
		~15 s against an unreachable host) and must never run on Indigo's
		callback thread.  Writes pause until it completes.  resetErrors clears
		the auth-failure stop and re-arms the one-time connection error message
		(a settings change); a lost connection keeps them."""
		if reason:
			self.logger.info(reason)
		if resetErrors:
			self.StopConnectionAttempts = False
			self.QuietConnectionError = False
			self.ConnectionRetryCount = 0
			self.pollingInterval = DEFAULT_POLLING_INTERVAL
		self.connected = False
		self.connectionState = 'connecting'
		threading.Thread(target=self.connect, kwargs={'force': True}, name="InfluxConnect", daemon=True).start()

	def markDisconnected(self, client, error):
		"""A write failed for a transient reason.  Queued points are kept."""
		if client is not self.connection or not self.connected:
			return  # a reconnect already replaced this client
		self.connected = False
		self.connectionState = 'retrying'
		self.lastConnectError = str(error)
		if not self.QuietConnectionError:
			self.QuietConnectionError = True
			self.logger.error(f"error while writing to InfluxDB ({error}); queued points are kept and will be written once the connection is restored.")
		self.requestReconnect(resetErrors=False)

	def applyRetentionInBackground(self):
		"""Re-apply the InfluxDB 1.x retention policy after the setting changed,
		on a worker thread (network) and without reconnecting."""
		def work():
			with self.connectionLock:
				client = self.connection
				if client is None or not self.connected or self.InfluxVersion != '1':
					return
				self.retentionNoticeLogged = False
				try:
					self.ensureRetentionPolicy(client)
				except InfluxError as e:
					self.logger.warning(f"could not apply the retention setting: {e}")

		threading.Thread(target=work, name="InfluxRetention", daemon=True).start()

	def testConnection(self, settings):
		"""Try proposed connection settings (influx_settings.validate_connection_settings
		output) without touching the live connection: ping, then an empty write
		that proves the credentials may write.  On InfluxDB 1.x a missing database
		is not a failure - connect() creates it when the user may.  Returns
		{'passed', 'server_version', 'server_build', 'status_code', 'error', 'warnings'}."""
		result = {'passed': False, 'server_version': None, 'server_build': None, 'status_code': None,
				  'error': None, 'warnings': []}
		client = self.newClient(settings)
		try:
			info = client.ping()
			result['server_version'] = info.get('version')
			result['server_build'] = info.get('build')
			try:
				client.check_write_access()
			except InfluxHTTPError as e:
				if settings['version'] == '1' and e.status_code == 404:
					result['warnings'].append(f"database '{settings['database']}' does not exist yet; the plugin creates it when it connects if the user has admin rights")
				else:
					raise
			version = str(result['server_version'] or '')
			if settings['version'] == '3' and version.startswith('1.'):
				result['warnings'].append(f"the server reports InfluxDB {version}, not InfluxDB 3")
			elif settings['version'] == '1' and version.startswith('3'):
				result['warnings'].append(f"the server reports InfluxDB {version}; select version 3")
			result['passed'] = True
		except InfluxError as e:
			result['status_code'] = e.status_code
			result['error'] = str(e)
		except Exception as e:
			result['error'] = f"{type(e).__name__}: {e}"
		finally:
			client.close()
		return result

	def acceptingPoints(self):
		"""Producers enqueue while connected, and keep enqueueing through an
		outage once a connection has been made (the bounded queue is the
		buffer).  Not while credentials are refused: that needs the user."""
		return (self.adaptor is not None and self.configured and not self.StopConnectionAttempts
				and (self.connected or self.everConnected))

################### Write pipeline ##############################################################

	# send this a dict of what to write; enqueues for the writer thread so
	# Indigo callbacks never block on the network
	def SendToInflux(self, tags, what, measurement='device_changes'):
		if not self.acceptingPoints():
			return

		if self.InfluxV3Compat:
			# IOx-based servers (InfluxDB 3) require a column to be a tag XOR
			# a field. Drop fields that duplicate a tag key (e.g. device
			# 'name') — InfluxDB 1.x silently accepted the overlap. A point
			# left with no fields carries nothing beyond its tags; skip it.
			what = {k: v for k, v in what.items() if k not in tags}
			if not what:
				return

		point = {
			'measurement': measurement,
			'tags': tags,
			'fields': what,
			# stamp client-side: batched points that shared a server-assigned
			# timestamp would overwrite each other within a series
			'time': datetime.datetime.now(datetime.timezone.utc)
		}

		try:
			self.write_queue.put_nowait(point)
		except queue.Full:
			self.stats.drop('queue_full')
			now = datetime.datetime.now()
			if self.lastQueueFullWarning is None or now - self.lastQueueFullWarning > datetime.timedelta(seconds=QUEUE_FULL_WARNING_INTERVAL):
				self.lastQueueFullWarning = now
				self.logger.warning(f"InfluxDB write queue is full ({INFLUX_QUEUE_MAX} points); dropping new points until it drains")

	def collectBatch(self):
		try:
			batch = [self.write_queue.get(timeout=0.5)]
		except queue.Empty:
			return []

		# coalesce whatever else arrives within the flush window into one
		# write_points() call — InfluxDB 3 holds every write for its WAL
		# flush (~1s), so per-point writes cap throughput at ~1 point/sec
		deadline = time.monotonic() + INFLUX_FLUSH_INTERVAL
		while len(batch) < INFLUX_BATCH_MAX and not self.writer_stop.is_set():
			remaining = deadline - time.monotonic()
			if remaining <= 0:
				break
			try:
				batch.append(self.write_queue.get(timeout=remaining))
			except queue.Empty:
				break
		return batch

	def influxWriterLoop(self):
		self.logger.debug("InfluxDB writer thread started")

		pending = None  # a batch kept after a transient failure; written first
		attempts = 0

		while not self.writer_stop.is_set():
			try:
				client = self.connection
				if not self.connected or client is None:
					# paused: queued points wait for the connection to return
					self.writer_stop.wait(WRITER_PAUSE_INTERVAL)
					continue

				batch = pending if pending is not None else self.collectBatch()
				pending = None
				if not batch:
					continue

				if self.writeBatch(client, batch) == WRITE_OK:
					attempts = 0
					continue

				attempts += 1
				if attempts >= MAX_BATCH_ATTEMPTS:
					self.stats.drop('gave_up', len(batch))
					self.logger.warning(f"gave up on a batch of {len(batch)} InfluxDB points after {attempts} failed attempts")
					attempts = 0
				else:
					pending = batch

			except Exception as e:
				# the writer must never die silently: log and keep going
				self.logRateLimited('writer', logging.ERROR, f"error in the InfluxDB writer thread: {e}")
				self.writer_stop.wait(WRITER_PAUSE_INTERVAL)

		self.drainOnShutdown(pending or [])
		self.logger.debug("InfluxDB writer thread stopped")

	def drainOnShutdown(self, points):
		# final drain so points captured just before shutdown still land
		while True:
			try:
				points.append(self.write_queue.get_nowait())
			except queue.Empty:
				break
		if not points:
			return

		client = self.connection
		if not self.connected or client is None:
			self.stats.drop('shutdown', len(points))
			self.logger.info(f"{len(points)} queued points were not written: InfluxDB was unreachable at shutdown")
			return

		for start in range(0, len(points), INFLUX_BATCH_MAX):
			chunk = points[start:start + INFLUX_BATCH_MAX]
			if self.writeBatch(client, chunk) != WRITE_OK:
				lost = len(points) - start
				self.stats.drop('shutdown', lost)
				self.logger.info(f"{lost} queued points were not written at shutdown")
				return

	def writeBatch(self, client, batch):
		"""Write one batch.  Returns WRITE_OK (written, or rejected data dropped),
		WRITE_RETRY (transient: keep the batch) or WRITE_HALT (credentials
		refused: keep the batch).

		Errors are told apart by HTTP status: 401/403 mean the credentials no
		longer work, 404 a missing database, 5xx and network errors a server
		problem - all of them configuration or connection failures, where
		re-sending the batch point by point would only multiply the requests.
		Only a 400 is about the data, and only then is the batch narrowed down."""
		points = list(batch)
		corrections = 0

		while points:
			try:
				client.write_points(points)
				self.stats.written(len(points))
				self.QuietConnectionError = False
				return WRITE_OK

			except InfluxConnectionError as e:
				self.stats.error(e)
				self.markDisconnected(client, e)
				return WRITE_RETRY

			except InfluxHTTPError as e:
				self.stats.error(e)
				status = e.status_code

				if status in (401, 403):
					# only the live connection's refusal counts: a 401 from a client a
					# reconnect is replacing must not block the new credentials
					if client is self.connection and self.connected:
						self.onAuthFailure(e)
					return WRITE_HALT

				if status == 404 or status >= 500:
					self.markDisconnected(client, e)
					return WRITE_RETRY

				if status != 400:
					self.stats.drop('rejected', len(points))
					self.logRateLimited('write-' + str(status), logging.WARNING, f"InfluxDB rejected a batch of {len(points)} points ({e}); the batch was dropped")
					return WRITE_OK

				# 400: InfluxDB 1.x stores the valid points of a batch and says
				# "partial write"; InfluxDB 3 rejects the whole batch and names the
				# first bad line
				partial = 'partial write' in e.message
				corrected = []
				if corrections < MAX_INFLUX_WRITE_RETRIES:
					corrected = self.applyTypeCorrection(e, points)

				if corrected:
					corrections += 1
					if partial:
						# only the points with the conflicting field were dropped
						points = corrected
					# a point whose only field could not be converted has nothing left
					empty = [point for point in points if not point.get('fields')]
					if empty:
						for point in empty:
							self.dropPoint(point, e)
						points = [point for point in points if point.get('fields')]
					continue

				if partial:
					match = re.search(r'dropped=(\d+)', e.message)
					self.stats.drop('rejected', int(match.group(1)) if match else 1)
					self.logger.debug("InfluxDB dropped part of a batch: " + e.message[:300])
					return WRITE_OK

				if e.point_index is not None and 0 <= e.point_index < len(points):
					bad = points.pop(e.point_index)
					self.dropPoint(bad, e)
					continue

				if len(points) == 1:
					self.dropPoint(points[0], e)
					return WRITE_OK

				# no line number to go on: narrow it down one point at a time
				for point in points:
					outcome = self.writeBatch(client, [point])
					if outcome != WRITE_OK:
						return outcome
				return WRITE_OK

		return WRITE_OK

	def dropPoint(self, point, error):
		self.stats.drop('rejected')
		self.logger.debug("dropping InfluxDB point that could not be written (" + error.message[:200] + "): "
						  + str(point.get('measurement')) + " " + str(point.get('tags', {}).get('name', ''))
						  + " fields=" + str(sorted(point.get('fields', {}).keys())))

	# parse a type-conflict error (InfluxDB 1.x or 3 v1-compat formats), teach
	# the adaptor's typecache, and coerce the offending field across the batch.
	# A value that can't be converted (e.g. '' for a float column) is removed
	# from its point instead, so the point's other fields are still written.
	# Returns the points that changed (empty when none did).
	def applyTypeCorrection(self, error, batch):
		field = None
		target = None
		error_text = error.message

		# InfluxDB 3 (IOx): "invalid column type for column 'x', expected
		# iox::column_type::field::string, got iox::column_type::field::boolean"
		match = re.search(r"column '([^']+)'.*?expected iox::column_type::field::(\w+)", error_text)
		if match:
			field = match.group(1)
			target = IOX_TYPE_MAP.get(match.group(2))
		else:
			# InfluxDB 1.x: 'input field "x" on measurement "m" is type
			# integer, already exists as type float'.  Matched against the
			# decoded message: before 2026.11.0 it ran on the raw JSON body,
			# where the quotes are escaped, and never matched.
			match = re.search(r'input field "([^"]+)" on measurement "[^"]*" is type \w+, already exists as type (\w+)', error_text)
			if match:
				field = match.group(1)
				target = match.group(2)

		if not field or not target:
			self.logger.debug("Could not parse InfluxDB error response: " + error_text[:300])
			return []

		converter = TYPE_CONVERTERS.get(target)
		if converter is None:
			self.logger.debug(f"Unknown type converter requested: {target}")
			return []

		# Store the type for future reference so to_json() coerces up-front
		if self.adaptor is not None:
			self.adaptor.typecache[field] = target

		changed = []
		for point in batch:
			fields = point.get('fields', {})
			if field not in fields:
				continue
			value = fields[field]
			try:
				converted = converter(str(value))
			except (ValueError, TypeError) as conv_err:
				del fields[field]
				changed.append(point)
				self.logger.debug(f"leaving {field} out of a point for {point.get('tags', {})}: {value!r} is not a {target}, "
								  f"the type of its InfluxDB column ({conv_err})")
				continue
			if type(converted) is not type(value) or converted != value:
				fields[field] = converted
				changed.append(point)

		return changed

################### Main loop and device processing #############################################

	def runConcurrentThread(self):
		self.logger.debug("fully initiatlized and ready.  starting concurrent tread...")

		try:
			while True:
				try:
					if not self.connected:
						self.connect()

					if self.connected:
						self.UpdateAll()

					if self.LastConfigRefresh + datetime.timedelta(minutes=UPDATE_STATES_LIST) < datetime.datetime.now():
						self.logger.debug("    triggering a refresh of the configuration lists")
						self.BuildConfigurationLists()

					# prune the logs
					if self.lastLogPrune and self.lastLogPrune < datetime.datetime.now()-datetime.timedelta(hours=LOG_PRUNE_FREQUENCY):
						self.pruneFilterBlocksEventLog()

				except self.StopThread:
					raise
				except Exception as e:
					self.logRateLimited('thread', logging.ERROR, f"error in the plugin's background thread: {e}")

				self.sleep(int(self.pollingInterval))

		except self.StopThread:
			self.logger.debug("Received StopThread")
			# leave the connection open: the writer thread does a final drain;
			# shutdown() joins it and then closes the connection
			self.writer_stop.set()

	def heartbeatDue(self, lastUpdate, now):
		"""Is a minimum-frequency heartbeat due for something last sent at lastUpdate?"""
		frequency = self.minimumUpdateFrequency
		if frequency == "smart":
			# legacy option: heartbeats only around midnight
			inWindow = (now.hour == 0 and now.minute < 15) or (now.hour == 23 and now.minute > 45)
			return inWindow and lastUpdate + datetime.timedelta(minutes=5) < now
		if not isinstance(frequency, int) or frequency <= 0:
			return False  # -1 = Disabled: no heartbeats at all
		return lastUpdate + datetime.timedelta(minutes=frequency) < now

	def UpdateAll(self):

		if not self.connected or self.adaptor is None:
			return

		if self.TransportDebugL2:
			self.logger.debug("running UpdateAll()")

		now = datetime.datetime.now()
		excluded = set(self.DeviceExcludeList)

		for dev in indigo.devices:
			if self.TransportDebugL2:
				self.logger.debug("    reviewing " + dev.name)

			# if the device is excluded, do nothing
			if dev.id in excluded:
				continue

			lastUpdate = self.deviceLastUpdated.get(dev.id)
			if lastUpdate is None:
				self.deviceLastUpdated[dev.id] = dev.lastChanged
				continue

			# a locked device sends nothing until it reports a change; the lock
			# and its release are logged when they happen (LockDeviceUpdates,
			# deviceUpdated), not on every poll
			if dev.id in self.deviceLocks:
				continue

			if self.heartbeatDue(lastUpdate, now):
				if self.TransportDebug:
					self.logger.debug("    minimum update period for device expired: " + dev.name + ", prior update timestamp: " + str(lastUpdate))
				self.deviceLastUpdated[dev.id] = now
				self.DeviceToInflux(None, dev, False)

		for var in indigo.variables:
			lastUpdate = self.variableLastUpdated.get(var.id)
			if lastUpdate is None:
				self.variableLastUpdated[var.id] = now
				continue

			if self.heartbeatDue(lastUpdate, now):
				if self.TransportDebug:
					self.logger.debug("    minimum update period for variable expired: " + var.name + ", prior update timestamp: " + str(lastUpdate))
				self.variableLastUpdated[var.id] = now
				self.VariableToInflux(var)

		if self.TransportDebugL2:
			self.logger.debug("completed UpdateAll()")

	def deviceUpdated(self, origDev, newDev):
		# call base implementation
		indigo.PluginBase.deviceUpdated(self, origDev, newDev)

		if not self.acceptingPoints():
			return

		# If the device is excluded, do nothing
		if newDev.id in self.DeviceExcludeList:
			if self.TransportDebugL2:
				self.logger.debug("   device was excluded from InfluxDB update: " + newDev.name)
			return

		device_was_updated, device_was_locked = self.DeviceToInflux(origDev, newDev, True)

		if not device_was_updated:
			if self.JSONDebug:
				self.logger.debug("   an update for device " + origDev.name + " resulted in no properties updated...")
			return

		if self.TransportDebug:
			self.logger.debug("deviceUpdated(): an update for device " + origDev.name + " is being processed...")

		self.deviceLastUpdated[newDev.id] = datetime.datetime.now()

		# unlock if locked since we rec'd an update, unless a filter locked the
		# device while processing this very update
		if newDev.id in self.deviceLocks and not device_was_locked:
			lock = self.deviceLocks.pop(newDev.id, None)
			if lock:
				self.logger.info(f"device {newDev.name} reported a change and is no longer locked (locked since {lock['since']:%Y-%m-%d %H:%M} by filter '{lock['filter']}')")

	def deviceDeleted(self, dev):
		indigo.PluginBase.deviceDeleted(self, dev)
		self.deviceLastUpdated.pop(dev.id, None)
		self.deviceLocks.pop(dev.id, None)
		self.DeviceLastWrittenValues.pop(dev.id, None)
		if self.adaptor is not None:
			self.adaptor.forget(dev.id)

	def RebuildFilterIndex(self):
		"""Index the states watched by at least one percentChanged filter.  Keeps
		the last-written baseline map small, and drops stale baselines whenever the
		filters change."""
		states = set()

		for influxFilterRecord in self.FilterList:
			if influxFilterRecord.filterStrategy == "percentChanged":
				states.add(influxFilterRecord.state)

		self.PercentChangedStates = states
		self.DeviceLastWrittenValues = {}

	def PreviousFilterValue(self, origDev, dev, key):
		"""Baseline for a percentChanged comparison.  Prefers the pre-change state
		Indigo handed us (deviceUpdated path), falling back to the last value this
		plugin actually wrote (UpdateAll path, which has no origDev).  Returns None
		when no baseline is known, meaning the value should be let through."""
		if origDev is not None:
			# 'key' is the adaptor's flattened key space ('state.onOffState',
			# 'batteryLevel.num', ...).  Only the un-prefixed, un-suffixed form maps
			# onto Indigo's own state namespace.
			stateKey = key[6:] if key.startswith("state.") else key
			if stateKey.endswith(".num"):
				stateKey = stateKey[:-4]

			if stateKey in origDev.states:
				return origDev.states[stateKey]

		return self.DeviceLastWrittenValues.get(dev.id, {}).get(key)

	def LockDeviceUpdates(self, dev, state, filterName=""):
		"""Lock a device out of the minimum-frequency heartbeat until Indigo reports
		a change for it.  Locking is per-device, not per-state: a device emitting
		garbage on one state is a sick device (see MenuItems.xml)."""
		if dev.id not in self.deviceLocks:
			self.deviceLocks[dev.id] = {'since': datetime.datetime.now(), 'filter': filterName, 'state': str(state)}
			# logged at info, NOT behind TransportDebug: a locked device sends
			# nothing at all for any of its states, which is indistinguishable
			# from a healthy quiet device unless something says so out loud.
			self.logger.info(f"device {dev.name} is locked from being updated as it failed the filter '{filterName}' (state/property '{state}'); no data is being recorded for it until it reports a change.")

		self.deviceLastUpdated.setdefault(dev.id, datetime.datetime.now())

	def evaluateFilter(self, influxFilterRecord, origDev, dev, key, value):
		"""(passed, previousValue, percentChange) for one filter and one value."""
		if influxFilterRecord.filterStrategy == "percentChanged":
			if self.TransportDebug:
				self.logger.debug(dev.name + "[" + key + "]: looking at filter (" + influxFilterRecord.name + "): " + influxFilterRecord.state + " for " + influxFilterRecord.appliesToString + " with a maximum percent change of " + str(influxFilterRecord.maxPercent))

			origValue = self.PreviousFilterValue(origDev, dev, key)
			percentValueChanged = percent_changed(origValue, value)

			if percentValueChanged is None:
				if self.TransportDebug:
					self.logger.debug("    no usable previous value for state/property '" + str(key) + "' on device '" + dev.name + "', unable to calculate percentage changed. Value will be sent on to InfluxDB.")
				return True, origValue, None

			if abs(percentValueChanged) > influxFilterRecord.maxPercent:
				return False, origValue, percentValueChanged

			if self.TransportDebug:
				self.logger.debug("    Filter passed (" + influxFilterRecord.name + "): a value (old value: " + str(origValue) + ", new value: " + str(value) + ") for state/property '" + str(key) + "' on device '" + dev.name + "' DID NOT exceeded percent changed (actual change: " + str(abs(percentValueChanged)) + ", threshhold: " + str(influxFilterRecord.maxPercent) + ") and will be sent to InfluxDB")
			return True, origValue, percentValueChanged

		if self.TransportDebug:
			self.logger.debug(dev.name + "[" + key + "]: looking at filter (" + influxFilterRecord.name + "): " + influxFilterRecord.state + " for " + influxFilterRecord.appliesToString + " with a range (" + str(influxFilterRecord.minValue) + ", " + str(influxFilterRecord.maxValue) + ")")

		number = numeric_value(value)
		if number is None:
			# min/max filters only judge numbers; anything else passes
			return True, None, None

		return influxFilterRecord.minValue <= number <= influxFilterRecord.maxValue, None, None

	def DeviceToInflux(self, origDev, dev, updateCheck = True):
		"""Returns (somethingWasSent, deviceWasLocked).  The second element lets
		deviceUpdated() tell 'this device was already locked' apart from 'a filter
		locked it while processing this very update' - without it, the unlock
		below would immediately undo the lock this call just took."""
		# custom add to influx work
		# tag by folder if present
		tagnames = 'name folderId'.split()
		deviceLocked = False

		# if the device is excluded, do nothing
		if dev.id in self.DeviceExcludeList:
			if self.TransportDebug:
				self.logger.debug("device was excluded from InfluxDB update: " + dev.name)
			return False, deviceLocked

		if dev.id in self.DeviceIncludeList:
			if self.TransportDebug:
				self.logger.debug("sending entire device to diff_to_json: " + dev.name)
			newjson = self.adaptor.diff_to_json(dev, None, updateCheck)
		else:
			newjson = self.adaptor.diff_to_json(dev, self.StatesIncludeList, updateCheck)

		if newjson is None:
			return False, deviceLocked

		# Advanced data filtering processing section.  A snapshot: filter edits
		# replace the list rather than mutate it, so this iteration is stable.
		filters = self.FilterList
		if len(filters) > 0:
			keys_to_delete = []  # Track keys to delete instead of using expensive deepcopy
			for kk, vv in newjson.items():
				for influxFilterRecord in filters:
					if kk != influxFilterRecord.state or not influxFilterRecord.appliesTo(dev.id):
						continue

					try:
						passedFilter, origValue, percentValueChanged = self.evaluateFilter(influxFilterRecord, origDev, dev, kk, vv)
					except Exception as e:
						passedFilter = True
						self.logRateLimited('filter-' + influxFilterRecord.name, logging.ERROR, f"there was a error while trying to process the filter '{influxFilterRecord.name}' for device '{dev.name}' (key {kk}, value {vv!r}): {e}")
						continue

					if passedFilter:
						continue

					# if the lock minimum updates is true, we need to mark the device as locked
					if influxFilterRecord.filterStrategy == "percentChanged" and influxFilterRecord.lockMinimumUpdates:
						self.LockDeviceUpdates(dev, kk, influxFilterRecord.name)
						deviceLocked = True

					if influxFilterRecord.filterStrategy == "minMax":
						logLine = "Filter block (" + influxFilterRecord.name + "): a value (" + str(vv) + ") for state/property '" + str(kk) + "' on device '" + dev.name + "' was not in the configured range (" + str(influxFilterRecord.minValue) + ", " + str(influxFilterRecord.maxValue) + ") and will not be sent to InfluxDB"
					else:
						logLine = "Filter block (" + influxFilterRecord.name + "): a value (previous value: " + str(origValue) + ", new value: " + str(vv) + ") for state/property '" + str(kk) + "' on device '" + dev.name + "' exceeded percent changed (percent changed: " + str(abs(percentValueChanged)) + "%, threshhold: " + str(influxFilterRecord.maxPercent) + "%) and will not be sent to InfluxDB"

					# a lock silently stops ALL updates for the device, so make sure
					# it lands in the filter log rather than only behind TransportDebug
					if deviceLocked:
						logLine = logLine + ".  The device has also been locked out of minimum-frequency updates until it reports a change."

					self.writeFilterLog(logLine)

					if influxFilterRecord.log:
						self.logger.info(logLine)
					else:
						self.logger.debug(logLine)

					keys_to_delete.append(kk)
					break # stop processing filter rules.

			# Delete filtered keys after iteration to avoid dictionary size change during iteration
			for key in keys_to_delete:
				if key in newjson:
					del newjson[key]

		### END Advanced data filtering section

		# Remember what actually reached InfluxDB, so UpdateAll() - which has no
		# origDev - has a percentChanged baseline.  Recorded AFTER filtering, so a
		# blocked value never becomes the baseline that lets its successor through.
		if self.PercentChangedStates:
			lastWritten = self.DeviceLastWrittenValues.setdefault(dev.id, {})
			for stateKey in self.PercentChangedStates:
				if stateKey in newjson:
					numeric = numeric_value(newjson[stateKey])
					if numeric is not None:
						lastWritten[stateKey] = numeric

		newtags = {}
		for tag in tagnames:
			newtags[tag] = str(getattr(dev, tag))

		# add a folder name tag
		if hasattr(dev, 'folderId') and dev.folderId != 0:
			try:
				newtags['folder'] = indigo.devices.folders[dev.folderId].name
			except (KeyError, IndexError):
				pass

		measurement = newjson['measurement']
		del newjson['measurement']
		self.SendToInflux(tags=newtags, what=newjson, measurement=measurement)

		return True, deviceLocked

	def writeFilterLog(self, logLine):
		if not self.FilterLogFileLoc:
			return
		try:
			with open(self.FilterLogFileLoc, "a") as logFile:
				logFile.write(datetime.datetime.now().strftime('%Y-%m-%d %H:%M') + ": " + logLine + '\n')
		except Exception as e:
			self.logRateLimited('filter-log', logging.ERROR, "error writing to filter log.  Error: " + str(e))

	def variableUpdated(self, origVar, newVar):
		indigo.PluginBase.variableUpdated(self, origVar, newVar)

		if not self.acceptingPoints():
			return

		## Log the timestamp for the variable update.  Keyed by variable id to match
		## UpdateAll().
		self.variableLastUpdated[newVar.id] = datetime.datetime.now()

		self.VariableToInflux(newVar)

	def VariableToInflux(self, var):
		newtags = {'varname': var.name}
		newjson = {'name': var.name, 'value': var.value }
		numval = self.adaptor.smart_value(var.value, True)
		if numval != None:
			newjson['value.num'] = numval

		self.SendToInflux(tags=newtags, what=newjson, measurement='variable_changes')

################### PluginConfig functions. #####################################################

	def getPrefsConfigUiValues(self):
		# a copy: the base class hands out pluginPrefs itself
		valuesDict = indigo.Dict()
		for key, value in self.pluginPrefs.items():
			valuesDict[key] = value

		with self.configLock:
			self.dialog = self.store.dialogBase()
			self.dialogPassword = self.InfluxPassword

		self.refreshDeviceNames()

		# These two list fields hold the SELECTION the remove buttons act on, not
		# the lists themselves (those come from the generators).  Start with
		# nothing selected, so "remove selected" can't remove everything.
		valuesDict['listIncStates'] = indigo.List()
		valuesDict['listIncDevices'] = indigo.List()

		return (valuesDict, indigo.Dict())

	def validatePrefsConfigUi(self, valuesDict):
		settings, errors = validate_connection_settings(valuesDict)
		errors.update(validate_other_settings(valuesDict))

		if errors:
			errorsDict = indigo.Dict()
			for field, message in errors.items():
				errorsDict[field] = message
			errorsDict['showAlertText'] = "Please correct the highlighted settings:\n\n" + "\n".join("• " + message for message in errors.values())
			return (False, valuesDict, errorsDict)

		valuesDict['InfluxHost'] = settings['host']
		valuesDict['InfluxHTTPPort'] = str(settings['port'])
		valuesDict['InfluxDB'] = settings['database']
		return (True, valuesDict)

	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		with self.configLock:
			dialog, self.dialog = self.dialog, None
			basePassword, self.dialogPassword = self.dialogPassword, None

		if userCancelled:
			self.logger.debug("plugin config dialog cancelled; nothing changed")
			return

		self.logger.debug("started processing closedPrefsConfigUi")

		wasConfigured = self.configured
		before = self.store.current()['connection']
		beforePassword = self.InfluxPassword
		beforeRetention = self.InfluxRetention

		values = {
			'exclude': self.cleanDeviceList(valuesDict.get("listExclDevices", [])),
			'settings': {
				'minimum_update_frequency': frequency_label(parse_frequency(valuesDict.get("MinimumUpdateFrequency", 5))),
				'retention': str(valuesDict.get('InfluxRetention', self.InfluxRetention)),
				'debug': {
					'plugin': to_bool(valuesDict.get("ServerDebug", False)),
					'config': to_bool(valuesDict.get("ConfigDebug", False)),
					'transport': to_bool(valuesDict.get("TransportDebug", False)),
					'transport_l2': to_bool(valuesDict.get("TransportDebugL2", False)),
					'json': to_bool(valuesDict.get("JSONDebug", False)),
				},
			},
			'connection': {
				'host': valuesDict['InfluxHost'],
				'port': str(valuesDict['InfluxHTTPPort']),
				'ssl': to_bool(valuesDict['InfluxSSL']),
				'version': str(valuesDict.get('InfluxVersion', '1')),
				'database': valuesDict['InfluxDB'],
				'user': valuesDict['InfluxUser'],
			},
		}

		# changes relative to what the dialog opened with, merged onto the current
		# configuration (an AI edit made while the dialog was open survives)
		result = self.store.commitDialog(dialog, values)
		for warning in result['warnings']:
			self.logger.warning("plugin config: " + warning)

		# the password is never part of the store; merge it the same way by hand
		newPassword = valuesDict.get('InfluxPassword', '')
		if (basePassword is None or newPassword != basePassword) and newPassword != self.InfluxPassword:
			self.InfluxPassword = newPassword
			self.store.apply('config dialog', bumpCredentials, summary='InfluxDB password changed')

		self.configured = True
		# Indigo has just stored the dialog's whole valuesDict, stale copies of the
		# plugin-owned keys included: write the live configuration back over it
		self.persistConfig()

		ConnectionChanged = (
			self.store.current()['connection'] != before or
			self.InfluxPassword != beforePassword or
			# retention is applied while connecting (InfluxDB 1.x)
			(self.InfluxRetention != beforeRetention and self.InfluxVersion == '1') or
			not wasConfigured or
			self.StopConnectionAttempts)

		if ConnectionChanged:
			self.retentionNoticeLogged = False
			self.requestReconnect("InfluxDB connection settings changed, reconnecting...")

		self.logger.debug("completed processing closedPrefsConfigUi")

	def persistConfig(self):
		"""Write the live configuration to pluginPrefs.  Run after every change
		(ConfigStore.apply) and after the config dialog saves: Indigo stores the
		dialog's whole valuesDict, which still holds the values these keys had
		when the dialog opened."""
		with self.configLock:
			prefs = self.pluginPrefs
			prefs["listIncStates"] = list(self.StatesIncludeList)
			prefs["listIncDevices"] = list(self.DeviceIncludeList)
			prefs["listExclDevices"] = list(self.DeviceExcludeList)
			if not self.filtersUnreadable:
				prefs["listFilterList"] = [influxFilterRecord.toPrefs() for influxFilterRecord in self.FilterList]
				prefs["preferencesFilterVersion"] = FILTER_PREFS_VERSION
			prefs["MinimumUpdateFrequency"] = str(self.minimumUpdateFrequency)
			prefs["InfluxRetention"] = str(self.InfluxRetention)
			prefs["ServerDebug"] = bool(self.debug)
			prefs["ConfigDebug"] = bool(self.ConfigDebug)
			prefs["TransportDebug"] = bool(self.TransportDebug)
			prefs["TransportDebugL2"] = bool(self.TransportDebugL2)
			prefs["JSONDebug"] = bool(self.JSONDebug)
			prefs["configRevision"] = self.store.revision
			# connection settings only once configured: their presence is what
			# marks the plugin as configured on the next start
			if self.configured:
				prefs["InfluxHost"] = self.InfluxHost
				prefs["InfluxHTTPPort"] = str(self.InfluxHTTPPort)
				prefs["InfluxSSL"] = bool(self.InfluxSSL)
				prefs["InfluxVersion"] = str(self.InfluxVersion)
				prefs["InfluxDB"] = self.InfluxDB
				prefs["InfluxUser"] = self.InfluxUser
				prefs["InfluxPassword"] = self.InfluxPassword
		self.savePrefs()

	def ValidateConfigLists(self):
		"""Drop devices that no longer exist from the include/exclude lists and
		the filters.  Include STATES are kept even when no device has them right
		now: a state is often missing only while its devices are offline, and
		dropping it then (as releases before 2026.11.0 did) lost it for good."""
		self.logger.debug("running ValidateConfigLists()")

		with self.configLock:
			gone = {dev_id for dev_id in self.DeviceIncludeList + self.DeviceExcludeList if dev_id not in indigo.devices}
			for influxFilterRecord in self.FilterList:
				gone |= {dev_id for dev_id in influxFilterRecord.scopeDevices if dev_id not in indigo.devices}

			if self.ConfigDebug:
				absent = [state for state in self.StatesIncludeList if state not in self.stateCatalog]
				if absent:
					self.logger.debug("   included states no device has right now: " + ", ".join(absent))

			if gone:
				def prune(config):
					config['include'] = [dev_id for dev_id in config['include'] if dev_id not in gone]
					config['exclude'] = [dev_id for dev_id in config['exclude'] if dev_id not in gone]
					for f in config['filters']:
						f['devices'] = [dev_id for dev_id in f['devices'] if dev_id not in gone]

				self.store.apply('housekeeping', prune)
				self.logger.info("removed deleted devices from the plugin configuration: " + ", ".join(str(dev_id) for dev_id in sorted(gone)))

		self.logger.debug("completed ValidateConfigLists()")

	def refreshDeviceNames(self):
		names = {}
		for dev in indigo.devices:
			names[dev.id] = ui_name(dev.name)
		self.deviceNames = names
		return names

	def BuildConfigurationLists(self):
		self.logger.debug("starting BuildConfigurationLists()")

		self.LastConfigRefresh = datetime.datetime.now()

		if self.adaptor is None:
			return

		catalog = {}
		names = {}
		keysByDevice = {}
		for dev in indigo.devices:
			names[dev.id] = ui_name(dev.name)
			### STATES List
			keys = []
			for kk in self.adaptor.to_json(dev):
				if kk != 'measurement':
					catalog[kk] = catalog.get(kk, 0) + 1
					keys.append(kk)
			keysByDevice[dev.id] = frozenset(keys)

		with self.configLock:
			self.stateCatalog = catalog
			self.deviceNames = names
			self.deviceKeys = keysByDevice
			self.catalogBuilt = datetime.datetime.now()
			# This makes sure that all the devices states exist before we build the UI for the plugin config
			self.ValidateConfigLists()

		self.adaptor.prune_cache(names.keys())

		self.logger.debug("completed BuildConfigurationLists()")

	def dialogLists(self):
		"""(states, devices) the plugin config dialog shows: its working copy
		while open, else the live lists."""
		dialog = self.dialog
		if dialog is not None:
			return dialog['states'], dialog['devices']
		return self.StatesIncludeList, self.DeviceIncludeList

	def editableDialog(self):
		with self.configLock:
			if self.dialog is None:
				self.dialog = self.store.dialogBase()
			return self.dialog

	def deviceLabel(self, dev_id):
		label = self.deviceNames.get(dev_id)
		if label is None:
			try:
				label = ui_name(indigo.devices[dev_id].name)
			except (KeyError, ValueError):
				label = str(dev_id)
		return label

	def stateLabel(self, state):
		return f"{state} ({self.stateCatalog.get(state, 0)})"

	def IncludedStatesListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		states, _ = self.dialogLists()
		if self.ConfigDebug:
			self.logger.debug("IncludedStatesListGenerator(): " + str(states))
		return [(state, state) for state in states if state.strip()]

	def IncludedFiltersListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		FilterListUI = []
		for filterItem in self.FilterList:
			FilterListUI.append((len(FilterListUI), str(len(FilterListUI) + 1) + ": " + ui_name(filterItem.name)))

		# what the dialog shows: a delete checks the positions still hold these
		self.filterListShown = [filterItem.name for filterItem in self.FilterList]
		return FilterListUI

	def IncludedDeviceListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		_, devices = self.dialogLists()
		return [(dev_id, self.deviceLabel(dev_id)) for dev_id in devices]

	def ExcludedDeviceListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		_, devices = self.dialogLists()
		included = set(devices)
		return [(dev_id, label) for dev_id, label in self.deviceNames.items() if dev_id not in included]

######
	def AvailableStatesGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		states, _ = self.dialogLists()
		included = set(states)
		# always-sent states are hidden from the include picker (adding them there
		# would multiply write volume) but kept in AllStatesGenerator, which feeds
		# the filter property pickers
		return [(state, self.stateLabel(state)) for state in sorted(self.stateCatalog)
				if state not in included and state.strip() and state not in ALWAYS_SENT_STATES]

	def AvailableDevicesGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		_, devices = self.dialogLists()
		unavailable = set(devices) | set(self.DeviceExcludeList)
		return [(dev_id, label) for dev_id, label in self.deviceNames.items() if dev_id not in unavailable]

	def AllStatesGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		return [(state, self.stateLabel(state)) for state in sorted(self.stateCatalog)]

######
	# The include/exclude buttons edit the dialog's working copy, committed by
	# closedPrefsConfigUi - so Cancel really cancels them.

	def AddDeviceToIncludedDeviceList(self, valuesDict, typeId="", devId=0):
		try:
			dev_id = int(valuesDict.get("menuAvailableDevices") or 0)
		except (TypeError, ValueError):
			return valuesDict

		if dev_id:
			with self.configLock:
				devices = self.editableDialog()['devices']
				if dev_id not in devices:
					devices.append(dev_id)

		return valuesDict

	def RemoveDeviceFromIncludedDeviceList(self, valuesDict, typeId="", devId=0):
		with self.configLock:
			devices = self.editableDialog()['devices']
			for item in valuesDict.get("listIncDevices", []):
				try:
					devices.remove(int(item))
				except (TypeError, ValueError) as e:
					self.logger.error(f"error while removing device from the inclusion list: {e}")

		valuesDict["listIncDevices"] = indigo.List()
		return valuesDict

	def AddStateToIncludedStateList(self, valuesDict, typeId="", devId=0):
		state = str(valuesDict.get("menuAvailableStates") or "").strip()
		if state:
			with self.configLock:
				states = self.editableDialog()['states']
				if state not in states:
					states.append(state)

		return valuesDict

	def RemoveStateFromIncludedDeviceList(self, valuesDict, typeId=0, devId=0):
		with self.configLock:
			states = self.editableDialog()['states']
			for state in valuesDict.get("listIncStates", []):
				if self.ConfigDebug:
					self.logger.debug("removing: " + str(state))
				try:
					states.remove(state)
				except ValueError as e:
					self.logger.error(f"error while removing state from inclusion list: {e}")

		valuesDict["listIncStates"] = indigo.List()
		return valuesDict

	def ResetStatesIncludedStateList(self, valuesDict, typeId="", devId=0):
		if self.ConfigDebug:
			self.logger.debug("resetting to default states")

		with self.configLock:
			self.editableDialog()['states'] = DEFAULT_STATES[:]

		return valuesDict

################### MCP tool provider (MCP Advanced Tools plugin) ###################################

	def handle_mcp_tool_invoke(self, action, dev=None, caller_waiting_for_result=True):
		"""Called cross-plugin by MCP Advanced Tools (com.vtmikel.mcp_server)
		via executeAction.  The bare tool name and a JSON-string arguments
		payload arrive in action.props; the reply is always a JSON-string
		envelope (mcp_api.tool_dispatcher).  Everything under mcp_api/ is
		imported lazily here, so a bug in tool code can never affect the plugin
		for users without MCP Advanced Tools."""
		try:
			if self._tool_dispatcher is None:
				from mcp_api.tool_dispatcher import ToolDispatcher
				from mcp_api.config_tools import InfluxLogTools
				self._tool_dispatcher = ToolDispatcher(InfluxLogTools(self))
		except Exception as e:
			self.logger.exception("Failed to initialize the MCP tool dispatcher")
			return json.dumps({"status": "error", "error": {"type": "internal", "message": f"MCP tool dispatcher failed to initialize: {e}"}})

		tool = action.props.get("tool", "")
		reply = self._tool_dispatcher.dispatch(tool, action.props.get("arguments", "{}"))
		if isinstance(reply, str):
			return reply

		# A tool that needs the network (update_connection's test) finishes on a
		# worker thread: Indigo's callback thread must never wait on I/O.
		handler = None
		if caller_waiting_for_result:
			try:
				handler = indigo.acquireCallbackCompleteHandler()
			except Exception as e:
				self.logger.debug(f"no completion handler ({e}); finishing {tool} synchronously")
				return self._tool_dispatcher.complete(tool, reply)

		def finish():
			envelope = self._tool_dispatcher.complete(tool, reply)
			if handler is not None:
				handler.returnResult(envelope)

		threading.Thread(target=finish, name="InfluxToolWorker", daemon=True).start()
		return None

### Other menu items

	def PrintDeviceToEventLog(self, valuesDict, typeId=0, devId=0):
		dev = indigo.devices[int(valuesDict["menuDevice"])]
		excluded = False
		included = False

		if dev.id in self.DeviceExcludeList:
			self.logger.info("NOTE: Device \"" + dev.name + "\" is EXCLUDED in your config and therefore nothing is sent to InfluxDB for it")
			excluded = True

		self.logger.info("JSON representation of device " + dev.name + ":")

		if dev.id in self.DeviceIncludeList and not excluded:
			included = True
			self.logger.info("NOTE: Device \"" + dev.name + "\" is INCLUDED in your config and therefore all states are sent to InfluxDB")

		# to_json, not diff_to_json: exploring a device must not touch the
		# adaptor's change-detection cache
		newjson = self.adaptor.to_json(dev)
		newjson.pop('measurement', None)

		if not newjson:
			self.logger.info("   the device: \"" + dev.name + "\" is not excluded from updates to InfluxDB, but it contains no states/properties that are capable of being sent to Influx/Grafana.")

		else:
			for kk, vv in sorted(newjson.items()):
				if not isinstance(vv, indigo.Dict) and not isinstance(vv, dict):
					if excluded:
						status = " (EXCLUDED)"
					elif kk in ALWAYS_SENT_STATES:
						status = " (ALWAYS SENT)"
					elif kk in self.StatesIncludeList or included:
						status = " (INCLUDED)"
					else:
						status = " (NOT INCLUDED)"

					# Value conversion
					value = str(vv) if not isinstance(vv, str) else vv

					self.logger.info("   " + str(kk) + ": " + value + status)

		return valuesDict

	def PrintStateToEventLog(self, valuesDict, typeId=0, devId=0):
		searchKey = valuesDict["menuProperty"]
		counter = 1

		self.logger.info("Devices containing the property " + searchKey + ":")
		for dev in indigo.devices:
			excluded = False
			if dev.id in self.DeviceExcludeList:
				excluded = True

			### STATES List
			for kk, vv in self.adaptor.to_json(dev).items():
				if not isinstance(vv, indigo.Dict) and not isinstance(vv, dict):
					if kk == searchKey:
						if excluded:
							status = " (EXCLUDED)"
						elif kk in ALWAYS_SENT_STATES:
							status = " (ALWAYS SENT)"
						elif kk in self.StatesIncludeList or dev.id in self.DeviceIncludeList:
							status = " (INCLUDED)"
						else:
							status = " (NOT INCLUDED)"

						# Value conversion
						value = str(vv) if not isinstance(vv, str) else vv

						self.logger.info("   " + str(counter) + ". " + dev.name + " ;  " + str(kk) + ": " + value + status)
						counter = counter + 1

		return valuesDict

	def resetDataFilters(self):
		self.logger.info("resetting data filters")
		self.store.apply('filters menu', lambda config: config.update(filters=[]))

	def ForceUpdate(self):
		self.UpdateAll()

	def rebuildConfig(self):
		self.BuildConfigurationLists()

	def printFilterBlocksEventLog(self):
		try:
			self.logger.info("Listing filter block log records (oldest to newest, maximum of " + str(MAX_LOG_FILE_OUTPUT_LINES) + " records):")
			with open(self.FilterLogFileLoc, "r") as log_file:
				lines = self.tail(log_file, MAX_LOG_FILE_OUTPUT_LINES)[0]

			for line in lines:
				self.logger.info(line)

			self.logger.info("completed log output")

		except Exception as e:
			self.logger.debug("log output Error: " + str(e))
			self.logger.info("    no log records exist")
			self.logger.info("completed log output")

	def pruneFilterBlocksEventLog(self):
		self.logger.debug("entering pruneFilterBlocksEventLog()")
		self.lastLogPrune = datetime.datetime.now()

		if not self.FilterLogFileLoc or not os.path.exists(self.FilterLogFileLoc):
			return

		try:
			with open(self.FilterLogFileLoc, "r") as log_file:
				lines = self.tail(log_file, MAX_LOG_FILE_OUTPUT_LINES)[0]

			os.remove(self.FilterLogFileLoc)

			with open(self.FilterLogFileLoc, "a") as logFile:
				for line in lines:
					logFile.write(line + '\n')

		except Exception as e:
			self.logger.debug("log prune error: " + str(e))

		self.logger.debug("completed pruneFilterBlocksEventLog()")

	def tail(self, f, n, offset=None):
		"""Reads a n lines from f with an offset of offset lines.  The return
		value is a tuple in the form ``(lines, has_more)`` where `has_more` is
		an indicator that is `True` if there are more lines in the file.
		"""
		avg_line_length = 74
		to_read = n + (offset or 0)

		while 1:
			try:
				f.seek(-(avg_line_length * to_read), 2)
			except IOError:
				# woops.  apparently file is smaller than what we want
				# to step back, go to the beginning instead
				f.seek(0)
			pos = f.tell()
			lines = f.read().splitlines()
			if len(lines) >= to_read or pos == 0:
				return lines[-to_read:offset and -offset or None], \
					   len(lines) > to_read or pos > 0
			avg_line_length *= 1.3

	def FilterAction(self, valuesDict, typeId = 0, devId = 0):
		if valuesDict["filterAction"] == "edit":
			if len(valuesDict["listFilters"]) != 1:
				self.logger.error("there must be one filter selected from the Filters List")
				return valuesDict

			try:
				editIndex = int(valuesDict["listFilters"][0])
				editItem = self.FilterList[editIndex]
				valuesDict["filterName"] = editItem.name
				valuesDict["filterProperty"] = editItem.state
				valuesDict["editFilterProperty"] = editItem.state
				valuesDict["filterOrder"] = str(editIndex + 1)

				valuesDict["filterStrategy"] = editItem.filterStrategy
				valuesDict["filterPropertyMinValue"] = editItem.minValue
				valuesDict["filterPropertyMaxValue"] = editItem.maxValue
				valuesDict["filterPropertyPercent"] = editItem.maxPercent
				valuesDict["preventMinimumUpdates"] = editItem.lockMinimumUpdates

				valuesDict["filterScope"] = editItem.scope
				# a list, not the filter's set: indigo.Dict rejects a set with a
				# TypeError, which is what broke Edit from v2025.0.1 on
				valuesDict["listDevices"] = [str(dev_id) for dev_id in sorted(editItem.scopeDevices)]
				valuesDict["logFailures"] = editItem.log

				valuesDict["editMode"] = True
				valuesDict["lockActionChange"] = True
				valuesDict["percentVisible"] = editItem.filterStrategy == "percentChanged"
				valuesDict["deviceListVisible"] = editItem.scope != "all"

				# positions shift if the filters change meanwhile (an MCP tool):
				# SaveFilterValues checks the filter is still the one loaded here
				self.filterEditGuard = (editIndex, editItem.name)

			except (IndexError, KeyError, ValueError, TypeError) as e:
				self.logger.error(f"could not load the selected filter for editing: {e}")

		elif valuesDict["filterAction"] == "delete":
			# positions arrive as strings; sort them as numbers ("10" < "9" as text)
			# and delete from the end so the remaining positions stay valid
			try:
				positions = sorted({int(i) for i in valuesDict["listFilters"]}, reverse=True)
			except (TypeError, ValueError) as e:
				self.logger.error(f"invalid filter selection: {e}")
				return valuesDict

			shown = self.filterListShown

			def delete(config):
				for i in positions:
					if shown is not None and (i >= len(shown) or i >= len(config['filters']) or InfluxFilter.fromDict(config['filters'][i]).name != shown[i]):
						raise ConfigError('conflict', "the filters changed since this list was shown; nothing was deleted. Close the dialog and open it again.")
				for i in positions:
					if 0 <= i < len(config['filters']):
						del config['filters'][i]

			try:
				self.store.apply('filters dialog', delete)
			except ConfigError as e:
				self.logger.error(e.message)

		return valuesDict

	def filterActionMenuChanged(self, valuesDict, typeId=0, devId=0):
		if valuesDict["filterAction"] == "add":
			valuesDict["editMode"] = True
		else:
			valuesDict["editMode"] = False

		return valuesDict

	def filterStrategyChanged(self, valuesDict, typeId=0, devId=0):
		valuesDict["percentVisible"] = valuesDict["filterStrategy"] == "percentChanged" and (valuesDict["filterAction"] == "edit" or valuesDict["filterAction"] == "add")
		valuesDict["preventMinimumUpdates"] = valuesDict["filterStrategy"] == "percentChanged" and (valuesDict["filterAction"] == "edit" or valuesDict["filterAction"] == "add")

		return valuesDict

	def filterScopeChanged(self, valuesDict, typeId=0, devId=0):
		valuesDict["deviceListVisible"] = valuesDict.get("filterScope", "all") != "all" and (valuesDict["filterAction"] == "edit" or valuesDict["filterAction"] == "add")

		return valuesDict

	# older dialogs bound to the checkbox this menu replaced
	filterAllDevicesChanged = filterScopeChanged

	def SaveFiltersToPreferences(self):
		with self.configLock:
			self.pluginPrefs["listFilterList"] = [influxFilterRecord.toPrefs() for influxFilterRecord in self.FilterList]
			self.pluginPrefs["preferencesFilterVersion"] = FILTER_PREFS_VERSION

			self.RebuildFilterIndex()

		self.savePrefs()

	def SaveFilterValues(self, valuesDict, typeId=0, devId=0):
		if not valuesDict.get("filterProperty"):
			self.logger.error("Select a valid property/state")
			return valuesDict

		if not valuesDict.get("filterOrder"):
			self.logger.error("Select an 'insert at' value")
			return valuesDict

		try:
			filterName = valuesDict.get("filterName", "")
			filterOrder = int(valuesDict["filterOrder"])
			filterProperty = valuesDict["filterProperty"]

			filterStrategy = valuesDict["filterStrategy"]
			filterPropertyMinValue = 0
			filterPropertyMaxValue = 0
			filterPropertyPercent = 0
			lockMinimumUpdates = True

			if filterStrategy == "minMax":
				filterPropertyMinValue = float(valuesDict["filterPropertyMinValue"])
				filterPropertyMaxValue = float(valuesDict["filterPropertyMaxValue"])
			else:
				filterPropertyPercent = float(valuesDict["filterPropertyPercent"])
				lockMinimumUpdates = valuesDict["preventMinimumUpdates"]

			filterScope = valuesDict.get("filterScope") or ("all" if valuesDict.get("filterAllDevices", True) else "devices")
			if filterScope not in ("all", "devices", "all_except"):
				raise ValueError(f"unknown scope {filterScope}")
			filterDevices = []

			if filterScope != "all":
				filterDevices = list(valuesDict["listDevices"])

			log = valuesDict["logFailures"]
			editIndex = int(valuesDict["listFilters"][0]) if valuesDict["filterAction"] == "edit" else None
		except ValueError as e:
			self.logger.error(f"Ensure that filter max and min values must be numeric: {e}")
			return valuesDict
		except (KeyError, TypeError, IndexError) as e:
			self.logger.error(f"Error validating the form.  Ensure that filter max and min values must be numeric, and all fields are filled in: {e}")
			return valuesDict

		if filterStrategy == "minMax" and filterPropertyMinValue >= filterPropertyMaxValue:
			self.logger.error("minimum value must be smaller than the maximum value.")
			return valuesDict

		if filterStrategy == "percentChanged" and filterPropertyPercent <= 0:
			self.logger.error("the maximum percentage change must be greater than 0.")
			return valuesDict

		if len(filterDevices) == 0 and filterScope != "all":
			self.logger.error("select the devices the filter applies to (or, for 'all devices except', the devices it skips).")
			return valuesDict

		# a generated name (or none) is regenerated from the new settings; a name
		# the user typed is kept
		newFilter = InfluxFilter(filterProperty.strip(), filterStrategy, filterPropertyMinValue, filterPropertyMaxValue, filterPropertyPercent,
								 filterScope != "devices", filterDevices if filterScope == "devices" else [], lockMinimumUpdates, log, filterName,
								 filterDevices if filterScope == "all_except" else [])

		guard = self.filterEditGuard

		def save(config):
			filters = config['filters']
			if editIndex is not None:
				if not 0 <= editIndex < len(filters) or (guard is not None and (guard[0] != editIndex or InfluxFilter.fromDict(filters[editIndex]).name != guard[1])):
					raise ConfigError('conflict', "the filters changed while this one was being edited; nothing was saved. Close the dialog and edit it again.")
				self.logger.debug("deleting index " + str(editIndex))
				del filters[editIndex]

			# 'insert at' past the end means last
			position = max(1, min(filterOrder, len(filters) + 1))
			filters.insert(position - 1, newFilter.toDict())

		try:
			self.store.apply('filters dialog', save)
		except ConfigError as e:
			self.logger.error(e.message)
			return valuesDict

		self.filterEditGuard = None
		self.logger.debug("added the filter " + newFilter.name)

		valuesDict["filterName"] = ""
		valuesDict["filterOrder"] = ""
		valuesDict["filterProperty"] = ""
		valuesDict["filterStrategy"] = "minMax"
		valuesDict["filterPropertyMinValue"] = ""
		valuesDict["filterPropertyMaxValue"] = ""
		valuesDict["filterPropertyPercent"] = ""
		valuesDict["preventMinimumUpdates"] = True
		valuesDict["filterScope"] = "all"
		valuesDict["listDevices"] = indigo.List()
		valuesDict["logFailures"] = True
		valuesDict["lockActionChange"] = False

		valuesDict["editMode"] = valuesDict["filterAction"] == "add"

		return valuesDict
