"""
Filter CRUD through the influxlog_* tools and the all_except scope (issue #11
phase 3), including the acceptance case: the Dometic cooler's setpoints,
blocked every 15 minutes by the all-device setpoint filters, fixed end to end.
"""

import json
import logging
import types

import pytest

from conftest import FakeDevice, FakeDict
from influx_filter import InfluxFilter

SECRET = 's3cret-token-value'


def invoke(plugin, tool, **arguments):
    reply = plugin.handle_mcp_tool_invoke(types.SimpleNamespace(props={'tool': tool, 'arguments': json.dumps(arguments)}))
    assert SECRET not in reply
    return json.loads(reply)


def ok(plugin, tool, **arguments):
    reply = invoke(plugin, tool, **arguments)
    assert reply['status'] == 'ok', reply
    return reply['result']


def error(plugin, tool, **arguments):
    reply = invoke(plugin, tool, **arguments)
    assert reply['status'] == 'error', reply
    return reply['error']


def record(state, strategy='minMax', lo=0.0, hi=100.0, pct=0.0, all_devices=True, devices=(), lock=True, log=False, name=''):
    return [state, strategy, lo, hi, pct, all_devices, list(devices), lock, log, name]


@pytest.fixture
def house(indigo, make_plugin):
    cooler = indigo.devices.add(FakeDevice("Dometic CFX5 Cooler", coolSetpoint=33.8, heatSetpoint=0.0))
    nest = indigo.devices.add(FakeDevice("Upstairs Nest", coolSetpoint=76.0, heatSetpoint=68.0))
    porch = indigo.devices.add(FakeDevice("Front Porch Luminance", sensorValue=1200.0))
    temp = indigo.devices.add(FakeDevice("Living Room Temperature", sensorValue=69.1))
    plugin = make_plugin(
        listIncStates=['sensorValue', 'coolSetpoint', 'heatSetpoint'],
        preferencesFilterVersion='2.0.0',
        listFilterList=[
            record('sensorValue', hi=2000.0, all_devices=False, devices=[porch.id], name='Front Porch Luminance'),
            record('sensorValue', 'percentChanged', pct=25.0, all_devices=False, devices=[temp.id], name='Temp Max Percent Changed'),
            record('heatSetpoint', lo=30.0, hi=80.0, name='heatSetpoint (all devices) min: 30.0, max: 80.0'),
            record('coolSetpoint', lo=50.0, hi=100.0, name='coolSetpoint (all devices) min: 50.0, max: 100.0'),
        ])
    plugin.everConnected = True
    return types.SimpleNamespace(plugin=plugin, cooler=cooler, nest=nest, porch=porch, temp=temp)


def queued_fields(plugin):
    fields = {}
    while not plugin.write_queue.empty():
        point = plugin.write_queue.get_nowait()
        fields[point['tags']['name']] = point['fields']
    return fields


