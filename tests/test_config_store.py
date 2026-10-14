"""
ConfigStore (issue #11): one owner for every configuration change - revision,
dry run, conflicts, and the plugin config dialog merging its changes onto an
edit made elsewhere while it was open.
"""

import threading

import pytest

from config_store import ConfigError, merge_dict, merge_list
from conftest import FakeDevice, FakeDict


def dialog_values(plugin):
    return FakeDict(plugin.getPrefsConfigUiValues()[0])


@pytest.fixture
def devices(indigo):
    return [indigo.devices.add(FakeDevice(f"Device {i}", sensorValue=float(i))) for i in range(4)]


def test_apply_bumps_and_persists_the_revision(make_plugin):
    plugin = make_plugin()
    start = plugin.store.revision
    result = plugin.store.apply('test', lambda c: c['states'].append('batteryLevel'))
    assert result['changed'] and result['revision'] == start + 1
    assert result['before'] == {'states': ['sensorValue', 'onState', 'coolSetpoint', 'heatSetpoint']}
    assert result['after']['states'][-1] == 'batteryLevel'
    assert plugin.pluginPrefs['configRevision'] == start + 1
    assert 'batteryLevel' in plugin.StatesIncludeList
    assert list(plugin.pluginPrefs['listIncStates'])[-1] == 'batteryLevel'


def test_revision_survives_a_restart(make_plugin):
    plugin = make_plugin()
    plugin.store.apply('test', lambda c: c['states'].append('x'))
    again = make_plugin(dict(plugin.pluginPrefs))
    assert again.store.revision == plugin.store.revision


def test_dry_run_and_no_op_change_nothing(make_plugin):
    plugin = make_plugin()
    start = plugin.store.revision
    dry = plugin.store.apply('test', lambda c: c['states'].append('x'), dry_run=True)
    assert dry['changed'] and dry['dry_run'] and dry['revision'] == start
    assert 'x' not in plugin.StatesIncludeList
    noop = plugin.store.apply('test', lambda c: None)
    assert not noop['changed'] and plugin.store.revision == start


def test_expected_revision_conflict(make_plugin):
    plugin = make_plugin()
    with pytest.raises(ConfigError) as raised:
        plugin.store.apply('test', lambda c: c['states'].append('x'), expected_revision=plugin.store.revision + 5)
    assert raised.value.kind == 'conflict'


def test_current_has_no_secrets(make_plugin):
    plugin = make_plugin()
    assert 's3cret-token-value' not in repr(plugin.store.current())


def test_dialog_save_merges_onto_an_edit_made_while_it_was_open(make_plugin, devices, monkeypatch, caplog):
    """An AI edit made while the config dialog is open must survive the save,
    and the dialog's own changes still apply."""
    plugin = make_plugin(listIncDevices=[devices[0].id], listExclDevices=[devices[1].id])
    monkeypatch.setattr(plugin, 'requestReconnect', lambda *a, **k: None)
    values = dialog_values(plugin)

    # the user, in the dialog: adds a state, includes device 2
    values['menuAvailableStates'] = 'batteryLevel'
    plugin.AddStateToIncludedStateList(values)
    values['menuAvailableDevices'] = str(devices[2].id)
    plugin.AddDeviceToIncludedDeviceList(values)

    # meanwhile, elsewhere (an MCP tool): removes onState, excludes device 3, sets frequency
    def ai(config):
        config['states'].remove('onState')
        config['exclude'].append(devices[3].id)
        config['settings']['minimum_update_frequency'] = 60
    plugin.store.apply('mcp', ai)

    # the dialog still shows its own exclude selection and the old frequency
    plugin.closedPrefsConfigUi(plugin.validatePrefsConfigUi(values)[1], False)

    assert plugin.StatesIncludeList == ['sensorValue', 'coolSetpoint', 'heatSetpoint', 'batteryLevel']
    assert plugin.DeviceIncludeList == [devices[0].id, devices[2].id]
    assert sorted(plugin.DeviceExcludeList) == sorted([devices[1].id, devices[3].id])
    assert plugin.minimumUpdateFrequency == 60


def test_dialog_save_without_concurrent_edits_is_the_dialog(make_plugin, devices, monkeypatch):
    plugin = make_plugin(listExclDevices=[devices[1].id])
    monkeypatch.setattr(plugin, 'requestReconnect', lambda *a, **k: None)
    values = dialog_values(plugin)
    values['listExclDevices'] = [str(devices[2].id)]
    values['MinimumUpdateFrequency'] = '-1'
    start = plugin.store.revision
    plugin.closedPrefsConfigUi(plugin.validatePrefsConfigUi(values)[1], False)
    assert plugin.DeviceExcludeList == [devices[2].id]
    assert plugin.minimumUpdateFrequency == -1
    assert plugin.pluginPrefs['MinimumUpdateFrequency'] == '-1'
    assert plugin.store.revision == start + 1


