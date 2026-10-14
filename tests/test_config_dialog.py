"""
The plugin config dialog: issue #12 items 7 (Cancel doesn't cancel), 9
(validatePrefsConfigUi), 13 (lock), and the low items about closedPrefsConfigUi.
"""

import threading

import pytest

from conftest import FakeDevice, FakeDict
from fake_influx import FakeInfluxClient


def dialog_values(plugin):
    values, errors = plugin.getPrefsConfigUiValues()
    return FakeDict(values)


@pytest.fixture
def devices(indigo):
    lamp = indigo.devices.add(FakeDevice("Living Room Lamp", states={'onOffState': True}))
    cooler = indigo.devices.add(FakeDevice("Dometic CFX5 Cooler", states={'coolSetpoint': 33.8}))
    return lamp, cooler


def test_cancel_discards_button_edits(make_plugin, devices, monkeypatch):
    """Item 7: the buttons changed the live lists, logging changed at once, and
    ValidateConfigLists saved them within 15 minutes even after Cancel."""
    lamp, cooler = devices
    plugin = make_plugin(listIncStates=['sensorValue', 'onState'], listIncDevices=[lamp.id])
    before = (list(plugin.StatesIncludeList), list(plugin.DeviceIncludeList))

    values = dialog_values(plugin)
    values['menuAvailableStates'] = 'coolSetpoint'
    plugin.AddStateToIncludedStateList(values)
    values['listIncStates'] = ['sensorValue']
    plugin.RemoveStateFromIncludedDeviceList(values)
    values['menuAvailableDevices'] = str(cooler.id)
    plugin.AddDeviceToIncludedDeviceList(values)
    values['listIncDevices'] = [str(lamp.id)]
    plugin.RemoveDeviceFromIncludedDeviceList(values)

    # the dialog shows the edits...
    assert [s for s, _ in plugin.IncludedStatesListGenerator()] == ['onState', 'coolSetpoint']
    assert [d for d, _ in plugin.IncludedDeviceListGenerator()] == [cooler.id]
    # ...but logging still uses the live lists
    assert (plugin.StatesIncludeList, plugin.DeviceIncludeList) == before

    plugin.closedPrefsConfigUi(values, True)
    plugin.ValidateConfigLists()

    assert (plugin.StatesIncludeList, plugin.DeviceIncludeList) == before
    assert list(plugin.pluginPrefs['listIncStates']) == before[0]
    assert list(plugin.pluginPrefs['listIncDevices']) == before[1]


def test_save_commits_button_edits(make_plugin, devices, monkeypatch):
    lamp, cooler = devices
    plugin = make_plugin(listIncStates=['sensorValue'], listIncDevices=[])
    monkeypatch.setattr(plugin, 'requestReconnect', lambda *a, **k: None)

    values = dialog_values(plugin)
    values['menuAvailableStates'] = 'coolSetpoint'
    plugin.AddStateToIncludedStateList(values)
    values['menuAvailableDevices'] = str(lamp.id)
    plugin.AddDeviceToIncludedDeviceList(values)
    values['listExclDevices'] = [str(cooler.id), str(lamp.id)]  # a device can't be both
    ok, values = plugin.validatePrefsConfigUi(values)[:2]
    assert ok
    plugin.closedPrefsConfigUi(values, False)

    assert plugin.StatesIncludeList == ['sensorValue', 'coolSetpoint']
    assert plugin.DeviceIncludeList == [lamp.id]
    assert plugin.DeviceExcludeList == [cooler.id]
    assert list(plugin.pluginPrefs['listIncStates']) == ['sensorValue', 'coolSetpoint']
    assert plugin.dialog is None


def test_dialog_values_are_a_copy_with_selections_cleared(make_plugin):
    plugin = make_plugin(listIncStates=['sensorValue', 'onState'])
    values = dialog_values(plugin)
    assert list(values['listIncStates']) == []  # nothing pre-selected for "remove selected"
    assert list(plugin.pluginPrefs['listIncStates']) == ['sensorValue', 'onState']
    values['InfluxHost'] = 'changed'
    assert plugin.pluginPrefs['InfluxHost'] == 'influx.example.com'


