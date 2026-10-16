"""
The influxlog_* write tools for inclusion, settings and the connection, and the
snapshots (issue #11 phase 2): validation with field paths, dry run, revision
guard, snapshot, one Event Log line, live without a restart, persisted - and
never the password in any output, log line or snapshot.
"""

import glob
import json
import logging
import os
import threading
import time
import types

import pytest

from conftest import FakeDevice
from fake_influx import FakeInfluxClient, http_error

SECRET = 's3cret-token-value'
NEW_SECRET = 'apiv3_NEW-token-value'


def invoke(plugin, tool, **arguments):
    """Call a tool the way MCP Advanced Tools does; wait for async replies."""
    action = types.SimpleNamespace(props={'tool': tool, 'arguments': json.dumps(arguments)})
    import indigo
    before = len(indigo.completion_handlers)
    reply = plugin.handle_mcp_tool_invoke(action, caller_waiting_for_result=True)
    if reply is None:  # finished on a worker thread through the completion handler
        handler = indigo.completion_handlers[before]
        deadline = time.monotonic() + 10
        while handler.result is None and time.monotonic() < deadline:
            time.sleep(0.02)
        reply = handler.result
    assert isinstance(reply, str), reply
    for secret in (SECRET, NEW_SECRET):
        assert secret not in reply
    return json.loads(reply)


def ok(plugin, tool, **arguments):
    reply = invoke(plugin, tool, **arguments)
    assert reply['status'] == 'ok', reply
    return reply['result']


def error(plugin, tool, **arguments):
    reply = invoke(plugin, tool, **arguments)
    assert reply['status'] == 'error', reply
    return reply['error']


@pytest.fixture
def house(indigo, make_plugin):
    lamp = indigo.devices.add(FakeDevice("Living Room Lamp", onState=True, brightness=40))
    lamp2 = indigo.devices.add(FakeDevice("Living Room Lamp 2", onState=False))
    cooler = indigo.devices.add(FakeDevice("Dometic CFX5 Cooler", coolSetpoint=33.8, heatSetpoint=0.0))
    plugin = make_plugin(listIncStates=['sensorValue', 'onState', 'coolSetpoint'], listExclDevices=[lamp2.id])
    client = FakeInfluxClient('3.10.3', 'Enterprise')
    plugin.newClient = lambda settings: client
    plugin.reconnects = []
    plugin.requestReconnect = lambda *a, **k: plugin.reconnects.append(a)
    return types.SimpleNamespace(plugin=plugin, lamp=lamp, lamp2=lamp2, cooler=cooler, client=client)


def snapshot_texts(indigo):
    folder = os.path.join(indigo.server.getInstallFolderPath(), 'Preferences', 'Plugins', 'com.vtmikel.grafana.snapshots')
    return [open(path).read() for path in glob.glob(os.path.join(folder, '*.json'))]


# --- set_device_mode ---------------------------------------------------------------

def test_set_device_mode_dry_run_then_real(house, caplog):
    plugin = house.plugin
    start = plugin.store.revision

    dry = ok(plugin, 'set_device_mode', devices=['Living Room Lamp'], mode='excluded', dry_run=True)
    assert dry['dry_run'] and dry['changed'] and dry['revision'] == start
    assert dry['affected_devices'] == [{'id': house.lamp.id, 'name': 'Living Room Lamp', 'previous_mode': 'global_states',
                                        'mode': 'excluded', 'keys': dry['affected_devices'][0]['keys']}]
    assert house.lamp.id not in plugin.DeviceExcludeList

    with caplog.at_level(logging.INFO, logger="Plugin"):
        real = ok(plugin, 'set_device_mode', devices=['Living Room Lamp'], mode='excluded', expected_revision=start)
    assert real['revision'] == start + 1
    assert house.lamp.id in plugin.DeviceExcludeList  # live, no restart
    assert house.lamp.id in list(plugin.pluginPrefs['listExclDevices'])  # persisted
    assert any(r.getMessage() == f"MCP: set_device_mode excluded: Living Room Lamp (revision {start + 1})" for r in caplog.records)

    # and back: reversible
    back = ok(plugin, 'set_device_mode', devices=[house.lamp.id], mode='default')
    assert house.lamp.id not in plugin.DeviceExcludeList and back['revision'] == start + 2