def test_dometic_cooler_end_to_end(house, caplog):
    """Acceptance (#11): find the blocks, explain the device, fix the filters
    with a dry run then for real, confirm with explain_device."""
    plugin = house.plugin
    plugin.DeviceToInflux(None, house.cooler, False)
    blocks = ok(plugin, 'get_filter_blocks', device='Dometic CFX5 Cooler')
    assert {b['state'] for b in blocks['entries']} == {'coolSetpoint', 'heatSetpoint'}

    explained = ok(plugin, 'explain_device', device='Dometic CFX5 Cooler')
    blocked = {s['key']: s['reason'] for s in explained['states'] if s['reason'].startswith('blocked')}
    assert set(blocked) == {'coolSetpoint', 'heatSetpoint'}

    config = ok(plugin, 'get_config')
    revision = config['revision']
    by_state = {f['state']: f for f in config['filters'] if f['scope'] == 'all'}

    for state in ('heatSetpoint', 'coolSetpoint'):
        f = by_state[state]
        dry = ok(plugin, 'update_filter', position=f['position'], expected_name=f['name'], scope='all_except',
                 devices=['Dometic CFX5 Cooler'], dry_run=True, expected_revision=revision)
        assert dry['dry_run'] and dry['filter']['scope'] == 'all_except'
        assert dry['filter']['name'] == f"{state} (all devices except 1) min: {f['min']}, max: {f['max']}"
        assert dry['affected_devices']['current_values_blocked_count'] == 0  # the cooler is out of scope now
        with caplog.at_level(logging.INFO, logger="Plugin"):
            real = ok(plugin, 'update_filter', position=f['position'], expected_name=f['name'], scope='all_except',
                      devices=['Dometic CFX5 Cooler'], expected_revision=revision)
        revision = real['revision']
        lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith('MCP: update_filter')]
        assert len(lines) == 1 and 'scope' in lines[0] and 'Dometic CFX5 Cooler' in lines[0]
        caplog.clear()

    explained = ok(plugin, 'explain_device', device='Dometic CFX5 Cooler')
    states = {s['key']: s for s in explained['states']}
    assert states['coolSetpoint']['sent'] and states['heatSetpoint']['sent']
    assert explained['summary']['blocked_by_filters'] == 0

    # and the writes really carry the setpoints now; the thermostat is still guarded
    plugin.DeviceToInflux(None, house.cooler, False)
    assert queued_fields(plugin)['Dometic CFX5 Cooler']['coolSetpoint'] == 33.8
    assert plugin.FilterList[3].appliesTo(house.nest.id) and not plugin.FilterList[3].appliesTo(house.cooler.id)
    # persisted as a 2.0.0 record with the except list appended (older releases ignore it)
    assert plugin.pluginPrefs['preferencesFilterVersion'] == '2.0.0'
    assert list(plugin.pluginPrefs['listFilterList'][3][10]) == [house.cooler.id]


def test_create_filter(house):
    plugin = house.plugin
    created = ok(plugin, 'create_filter', state='sensorValue', strategy='min_max', min=0, max=1000,
                 scope='devices', devices=['Front Porch Luminance', house.temp.id], position=1, log_to_event_log=True)
    assert created['filter']['position'] == 1
    assert created['filter']['name'] == 'sensorValue (specific devices) min: 0.0, max: 1000.0'
    assert created['affected_devices']['devices_with_state_in_scope'] == 2
    assert [b['name'] for b in created['affected_devices']['current_values_blocked']] == ['Front Porch Luminance']
    assert plugin.FilterList[0].appliedDevices == {house.porch.id, house.temp.id}
    assert len(plugin.FilterList) == 5

    pct = ok(plugin, 'create_filter', state='coolSetpoint', strategy='percent_changed', max_percent=30,
             lock_on_failure=False, name='Setpoint jumps')
    assert pct['filter']['position'] == 6 and pct['filter']['name'] == 'Setpoint jumps'
    assert plugin.FilterList[5].lockMinimumUpdates is False


@pytest.mark.parametrize("args,paths", [
    ({'state': 'sensorValue', 'strategy': 'min_max', 'min': 5, 'max': 1}, ['min']),
    ({'state': 'sensorValue', 'strategy': 'min_max'}, []),  # min 0 / max 0
    ({'state': 'sensorValue', 'strategy': 'percent_changed', 'max_percent': 0}, ['max_percent']),
    ({'state': 'sensorValue', 'strategy': 'average'}, ['strategy']),
    ({'state': 'sensorValue', 'strategy': 'min_max', 'min': 0, 'max': 1, 'scope': 'devices'}, ['devices']),
    ({'state': 'sensorValue', 'strategy': 'min_max', 'min': 0, 'max': 1, 'scope': 'everything'}, ['scope']),
    ({'state': 'sensorValue', 'strategy': 'min_max', 'min': 0, 'max': 1, 'devices': ['Upstairs Nest']}, ['devices']),
    ({'state': 'sensorValue', 'strategy': 'min_max', 'min': 'low', 'max': 1}, ['min']),
    ({'state': 'sensorValue', 'strategy': 'min_max', 'min': 0, 'max': 1, 'position': 9}, ['position']),
])
def test_create_filter_validation(house, args, paths):
    err = error(house.plugin, 'create_filter', **args)
    assert err['type'] == 'validation'
    if paths:
        assert paths[0] in [e['path'] for e in err['details']['errors']]
    assert len(house.plugin.FilterList) == 4


