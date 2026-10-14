# Copyright (c) 2017, 2018, Dave Brown

from datetime import date, datetime
import time as time_
import json
import indigo
from enum import Enum

def to_bool(value):
	"""Convert a string representation to a real boolean ('False' -> False)."""
	return str(value).strip().lower() in ('true', 't', '1', 'yes', 'on')

def to_int(value):
	"""int('3.0') raises, yet every number reaches the plugin as a float (see
	smart_value), so accept a float string with an integral value."""
	try:
		return int(value)
	except ValueError:
		number = float(value)
		if not number.is_integer():
			raise
		return int(number)

# Type converter mapping (replaces eval() for security).  Keys are the type
# names InfluxDB 1.x reports in type-conflict errors, plus the plugin's own.
TYPE_CONVERTERS = {
	'int': to_int,
	'str': str,
	'float': float,
	'integer': to_int,  # InfluxDB sometimes returns "integer"
	'string': str,   # InfluxDB sometimes returns "string"
	'bool': to_bool,
	'boolean': to_bool
}

# Device liveness markers, emitted on every device point by diff_to_json() so that
# a flat line from a DEAD device is distinguishable from a flat line from a merely
# QUIET one.  Each pair is (indigo attribute, derived age field): the absolute
# timestamp is the backfill-correct record, the age is what you can actually alert
# on, since InfluxQL has no way to express now() - field in a SELECT projection.
LIVENESS_FIELDS = (
	('lastChanged', 'secondsSinceLastChanged'),
	('lastSuccessfulComm', 'secondsSinceLastSuccessfulComm')
)

# Indigo reports a placeholder timestamp of 2000-01-01 LOCAL time for devices that
# have never communicated (virtual devices, device groups, some plugin-backed
# devices).  smart_value() converts via .timestamp(), so the epoch depends on the
# server's UTC offset - 946702800 on a US Eastern server, up to 946728000 at UTC-12.
# The floor is therefore 2000-01-02T00:00Z, which covers the placeholder in every
# timezone while staying far below any real observation.
#
# Do not lower this to 2000-01-01T00:00Z: on any server west of UTC the placeholder
# then sorts ABOVE the floor and those devices report as ~26 years stale, pinning
# the top of every staleness panel - the exact outcome this floor exists to prevent.
LIVENESS_SENTINEL_FLOOR = 946771200.0

# explicit changes
def indigo_json_serial(obj):
	"""JSON serializer for objects not serializable by default json code"""
	#indigo.server.log(unicode(obj))
	if isinstance(obj, (datetime, date)):
		# Use timestamp() for consistent conversion (includes timezone info)
		return int(obj.timestamp())
	if isinstance(obj, indigo.Dict):
		dd = {}
		for key,value in obj.items():
			dd[key] = value
		return dd
	raise TypeError ("Type %s not serializable" % type(obj))

