"""
Pytest configuration: a fake `indigo` module, installed before any plugin import.

The plugin runs inside Indigo's embedded Python, where `indigo` is injected by the
host.  The fake covers the surface the plugin touches, and it is strict where the
real one is strict: indigo.Dict and indigo.List refuse values the real ones refuse
(a Python set, None, arbitrary objects) with the same TypeError.  A plain-dict
stand-in accepted a set, which is how the broken filter Edit (issue #12 item 1)
went unnoticed.
"""

import datetime
import logging
import os
import sys
import types

import pytest

PLUGIN_DIR = os.path.join(os.path.dirname(__file__), '..', 'Grafana Home Dashboard.indigoPlugin', 'Contents', 'Server Plugin')
sys.path.insert(0, os.path.abspath(PLUGIN_DIR))


def _rejected(value):
    return TypeError(
        "No registered converter was able to produce a C++ rvalue of type CCString "
        f"from this Python object of type {type(value).__name__}")


def _convert(value):
    """What storing a value in an indigo.Dict / indigo.List does: scalars pass,
    lists and dicts are copied into indigo containers, anything else is refused."""
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, FakeDict):
        return FakeDict(value)
    if isinstance(value, (list, tuple)):
        return FakeList(value)
    if isinstance(value, dict):
        return FakeDict(value)
    raise _rejected(value)


class FakeList(list):
    def __init__(self, items=()):
        super().__init__(_convert(item) for item in items)

    def append(self, item):
        super().append(_convert(item))

    def extend(self, items):
        super().extend(_convert(item) for item in items)

    def insert(self, index, item):
        super().insert(index, _convert(item))

    def __setitem__(self, index, item):
        super().__setitem__(index, _convert(item))


class FakeDict(dict):
    def __init__(self, items=None):
        super().__init__()
        for key, value in dict(items or {}).items():
            self[key] = value

    def __setitem__(self, key, value):
        super().__setitem__(str(key), _convert(value))

    def update(self, other=(), **kwargs):
        for key, value in dict(other, **kwargs).items():
            self[key] = value

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]


class FakeDeviceList(dict):
    """indigo.devices / indigo.variables: a dict keyed by id that iterates over
    its objects; like the real lists, membership and lookup also accept names."""

    def __init__(self):
        super().__init__()
        self.folders = {}

    def __iter__(self):
        return iter(list(self.values()))

    def __contains__(self, key):
        return super().__contains__(key) or any(getattr(obj, 'name', None) == key for obj in self.values())

    def __getitem__(self, key):
        if super().__contains__(key):
            return super().__getitem__(key)
        for obj in self.values():
            if getattr(obj, 'name', None) == key:
                return obj
        raise KeyError(key)

    def add(self, obj):
        super().__setitem__(obj.id, obj)
        return obj

    def subscribeToChanges(self):
        pass


class FakeDevice:
    _next_id = 1000

    def __init__(self, name, dev_id=None, states=None, model="Test Model", folderId=0,
                 lastChanged=None, lastSuccessfulComm=None, deviceTypeId="", pluginId="", **attrs):
        if dev_id is None:
            FakeDevice._next_id += 1
            dev_id = FakeDevice._next_id
        self.id = dev_id
        self.name = name
        self.states = dict(states or {})
        self.model = model
        self.subModel = ""
        self.deviceTypeId = deviceTypeId
        self.pluginId = pluginId
        self.folderId = folderId
        self.enabled = True
        self.configured = True
        now = datetime.datetime.now()
        self.lastChanged = lastChanged or now
        self.lastSuccessfulComm = lastSuccessfulComm or now
        for key, value in attrs.items():
            setattr(self, key, value)


class FakeVariable:
    _next_id = 5000

    def __init__(self, name, value, var_id=None):
        if var_id is None:
            FakeVariable._next_id += 1
            var_id = FakeVariable._next_id
        self.id = var_id
        self.name = name
        self.value = value