def test_set_device_mode_moves_between_lists(house):
    plugin = house.plugin
    ok(plugin, 'set_device_mode', devices=['Living Room Lamp 2'], mode='all_states')
    assert house.lamp2.id in plugin.DeviceIncludeList and house.lamp2.id not in plugin.DeviceExcludeList


def test_set_device_mode_validation(house):
    plugin = house.plugin
    err = error(plugin, 'set_device_mode', devices=['Living Room Lmp', 999], mode='excluded')
    assert err['type'] == 'validation'
    assert [e['path'] for e in err['details']['errors']] == ['devices[0]', 'devices[1]']
    assert 'Living Room Lamp' in err['details']['did_you_mean']['Living Room Lmp']
    assert error(plugin, 'set_device_mode', devices=['Living Room Lamp'], mode='hidden')['type'] == 'validation'
    assert error(plugin, 'set_device_mode', devices=list(range(51)), mode='excluded')['type'] == 'validation'
    conflict = error(plugin, 'set_device_mode', devices=['Living Room Lamp'], mode='excluded', expected_revision=999)
    assert conflict['type'] == 'conflict'


def test_already_in_mode_is_a_warning(house):
    result = ok(house.plugin, 'set_device_mode', devices=['Living Room Lamp 2'], mode='excluded')
    assert not result['changed']
    assert result['warnings'] == ["Living Room Lamp 2 is already 'excluded'"]


# --- update_included_states -----------------------------------------------------------

def test_update_included_states(house):
    plugin = house.plugin
    result = ok(plugin, 'update_included_states', add=['brightness'], remove=['sensorValue'])
    assert plugin.StatesIncludeList == ['onState', 'coolSetpoint', 'brightness']
    assert result['affected_devices'] == {'added': {'brightness': 1}, 'removed': {'sensorValue': 0}}


def test_update_included_states_refusals(house):
    plugin = house.plugin
    unknown = error(plugin, 'update_included_states', add=['brightnes'])
    assert unknown['type'] == 'validation' and 'brightness' in unknown['details']['did_you_mean']['brightnes']
    assert ok(plugin, 'update_included_states', add=['futureState'], allow_unknown=True)['changed']

    always = error(plugin, 'update_included_states', add=['lastChanged'])
    assert 'multiply the write volume' in always['details']['errors'][0]['message']

    empty = error(plugin, 'update_included_states', remove=list(plugin.StatesIncludeList))
    assert empty['type'] == 'validation' and 'empty' in empty['message']
    assert plugin.StatesIncludeList  # unchanged

    assert error(plugin, 'update_included_states')['type'] == 'validation'


def test_reset_to_defaults(house):
    plugin = house.plugin
    ok(plugin, 'update_included_states', reset_to_defaults=True, add=['brightness'])
    assert plugin.StatesIncludeList[0] == 'state.onOffState' and plugin.StatesIncludeList[-1] == 'brightness'


# --- update_settings --------------------------------------------------------------------

def test_update_settings(house, monkeypatch):
    plugin = house.plugin
    applied = []
    monkeypatch.setattr(plugin, 'applyRetentionInBackground', lambda: applied.append(True))

    ok(plugin, 'update_settings', minimum_update_frequency='disabled', debug={'transport': True})
    assert plugin.minimumUpdateFrequency == -1 and plugin.pluginPrefs['MinimumUpdateFrequency'] == '-1'
    assert plugin.TransportDebug is True and plugin.adaptor.TransportDebug is True
    assert not applied  # retention untouched

    result = ok(plugin, 'update_settings', retention='forever')
    assert plugin.InfluxRetention == '-1' and applied == [True]
    assert result['after']['settings']['retention'] == '-1'

    for bad in ({'minimum_update_frequency': 7}, {'retention': 'ten'}, {'debug': {'loud': True}}, {'debug': {'json': 'yes'}}, {}):
        assert error(plugin, 'update_settings', **bad)['type'] == 'validation', bad


def test_retention_on_v3_is_a_warning(make_plugin, indigo):
    plugin = make_plugin(InfluxVersion='3')
    plugin.applyRetentionInBackground = lambda: pytest.fail("no retention DDL on InfluxDB 3")
    result = ok(plugin, 'update_settings', retention=12)
    assert any('InfluxDB 1.x only' in w for w in result['warnings'])


# --- update_connection ---------------------------------------------------------------------

