#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2018 Mike Lamoureux
# Modernized 2025 - InfluxDB client only (no bundled servers)

import indigo
import datetime
import time
import json
import copy
import os
from json_adaptor import JSONAdaptor
from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError

WAIT_POLLING_INTERVAL = 5 # used ocassionally to wait for a sequantal process to happen
FAST_POLLING_INTERVAL = 5
DEFAULT_POLLING_INTERVAL = 60  # number of seconds between each poll
LONG_POLLING_INTERVAL = 60 * 15
UPDATE_STATES_LIST = 15 # how frequently (in minutes) to update the state list
DEFAULT_UPDATE_FREQUENCY = 24 # frequency of update check, in hours
MAX_LOG_FILE_OUTPUT_LINES = 50
LOG_PRUNE_FREQUENCY = 24 # how frequently to prune the logs to the MAX_LOG_FILE_OUTPUT_LINES length

DEFAULT_STATES = ["state.onOffState", "onState", "onState.num", "model", "subModel", "deviceTypeId", "state.hvac_state", "energyCurLevel", "energyAccumTotal", "value.num", "sensorValue", "coolSetpoint", "heatSetpoint", "batteryLevel", "batteryLevel.num"]

class InfluxFilter(object):
	def __init__(self, state, filterStrategy, minValue, maxValue, maxPercent, allDevices, appliedDevices, lockMinimumUpdates, log):
		self.state = state
		self.filterStrategy = filterStrategy
		self.minValue = float(minValue)
		self.maxValue = float(maxValue)
		self.maxPercent = float(maxPercent)
		self.allDevices = allDevices
		self.appliedDevices = list(map(int, appliedDevices))
		self.lockMinimumUpdates = lockMinimumUpdates
		self.log = log

		if self.allDevices:
			self.appliesToString = "all devices"
		else:
			self.appliesToString = "specific devices"

		if self.allDevices:
			appliesto = "(all devices)"
		else:
			appliesto = "(specific devices)"

		if self.filterStrategy == "minMax":
			values = "min: " + str(self.minValue) + ", max: " + str(self.maxValue)
		else:
			values = "percent: " + str(self.maxPercent)

		self.name = self.state + " " + appliesto + " " + values

