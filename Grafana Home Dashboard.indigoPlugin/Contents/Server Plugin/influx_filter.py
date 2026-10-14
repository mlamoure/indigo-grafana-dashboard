#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""Data filters: the InfluxFilter rule, its preferences record and the plain
dict form the config store and the MCP tools work with.

A filter's scope is one of:
  all         every device
  devices     only appliedDevices
  all_except  every device except exceptDevices (2026.11.0)

The prefs record stays format 2.0.0 with the except list as an optional 11th
element.  Releases before 2026.11.0 read the first ten and ignore the rest, so
a rollback keeps every filter (an all_except filter then simply applies to all
devices again).  A new format number would have made them load no filters at
all, silently.
"""

import re

# A name the plugin generated rather than one the user typed.  Generated names
# describe the thresholds, so they are regenerated whenever those change - a
# stale one ("... (all devices) ..." on a filter scoped to 300 devices) misleads.
GENERATED_FILTER_NAME = re.compile(
	r"^.+ \((?:all devices|specific devices|all devices except \d+)\) (?:min: \S+, max: \S+|percent: \S+)$")

# preferencesFilterVersion written by this release (see the module docstring)
FILTER_PREFS_VERSION = "2.0.0"

SCOPES = ('all', 'devices', 'all_except')

# internal strategy names <-> the names the tools use
STRATEGY_TO_TOOL = {'minMax': 'min_max', 'percentChanged': 'percent_changed'}
STRATEGY_FROM_TOOL = {tool: internal for internal, tool in STRATEGY_TO_TOOL.items()}


class InfluxFilter:
	"""Filter configuration for InfluxDB data validation"""

	def __init__(self, state, filterStrategy, minValue, maxValue, maxPercent, allDevices, appliedDevices, lockMinimumUpdates, log, name="", exceptDevices=()):
		self.state = state
		self.filterStrategy = filterStrategy  # "minMax" or "percentChanged"
		self.minValue = float(minValue)
		self.maxValue = float(maxValue)
		self.maxPercent = float(maxPercent)
		self.allDevices = bool(allDevices)
		# Use set for O(1) lookup performance instead of list O(n)
		self.appliedDevices = set(int(dev) for dev in (appliedDevices or [])) if not self.allDevices else set()
		self.exceptDevices = set(int(dev) for dev in (exceptDevices or [])) if self.allDevices else set()
		self.lockMinimumUpdates = bool(lockMinimumUpdates)
		self.log = bool(log)
		self.name = name

	@property
	def scope(self):
		if not self.allDevices:
			return "devices"
		return "all_except" if self.exceptDevices else "all"

	@property
	def scopeDevices(self):
		"""The devices the scope names: those it applies to, or those it skips."""
		return self.exceptDevices if self.allDevices else self.appliedDevices

	@property
	def appliesToString(self):
		if not self.allDevices:
			return "specific devices"
		if self.exceptDevices:
			return f"all devices except {len(self.exceptDevices)}"
		return "all devices"

	def generatedName(self):
		if self.filterStrategy == "minMax":
			values = f"min: {self.minValue}, max: {self.maxValue}"
		else:
			values = f"percent: {self.maxPercent}"
		return f"{self.state} ({self.appliesToString}) {values}"

	@property
	def name(self):
		return self.customName or self.generatedName()

	@name.setter
	def name(self, value):
		value = str(value or "").strip()
		self.customName = "" if GENERATED_FILTER_NAME.match(value) else value

	def appliesTo(self, devId):
		if self.allDevices:
			return devId not in self.exceptDevices
		return devId in self.appliedDevices

	def toPrefs(self):
		"""The preferencesFilterVersion 2.0.0 record, plus the except list as an
		11th element that older releases ignore."""
		return [self.state, self.filterStrategy, self.minValue, self.maxValue, self.maxPercent, self.allDevices,
				sorted(self.appliedDevices), self.lockMinimumUpdates, self.log, self.name, sorted(self.exceptDevices)]

	@classmethod
	def fromPrefs(cls, item, version):
		"""A filter from a prefs record of format 2.0.0 (with or without the
		except list) or 1.0.0.  "3.0.0" was written by 2026.11.0 pre-release
		builds only: the same record."""
		if version == "1.0.0":
			return cls(item[0], item[1], item[2], item[3], item[4], item[5], item[6], True, item[7])
		name = item[9] if len(item) > 9 else ""
		exceptDevices = item[10] if len(item) > 10 else ()
		return cls(item[0], item[1], item[2], item[3], item[4], item[5], item[6], item[7], item[8], name, exceptDevices)

	def toDict(self):
		"""The plain form the config store and the MCP tools use."""
		return {
			'state': self.state,
			'strategy': STRATEGY_TO_TOOL.get(self.filterStrategy, self.filterStrategy),
			'min': self.minValue,
			'max': self.maxValue,
			'max_percent': self.maxPercent,
			'scope': self.scope,
			'devices': sorted(self.scopeDevices),
			'lock_on_failure': self.lockMinimumUpdates,
			'log_to_event_log': self.log,
			'name': self.customName,
		}

	@classmethod
	def fromDict(cls, data):
		scope = data.get('scope', 'all')
		devices = data.get('devices', [])
		return cls(data['state'], STRATEGY_FROM_TOOL.get(data['strategy'], data['strategy']), data.get('min', 0.0),
				   data.get('max', 0.0), data.get('max_percent', 0.0), scope != 'devices',
				   devices if scope == 'devices' else [], data.get('lock_on_failure', True),
				   data.get('log_to_event_log', False), data.get('name', ''),
				   devices if scope == 'all_except' else [])