def test_create_filter_unknown_state_suggests(house):
    err = error(house.plugin, 'create_filter', state='coolSetpont', strategy='min_max', min=0, max=1)
    assert 'coolSetpoint' in err['details']['did_you_mean']['coolSetpont']
    ok(house.plugin, 'create_filter', state='futureState', strategy='min_max', min=0, max=1, allow_unknown=True)


def test_create_filter_warns_when_the_state_is_not_sent(house):
    result = ok(house.plugin, 'create_filter', state='model', strategy='min_max', min=0, max=1, dry_run=True)
    assert any('not sent for any device' in w for w in result['warnings'])


def test_update_filter_guards_positions(house):
    plugin = house.plugin
    conflict = error(plugin, 'update_filter', position=1, expected_name='coolSetpoint (all devices) min: 50.0, max: 100.0', max=3000)
    assert conflict['type'] == 'conflict' and 'positions shift' in conflict['message']
    assert error(plugin, 'update_filter', position=9, expected_name='x', max=1)['type'] == 'not_found'
    assert error(plugin, 'update_filter', position=1, expected_name='Front Porch Luminance')['type'] == 'validation'  # nothing to change
    # expected_name is required: an unguarded position could hit a filter that moved
    assert error(plugin, 'update_filter', position=1, max=3000)['type'] == 'validation'


def test_rename_and_back(house):
    """Reversible write from the #11 production test plan."""
    plugin = house.plugin
    ok(plugin, 'update_filter', position=1, expected_name='Front Porch Luminance', name='Porch light level')
    assert plugin.FilterList[0].name == 'Porch light level'
    ok(plugin, 'update_filter', position=1, expected_name='Porch light level', name='Front Porch Luminance')
    assert plugin.FilterList[0].name == 'Front Porch Luminance'
    generated = ok(plugin, 'update_filter', position=1, expected_name='Front Porch Luminance', name='')
    assert generated['filter']['name'] == 'sensorValue (specific devices) min: 0.0, max: 2000.0'


def test_update_filter_device_lists_and_move(house):
    plugin = house.plugin
    name = 'Temp Max Percent Changed'
    ok(plugin, 'update_filter', position=2, expected_name=name, add_devices=['Front Porch Luminance'])
    assert plugin.FilterList[1].appliedDevices == {house.temp.id, house.porch.id}
    ok(plugin, 'update_filter', position=2, expected_name=name, remove_devices=[house.temp.id], new_position=4)
    assert plugin.FilterList[3].name == name
    assert plugin.FilterList[3].appliedDevices == {house.porch.id}
    err = error(plugin, 'update_filter', position=4, expected_name=name, remove_devices=[house.porch.id])
    assert err['type'] == 'validation'  # a device scope can't be emptied
    err = error(plugin, 'update_filter', position=1, expected_name='Front Porch Luminance', scope='all_except')
    assert 'needs at least one device' in json.dumps(err)


def test_delete_filter(house):
    plugin = house.plugin
    assert error(plugin, 'delete_filter', position=2, expected_name='Front Porch Luminance')['type'] == 'conflict'
    deleted = ok(plugin, 'delete_filter', position=2, expected_name='Temp Max Percent Changed')
    assert deleted['deleted']['name'] == 'Temp Max Percent Changed'
    assert [f.name for f in plugin.FilterList][1] == 'heatSetpoint (all devices) min: 30.0, max: 80.0'
    undone = ok(plugin, 'restore_snapshot', revision=deleted['revision'] - 1)
    assert len(plugin.FilterList) == 4 and undone['changed']