class Plugin(indigo.PluginBase):
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		indigo.devices.subscribeToChanges()
		indigo.variables.subscribeToChanges()
		self.connection = None
		self.adaptor = None
		self.configured = True

		self.ConnectionRetryCount = 0
		self.QuietConnectionError = False
		self.StopConnectionAttempts = False

		self.VariableLastUpdatedList = []
		self.DeviceLastUpdatedList = []

		self.FullStateList = []
		self.AllStatesUI = []
		self.AvailableStatesUI = []
		self.AvailableIncDevices = []
		self.AvailableExlDevices = []

		self.DeviceIncludeListUI = []
		self.DeviceListExcludeListUI = []

		self.folders = {}
		self.pollingInterval = DEFAULT_POLLING_INTERVAL
		self.connected = False
		self.FilterLogFileLoc = os.getcwd() + '/filter.log'

		self.LastConfigRefresh = datetime.datetime.now()

		self.lastUpdateCheck = None
		self.lastLogPrune = None

	def startup(self):
		try:
			self.InfluxHost = self.pluginPrefs.get('InfluxHost', 'localhost')
			self.InfluxSSL = self.pluginPrefs.get('InfluxSSL', False)
			self.InfluxHTTPPort = self.pluginPrefs.get('InfluxHTTPPort', '8086')
			self.InfluxUser = self.pluginPrefs.get('InfluxUser', 'indigo')
			self.InfluxPassword = self.pluginPrefs.get('InfluxPassword', 'indigo')
			self.InfluxDB = self.pluginPrefs.get('InfluxDB', 'indigo')
			self.InfluxRetention = self.pluginPrefs.get('InfluxRetention', 6)

			if self.pluginPrefs.get("MinimumUpdateFrequency", DEFAULT_POLLING_INTERVAL/60) == "smart":
				self.miniumumUpdateFrequency = "smart"
			else:
				self.miniumumUpdateFrequency = int(self.pluginPrefs.get("MinimumUpdateFrequency", DEFAULT_POLLING_INTERVAL/60))

			# Debug Preferences
			self.debug = self.pluginPrefs.get("ServerDebug", False)
			self.ConfigDebug = self.pluginPrefs.get("ConfigDebug", False)
			self.TransportDebug = self.pluginPrefs.get("TransportDebug", False)
			self.TransportDebugL2 = self.pluginPrefs.get("TransportDebugL2", False)
			self.JSONDebug = self.pluginPrefs.get("JSONDebug", False)

			self.StatesIncludeList = self.pluginPrefs.get("listIncStates", [])
			self.DeviceIncludeList = self.pluginPrefs.get("listIncDevices", [])
			self.DeviceExcludeList = self.pluginPrefs.get("listExclDevices", [])
			
			preferencesFilterList = self.pluginPrefs.get("listFilterList", [])
			preferencesFilterVersion = self.pluginPrefs.get("preferencesFilterVersion", "1.0.0")

			self.FilterList = []

			try:
				if preferencesFilterVersion == "2.0.0":
					for item in preferencesFilterList:
						newFilter = InfluxFilter(item[0], item[1], item[2], item[3], item[4], item[5], item[6], item[7], item[8])
						try:
							newFilter.name = item[9]
						except:
							pass

						self.FilterList.append(newFilter)

				elif preferencesFilterVersion == "1.0.0":
					self.logger.info("upgrading data filters")
					for item in preferencesFilterList:
						newFilter = InfluxFilter(item[0], item[1], item[2], item[3], item[4], item[5], item[6], True, item[7])
						self.FilterList.append(newFilter)
		
					self.SaveFiltersToPreferences()

			except:
				self.logger.error("there was an error loading/upgrading your filters.  Please check the filters configuration to correct.")
				pass

			# sets the default include states when the plugin has never been configured.
			if len(self.StatesIncludeList) == 0:
				self.configured = False
				self.StatesIncludeList = DEFAULT_STATES[:]

			self.adaptor = JSONAdaptor(self.logger, self.TransportDebug, self.TransportDebugL2, self.JSONDebug)

		except Exception as e:
			self.logger.debug("error on startup: " + str(e))
			self.logger.error("missing proper configuration to start up.")
			self.configured = False
			pass

		if self.configured:
			self.connect()

		self.BuildConfigurationLists()
		self.UpdateAll()

		self.pruneFilterBlocksEventLog()

	# called after runConcurrentThread() exits
	def shutdown(self):
		if self.connection:
			self.connection.close()
		self.connected = False

	def connect(self):
		self.logger.debug("running connect()")

		if self.StopConnectionAttempts:
			self.logger.debug("   haulting connect(); StopConnectionAttempts = true")			
			return

		if not self.configured:
			self.logger.debug("   haulting connect(); configured = false")
			return

		if not self.QuietConnectionError or self.debug:
			self.logger.info("connecting to InfluxDB... " + self.InfluxHost + ":" + self.InfluxHTTPPort + " using user account: " + self.InfluxUser)

		self.connected = False

		self.connection = InfluxDBClient(
			host=self.InfluxHost,
			port=int(self.InfluxHTTPPort),
			username=self.InfluxUser,
			password=self.InfluxPassword,
			database=self.InfluxDB,
			ssl=self.InfluxSSL,
			verify_ssl=self.InfluxSSL,
			timeout=5
			)

		try:
			self.connection.create_database(self.InfluxDB)
			self.connection.switch_database(self.InfluxDB)

			if self.InfluxRetention == -1:
				retain = "INF"
			else:
				retain = str(int(self.InfluxRetention) * 30) + "d"

			self.logger.debug("    setting Influx retention policy of: " + retain)

			try:
				self.connection.create_retention_policy('indigo_policy', retain, '1')
			except Exception as e:
				self.logger.debug("    error while setting the retention policy: " + str(e))

			if self.ExternalDB or self.debug or self.QuietConnectionError:
				self.logger.info("######## connected to InfluxDB successfully... plugin will now resume logging data to InfluxDB ########")

			self.ConnectionRetryCount = 0
			self.connected = True
			self.QuietConnectionError = False
			self.pollingInterval = DEFAULT_POLLING_INTERVAL
		
		except Exception as e:
			self.ConnectionRetryCount = self.ConnectionRetryCount + 1
			self.connected = False

			self.logger.debug("   connection attempt " + str(self.ConnectionRetryCount) + ": error while connecting to InfluxDB: " + str(e))

			# Check for authorization failures
			if "authorization failed" in str(e).lower():
				if not self.QuietConnectionError:
					self.logger.error("    error while connecting to InfluxDB: authorization failed. Please check your credentials.")
				self.StopConnectionAttempts = True
				self.QuietConnectionError = True
			elif not self.QuietConnectionError:
				self.logger.error("error while connecting to InfluxDB, will continue to try silently in the background.")
				self.QuietConnectionError = True
			elif self.ConnectionRetryCount > 10:
				self.pollingInterval = LONG_POLLING_INTERVAL
				self.logger.error("error while connecting to InfluxDB after " + str(self.ConnectionRetryCount) + " attempts, will now attempt silently every 15 minutes.  Most recent connection error: " + str(e))

		self.logger.debug("completed connect()")

	# send this a dict of what to write
	def SendToInflux(self, tags, what, measurement='device_changes'):
		if not self.connected:
			return

		json_body=[
			{
				'measurement': measurement,
				'tags' : tags,
				'fields':  what
			}
		]

		# don't like my types? ok, fine, what DO you want?
		retrylimit = 30
		unsent = True
		while unsent and retrylimit > 0:
			retrylimit -= 1
			try:
				self.connection.write_points(json_body)
				unsent = False
				self.QuietConnectionError = False
			except InfluxDBClientError as e:
				self.logger.debug("Influx client error: " + str(e))

				try:
					field = json.loads(e.content)['error'].split('"')[1]
					#measurement = json.loads(e.content)['error'].split('"')[3]
					retry = json.loads(e.content)['error'].split('"')[4].split()[7]
					if retry == 'integer':
						retry = 'int'
					if retry == 'string':
						retry = 'str'
					# float is already float
					# now we know to try to force this field to this type forever more
					self.adaptor.typecache[field] = retry

					newcode = '%s("%s")' % (retry, str(json_body[0]['fields'][field]))
					#self.logger.info(newcode)
					json_body[0]['fields'][field] = eval(newcode)
				except:
					pass
			except ValueError:
				self.logger.debug("unable to force a field to the type in Influx - a partial record was still written")
			except Exception as e:
				self.connected = False
				if not self.QuietConnectionError:
					self.logger.error("error while trying to write to InfluxDB... please wait a moment, will work silently to correct in the background")
					self.QuietConnectionError = True
					self.logger.debug(str(e))


	def runConcurrentThread(self):
		self.logger.debug("fully initiatlized and ready.  starting concurrent tread...")
		self.sleep(int(self.pollingInterval))

		try:
			while True:
				try:
					if not self.connected:
						self.connect()

					if self.connected:
						self.UpdateAll()

					# prune the logs
					if self.lastLogPrune and self.lastLogPrune < datetime.datetime.now()-datetime.timedelta(hours=LOG_PRUNE_FREQUENCY):
						self.pruneFilterBlocksEventLog()

				except Exception as e:
					if self.debug:
						self.logger.error("Error in thread: " + str(e))

					if not self.connected:
						self.connect()
					pass

				self.sleep(int(self.pollingInterval))

		except self.StopThread:
			self.logger.debug("Received StopThread")
			if self.connection:
				self.connection.close()
			self.connected = False

	def UpdateAll(self):

		if not self.connected or self.adaptor is None:
			return

		self.logger.debug("running UpdateAll()")

		for dev in indigo.devices:
			needsUpdating = False
			found = False

			if self.TransportDebugL2:
				self.logger.debug("    reviewing " + dev.name)

			# if the device is excluded, do nothing
			if dev.id in self.DeviceExcludeList:
				if self.TransportDebugL2:
					self.logger.debug("    device was excluded from InfluxDB update: " + dev.name)
				continue

			for devSearch in self.DeviceLastUpdatedList:
				if devSearch[0] == dev.id:
					found = True
					locked = devSearch[2]

					if self.miniumumUpdateFrequency == "smart" and ((datetime.datetime.now().hour == 0 and datetime.datetime.now().minute < 15) or (datetime.datetime.now().hour == 23 and datetime.datetime.now().minute > 45)) and devSearch[1] + datetime.timedelta(minutes=5) < datetime.datetime.now() and not locked:
						if self.TransportDebug:
							self.logger.debug("    SMART minimum update period for device expired: " + dev.name + ", prior update timestamp: " + str(devSearch[1]))

						needsUpdating = True
						devSearch[1] = datetime.datetime.now()
					elif devSearch[1] + datetime.timedelta(minutes=self.miniumumUpdateFrequency) < datetime.datetime.now() and not locked:
						if self.TransportDebug:
							self.logger.debug("    minimum update period for device expired: " + dev.name + ", prior update timestamp: " + str(devSearch[1]))

						needsUpdating = True
						devSearch[1] = datetime.datetime.now()
					elif locked:
						if self.TransportDebug:
							self.logger.debug("    device " + dev.name + " was locked from being updated as it failed a device filter.")						

					break  # STOP THE search through the update list

			if not found:
				self.DeviceLastUpdatedList.append([dev.id, dev.lastChanged, False])

			if self.LastConfigRefresh + datetime.timedelta(minutes=UPDATE_STATES_LIST) < datetime.datetime.now():
				self.logger.debug("    triggering a refresh of the configuration lists")
				self.BuildConfigurationLists()

			if needsUpdating:
				self.DeviceToInflux(None, dev, False)
			elif self.TransportDebugL2 and not needsUpdating:
				self.logger.debug("    no update needed for device: " + dev.name)

		for var in indigo.variables:
			needsUpdating = False
			found = False

			for varSearch in self.VariableLastUpdatedList:
				if varSearch[0] == var.id:
					found = True

					if self.miniumumUpdateFrequency == "smart" and ((datetime.datetime.now().hour == 0 and datetime.datetime.now().minute < 15) or (datetime.datetime.now().hour == 23 and datetime.datetime.now().minute > 45)) and varSearch[1] + datetime.timedelta(minutes=5) < datetime.datetime.now():
						if self.TransportDebug:
							self.logger.debug("    SMART minimum update period for variable expired: " + var.name + ", prior update timestamp: " + str(varSearch[1]))

						needsUpdating = True
						varSearch[1] = datetime.datetime.now()
					
					elif varSearch[1] + datetime.timedelta(minutes=self.miniumumUpdateFrequency) < datetime.datetime.now():
						if self.TransportDebug:
							self.logger.debug("    minimum update period for variable expired: " + var.name + ", prior update timestamp: " + str(varSearch[1]))

						needsUpdating = True
						varSearch[1] = datetime.datetime.now()

					break

			if not found:
				self.VariableLastUpdatedList.append([var.id, datetime.datetime.now()])

			if needsUpdating:
				self.VariableToInflux(var)

		self.logger.debug("completed UpdateAll()")

	def deviceUpdated(self, origDev, newDev):
		# call base implementation
		indigo.PluginBase.deviceUpdated(self, origDev, newDev)

		if not self.connected:
			return

		# If the device is excluded, do nothing
		if newDev.id in self.DeviceExcludeList:
			if self.TransportDebugL2:
				self.logger.debug("   device was excluded from InfluxDB update: " + newDev.name)
			return

		device_was_updated = self.DeviceToInflux(origDev, newDev, True)

		if not device_was_updated:
			if self.JSONDebug:
				self.logger.debug("   an update for device " + origDev.name + " resulted in no properties updated...")
			return

		if self.TransportDebug:
			self.logger.debug("deviceUpdated(): an update for device " + origDev.name + " is being processed...")

		found = False
		for devSearch in self.DeviceLastUpdatedList:
			if devSearch[0] == origDev.name:
				locked = devSearch[2]
				found = True

				devSearch[1] = datetime.datetime.now()

				# unlock if locked since we rec'd an update
				if locked:
					devSearch[2] = False

				break

		if not found:
			self.DeviceLastUpdatedList.append([origDev.name, datetime.datetime.now(), False])

		if self.TransportDebug:
			self.logger.debug("completed deviceUpdated() for " + origDev.name)

	def DeviceToInflux(self, origDev, dev, updateCheck = True):
		# custom add to influx work
		# tag by folder if present
		tagnames = 'name folderId'.split()

		# if the device is excluded, do nothing
		if dev.id in self.DeviceExcludeList:
			if self.TransportDebug:
				self.logger.debug("device was excluded from InfluxDB update: " + dev.name)
			return False

		if dev.id in self.DeviceIncludeList:
			self.logger.debug("sending entire device to diff_to_json: " + dev.name)
			newjson = self.adaptor.diff_to_json(dev, [], updateCheck)
		else:
			newjson = self.adaptor.diff_to_json(dev, self.StatesIncludeList, updateCheck)

		if newjson is None:
			return False

		# Advanced data filtering processing section
		if len(self.FilterList) > 0:
			filterjson = copy.deepcopy(newjson)
			for kk, vv in filterjson.items():
				for influxFilterRecord in self.FilterList:
					passedFilter = True
					try:
						if (dev.id in influxFilterRecord.appliedDevices or influxFilterRecord.allDevices) and kk == influxFilterRecord.state:
							self.logger.debug(dev.name + "[" + kk + "]: looking at filter (" + influxFilterRecord.name + "): " + influxFilterRecord.state + " for " + influxFilterRecord.appliesToString + " with a range (" + str(influxFilterRecord.minValue) + ", " + str(influxFilterRecord.maxValue) + ")")
							if influxFilterRecord.filterStrategy == "minMax" and (influxFilterRecord.minValue <= float(vv) <= influxFilterRecord.maxValue):
								if self.TransportDebug:
									self.logger.debug("    Filter passed (" + influxFilterRecord.name + "): a value (" + str(vv) + ") for state/property '" + str(kk) + "' on device " + dev.name + "' was WITHIN the specified range (" + str(influxFilterRecord.minValue) + ", " + str(influxFilterRecord.maxValue) + ") and will be sent to InfluxDB")
							elif origDev is not None and influxFilterRecord.filterStrategy == "percentChanged":
								try:
									origValue = origDev.states[kk]
									percentValueChanged = ((origValue - vv) / origValue) * 100

									if abs(percentValueChanged) > influxFilterRecord.maxPercent:
										passedFilter = False

										# if the lock minimum updates is true, we need to mark the device as locked
										if influxFilterRecord.lockMinimumUpdates:
											found = False
											for devSearch in self.DeviceLastUpdatedList:
												if devSearch[0] == dev.id:
													devSearch[2] = True
													found = True
													break

											if not found:  # if we couldn't find it in the DeviceLastUpdated list, we add it, and lock it.
												self.DeviceLastUpdatedList.append([dev.id, datetime.datetime.now(), True])
												found = True

											if found and self.TransportDebug:
												self.logger.debug("    locked device " + dev.name + " from InfluxDB updates until a device change occurs.")

									else:
										if self.TransportDebug:
											self.logger.debug("    Filter passed (" + influxFilterRecord.name + "): a value (old value: " + str(origValue) + ", new value: " + str(vv) + ") for state/property '" + str(kk) + "' on device '" + dev.name + "' DID NOT exceeded percent changed (actual change: " + str(abs(percentValueChanged)) + ", threshhold: " + str(influxFilterRecord.maxPercent) + ") and will be sent to InfluxDB")									

								except Exception as e:
									passedFilter = True
									self.logger.debug("    error while trying to compute the percentage changed. Value will be sent on to InfluxDB.  Error: " + str(e))
							elif origDev is None and influxFilterRecord.filterStrategy == "percentChanged":
								self.logger.debug("    original device was not provided to compare, no ability to calcualte percentage changed")
							else: #minMax comes here if the values were not within range
								passedFilter = False

					except Exception as e:
						passedFilter = True
						self.logger.error("there was a error while trying to process filters, please check the debug logs or recreate your filters")
						self.logger.debug("   Key: " + str(kk))
						self.logger.debug("   Value: " + str(vv))
						self.logger.debug("   Device: " + str(dev.name))
						self.logger.debug("   Min: " + str(influxFilterRecord.minValue))
						self.logger.debug("   Max: " + str(influxFilterRecord.maxValue))
						self.logger.debug("   Error: " + str(e))

					if not passedFilter:
						if influxFilterRecord.filterStrategy == "minMax":
							logLine = "Filter block (" + influxFilterRecord.name + "): a value (" + str(vv) + ") for state/property '" + str(kk) + "' on device '" + dev.name + "' was not in the configured range (" + str(influxFilterRecord.minValue) + ", " + str(influxFilterRecord.maxValue) + ") and will not be sent to InfluxDB"
						else:
							logLine = "Filter block (" + influxFilterRecord.name + "): a value (previous value: " + str(origValue) + ", new value: " + str(vv) + ") for state/property '" + str(kk) + "' on device '" + dev.name + "' exceeded percent changed (percent changed: " + str(abs(percentValueChanged)) + "%, threshhold: " + str(influxFilterRecord.maxPercent) + "%) and will not be sent to InfluxDB"

						try:
							with open(self.FilterLogFileLoc, "a") as logFile:
								logFile.write(datetime.datetime.now().strftime('%Y-%m-%d %H:%M') + ": " + logLine + '\n')
						except Exception as e:
							self.logger.error("error writing to filter log.  Error: " + str(e))

						if influxFilterRecord.log:
							self.logger.info(logLine)
						else:
							self.logger.debug(logLine)

						del newjson[kk]
						break # stop processing filter rules.

		### END Advanced data filtering section

		newtags = {}
		for tag in tagnames:
			newtags[tag] = str(getattr(dev, tag))

		# add a folder name tag
		if hasattr(dev, 'folderId') and dev.folderId != 0:
			newtags['folder'] = indigo.devices.folders[dev.folderId].name

		measurement = newjson['measurement']
		del newjson['measurement']
		self.SendToInflux(tags=newtags, what=newjson, measurement=measurement)

		return True

	def variableUpdated(self, origVar, newVar):
		indigo.PluginBase.variableUpdated(self, origVar, newVar)

		if not self.connected:
			return

		## Log the timestamp for the variable update
		found = False
		for varSearch in self.VariableLastUpdatedList:
			if varSearch[0] == origVar.name:
				found = True

				varSearch[1] = datetime.datetime.now()
				break

		if not found:
			self.VariableLastUpdatedList.append([origVar.name, datetime.datetime.now()])

		self.VariableToInflux(newVar)

	def VariableToInflux(self, var):
		newtags = {'varname': var.name}
		newjson = {'name': var.name, 'value': var.value }
		numval = self.adaptor.smart_value(var.value, True)
		if numval != None:
			newjson['value.num'] = numval

		self.SendToInflux(tags=newtags, what=newjson, measurement='variable_changes')