def test_password_changed_elsewhere_survives_a_dialog_save(make_plugin, monkeypatch):
    plugin = make_plugin()
    monkeypatch.setattr(plugin, 'requestReconnect', lambda *a, **k: None)
    values = dialog_values(plugin)
    plugin.InfluxPassword = 'rotated-token'  # update_connection while the dialog was open
    for key, value in values.items():  # Indigo stores the stale valuesDict...
        plugin.pluginPrefs[key] = value
    plugin.closedPrefsConfigUi(plugin.validatePrefsConfigUi(values)[1], False)  # ...then calls us
    assert plugin.InfluxPassword == 'rotated-token'
    assert plugin.pluginPrefs['InfluxPassword'] == 'rotated-token'


def test_password_typed_in_the_dialog_is_applied(make_plugin):
    plugin = make_plugin()
    reconnects = []
    plugin.requestReconnect = lambda *a, **k: reconnects.append(a)
    values = dialog_values(plugin)
    values['InfluxPassword'] = 'new-from-dialog'
    plugin.closedPrefsConfigUi(plugin.validatePrefsConfigUi(values)[1], False)
    assert plugin.InfluxPassword == 'new-from-dialog'
    assert reconnects


def test_filters_dialog_edit_refuses_when_filters_moved(make_plugin, caplog):
    plugin = make_plugin(listFilterList=[['a', 'minMax', 0, 1, 0, True, [], True, False, 'first'],
                                         ['b', 'minMax', 0, 1, 0, True, [], True, False, 'second']])
    values = plugin.FilterAction(FakeDict({'filterAction': 'edit', 'listFilters': ['1'], 'filterName': '',
                                           'filterOrder': '', 'filterProperty': ''}))
    # an MCP tool inserts a filter at the top meanwhile
    plugin.store.apply('mcp', lambda c: c['filters'].insert(0, dict(c['filters'][0], state='z', name='new')))
    values['filterPropertyMinValue'] = '5'
    values['filterPropertyMaxValue'] = '9'
    plugin.SaveFilterValues(values)
    assert [f.name for f in plugin.FilterList] == ['new', 'first', 'second']
    assert any('changed while this one was being edited' in r.getMessage() for r in caplog.records)


def test_housekeeping_prunes_deleted_devices_everywhere(make_plugin, indigo, devices):
    plugin = make_plugin(listIncDevices=[devices[0].id], listExclDevices=[devices[1].id],
                         listFilterList=[['sensorValue', 'minMax', 0, 1, 0, False, [devices[0].id, devices[2].id], True, False, '']])
    start = plugin.store.revision
    del indigo.devices[devices[0].id]
    plugin.BuildConfigurationLists()
    assert plugin.DeviceIncludeList == []
    assert plugin.FilterList[0].appliedDevices == {devices[2].id}
    assert plugin.store.revision == start + 1
    plugin.BuildConfigurationLists()
    assert plugin.store.revision == start + 1  # nothing else to prune: no new revision


def test_list_rebuilds_while_tools_write(make_plugin, devices):
    """Concurrency: the 15-minute rebuild on the concurrent thread against
    writes on the callback thread."""
    plugin = make_plugin()
    errors = []
    stop = threading.Event()

    def rebuild():
        while not stop.is_set():
            try:
                plugin.BuildConfigurationLists()
            except Exception as e:  # pragma: no cover - the assertion reports it
                errors.append(e)

    worker = threading.Thread(target=rebuild)
    worker.start()
    try:
        for i in range(200):
            plugin.store.apply('mcp', lambda c, i=i: c['states'].append(f"state{i}"))
    finally:
        stop.set()
        worker.join()
    assert not errors
    assert plugin.StatesIncludeList[-1] == 'state199'
    assert len(plugin.pluginPrefs['listIncStates']) == len(plugin.StatesIncludeList)


def test_merge_helpers():
    assert merge_list(['a', 'b'], ['a', 'b', 'c'], ['a', 'b']) == (['a', 'b', 'c'], [])
    assert merge_list(['a', 'b'], ['b', 'c'], ['a', 'b', 'd']) == (['b', 'd', 'c'], [])
    merged, conflicts = merge_list(['a'], [], ['a', 'x'])
    assert merged == ['x'] and conflicts == []
    merged, conflicts = merge_dict({'x': 1, 'd': {'y': 1}}, {'x': 2, 'd': {'y': 1}}, {'x': 3, 'd': {'y': 5}})
    assert merged == {'x': 2, 'd': {'y': 5}} and conflicts == ['x']
