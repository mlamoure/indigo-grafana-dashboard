# Copyright (c) 2017, 2018, Dave Brown

from datetime import date, datetime
import time as time_
import json
import indigo
from enum import Enum

# explicit changes
def indigo_json_serial(obj):
	"""JSON serializer for objects not serializable by default json code"""
	#indigo.server.log(unicode(obj))
	if isinstance(obj, (datetime, date)):
		ut = time_.mktime(obj.timetuple())
		return int(ut)
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

		# have the json serializer always use this
		json.JSONEncoder.default = indigo_json_serial

		# remember previous states for diffing, smaller databases
		self.cache = {}
		# remember column name/type mappings to reduce exceptions
		self.typecache = {}

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
				# convert datetime to timestamps of another flavor
				elif isinstance(invalue, (datetime, date)):
					value = time_.mktime(invalue.timetuple())
					#value = int(ut)
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
				try:
					newjson[key] = eval( '%s("%s")' % (self.typecache[key], str(newjson[key])))
				except ValueError:
					self.logger.debug('One of the columns just will not convert to the requested type. Partial record written.')
					pass
				except Exception as e:
					self.logger.debug('Unknown problem.  Partial record written.  Error:' + str(e))
					pass

		return newjson

	def diff_to_json(self, device, includeStates = [], updateCheck = True):
		# strip out matching values?
		# find or create our cache dict
		newjson = self.to_json(device)

		if self.JSONDebug:
			self.logger.debug("currently in: diff_to_json for " + device.name)

		localcache = {}
		if device.name in list(self.cache.keys()):
			localcache = self.cache[device.name]

		diffjson = {}
		hasUpdate = False
		for kk, vv in newjson.items():

			# Check if it's changed
			if kk not in localcache or localcache[kk] != vv or not updateCheck:

				if updateCheck:
					try:
						if kk in localcache and isinstance(vv, str) and (str(localcache[kk]).encode('utf-8').lower() == str(vv).encode('utf-8').lower() or len(str(vv).encode('utf-8')) == 0):
							if self.TransportDebugL2:
								self.logger.debug('NOT sending property: ' + kk + " to InfluxDB for device: " + device.name + " because the value NOT has changed.  Prev value: " + str(localcache[kk]) + ", new value: " + str(vv))

							continue
					except:
						pass

				# either the key is in the include states, the entire device needs to be sent
				if (kk in includeStates) or len(includeStates) == 0:
					if not isinstance(vv, indigo.Dict) and not isinstance(vv, dict):
						diffjson[kk] = vv

						if self.TransportDebugL2:
							try:
								if kk in localcache:
									self.logger.debug('sending property: ' + kk + " to InfluxDB for device: " + device.name + " because the value has changed.  Prev value: " + str(localcache[kk]) + ", new value: " + str(vv))
								else:
									self.logger.debug('sending property: ' + kk + " to InfluxDB for device: " + device.name + " because the value has changed.  Prev value: <no previous value>, new value: " + str(vv))
							except:
								pass

						hasUpdate = True

		if not hasUpdate:
			if self.TransportDebugL2:
				self.logger.debug("no changed values found for device: " + device.name)

			return None
			
		if not device.name in list(self.cache.keys()):
			self.cache[device.name] = {}
		self.cache[device.name].update(newjson)

		# always make sure these survive
		diffjson['name'] = device.name
		diffjson['id'] = float(device.id)
		diffjson['measurement'] = newjson['measurement']

		if self.JSONDebug:
			self.logger.debug(json.dumps(newjson, default=indigo_json_serial).encode('utf-8'))
			self.logger.debug('diff:')
			self.logger.debug(json.dumps(diffjson, default=indigo_json_serial).encode('utf-8'))

		return diffjson