################### PluginConfig functions. #####################################################

	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		if not userCancelled:
			ConnectionChanged = False

			self.debug = valuesDict["ServerDebug"]
			self.ConfigDebug = valuesDict["ConfigDebug"]
			self.TransportDebug = valuesDict["TransportDebug"]
			self.TransportDebugL2 = valuesDict["TransportDebugL2"]
			self.JSONDebug = valuesDict["JSONDebug"]

			self.adaptor.TransportDebug = self.TransportDebug
			self.adaptor.TransportDebugL2 = self.TransportDebugL2
			self.adaptor.JSONDebug = self.JSONDebug

			self.logger.debug("started processing closedPrefsConfigUi")

			# Check if connection settings changed
			if (self.InfluxHost != valuesDict['InfluxHost'] or
				self.InfluxSSL != valuesDict['InfluxSSL'] or
				self.InfluxHTTPPort != valuesDict['InfluxHTTPPort'] or
				self.InfluxUser != valuesDict['InfluxUser'] or
				self.InfluxPassword != valuesDict['InfluxPassword'] or
				self.InfluxDB != valuesDict['InfluxDB'] or
				not self.configured):
				ConnectionChanged = True

			# Update connection settings
			self.InfluxHost = valuesDict['InfluxHost']
			self.InfluxSSL = valuesDict['InfluxSSL']
			self.InfluxHTTPPort = valuesDict['InfluxHTTPPort']
			self.InfluxUser = valuesDict['InfluxUser']
			self.InfluxPassword = valuesDict['InfluxPassword']
			self.InfluxDB = valuesDict['InfluxDB']

			# Update retention policy if changed
			if self.InfluxRetention != valuesDict.get('InfluxRetention', 6):
				self.InfluxRetention = valuesDict.get('InfluxRetention', 6)
				ConnectionChanged = True

			self.configured = True

			# Reconnect if settings changed
			if ConnectionChanged:
				self.logger.info("InfluxDB connection settings changed, reconnecting...")
				self.StopConnectionAttempts = False
				self.QuietConnectionError = False
				self.connect()

			# Update minimum update frequency
			if valuesDict["MinimumUpdateFrequency"] == "smart":
				self.miniumumUpdateFrequency = "smart"
			else:
				self.miniumumUpdateFrequency = int(valuesDict["MinimumUpdateFrequency"])

			# Update device exclude list
			self.DeviceExcludeList = []
			for dev in valuesDict["listExclDevices"]:
				self.DeviceExcludeList.append(int(dev))

			# Save preferences
			self.pluginPrefs["listIncStates"] = self.StatesIncludeList
			self.pluginPrefs["listIncDevices"] = self.DeviceIncludeList
			self.pluginPrefs["listExclDevices"] = self.DeviceExcludeList

		self.logger.debug("completed processing closedPrefsConfigUi")

	def ValidateConfigLists(self):
		self.logger.debug("running ValidateConfigLists()")

		newDeviceIncludeList = []
		for item in self.DeviceIncludeList:
			try:
				if isinstance(item, str):
					dev_id = int(item)
				else:
					dev_id = item

				if dev_id in indigo.devices and dev_id not in newDeviceIncludeList:
					if self.ConfigDebug:
						self.logger.debug("   validated included device: " + indigo.devices[dev_id].name)
					newDeviceIncludeList.append(dev_id)
				else:
					self.logger.info("removed a no longer present device from include device list: " + str(item))
			except Exception as e:
				indigo.server.debug("removed a invalid device from the included device list, because of error: " + str(e))
				continue

		self.DeviceIncludeList = newDeviceIncludeList

		newStatesIncludeList = []
		for item in self.StatesIncludeList:
			try:
				if len(item) > 0:
					# Find if the state exists in the full state list
					try:
						index = -1
						index = [y[0] for y in self.FullStateList].index(item)
					except:
						index = -1

					if index != -1:
						if self.ConfigDebug:
							self.logger.debug("   validated included state: " + item)
						newStatesIncludeList.append(item)
					else:
						self.logger.info("removed a no longer present state from the state include list: " + str(item))
				else:
					self.logger.debug("   REMOVED a empty state??!")
			except Exception as e:
				self.logger.debug("removed a invalid state from the included state list, because of error: " + str(e))
				continue

		self.StatesIncludeList = newStatesIncludeList

		newDeviceExcludeList = []
		for item in self.DeviceExcludeList:
			try:
				if isinstance(item, str):
					dev_id = int(item)
				else:
					dev_id = item

				if dev_id in indigo.devices:
					if self.ConfigDebug:
						self.logger.debug("   validated excluded device: " + indigo.devices[dev_id].name)
					newDeviceExcludeList.append(dev_id)
				else:
					self.logger.info("removed a no longer present device from exclude device list: " + str(item))

			except Exception as e:
				self.logger.debug("removed a invalid device from the excluded device list, because of error: " + str(e))
				continue

		self.DeviceExcludeList = newDeviceExcludeList

		if self.ConfigDebug:
			self.logger.debug("   saving the IncStates, IncDevices, ExclDevices lists to plugin preferences...")
	
		self.pluginPrefs["listIncStates"] = self.StatesIncludeList
		self.pluginPrefs["listIncDevices"] = self.DeviceIncludeList
		self.pluginPrefs["listExclDevices"] = self.DeviceExcludeList

		self.logger.debug("completed ValidateConfigLists()")

	def BuildConfigurationLists(self):
		self.logger.debug("starting BuildConfigurationLists()")

		self.LastConfigRefresh = datetime.datetime.now()

		self.FullStateList = []
		self.AvailableIncDevices = []
		self.AvailableExlDevices = []

		for dev in indigo.devices:
			### STATES List
			for kk, vv in self.adaptor.to_json(dev).items():
				try:
					index = -1
					index = [y[0] for y in self.FullStateList].index(kk)
				except:
					index = -1

				if index == -1:
					self.FullStateList.append((kk, 1))
				else:
					count = int(self.FullStateList[index][1]) + 1
					self.FullStateList[index] = (kk, count)

			### Included and Excluded Devices Available to assign list
			if dev.id not in self.DeviceIncludeList and dev.id not in self.DeviceExcludeList:
				self.AvailableIncDevices.append((dev.id, dev.name.replace(",", " ").replace(";", " ")))
			
			### Excluded Devices Available		
			if dev.id not in self.DeviceIncludeList:
				self.AvailableExlDevices.append((dev.id, dev.name.replace(",", " ").replace(";", " ")))

		########################

		# This makes sure that all the devices states exist before we build the UI for the plugin config
		self.ValidateConfigLists()

		# BUILD UI LISTS  -- STATES
		self.AvailableStatesUI = []

		for ui in sorted(self.FullStateList, key=lambda tup: tup[0]):
			if not ui[0] in self.StatesIncludeList and len(ui[0].strip()) > 0:
				self.AvailableStatesUI.append((ui[0], ui[0] + " (" + str(ui[1]) + ")"))
			self.AllStatesUI.append((ui[0], ui[0] + " (" + str(ui[1]) + ")"))

		# BUILD UI LISTS  -- INCLUDE
		self.DeviceIncludeListUI = []

		for item in self.DeviceIncludeList:
			try:
				self.DeviceIncludeListUI.append((int(item), indigo.devices[int(item)].name.replace(",", " ").replace(";", " ")))
			except:
				self.logger.error("could not find device " + item + " to add to the InfluxDB device list")
				pass

		# BUILD UI LISTS  -- EXCLUDE
		self.DeviceListExcludeListUI = []

		for item in self.DeviceExcludeList:
			try:
				self.DeviceListExcludeListUI.append((item, indigo.devices[int(item)].name.replace(",", " ").replace(";", " ")))
			except:
				self.logger.error("could not find device " + item + " to add to the InfluxDB exclude device list")
				pass

		self.logger.debug("completed BuildConfigurationLists()")

	def IncludedStatesListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		if self.ConfigDebug:
			self.logger.debug("IncludedStatesListGenerator()")
			self.logger.debug("self.StatesIncludeList: " + str(self.StatesIncludeList))

		toReturn = []

		for item in self.StatesIncludeList:
			if len(item.strip()) > 0:
				toReturn.append((item, item))

		return toReturn

	def IncludedFiltersListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		FilterListUI = []
		for filterItem in self.FilterList:
			FilterListUI.append((len(FilterListUI), str(len(FilterListUI) + 1) + ": " + filterItem.name))

		return FilterListUI

	def IncludedDeviceListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		if self.ConfigDebug:
			self.logger.debug("IncludedDeviceListGenerator()")
			self.logger.debug("self.DeviceIncludeListUI: " + str(self.DeviceIncludeListUI))

		return self.DeviceIncludeListUI

	def ExcludedDeviceListGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		if self.ConfigDebug:
			self.logger.debug("ExcludedDeviceListGenerator()")
			self.logger.debug("self.AvailableExlDevices: " + str(self.AvailableExlDevices))

		return self.AvailableExlDevices

