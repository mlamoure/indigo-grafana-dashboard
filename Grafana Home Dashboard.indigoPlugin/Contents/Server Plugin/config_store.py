#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""ConfigStore: the one owner of the plugin's logging configuration.

The configuration itself still lives on the Plugin object (the include/exclude
lists, the filters, the settings) because the write pipeline reads it on every
device change.  Every change goes through ConfigStore.apply(), whatever its
source - the config dialog, the filters dialog, housekeeping, or an MCP tool:

    lock -> revision check -> mutate a plain copy -> validate -> diff
         -> load into the plugin -> persist -> rebuild derived state -> revision + 1

The plain copy (`current()`) holds no secrets: the InfluxDB password/token is
never part of it, so nothing built from it - tool output, snapshots, log lines -
can contain it.
"""

import copy
import datetime
import json
import os
import re

import indigo

from influx_filter import InfluxFilter


class ConfigError(Exception):
	"""A change the store refused.  kind is 'validation' or 'conflict';
	errors is a list of {'path', 'message'} for validation failures."""

	def __init__(self, kind, message, errors=None, details=None):
		super().__init__(message)
		self.kind = kind
		self.message = message
		self.errors = errors or []
		self.details = details


CONNECTION_FIELDS = ('host', 'port', 'ssl', 'version', 'database', 'user')

# the sections a snapshot restores; the connection is reported, never restored
RESTORABLE = ('states', 'include', 'exclude', 'filters', 'settings')
SNAPSHOTS_KEPT = 20
SNAPSHOT_FILE = re.compile(r'^(\d{6,})\.json$')
DEBUG_FIELDS = {'plugin': 'debug', 'config': 'ConfigDebug', 'transport': 'TransportDebug',
				'transport_l2': 'TransportDebugL2', 'json': 'JSONDebug'}


def frequency_label(value):
	"""'disabled' for -1, else the minutes (or the legacy 'smart')."""
	if value == 'smart':
		return 'smart'
	return 'disabled' if value == -1 else value


def frequency_value(label):
	if label == 'disabled':
		return -1
	return label


class ConfigStore:
	def __init__(self, plugin):
		self.plugin = plugin
		self.lock = plugin.configLock
		try:
			self.revision = int(plugin.pluginPrefs.get('configRevision', 0) or 0)
		except (TypeError, ValueError):
			self.revision = 0
		self.snapshotDir = None

	# ------------------------------------------------------------------
	# reading

	def current(self):
		"""The configuration as plain, JSON-able data, without secrets."""
		p = self.plugin
		with self.lock:
			return {
				'states': list(p.StatesIncludeList),
				'include': list(p.DeviceIncludeList),
				'exclude': list(p.DeviceExcludeList),
				'filters': [f.toDict() for f in p.FilterList],
				'settings': {
					'minimum_update_frequency': frequency_label(p.minimumUpdateFrequency),
					'retention': str(p.InfluxRetention),
					'debug': {key: bool(getattr(p, attr, False)) for key, attr in DEBUG_FIELDS.items()},
				},
				'connection': {
					'host': p.InfluxHost,
					'port': str(p.InfluxHTTPPort),
					'ssl': bool(p.InfluxSSL),
					'version': str(p.InfluxVersion),
					'database': p.InfluxDB,
					'user': p.InfluxUser,
					# counts password changes, so changing only the password is
					# still a change (a revision, a snapshot) without the store
					# ever holding the secret
					'credentials_version': p.credentialsVersion,
				},
			}

	def ensureCatalog(self, max_age=datetime.timedelta(minutes=15)):
		"""Rebuild the state catalog when it is older than max_age."""
		built = self.plugin.catalogBuilt
		if built is None or datetime.datetime.now() - built > max_age:
			self.plugin.BuildConfigurationLists()

	# ------------------------------------------------------------------
	# writing

	def apply(self, source, mutate, dry_run=False, expected_revision=None, summary=None, log=None):
		"""Apply mutate(config) -> warnings to a copy of the configuration.

		mutate edits the plain dict in place and may raise ConfigError.  Returns
		{'revision', 'changed', 'dry_run', 'before', 'after', 'warnings'} where
		before/after hold only the sections that changed."""
		with self.lock:
			if expected_revision is not None and int(expected_revision) != self.revision:
				raise ConfigError('conflict', f"the configuration changed since revision {expected_revision} "
											  f"(now {self.revision}); read it again and retry",
								  details={'current_revision': self.revision})

			before = self.current()
			after = copy.deepcopy(before)
			warnings = list(mutate(after) or [])
			self.normalize(after)
			changed = {section for section in after if after[section] != before[section]}

			result = {
				'revision': self.revision,
				'changed': bool(changed),
				'dry_run': bool(dry_run),
				'before': {section: before[section] for section in sorted(changed)},
				'after': {section: after[section] for section in sorted(changed)},
				'warnings': warnings,
			}
			if dry_run or not changed:
				return result

			self.beforeCommit(source, before, summary)
			self.load(after, changed)
			self.revision += 1
			self.plugin.persistConfig()
			result['revision'] = self.revision

		if log:
			self.plugin.logger.info(f"{log} (revision {self.revision})")
		return result

	def beforeCommit(self, source, before, summary):
		"""Snapshot the configuration a change is about to replace (lock held)."""
		try:
			self.saveSnapshot(before, source, summary)
		except OSError as e:
			self.plugin.logger.warning(f"could not save a configuration snapshot: {e}")

	# ------------------------------------------------------------------
	# snapshots: the configuration before each change, as JSON files without
	# secrets, the newest SNAPSHOTS_KEPT kept

	def snapshotFolder(self):
		if self.snapshotDir is None:
			self.snapshotDir = os.path.join(indigo.server.getInstallFolderPath(), 'Preferences', 'Plugins',
											self.plugin.pluginId + '.snapshots')
		os.makedirs(self.snapshotDir, exist_ok=True)
		return self.snapshotDir

	def saveSnapshot(self, config, source, summary):
		folder = self.snapshotFolder()
		record = {'revision': self.revision, 'time': now_iso(), 'source': source,
				  'summary': summary or source, 'config': config}
		path = os.path.join(folder, f"{self.revision:06d}.json")
		with open(path + '.tmp', 'w') as f:
			json.dump(record, f, indent=1)
		os.replace(path + '.tmp', path)

		snapshots = self.snapshotFiles()
		for revision, name in snapshots[SNAPSHOTS_KEPT:]:
			os.remove(os.path.join(folder, name))

	def snapshotFiles(self):
		"""[(revision, file name)], newest first."""
		folder = self.snapshotFolder()
		found = []
		for name in os.listdir(folder):
			match = SNAPSHOT_FILE.match(name)
			if match:
				found.append((int(match.group(1)), name))
		return sorted(found, reverse=True)

	def listSnapshots(self):
		listing = []
		for revision, name in self.snapshotFiles():
			try:
				with open(os.path.join(self.snapshotFolder(), name)) as f:
					record = json.load(f)
			except (OSError, ValueError) as e:
				listing.append({'revision': revision, 'error': f"unreadable: {e}"})
				continue
			listing.append({'revision': record.get('revision', revision), 'time': record.get('time'),
							'source': record.get('source'), 'summary': record.get('summary')})
		return listing

	def readSnapshot(self, revision):
		path = os.path.join(self.snapshotFolder(), f"{int(revision):06d}.json")
		if not os.path.isfile(path):
			return None
		with open(path) as f:
			return json.load(f)

	@staticmethod
	def normalize(config):
		config['states'] = _dedupe(str(s).strip() for s in config['states'] if str(s).strip())
		config['include'] = _dedupe(int(d) for d in config['include'])
		included = set(config['include'])
		config['exclude'] = _dedupe(int(d) for d in config['exclude'] if int(d) not in included)
		for f in config['filters']:
			f['devices'] = sorted(set(int(d) for d in f.get('devices', [])))
			if f.get('scope') == 'all':
				f['devices'] = []

	def load(self, config, sections):
		"""Put a configuration into the running plugin."""
		p = self.plugin
		if 'states' in sections:
			p.StatesIncludeList = list(config['states'])
		if 'include' in sections:
			p.DeviceIncludeList = list(config['include'])
		if 'exclude' in sections:
			p.DeviceExcludeList = list(config['exclude'])
		if 'filters' in sections:
			p.FilterList = [InfluxFilter.fromDict(f) for f in config['filters']]
			p.filtersUnreadable = False  # an explicit edit replaces filters that could not be read
			p.RebuildFilterIndex()
		if 'settings' in sections:
			settings = config['settings']
			p.minimumUpdateFrequency = frequency_value(settings['minimum_update_frequency'])
			p.InfluxRetention = str(settings['retention'])
			for key, attr in DEBUG_FIELDS.items():
				setattr(p, attr, bool(settings['debug'][key]))
			if p.adaptor is not None:
				p.adaptor.TransportDebug = p.TransportDebug
				p.adaptor.TransportDebugL2 = p.TransportDebugL2
				p.adaptor.JSONDebug = p.JSONDebug
		if 'connection' in sections:
			connection = config['connection']
			p.InfluxHost = connection['host']
			p.InfluxHTTPPort = str(connection['port'])
			p.InfluxSSL = bool(connection['ssl'])
			p.InfluxVersion = str(connection['version'])
			p.InfluxV3Compat = p.InfluxVersion == '3'
			p.InfluxDB = connection['database']
			p.InfluxUser = connection['user']
			p.credentialsVersion = connection.get('credentials_version', p.credentialsVersion)

	# ------------------------------------------------------------------
	# the plugin config dialog

	def dialogBase(self):
		"""What the plugin config dialog opened with: its working copy plus the
		base a later commit is merged against."""
		config = self.current()
		return {
			'revision': self.revision,
			'base': config,
			'states': list(config['states']),
			'devices': list(config['include']),
		}

	def commitDialog(self, dialog, values):
		"""Commit the plugin config dialog.  values: the dialog's settings in
		current()'s shape ({'exclude', 'settings', 'connection'}).

		When nothing else changed the configuration while the dialog was open,
		the dialog's state is simply the new configuration.  Otherwise its
		changes - relative to what it opened with - are applied on top of the
		current configuration, so an AI edit made meanwhile survives; a warning
		names any item both changed."""
		base = dialog['base'] if dialog else self.current()
		dialog_view = {
			'states': dialog['states'] if dialog else base['states'],
			'include': dialog['devices'] if dialog else base['include'],
			'exclude': values['exclude'],
		}

		def mutate(config):
			warnings = []
			for section in ('states', 'include', 'exclude'):
				config[section], conflicts = merge_list(base[section], dialog_view[section], config[section])
				warnings += [f"{section}: {item!r} was changed both in the dialog and elsewhere; the dialog's change was applied"
							 for item in conflicts]
			for section in ('settings', 'connection'):
				config[section], conflicts = merge_dict(base[section], values[section], config[section])
				warnings += [f"{section}.{key} was changed both in the dialog and elsewhere; the dialog's value was applied"
							 for key in conflicts]
			return warnings

		return self.apply('config dialog', mutate)


def _dedupe(items):
	seen = []
	for item in items:
		if item not in seen:
			seen.append(item)
	return seen


def merge_list(base, mine, theirs):
	"""Three-way merge of an ordered list: apply mine's additions and removals
	(relative to base) to theirs.  Returns (merged, conflicting items)."""
	base_set, mine_set, theirs_set = set(base), set(mine), set(theirs)
	added = mine_set - base_set
	removed = base_set - mine_set
	if theirs_set == base_set:
		# nothing changed elsewhere: mine is the result, in mine's order
		return list(mine), []
	merged = [item for item in theirs if item not in removed]
	merged += [item for item in mine if item in added and item not in merged]
	changed_elsewhere = theirs_set ^ base_set
	return merged, sorted((added | removed) & changed_elsewhere, key=str)


def merge_dict(base, mine, theirs):
	"""Three-way merge of a (possibly nested) settings dict: keys mine changed
	relative to base take mine's value; the rest keep theirs."""
	merged = copy.deepcopy(theirs)
	conflicts = []
	for key, value in mine.items():
		if isinstance(value, dict):
			merged[key], nested = merge_dict(base.get(key, {}), value, theirs.get(key, {}))
			conflicts += [f"{key}.{n}" for n in nested]
			continue
		if value != base.get(key):
			if theirs.get(key) != base.get(key) and theirs.get(key) != value:
				conflicts.append(key)
			merged[key] = value
	return merged, conflicts


def now_iso():
	return datetime.datetime.now().astimezone().isoformat(timespec='seconds')