def test_2_0_0_records_gain_the_except_list_and_keep_every_filter(house):
    plugin = house.plugin
    assert plugin.pluginPrefs['preferencesFilterVersion'] == '2.0.0'
    assert [f.name for f in plugin.FilterList] == ['Front Porch Luminance', 'Temp Max Percent Changed',
                                                   'heatSetpoint (all devices) min: 30.0, max: 80.0',
                                                   'coolSetpoint (all devices) min: 50.0, max: 100.0']
    assert all(len(item) == 10 for item in plugin.pluginPrefs['listFilterList'])  # untouched until a change
    plugin.store.apply('test', lambda c: c['states'].append('x'))
    assert all(len(item) == 11 for item in plugin.pluginPrefs['listFilterList'])
    assert plugin.FilterList[1].appliedDevices == {house.temp.id} and plugin.FilterList[1].maxPercent == 25.0


def test_all_except_survives_a_restart(make_plugin, indigo):
    cooler = indigo.devices.add(FakeDevice("Cooler", coolSetpoint=33.8))
    plugin = make_plugin(preferencesFilterVersion='2.0.0',
                         listFilterList=[record('coolSetpoint', lo=50.0, hi=100.0) + [[cooler.id]]])
    f = plugin.FilterList[0]
    assert f.scope == 'all_except' and not f.appliesTo(cooler.id) and f.appliesTo(12345)
    assert f.name == 'coolSetpoint (all devices except 1) min: 50.0, max: 100.0'


def test_unreadable_filters_are_never_overwritten(make_plugin, caplog):
    plugin = make_plugin(preferencesFilterVersion='9.0.0', listFilterList=[['from', 'the', 'future']])
    plugin.store.apply('test', lambda c: c['states'].append('x'))  # some unrelated change persists
    assert plugin.pluginPrefs['preferencesFilterVersion'] == '9.0.0'
    assert list(plugin.pluginPrefs['listFilterList'][0]) == ['from', 'the', 'future']


def test_filters_dialog_all_except(house):
    plugin = house.plugin
    values = plugin.FilterAction(FakeDict({'filterAction': 'edit', 'listFilters': ['3'], 'filterName': '',
                                           'filterOrder': '', 'filterProperty': ''}))
    assert values['filterScope'] == 'all' and values['deviceListVisible'] is False
    values['filterScope'] = 'all_except'
    values['listDevices'] = [str(house.cooler.id)]
    plugin.filterScopeChanged(values)
    assert values['deviceListVisible'] is True
    plugin.SaveFilterValues(values)
    f = plugin.FilterList[3]
    assert f.scope == 'all_except' and f.exceptDevices == {house.cooler.id}
    assert f.name == 'coolSetpoint (all devices except 1) min: 50.0, max: 100.0'

    again = plugin.FilterAction(FakeDict({'filterAction': 'edit', 'listFilters': ['3'], 'filterName': '',
                                          'filterOrder': '', 'filterProperty': ''}))
    assert again['filterScope'] == 'all_except' and list(again['listDevices']) == [str(house.cooler.id)]


def test_filter_dict_round_trip():
    for scope, devices in (('all', []), ('devices', [1, 2]), ('all_except', [3])):
        d = {'state': 's', 'strategy': 'min_max', 'min': 0.0, 'max': 1.0, 'max_percent': 0.0, 'scope': scope,
             'devices': devices, 'lock_on_failure': True, 'log_to_event_log': False, 'name': ''}
        assert InfluxFilter.fromDict(d).toDict() == d