######
	def AvailableStatesGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		if self.ConfigDebug:
			self.logger.debug("AvailableStatesGenerator()")
			self.logger.debug("self.AvailableStatesUI: " + str(self.AvailableStatesUI))

		return self.AvailableStatesUI

	def AvailableDevicesGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		if self.ConfigDebug:
			self.logger.debug("AvailableDevicesGenerator()")
			self.logger.debug("self.AvailableIncDevices: " + str(self.AvailableIncDevices))

		return self.AvailableIncDevices

	def AllStatesGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
		if self.ConfigDebug:
			self.logger.debug("AllStatesGenerator()")
			self.logger.debug("self.AllStatesUI: " + str(self.AllStatesUI))

		return self.AllStatesUI

######
	def AddDeviceToIncludedDeviceList(self, valuesDict, typeId="", devId=0):
		self.DeviceIncludeList.append(int(valuesDict["menuAvailableDevices"]))
		self.DeviceIncludeListUI.append((int(valuesDict["menuAvailableDevices"]), indigo.devices[int(valuesDict["menuAvailableDevices"])].name.replace(",", " ").replace(";", " ")))

		for item in self.AvailableIncDevices:
			if item[0] == int(valuesDict["menuAvailableDevices"]):
				self.AvailableIncDevices.remove(item)

		for item in self.AvailableExlDevices:
			if item[0] == int(valuesDict["menuAvailableDevices"]):
				self.AvailableExlDevices.remove(item)

		return valuesDict

	def RemoveDeviceFromIncludedDeviceList(self, valuesDict, typeId="", devId=0):
		for dev in valuesDict["listIncDevices"]:
			indigodev = indigo.devices[int(dev)]

			try:
				self.DeviceIncludeList.remove(indigodev.id)
			except:
				self.logger.error("error while removing device from the inclusion list")

			self.DeviceIncludeListUI = [item for item in self.DeviceIncludeListUI if item[0] != indigodev.id]

			self.AvailableIncDevices.append((indigodev.id, indigodev.name.replace(",", " ").replace(";", " ")))
			self.AvailableExlDevices.append((indigodev.id, indigodev.name.replace(",", " ").replace(";", " ")))

		return valuesDict


	def AddStateToIncludedStateList(self, valuesDict, typeId="", devId=0):
		self.StatesIncludeList.append(valuesDict["menuAvailableStates"])

		for item in self.AvailableStatesUI:
			if item[0] == valuesDict["menuAvailableStates"]:
				self.AvailableStatesUI.remove(item)

		return valuesDict

	def RemoveStateFromIncludedDeviceList(self, valuesDict, typeId=0, devId=0):
		for state in valuesDict["listIncStates"]:
			if self.ConfigDebug:
				self.logger.debug("removing: " + str(state))

			try:
				self.StatesIncludeList.remove(state)
			except:
				self.logger.error("error while removing state from inclusion list")

			for ui in sorted(self.FullStateList, key=lambda tup: tup[0]):
				if ui[0] == state:
					self.AvailableStatesUI.append((ui[0], ui[0] + " (" + str(ui[1]) + ")"))

		return valuesDict

	def ResetStatesIncludedStateList(self, valuesDict, typeId="", devId=0):
		if self.ConfigDebug:
			self.logger.debug("resetting to default states")

		self.StatesIncludeList = DEFAULT_STATES[:]

		self.AvailableStatesUI = []		
		for ui in sorted(self.FullStateList, key=lambda tup: tup[0]):
			if not ui[0] in self.StatesIncludeList:
				self.AvailableStatesUI.append((ui[0], ui[0] + " (" + str(ui[1]) + ")"))

		return valuesDict