class JSONAdaptor():
	'''
	Change indigo objects to flat dicts for simpler databases
	'''
	def __init__(self, logger, transport_debug, transport_debug_l2, json_debug):
		self.logger = logger

		self.TransportDebug = transport_debug
		self.TransportDebugL2 = transport_debug_l2
		self.JSONDebug = json_debug

		# Class Properties on http://wiki.indigodomo.com/doku.php?id=indigo_7_documentation:device_class
		self.stringonly = 'displayStateValRaw displayStateValUi displayStateImageSel protocol'.split()

		# remember previous states for diffing, smaller databases.  Keyed by device
		# id, so a rename doesn't orphan an entry; bounded by the device count and
		# pruned of deleted devices (prune_cache).  The old 1000-entry cap was
		# below production's device count and evicted ~12,000 entries a day,
		# each eviction re-sending every included state of that device.
		self.cache = {}
		# remember column name/type mappings to reduce exceptions
		self.typecache = {}

	def forget(self, device_id):
		self.cache.pop(device_id, None)

	def prune_cache(self, device_ids):
		"""Drop cache entries for devices that no longer exist."""
		keep = set(device_ids)
		# list(): device updates add entries from another thread meanwhile
		for device_id in [key for key in list(self.cache) if key not in keep]:
			self.cache.pop(device_id, None)

	# returns None or a value, trying to convert strings to floats where
	# possible
	def smart_value(self, invalue, mknumbers=False):
		value = None
		if str(invalue) != "null" \
			and str(invalue) != "None" \
			and not isinstance(invalue, indigo.List) \
			and not isinstance(invalue, list) \
			and not isinstance(invalue, indigo.Dict) \
			and not isinstance(invalue, dict):
			value = invalue
			try:
				if mknumbers:
					# early exit if we want a number but already have one
					if isinstance(invalue, float):
						value = None
					elif isinstance(invalue, (datetime, date)):
						value = None
					# if we have a string, but it really is a number,
					# MAKE IT A NUMBER IDIOTS
					elif isinstance(invalue, str):
						value = float(invalue)
					elif isinstance(invalue, int):
						value = float(invalue)
				elif isinstance(invalue, bool):
					# bypass for bools - getting casted as ints
					value = bool(invalue)
				elif isinstance(invalue, int):
					# convert ALL numbers to floats for influx
					value = float(invalue)
				# convert datetime to Unix timestamp (consistent with indigo_json_serial)
				elif isinstance(invalue, (datetime, date)):
					value = invalue.timestamp()
				# explicitly change enum values to strings
				# TODO find a more reliable way to change enums to strings
				elif invalue.__class__.__bases__[0].__name__ == 'enum':
					value = str(invalue)
			except ValueError:
				if mknumbers:
					# if we were trying to force numbers but couldn't
					value = None
				pass
		return value

	def to_json(self, device):
		attrlist = [attr for attr in dir(device) if
					attr[:2] + attr[-2:] != '____' and not callable(getattr(device, attr))]
		#indigo.server.log(device.name + ' ' + ' '.join(attrlist))
		newjson = {}
		newjson['name'] = str(device.name)
		for key in attrlist:
			#import pdb; pdb.set_trace()
			if hasattr(device, key) \
				and key not in list(newjson.keys()):
				val = self.smart_value(getattr(device, key), False);
				# some things change types - define the original name as original type, key.num as numeric
				if val != None:
					newjson[key] = val
				if key in self.stringonly:
					continue
				val = self.smart_value(getattr(device, key), True);
				if val is not None:
					newjson[key + '.num'] = val

		# trouble areas
		# dicts end enums will not upload without a little abuse
		for key in 'states globalProps pluginProps ' \
			'ownerProps'.split():
			if key in list(newjson.keys()):
				del newjson[key]

		for key in list(newjson.keys()):
			if newjson[key].__class__.__name__.startswith('k'):
				newjson[key] = str(newjson[key])

		for key in self.stringonly:
			if key in list(newjson.keys()):
				newjson[key] = str(newjson[key])

		for state in device.states:
			val = self.smart_value(device.states[state], False);
			if val != None:
				newjson[str('state.' + state)] = val
			if state in self.stringonly:
				continue
			val = self.smart_value(device.states[state], True);
			if val != None:
				newjson[str('state.' + state + '.num')] = val

		# Try to tell the caller what kind of measurement this is
		if 'setpointHeat' in list(device.states.keys()):
			newjson['measurement'] = 'thermostat_changes'
		elif device.model == 'Weather Station':
			newjson['measurement'] = 'weather_changes'
		else:
			newjson['measurement'] = 'device_changes'

		# try to honor previous complaints about column types
		for key in list(self.typecache.keys()):
			if key in list(newjson.keys()):
				converter = TYPE_CONVERTERS.get(self.typecache[key])
				if converter:
					try:
						newjson[key] = converter(str(newjson[key]))
					except (ValueError, TypeError):
						self.logger.debug('One of the columns just will not convert to the requested type. Partial record written.')
					except Exception as e:
						self.logger.debug('Unknown problem.  Partial record written.  Error:' + str(e))
				else:
					self.logger.debug(f'Unknown type converter requested: {self.typecache[key]}')

		return newjson

	def diff_to_json(self, device, includeStates=None, updateCheck=True):
		"""The changed keys of a device worth sending, or None when nothing is.

		includeStates=None sends every state (an included device); a list sends
		only those keys - an EMPTY list sends nothing.  It used to mean "all",
		so an emptied global include list sent every state of every device."""
		newjson = self.to_json(device)

		if self.JSONDebug:
			self.logger.debug("currently in: diff_to_json for " + device.name)

		localcache = self.cache.get(device.id, {})
		includeAll = includeStates is None
		includeSet = set() if includeAll else set(includeStates)

		diffjson = {}
		hasUpdate = False
		for kk, vv in newjson.items():

			# Check if it's changed.  An exact comparison: a change only in letter
			# case, or to "", is a change and is sent now, not at the next heartbeat.
			if kk not in localcache or localcache[kk] != vv or not updateCheck:

				# either the key is in the include states, the entire device needs to be sent
				if includeAll or kk in includeSet:
					if not isinstance(vv, indigo.Dict) and not isinstance(vv, dict):
						diffjson[kk] = vv

						if self.TransportDebugL2:
							try:
								if kk in localcache:
									self.logger.debug('sending property: ' + kk + " to InfluxDB for device: " + device.name + " because the value has changed.  Prev value: " + str(localcache[kk]) + ", new value: " + str(vv))
								else:
									self.logger.debug('sending property: ' + kk + " to InfluxDB for device: " + device.name + " because the value has changed.  Prev value: <no previous value>, new value: " + str(vv))
							except (AttributeError, UnicodeDecodeError):
								# Debug logging failed, continue anyway
								pass

						hasUpdate = True

		if not hasUpdate:
			if self.TransportDebugL2:
				self.logger.debug("no changed values found for device: " + device.name)

			return None
			
		self.cache.setdefault(device.id, {}).update(newjson)

		# always make sure these survive
		diffjson['name'] = device.name
		diffjson['id'] = float(device.id)
		diffjson['measurement'] = newjson['measurement']

		# Device liveness.  Emitted HERE, after the `not hasUpdate` return above, so
		# these enrich points that were already going to be written rather than
		# creating new ones: lastChanged moves constantly and, if it reached the
		# include-gate above, would defeat the dedup and multiply write volume.
		# For the same reason these must never be added to the include-states list.
		now = time_.time()
		for key, agekey in LIVENESS_FIELDS:
			raw = newjson.get(key)
			try:
				ts = float(raw)
			except (TypeError, ValueError):
				# attribute absent (not every device class communicates), or coerced
				# to something non-numeric by the typecache
				continue

			if ts < LIVENESS_SENTINEL_FLOOR:
				# never-communicated placeholder: omit rather than write 0, so that
				# "not applicable" stays distinct from "stale" in Grafana
				continue

			# write the value to_json() produced, not the float, so a typecache
			# correction already applied to this column is not undone here
			diffjson[key] = raw
			diffjson[agekey] = max(0.0, round(now - ts, 3))

		if self.JSONDebug:
			self.logger.debug(json.dumps(newjson, default=indigo_json_serial).encode('utf-8'))
			self.logger.debug('diff:')
			self.logger.debug(json.dumps(diffjson, default=indigo_json_serial).encode('utf-8'))

		return diffjson