def test_a_release_before_2026_11_reads_the_record(house):
    """Rollback safety: 2026.8.0 builds a filter from item[0..8] and the name from
    item[9]; the except list at item[10] is ignored, so every filter survives."""
    plugin = house.plugin
    ok(plugin, 'update_filter', position=4, expected_name='coolSetpoint (all devices) min: 50.0, max: 100.0',
       scope='all_except', devices=['Dometic CFX5 Cooler'])
    for item in plugin.pluginPrefs['listFilterList']:
        old = InfluxFilter(item[0], item[1], item[2], item[3], item[4], item[5], item[6], item[7], item[8])
        old.name = item[9]
        assert old.state == item[0]
    assert plugin.pluginPrefs['listFilterList'][3][5] is True  # reads as an all-device filter


def test_pre_release_3_0_0_is_read_and_rewritten_as_2_0_0(make_plugin, indigo):
    cooler = indigo.devices.add(FakeDevice("Cooler", coolSetpoint=33.8))
    plugin = make_plugin(preferencesFilterVersion='3.0.0',
                         listFilterList=[record('coolSetpoint', lo=50.0, hi=100.0) + [[cooler.id]]])
    assert plugin.FilterList[0].scope == 'all_except'
    assert plugin.pluginPrefs['preferencesFilterVersion'] == '2.0.0'


def test_housekeeping_prunes_deleted_except_devices(house, indigo):
    plugin = house.plugin
    ok(plugin, 'update_filter', position=4, expected_name='coolSetpoint (all devices) min: 50.0, max: 100.0',
       scope='all_except', devices=['Dometic CFX5 Cooler', 'Upstairs Nest'])
    del indigo.devices[house.cooler.id]
    plugin.BuildConfigurationLists()
    assert plugin.FilterList[3].exceptDevices == {house.nest.id}
    assert plugin.FilterList[3].name == 'coolSetpoint (all devices except 1) min: 50.0, max: 100.0'


def test_filters_dialog_delete_refuses_when_filters_moved(house, caplog):
    plugin = house.plugin
    plugin.IncludedFiltersListGenerator()  # the dialog lists the filters
    ok(plugin, 'create_filter', state='sensorValue', strategy='min_max', min=0, max=9999, position=1)  # meanwhile
    plugin.FilterAction(FakeDict({'filterAction': 'delete', 'listFilters': ['1']}))
    assert len(plugin.FilterList) == 5
    assert any('changed since this list was shown' in r.getMessage() for r in caplog.records)
    plugin.IncludedFiltersListGenerator()  # reopened
    plugin.FilterAction(FakeDict({'filterAction': 'delete', 'listFilters': ['1']}))
    assert len(plugin.FilterList) == 4 and plugin.FilterList[1].name == 'Temp Max Percent Changed'


def test_a_filter_whose_devices_were_deleted_can_still_be_edited(house, indigo):
    """Found on production: housekeeping left 'Front Porch Luminance' scoped to
    no devices (its only device was deleted); a rename must still work."""
    plugin = house.plugin
    del indigo.devices[house.porch.id]
    plugin.BuildConfigurationLists()
    assert plugin.FilterList[0].appliedDevices == set()
    assert ok(plugin, 'get_config')['filters'][0]['applies_to_no_devices'] is True

    renamed = ok(plugin, 'update_filter', position=1, expected_name='Front Porch Luminance', name='Porch (test)')
    assert plugin.FilterList[0].name == 'Porch (test)'
    assert any('applies to no devices' in w for w in renamed['warnings'])
    # changing the scope still needs devices
    assert error(plugin, 'update_filter', position=1, expected_name='Porch (test)', scope='all_except')['type'] == 'validation'
    ok(plugin, 'update_filter', position=1, expected_name='Porch (test)', devices=['Living Room Temperature'])
    assert plugin.FilterList[0].appliedDevices == {house.temp.id}


def test_update_filter_snapshot_summary_names_the_filter(house):
    plugin = house.plugin
    ok(plugin, 'update_filter', position=1, expected_name='Front Porch Luminance', name='Porch')
    latest = ok(plugin, 'list_snapshots')['snapshots'][0]
    assert latest['summary'] == "1 'Front Porch Luminance'" and latest['source'] == 'mcp: update_filter'