### Other menu items

	def PrintDeviceToEventLog(self, valuesDict, typeId=0, devId=0):
		dev = indigo.devices[int(valuesDict["menuDevice"])]
		excluded = False
		included = False

		if dev.id in self.DeviceExcludeList:
			self.logger.info("NOTE: Device \"" + dev.name + "\" is EXCLUDED in your config and therefore all states are sent to InfluxDB")
			excluded = True

		self.logger.info("JSON representation of device " + dev.name + ":")

		if dev.id in self.DeviceIncludeList and not excluded:
			included = True
			self.logger.info("NOTE: Device \"" + dev.name + "\" is INCLUDED in your config and therefore all states are sent to InfluxDB")
			self.logger.debug("PrintDeviceToEventLog(): sending entire device to diff_to_json for device: " + dev.name)
			newjson = self.adaptor.diff_to_json(dev, [], False)
		else:
			newjson = self.adaptor.diff_to_json(dev, [], False)

		if newjson is None:
			self.logger.info("   the device: \"" + dev.name + "\" is not excluded from updates to InfluxDB, but it contains no states/properties that are capable of being sent to Influx/Grafana.")			

		else:
			for kk, vv in sorted(newjson.items()):
				if not isinstance(vv, indigo.Dict) and not isinstance(vv, dict):
					if (kk in self.StatesIncludeList or included) and not excluded:
						status = " (INCLUDED)"
					elif excluded:
						status = " (EXCLUDED)"
					else:
						status = " (NOT INCLUDED)"

					# Value conversion
					value = None

					if isinstance(vv, str):
						value = vv
					elif isinstance(vv, str):
						value = vv.encode('utf-8')
					else:
						value = str(vv)

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
						if kk in self.StatesIncludeList and not excluded:
							status = " (INCLUDED)"
						elif excluded:
							status = " (EXCLUDED)"
						else:
							status = " (NOT INCLUDED)"

						# Value conversion
						value = None

						if isinstance(vv, str):
							value = vv
						elif isinstance(vv, str):
							value = vv.encode('utf-8')
						else:
							value = str(vv)

						self.logger.info("   " + str(counter) + ". " + dev.name + " ;  " + str(kk) + ": " + value + status)
						counter = counter + 1

		return valuesDict

	def resetDataFilters(self):
		self.logger.info("resetting data filters")
		self.FilterList = []
		self.SaveFiltersToPreferences()

	def ForceUpdate(self):
		self.UpdateAll()

	def rebuildConfig(self):
		self.BuildConfigurationLists()

	def printFilterBlocksEventLog(self):
		try:
			self.logger.info("Listing filter block log records (oldest to newest, maximum of " + str(MAX_LOG_FILE_OUTPUT_LINES) + " records):")
			log_file = open(self.FilterLogFileLoc, "r")
			lines = self.tail(log_file, MAX_LOG_FILE_OUTPUT_LINES)[0]
			log_file.close()

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

		try:
			log_file = open(self.FilterLogFileLoc, "r")
			lines = self.tail(log_file, MAX_LOG_FILE_OUTPUT_LINES)[0]
			log_file.close()

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
				editItem = self.FilterList[int(valuesDict["listFilters"][0])]
				valuesDict["filterName"] = editItem.name
				valuesDict["filterProperty"] = editItem.state
				valuesDict["editFilterProperty"] = editItem.state
				valuesDict["filterOrder"] = int(valuesDict["listFilters"][0]) + 1
				
				valuesDict["filterStrategy"] = editItem.filterStrategy
				valuesDict["filterPropertyMinValue"] = editItem.minValue
				valuesDict["filterPropertyMaxValue"] = editItem.maxValue
				valuesDict["filterPropertyPercent"] = editItem.maxPercent
				valuesDict["preventMinimumUpdates"] = editItem.lockMinimumUpdates

				valuesDict["filterAllDevices"] = editItem.allDevices				
				valuesDict["listDevices"] = editItem.appliedDevices
				valuesDict["logFailures"] = editItem.log

				valuesDict["editMode"] = True
				valuesDict["lockActionChange"] = True
				valuesDict["percentVisible"] = editItem.filterStrategy == "percentChanged"
				valuesDict["preventMinimumUpdates"] = editItem.filterStrategy == "percentChanged"
				valuesDict["deviceListVisible"] = not editItem.allDevices

			except Exception as e:
				self.logger.debug("error editing the filter: " + str(e))
				pass

		elif valuesDict["filterAction"] == "delete":
			listToDelete = []
			for i in valuesDict["listFilters"]:
				listToDelete.append(i)

			listToDelete.sort(reverse=True)
	
			for i in listToDelete:
				del self.FilterList[int(i)]

			self.SaveFiltersToPreferences()

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

	def filterAllDevicesChanged(self, valuesDict, typeId=0, devId=0):
		valuesDict["deviceListVisible"] = not valuesDict["filterAllDevices"]  and (valuesDict["filterAction"] == "edit" or valuesDict["filterAction"] == "add")

		return valuesDict

	def SaveFiltersToPreferences(self):
		toSave = []

		for influxFilterRecord in self.FilterList:
			toSave.append([influxFilterRecord.state, influxFilterRecord.filterStrategy, influxFilterRecord.minValue, influxFilterRecord.maxValue, influxFilterRecord.maxPercent, influxFilterRecord.allDevices, influxFilterRecord.appliedDevices, influxFilterRecord.lockMinimumUpdates, influxFilterRecord.log, influxFilterRecord.name])

		self.pluginPrefs["listFilterList"] = toSave
		self.pluginPrefs["preferencesFilterVersion"] = "2.0.0"

	def SaveFilterValues(self, valuesDict, typeId=0, devId=0):
		if valuesDict["filterProperty"] is None:
			self.logger.error("Select a valid property/state")
			return valuesDict

		if valuesDict["filterOrder"] is None:
			self.logger.error("Select an 'insert at' value")
			return valuesDict

		try:
			filterName = valuesDict["filterName"]
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

			filterAllDevices = valuesDict["filterAllDevices"]
			filterDevices = []
	
			if not filterAllDevices:
				filterDevices = valuesDict["listDevices"]
	
			log = valuesDict["logFailures"]
		except ValueError:
			self.logger.error("Ensure that filter max and min values must be numeric")
			return valuesDict
		except:
			self.logger.error("Error validating the form.  Ensure that filter max and min values must be numeric, and all fields are filled in.")
			return valuesDict

		if filterStrategy == "minMax" and filterPropertyMinValue >= filterPropertyMaxValue:
			self.logger.error("minimum value must be smaller than the maximum value.")
			return valuesDict

		if len(filterDevices) == 0 and not filterAllDevices:
			self.logger.error("the filter must be applied to one or more devices.")
			return valuesDict

		if filterOrder > len(self.FilterList):
			filterOrder = len(self.FilterList)

		if valuesDict["filterAction"] == "edit":
			self.logger.debug("deleting index " + valuesDict["listFilters"][0])
			del self.FilterList[int(valuesDict["listFilters"][0])]

		self.logger.debug("added the filter property for state " + filterProperty + " (" + str(filterPropertyMinValue) + ", " + str(filterPropertyMaxValue) + "), applies to: ")

		if filterAllDevices:
			self.logger.debug("   ALL devices")
		else:
			self.logger.debug(filterDevices)

		newFilter = InfluxFilter(filterProperty.strip(), filterStrategy, filterPropertyMinValue, filterPropertyMaxValue, filterPropertyPercent, filterAllDevices, filterDevices, lockMinimumUpdates, log)

		if len(filterName) > 0:
			newFilter.name = filterName

		try:
			self.FilterList.insert(filterOrder - 1, newFilter)
		except Exception as e:
			self.logger.error("error while trying to insert into filters list, appending to the end of the list instead.  Order of filters may be incorrect.")
			self.logger.debug(" Error: " + str(e))
			self.FilterList.append(newFilter)

		self.SaveFiltersToPreferences()

		valuesDict["filterName"] = ""
		valuesDict["filterOrder"] = ""
		valuesDict["filterProperty"] = ""
		valuesDict["filterStrategy"] = "minMax"
		valuesDict["filterPropertyMinValue"] = ""
		valuesDict["filterPropertyMaxValue"] = ""
		valuesDict["filterPropertyPercent"] = ""
		valuesDict["preventMinimumUpdates"] = True
		valuesDict["filterAllDevices"] = True
		valuesDict["listDevices"] = []
		valuesDict["logFailures"] = True
		valuesDict["lockActionChange"] = False

		valuesDict["editMode"] = valuesDict["filterAction"] == "add"

		return valuesDict