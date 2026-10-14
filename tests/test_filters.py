"""
Data filters: issue #12 items 1 (Edit broken), 12 (lock re-enabled on edit), and
the low items (delete order, insert-at past the end, non-numeric values, stale
generated names, filter.log location).
"""

import logging
import os

import pytest

import plugin as plugin_module
from conftest import FakeDevice, FakeDict
from plugin import InfluxFilter


def filter_record(state='sensorValue', strategy='minMax', lo=0.0, hi=100.0, pct=0.0, all_devices=True,
                  devices=(), lock=True, log=False, name=''):
    return [state, strategy, lo, hi, pct, all_devices, list(devices), lock, log, name]


def form(**values):
    base = {
        'filterAction': 'add', 'filterName': '', 'filterOrder': '1', 'filterProperty': 'sensorValue',
        'filterStrategy': 'minMax', 'filterPropertyMinValue': '0', 'filterPropertyMaxValue': '100',
        'filterPropertyPercent': '', 'preventMinimumUpdates': True, 'filterAllDevices': True,
        'listDevices': [], 'logFailures': False, 'listFilters': [],
    }
    base.update(values)
    return FakeDict(base)


def test_edit_loads_a_device_scoped_filter(make_plugin, indigo):
    """Item 1: FilterAction put the filter's set into valuesDict; indigo.Dict
    refuses a set with TypeError, the except swallowed it at debug, and the edit
    fields stayed disabled."""
    indigo.devices.add(FakeDevice("Porch Sensor", dev_id=11))
    indigo.devices.add(FakeDevice("Porch Sensor 2", dev_id=22))
    plugin = make_plugin(listFilterList=[filter_record(all_devices=False, devices=[11, 22], name='Front Porch Luminance')])
    values = form(filterAction='edit', listFilters=['0'])

    values = plugin.FilterAction(values)

    assert values['editMode'] is True
    assert values['lockActionChange'] is True
    assert values['deviceListVisible'] is True
    assert list(values['listDevices']) == ['11', '22']
    assert values['filterName'] == 'Front Porch Luminance'


def test_edit_keeps_lock_setting_of_percent_filter(make_plugin):
    """Item 12: editing a percentChanged filter turned 'lock minimum updates' back on."""
    plugin = make_plugin(listFilterList=[filter_record(strategy='percentChanged', pct=25.0, lock=False)])
    values = plugin.FilterAction(form(filterAction='edit', listFilters=['0']))
    assert values['preventMinimumUpdates'] is False
    assert values['percentVisible'] is True


def test_edit_saves_in_place_and_regenerates_a_generated_name(make_plugin):
    plugin = make_plugin(listFilterList=[filter_record(state='a', name='first'),
                                         filter_record(state='heatSetpoint', lo=30.0, hi=80.0),
                                         filter_record(state='c', name='third')])
    values = plugin.FilterAction(form(filterAction='edit', listFilters=['1']))
    assert values['filterName'] == 'heatSetpoint (all devices) min: 30.0, max: 80.0'
    values['filterPropertyMinValue'] = '10'
    plugin.SaveFilterValues(values)

    assert [f.state for f in plugin.FilterList] == ['a', 'heatSetpoint', 'c']
    assert plugin.FilterList[1].minValue == 10.0
    assert plugin.FilterList[1].name == 'heatSetpoint (all devices) min: 10.0, max: 80.0'


def test_custom_names_are_kept(make_plugin):
    plugin = make_plugin(listFilterList=[filter_record(name='Front Porch Luminance')])
    values = plugin.FilterAction(form(filterAction='edit', listFilters=['0']))
    values['filterPropertyMaxValue'] = '5000'
    plugin.SaveFilterValues(values)
    assert plugin.FilterList[0].name == 'Front Porch Luminance'


def test_stale_generated_name_is_refreshed_on_load(make_plugin, indigo):
    """Production's 'energyCurLevel (all devices) ...' filter is scoped to ~280
    specific devices; a generated name follows the filter's real settings."""
    indigo.devices.add(FakeDevice("Meter 1", dev_id=1))
    indigo.devices.add(FakeDevice("Meter 2", dev_id=2))
    plugin = make_plugin(listFilterList=[filter_record(state='energyCurLevel', hi=500.0, all_devices=False,
                                                       devices=[1, 2], name='energyCurLevel (all devices) min: 0.0, max: 500.0')])
    assert plugin.FilterList[0].name == 'energyCurLevel (specific devices) min: 0.0, max: 500.0'


def test_multi_delete_sorts_positions_as_numbers(make_plugin):
    """Low item: positions were sorted as strings, so with 10+ filters the
    wrong ones were deleted."""
    records = [filter_record(state=f"s{i}", name=f"filter {i}") for i in range(12)]
    plugin = make_plugin(listFilterList=records)

    plugin.FilterAction(form(filterAction='delete', listFilters=['1', '9', '10']))

    assert [f.name for f in plugin.FilterList] == [f"filter {i}" for i in range(12) if i not in (1, 9, 10)]
    assert len(plugin.pluginPrefs['listFilterList']) == 9