def test_saving_restores_plugin_owned_keys_from_live_state(make_plugin, monkeypatch):
    """Indigo stores the dialog's whole valuesDict, which still holds the filter
    list as it was when the dialog opened; a filter edited meanwhile (filters
    menu, or later an MCP tool) must survive the save."""
    plugin = make_plugin()
    monkeypatch.setattr(plugin, 'requestReconnect', lambda *a, **k: None)
    values = dialog_values(plugin)

    # filters edited while the plugin config dialog is open
    plugin.SaveFilterValues(FakeDict({
        'filterAction': 'add', 'filterName': '', 'filterOrder': '1', 'filterProperty': 'sensorValue',
        'filterStrategy': 'minMax', 'filterPropertyMinValue': '0', 'filterPropertyMaxValue': '100',
        'filterPropertyPercent': '', 'preventMinimumUpdates': True, 'filterAllDevices': True,
        'listDevices': [], 'logFailures': False, 'listFilters': [],
    }))
    assert len(plugin.FilterList) == 1

    # Indigo saves the stale valuesDict, then calls closedPrefsConfigUi
    for key, value in values.items():
        plugin.pluginPrefs[key] = value
    assert list(plugin.pluginPrefs['listFilterList']) == []
    plugin.closedPrefsConfigUi(values, False)

    assert len(plugin.pluginPrefs['listFilterList']) == 1


@pytest.mark.parametrize("field,value", [
    ('InfluxHTTPPort', ''), ('InfluxHTTPPort', 'abc'), ('InfluxHTTPPort', '0'), ('InfluxHTTPPort', '65536'),
    ('InfluxHost', ''), ('InfluxHost', 'https://influx.example.com'), ('InfluxHost', 'influx example'),
    ('InfluxVersion', '2'), ('InfluxDB', ' '), ('InfluxRetention', '7'), ('MinimumUpdateFrequency', '3'),
])
def test_validate_rejects_bad_settings(make_plugin, field, value):
    """Item 9: there was no validatePrefsConfigUi at all."""
    plugin = make_plugin()
    values = dialog_values(plugin)
    values[field] = value
    result = plugin.validatePrefsConfigUi(values)
    assert result[0] is False
    errors = result[2]
    assert field in errors
    assert errors['showAlertText']


def test_validate_normalizes_good_settings(make_plugin):
    plugin = make_plugin()
    values = dialog_values(plugin)
    values['InfluxHost'] = '  influx3.example.com '
    values['InfluxHTTPPort'] = ' 443 '
    ok, values = plugin.validatePrefsConfigUi(values)
    assert ok
    assert values['InfluxHost'] == 'influx3.example.com'
    assert values['InfluxHTTPPort'] == '443'


def test_closing_the_dialog_never_connects_on_the_callback_thread(make_plugin):
    """Low item: closedPrefsConfigUi called connect() on the main thread, up to
    ~15 s against an unreachable host."""
    plugin = make_plugin()
    callers = []
    done = threading.Event()

    def record(settings):
        callers.append(threading.current_thread())
        done.set()
        return FakeInfluxClient()

    plugin.newClient = record
    values = dialog_values(plugin)
    values['InfluxHost'] = 'other.example.com'
    plugin.closedPrefsConfigUi(plugin.validatePrefsConfigUi(values)[1], False)

    assert done.wait(5)
    assert callers and callers[0] is not threading.current_thread()


def test_unchanged_connection_settings_do_not_reconnect(make_plugin, monkeypatch):
    plugin = make_plugin()
    plugin.newClient = lambda settings: FakeInfluxClient()
    plugin.connect()
    calls = []
    monkeypatch.setattr(plugin, 'requestReconnect', lambda *a, **k: calls.append(a))
    values = dialog_values(plugin)
    plugin.closedPrefsConfigUi(plugin.validatePrefsConfigUi(values)[1], False)
    assert calls == []


def test_closing_after_a_failed_startup_does_not_crash(make_plugin, monkeypatch):
    """Low item: closedPrefsConfigUi used self.adaptor, None after a failed startup."""
    plugin = make_plugin()
    plugin.adaptor = None
    monkeypatch.setattr(plugin, 'requestReconnect', lambda *a, **k: None)
    values = dialog_values(plugin)
    values['TransportDebug'] = True
    plugin.closedPrefsConfigUi(plugin.validatePrefsConfigUi(values)[1], False)
    assert plugin.TransportDebug is True


def test_list_rebuild_and_dialog_edits_share_a_lock(make_plugin, devices):
    """Item 13: BuildConfigurationLists / ValidateConfigLists ran on the concurrent
    thread with no lock while the dialog edited the same lists."""
    plugin = make_plugin()
    acquired = threading.Event()
    release = threading.Event()

    def hold():
        with plugin.configLock:
            acquired.set()
            release.wait(5)

    holder = threading.Thread(target=hold)
    holder.start()
    acquired.wait(5)
    finished = threading.Event()
    rebuild = threading.Thread(target=lambda: (plugin.ValidateConfigLists(), finished.set()))
    rebuild.start()
    assert not finished.wait(0.3)  # blocked behind the dialog's lock
    release.set()
    assert finished.wait(5)
    holder.join()
    rebuild.join()