def test_update_connection_validation_names_the_fields(house):
    err = error(house.plugin, 'update_connection', host='https://influx', port=0)
    assert err['type'] == 'validation'
    assert sorted(e['path'] for e in err['details']['errors']) == ['host', 'port']
    assert error(house.plugin, 'update_connection')['type'] == 'validation'
    assert error(house.plugin, 'update_connection', ssl='yes')['type'] == 'validation'


def test_update_connection_dry_run_never_connects(house):
    plugin = house.plugin
    plugin.newClient = lambda settings: pytest.fail("a dry run must not connect")
    result = ok(plugin, 'update_connection', port=8181, password=NEW_SECRET, dry_run=True)
    assert result['dry_run'] and not result['committed'] and result['password_changed']
    assert result['after']['connection']['port'] == '8181'
    assert plugin.InfluxHTTPPort == '8086' and plugin.InfluxPassword == SECRET


def test_update_connection_failed_test_keeps_the_old_settings(house):
    plugin = house.plugin
    house.client.check_write_error = http_error(401, 'the request was not authenticated')
    start = plugin.store.revision
    err = error(plugin, 'update_connection', password=NEW_SECRET)
    assert err['type'] == 'validation' and 'connection test failed' in err['message']
    assert err['details']['test']['status_code'] == 401
    assert plugin.InfluxPassword == SECRET and plugin.store.revision == start and not plugin.reconnects


def test_update_connection_force_saves_anyway(house):
    plugin = house.plugin
    house.client.ping_error = http_error(503, 'down')
    result = ok(plugin, 'update_connection', host='influx-new.example.com', force=True)
    assert result['committed'] and not result['test']['passed']
    assert plugin.InfluxHost == 'influx-new.example.com' and plugin.reconnects


def test_update_connection_tests_then_commits(house, caplog):
    """Re-pointing the connection: tested on a worker thread (Indigo's callback
    thread never waits on the network), committed, reconnected."""
    plugin = house.plugin
    tested_on = []
    original = plugin.testConnection

    def spy(settings):
        tested_on.append(threading.current_thread().name)
        return original(settings)

    plugin.testConnection = spy
    start = plugin.store.revision
    with caplog.at_level(logging.INFO, logger="Plugin"):
        result = ok(plugin, 'update_connection', host='influx3.example.com', port=443, ssl=True, version='3',
                    password=NEW_SECRET, expected_revision=start)

    assert tested_on == ['InfluxToolWorker']
    assert result['committed'] and result['test']['passed'] and result['password_changed']
    assert result['revision'] == start + 1
    assert (plugin.InfluxHost, plugin.InfluxHTTPPort, plugin.InfluxSSL, plugin.InfluxVersion) == ('influx3.example.com', '443', True, '3')
    assert plugin.InfluxV3Compat
    assert plugin.InfluxPassword == NEW_SECRET and plugin.pluginPrefs['InfluxPassword'] == NEW_SECRET
    assert plugin.reconnects
    line = next(r.getMessage() for r in caplog.records if r.getMessage().startswith('MCP: update_connection'))
    assert 'password changed' in line
    for record in caplog.records:
        assert NEW_SECRET not in record.getMessage() and SECRET not in record.getMessage()


def test_password_only_change_is_a_revision(house):
    plugin = house.plugin
    start = plugin.store.revision
    result = ok(plugin, 'update_connection', password=NEW_SECRET)
    assert result['revision'] == start + 1 and result['password_changed']
    assert set(result['before']) == {'connection'}
    assert 'credentials_version' not in result['after'].get('connection', {})


def test_current_settings_are_tested_and_nothing_changes(house):
    plugin = house.plugin
    start = plugin.store.revision
    result = ok(plugin, 'update_connection', host='influx.example.com', password=SECRET)
    assert not result['changed'] and not result['committed']
    assert result['test']['passed'] and result['test']['server_version'] == '3.10.3'
    assert plugin.store.revision == start and not plugin.reconnects

    house.client.ping_error = http_error(503, 'down')
    failed = ok(plugin, 'update_connection', port=8086)
    assert not failed['test']['passed'] and not failed['committed']


def test_reconnect_clears_the_auth_stop(house):
    plugin = house.plugin
    plugin.StopConnectionAttempts = True
    plugin.connectionState = 'stopped_auth_failure'
    result = ok(plugin, 'reconnect')
    assert result['previous_state'] == 'stopped_auth_failure' and plugin.reconnects


# --- snapshots --------------------------------------------------------------------------