def test_insert_at_past_the_end_appends(make_plugin):
    """Low item: 'insert at' past the end put the new filter second-to-last."""
    plugin = make_plugin(listFilterList=[filter_record(state='a', name='a'), filter_record(state='b', name='b')])
    plugin.SaveFilterValues(form(filterOrder='10', filterProperty='new'))
    assert [f.state for f in plugin.FilterList] == ['a', 'b', 'new']


def test_saved_filters_hold_lists_not_sets(make_plugin):
    plugin = make_plugin()
    plugin.SaveFilterValues(form(filterAllDevices=False, listDevices=['5', '3']))
    record = plugin.pluginPrefs['listFilterList'][0]
    assert list(record[6]) == [3, 5]
    assert plugin.pluginPrefs['preferencesFilterVersion'] == '2.0.0'


def test_percent_filter_requires_a_positive_threshold(make_plugin, caplog):
    plugin = make_plugin()
    with caplog.at_level(logging.ERROR, logger="Plugin"):
        plugin.SaveFilterValues(form(filterStrategy='percentChanged', filterPropertyPercent='0'))
    assert plugin.FilterList == []


def test_min_max_filter_ignores_non_numeric_values(make_plugin, indigo, caplog):
    """Low item: float(vv) raised on a non-numeric value and logged an ERROR on
    every update."""
    dev = indigo.devices.add(FakeDevice("Text Device", sensorValue='n/a'))
    plugin = make_plugin(listFilterList=[filter_record()], listIncStates=['sensorValue'])
    plugin.everConnected = True
    with caplog.at_level(logging.ERROR, logger="Plugin"):
        sent, locked = plugin.DeviceToInflux(None, dev, False)
    assert sent
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert plugin.write_queue.queue[-1]['fields']['sensorValue'] == 'n/a'


def test_blocked_value_goes_to_filter_log_in_indigos_log_folder(make_plugin, indigo):
    """Item 11: filter.log was hard-coded under ~/Library/.../Indigo 2025.1/Logs."""
    dev = indigo.devices.add(FakeDevice("Dometic CFX5 Cooler", coolSetpoint=33.8))
    plugin = make_plugin(listFilterList=[filter_record(state='coolSetpoint', lo=50.0, hi=100.0)],
                         listIncStates=['coolSetpoint'])
    plugin.everConnected = True

    plugin.DeviceToInflux(None, dev, False)

    expected = os.path.join(indigo.server.getLogsFolderPath('com.vtmikel.grafana'), 'filter.log')
    assert plugin.FilterLogFileLoc == expected
    with open(expected) as log:
        line = log.read()
    assert "Filter block (coolSetpoint (all devices) min: 50.0, max: 100.0): a value (33.8) for state/property 'coolSetpoint' on device 'Dometic CFX5 Cooler'" in line
    queued = plugin.write_queue.queue[-1]
    assert 'coolSetpoint' not in queued['fields']


def test_lock_is_logged_once_and_released_on_change(make_plugin, indigo, caplog):
    """Low item: a locked device logged an INFO line on every 60-second poll."""
    dev = indigo.devices.add(FakeDevice("Thermo", states={'temp': 70.0}, sensorValue=70.0))
    plugin = make_plugin(listFilterList=[filter_record(strategy='percentChanged', pct=20.0, lock=True)],
                         listIncStates=['sensorValue'], MinimumUpdateFrequency='5')
    plugin.connected = True
    plugin.everConnected = True

    orig = FakeDevice("Thermo", dev_id=dev.id, sensorValue=70.0, states={'sensorValue': 70.0})
    dev.sensorValue = 200.0
    dev.states = {'sensorValue': 200.0}
    with caplog.at_level(logging.INFO, logger="Plugin"):
        plugin.deviceUpdated(orig, dev)
        for _ in range(3):
            plugin.UpdateAll()
    locks = [r for r in caplog.records if 'is locked' in r.getMessage()]
    assert len(locks) == 1
    assert dev.id in plugin.deviceLocks

    caplog.clear()
    orig = FakeDevice("Thermo", dev_id=dev.id, sensorValue=200.0, states={'sensorValue': 200.0})
    dev.sensorValue = 205.0
    dev.states = {'sensorValue': 205.0}
    with caplog.at_level(logging.INFO, logger="Plugin"):
        plugin.deviceUpdated(orig, dev)
    assert dev.id not in plugin.deviceLocks
    assert any('no longer locked' in r.getMessage() for r in caplog.records)


def test_generated_name_pattern():
    f = InfluxFilter('sensorValue', 'percentChanged', 0, 0, 25, True, [], True, False)
    assert f.name == 'sensorValue (all devices) percent: 25.0'
    f.name = 'sensorValue (all devices) percent: 25.0'
    assert f.customName == ''
    f.name = 'My filter'
    assert f.name == 'My filter'