class FakeServer:
    def __init__(self):
        self.root = None
        self.saved_prefs = 0
        self.broadcasts = []
        self.logged = []

    def getInstallFolderPath(self):
        return self.root

    def getLogsFolderPath(self, plugin_id=None):
        path = os.path.join(self.root, 'Logs')
        return os.path.join(path, plugin_id) if plugin_id else path

    def savePluginPrefs(self):
        self.saved_prefs += 1

    def broadcastToSubscribers(self, key, value=None):
        self.broadcasts.append((key, value))

    def log(self, message, isError=False):
        self.logged.append(message)


class FakePluginBase:
    class StopThread(Exception):
        pass

    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        self.pluginId = pluginId
        self.pluginDisplayName = pluginDisplayName
        self.pluginVersion = pluginVersion
        self.pluginPrefs = pluginPrefs if isinstance(pluginPrefs, FakeDict) else FakeDict(pluginPrefs)
        self.logger = logging.getLogger("Plugin")
        self.debug = False

    def deviceUpdated(self, origDev, newDev):
        pass

    def variableUpdated(self, origVar, newVar):
        pass

    def deviceDeleted(self, dev):
        pass

    def sleep(self, seconds):
        raise self.StopThread()

    def getPrefsConfigUiValues(self):
        return (self.pluginPrefs, FakeDict())


def _build_indigo():
    indigo = types.ModuleType('indigo')
    indigo.Dict = FakeDict
    indigo.List = FakeList
    indigo.PluginBase = FakePluginBase
    indigo.devices = FakeDeviceList()
    indigo.variables = FakeDeviceList()
    indigo.server = FakeServer()
    indigo.completion_handlers = []

    def acquireCallbackCompleteHandler():
        handler = types.SimpleNamespace(result=None, exception=None)
        handler.returnResult = lambda result: setattr(handler, 'result', result)
        handler.returnException = lambda exc: setattr(handler, 'exception', exc)
        indigo.completion_handlers.append(handler)
        return handler

    indigo.acquireCallbackCompleteHandler = acquireCallbackCompleteHandler
    return indigo


INDIGO = _build_indigo()
sys.modules['indigo'] = INDIGO


@pytest.fixture
def indigo(tmp_path):
    """The fake indigo module, emptied for each test."""
    INDIGO.devices = FakeDeviceList()
    INDIGO.variables = FakeDeviceList()
    INDIGO.server = FakeServer()
    INDIGO.server.root = str(tmp_path / 'indigo')
    INDIGO.completion_handlers = []
    os.makedirs(INDIGO.server.root, exist_ok=True)
    return INDIGO


# Prefs as production stores them (string retention / frequency, int device ids)
BASE_PREFS = {
    'InfluxHost': 'influx.example.com',
    'InfluxSSL': False,
    'InfluxHTTPPort': '8086',
    'InfluxUser': 'indigo',
    'InfluxPassword': 's3cret-token-value',
    'InfluxDB': 'indigo',
    'InfluxRetention': '24',
    'InfluxVersion': '1',
    'MinimumUpdateFrequency': '15',
    'ServerDebug': False,
    'ConfigDebug': False,
    'TransportDebug': False,
    'TransportDebugL2': False,
    'JSONDebug': False,
    'listIncStates': ['sensorValue', 'onState', 'coolSetpoint', 'heatSetpoint'],
    'listIncDevices': [],
    'listExclDevices': [],
    'listFilterList': [],
    'preferencesFilterVersion': '2.0.0',
}


@pytest.fixture
def make_plugin(indigo, monkeypatch):
    """Build a Plugin with the given prefs.  startup() runs for real unless
    start=False; the writer thread it starts is stopped after the test."""
    import plugin as plugin_module

    created = []

    def factory(prefs=None, start=True, **overrides):
        values = dict(BASE_PREFS)
        if prefs is not None:
            values.update(prefs)
        values.update(overrides)
        plugin = plugin_module.Plugin('com.vtmikel.grafana', 'Grafana Home Dashboard', '2026.11.0', FakeDict(values))
        created.append(plugin)
        if start:
            plugin.startup()
        return plugin

    yield factory

    for plugin in created:
        plugin.writer_stop.set()
        if plugin.writer_thread is not None:
            plugin.writer_thread.join(timeout=5)