def test_snapshots_restore_and_undo(house, indigo):
    plugin = house.plugin
    r0 = plugin.store.revision
    ok(plugin, 'set_device_mode', devices=['Living Room Lamp'], mode='excluded')
    ok(plugin, 'update_included_states', add=['brightness'])

    listing = ok(plugin, 'list_snapshots')['snapshots']
    assert [s['revision'] for s in listing][:2] == [r0 + 1, r0]
    assert listing[0]['source'] == 'mcp: update_included_states'

    restored = ok(plugin, 'restore_snapshot', revision=r0)
    assert house.lamp.id not in plugin.DeviceExcludeList and 'brightness' not in plugin.StatesIncludeList
    assert restored['restored_from']['revision'] == r0

    # the restore is itself snapshotted: undo it
    ok(plugin, 'restore_snapshot', revision=r0 + 2)
    assert house.lamp.id in plugin.DeviceExcludeList and 'brightness' in plugin.StatesIncludeList

    assert error(plugin, 'restore_snapshot', revision=12345)['type'] == 'not_found'


def test_restore_never_touches_the_connection(house):
    plugin = house.plugin
    r0 = plugin.store.revision
    ok(plugin, 'update_connection', port=8087, password=NEW_SECRET)
    result = ok(plugin, 'restore_snapshot', revision=r0, dry_run=True)
    assert any("port='8086'" in w for w in result['warnings'])
    ok(plugin, 'restore_snapshot', revision=r0)
    assert plugin.InfluxHTTPPort == '8087' and plugin.InfluxPassword == NEW_SECRET


def test_only_twenty_snapshots_are_kept(house):
    plugin = house.plugin
    for i in range(25):
        ok(plugin, 'update_included_states', add=[f"s{i}"], allow_unknown=True)
    assert len(ok(plugin, 'list_snapshots')['snapshots']) == 20


def test_no_secret_anywhere(house, indigo, caplog):
    """No tool output, snapshot or log line ever contains the password/token."""
    plugin = house.plugin
    with caplog.at_level(logging.DEBUG):
        for tool, args in [('get_status', {}), ('get_config', {'include_filter_devices': True}),
                           ('explain_device', {'device': 'Living Room Lamp'}), ('list_snapshots', {}),
                           ('update_connection', {'password': NEW_SECRET, 'dry_run': True}),
                           ('update_connection', {'password': NEW_SECRET}),
                           ('update_connection', {'user': 'other', 'password': SECRET}),
                           ('set_device_mode', {'devices': ['Living Room Lamp'], 'mode': 'all_states'}),
                           ('update_settings', {'debug': {'json': True}})]:
            invoke(plugin, tool, **args)  # asserts on the reply itself
        plugin.store.apply('test', lambda c: c['states'].append('x'))
    for text in snapshot_texts(indigo):
        assert SECRET not in text and NEW_SECRET not in text
    for record in caplog.records:
        assert SECRET not in record.getMessage() and NEW_SECRET not in record.getMessage()


def test_first_connection_settings_configure_the_plugin(indigo, make_plugin):
    """Review finding: on a never-configured plugin update_connection said
    committed but saved nothing and never connected."""
    plugin = make_plugin(start=False)
    for key in ('InfluxHost', 'InfluxPassword'):
        del plugin.pluginPrefs[key]
    plugin.startup()
    assert not plugin.configured
    plugin.newClient = lambda settings: FakeInfluxClient('3.10.3', 'Enterprise')
    reconnects = []
    plugin.requestReconnect = lambda *a, **k: reconnects.append(a)

    result = ok(plugin, 'update_connection', host='influx3.example.com', port=443, ssl=True, version='3',
                database='indigo', user='indigo', password=NEW_SECRET)

    assert result['committed'] and plugin.configured and reconnects
    assert plugin.pluginPrefs['InfluxHost'] == 'influx3.example.com'
    assert plugin.pluginPrefs['InfluxPassword'] == NEW_SECRET
    assert ok(plugin, 'reconnect')['requested']


def test_restoring_retention_reapplies_it(house, monkeypatch):
    plugin = house.plugin
    applied = []
    monkeypatch.setattr(plugin, 'applyRetentionInBackground', lambda: applied.append(True))
    r0 = plugin.store.revision
    ok(plugin, 'update_settings', retention='forever')
    ok(plugin, 'restore_snapshot', revision=r0)
    assert plugin.InfluxRetention == '24' and applied == [True, True]
