"""
The read-only influxlog_* tools (issue #11 phase 1), driven exactly as the MCP
Server drives them: plugin.handle_mcp_tool_invoke with a tool name and a
JSON-string arguments payload, returning a JSON-string envelope.
"""

import datetime
import json
import types

import pytest

from conftest import FakeDevice
from fake_influx import FakeInfluxClient, http_error

SECRET = 's3cret-token-value'  # BASE_PREFS' password


def invoke(plugin, tool, arguments=None, raw=None):
    action = types.SimpleNamespace(props={'tool': tool, 'arguments': raw if raw is not None else json.dumps(arguments or {})})
    reply = plugin.handle_mcp_tool_invoke(action)
    assert isinstance(reply, str)
    assert SECRET not in reply
    return json.loads(reply)


def ok(plugin, tool, **arguments):
    reply = invoke(plugin, tool, arguments)
    assert reply['status'] == 'ok', reply
    return reply['result']


def error(plugin, tool, **arguments):
    reply = invoke(plugin, tool, arguments)
    assert reply['status'] == 'error', reply
    return reply['error']


def record(state, strategy='minMax', lo=0.0, hi=100.0, pct=0.0, all_devices=True, devices=(), lock=True, log=False, name=''):
    return [state, strategy, lo, hi, pct, all_devices, list(devices), lock, log, name]


@pytest.fixture
def house(indigo, make_plugin):
    cooler = indigo.devices.add(FakeDevice("Dometic CFX5 Cooler", coolSetpoint=33.8, heatSetpoint=0.0, model="CFX5"))
    lamp = indigo.devices.add(FakeDevice("Living Room Lamp", onState=True, states={'onOffState': True}))
    thermo = indigo.devices.add(FakeDevice("Living Room Temperature", sensorValue=69.1))
    noisy = indigo.devices.add(FakeDevice("Noisy Meter", energyCurLevel=12.0))
    plugin = make_plugin(
        listIncStates=['sensorValue', 'coolSetpoint', 'heatSetpoint', 'onState'],
        listIncDevices=[lamp.id], listExclDevices=[noisy.id],
        listFilterList=[
            record('heatSetpoint', lo=30.0, hi=80.0),
            record('coolSetpoint', lo=50.0, hi=100.0),
            record('sensorValue', 'percentChanged', pct=25.0, all_devices=False, devices=[thermo.id], lock=False,
                   name='Temp Max Percent Changed'),
        ])
    plugin.newClient = lambda settings: FakeInfluxClient('3.10.3', 'Enterprise')
    return types.SimpleNamespace(plugin=plugin, cooler=cooler, lamp=lamp, thermo=thermo, noisy=noisy)


# --- dispatcher envelopes --------------------------------------------------------

def test_unknown_tool(house):
    err = error(house.plugin, 'drop_database')
    assert err['type'] == 'not_found'
    assert 'get_status' in err['message']


@pytest.mark.parametrize("raw,fragment", [('{not json', 'not valid JSON'), ('[1, 2]', 'JSON object')])
def test_bad_arguments_payload(house, raw, fragment):
    reply = invoke(house.plugin, 'get_status', raw=raw)
    assert reply['status'] == 'error' and reply['error']['type'] == 'validation'
    assert fragment in reply['error']['message']


def test_unexpected_argument(house):
    err = error(house.plugin, 'get_status', verbose=True)
    assert err['type'] == 'validation'


def test_dispatcher_survives_a_tool_crash(house, monkeypatch):
    invoke(house.plugin, 'get_status')  # builds the dispatcher
    tools = house.plugin._tool_dispatcher._service
    monkeypatch.setitem(house.plugin._tool_dispatcher._tools, 'get_status', lambda: 1 / 0)
    err = error(house.plugin, 'get_status')
    assert err['type'] == 'internal' and 'ZeroDivisionError' in err['message']


# --- get_status -----------------------------------------------------------------

def test_get_status(house):
    plugin = house.plugin
    plugin.connect()
    plugin.LockDeviceUpdates(house.thermo, 'sensorValue', 'Temp Max Percent Changed')
    plugin.stats.written(42)
    plugin.stats.error(http_error(401, 'authorization failed'))

    status = ok(plugin, 'get_status')

    assert status['connection']['state'] == 'connected'
    assert status['connection']['server_version'] == '3.10.3'
    assert status['connection']['host'] == 'influx.example.com'
    assert status['writes']['points_written'] == 42
    assert status['writes']['last_error']['status'] == 401
    assert status['writes']['queue_capacity'] == 10000
    assert status['locked_devices'][0]['name'] == 'Living Room Temperature'
    assert status['locked_devices'][0]['filter'] == 'Temp Max Percent Changed'
    assert status['plugin_version'] == '2026.11.0'


def test_get_status_reports_auth_failure(house):
    plugin = house.plugin
    client = FakeInfluxClient()
    client.check_write_error = http_error(401, 'authorization failed')
    plugin.newClient = lambda settings: client
    plugin.connect()
    assert ok(plugin, 'get_status')['connection']['state'] == 'stopped_auth_failure'


# --- get_config -----------------------------------------------------------------

def test_get_config(house):
    config = ok(house.plugin, 'get_config')

    assert config['connection']['password_set'] is True
    assert 'password' not in config['connection']
    assert config['settings']['minimum_update_frequency'] == 15
    assert config['settings']['retention'] == 24
    assert config['settings']['retention_applies'] is True
    assert {'state': 'coolSetpoint', 'devices': 1} in config['included_states']
    assert config['included_devices'] == [{'id': house.lamp.id, 'name': 'Living Room Lamp'}]
    assert config['excluded_devices'] == [{'id': house.noisy.id, 'name': 'Noisy Meter'}]

    filters = config['filters']
    assert [f['position'] for f in filters] == [1, 2, 3]
    assert filters[0] == {'position': 1, 'name': 'heatSetpoint (all devices) min: 30.0, max: 80.0',
                          'name_is_generated': True, 'state': 'heatSetpoint', 'state_device_count': 1,
                          'strategy': 'min_max', 'scope': 'all', 'log_to_event_log': False, 'min': 30.0, 'max': 80.0}
    assert filters[2]['scope'] == 'devices'
    assert filters[2]['devices'] == [{'id': house.thermo.id, 'name': 'Living Room Temperature'}]
    assert filters[2]['lock_on_failure'] is False
    assert config['revision'] == house.plugin.store.revision


def test_get_config_truncates_big_device_scopes(house, indigo):
    plugin = house.plugin
    meters = [indigo.devices.add(FakeDevice(f"Meter {i}", energyCurLevel=1.0)) for i in range(15)]
    plugin.store.apply('test', lambda c: c['filters'].append(
        {'state': 'energyCurLevel', 'strategy': 'min_max', 'min': 0.0, 'max': 500.0, 'max_percent': 0.0,
         'scope': 'devices', 'devices': [m.id for m in meters], 'lock_on_failure': True, 'log_to_event_log': True,
         'name': ''}))
    short = ok(plugin, 'get_config')['filters'][3]
    assert short['device_count'] == 15 and len(short['devices']) == 10 and short['devices_truncated']
    full = ok(plugin, 'get_config', include_filter_devices=True)['filters'][3]
    assert len(full['devices']) == 15


# --- explain_device ---------------------------------------------------------------

def test_explain_the_dometic_cooler(house):
    """The case that motivated #11: the all-device setpoint filters block the
    cooler's real setpoints every 15 minutes."""
    plugin = house.plugin
    explained = ok(plugin, 'explain_device', device='Dometic CFX5 Cooler')

    assert explained['device'] == {'id': house.cooler.id, 'name': 'Dometic CFX5 Cooler'}
    assert explained['mode'] == 'global_states'
    states = {s['key']: s for s in explained['states']}
    assert states['coolSetpoint']['sent'] is False
    assert states['coolSetpoint']['reason'] == "blocked by filter 2 'coolSetpoint (all devices) min: 50.0, max: 100.0'"
    assert states['heatSetpoint']['filters'] == [{'position': 1, 'name': 'heatSetpoint (all devices) min: 30.0, max: 80.0', 'passes': False}]
    assert states['model']['sent'] is False and states['model']['reason'] == 'not in the global include list'
    assert states['name']['reason'] == 'always sent'
    assert explained['summary']['blocked_by_filters'] == 2


def test_explain_device_modes_and_cache_untouched(house):
    plugin = house.plugin
    cache_before = dict(plugin.adaptor.cache)
    lamp = ok(plugin, 'explain_device', device=house.lamp.id)
    noisy = ok(plugin, 'explain_device', device=str(house.noisy.id))
    assert lamp['mode'] == 'all_states'
    assert all(s['sent'] for s in lamp['states'])
    assert noisy['mode'] == 'excluded' and not any(s['sent'] for s in noisy['states'])
    assert plugin.adaptor.cache == cache_before  # to_json, never diff_to_json


def test_explain_unknown_device_suggests(house):
    err = error(house.plugin, 'explain_device', device='Dometic Cooler')
    assert err['type'] == 'not_found'
    assert 'Dometic CFX5 Cooler' in err['details']['did_you_mean']
    assert error(house.plugin, 'explain_device', device=999999)['type'] == 'not_found'


# --- search_states ----------------------------------------------------------------

def test_search_states_by_query(house):
    result = ok(house.plugin, 'search_states', query='setpoint')
    assert {r['state'] for r in result['results']} == {'coolSetpoint', 'heatSetpoint'}  # floats get no .num twin
    assert next(r for r in result['results'] if r['state'] == 'coolSetpoint')['included'] is True


def test_search_states_by_state(house):
    result = ok(house.plugin, 'search_states', state='coolSetpoint')
    assert result['total'] == 1
    assert result['results'][0]['name'] == 'Dometic CFX5 Cooler'
    assert result['results'][0]['value'] == 33.8
    assert result['results'][0]['sent'] is True


def test_search_states_pagination_and_validation(house, indigo):
    plugin = house.plugin
    for i in range(7):
        indigo.devices.add(FakeDevice(f"Sensor {i}", sensorValue=float(i)))
    plugin.catalogBuilt = None  # stale: rebuilt on demand
    page = ok(plugin, 'search_states', state='sensorValue', limit=3, offset=3)
    assert page['total'] == 8 and len(page['results']) == 3
    assert error(plugin, 'search_states')['type'] == 'validation'
    assert error(plugin, 'search_states', query='a', state='b')['type'] == 'validation'
    assert error(plugin, 'search_states', query='a', limit=500)['type'] == 'validation'
    missing = error(plugin, 'search_states', state='sensorValu')
    assert missing['type'] == 'not_found' and 'sensorValue' in missing['details']['did_you_mean']


# --- get_filter_blocks --------------------------------------------------------------

def test_get_filter_blocks(house):
    plugin = house.plugin
    plugin.everConnected = True
    plugin.DeviceToInflux(None, house.cooler, False)
    with open(plugin.FilterLogFileLoc, 'a') as log:
        log.write("2026-10-14 07:47: Filter block (Temp Max Percent Changed): a value (previous value: 70.0, new value: 200.0) "
                  "for state/property 'sensorValue' on device 'Living Room Temperature' exceeded percent changed "
                  "(percent changed: 185.71428571428572%, threshhold: 25.0%) and will not be sent to InfluxDB.  The device "
                  "has also been locked out of minimum-frequency updates until it reports a change.\n")
        log.write("some other line\n")

    blocks = ok(plugin, 'get_filter_blocks')
    assert blocks['count'] == 4
    assert blocks['entries'][0] == {'raw': 'some other line'}
    percent = blocks['entries'][1]
    assert percent['previous_value'] == '70.0' and percent['locked'] is True
    assert percent['reason'] == 'changed 185.71428571428572% (more than 25.0%)'

    cooler = ok(plugin, 'get_filter_blocks', device='Dometic CFX5 Cooler', state='coolSetpoint')
    assert cooler['count'] == 1
    entry = cooler['entries'][0]
    assert entry['filter'] == 'coolSetpoint (all devices) min: 50.0, max: 100.0'
    assert entry['value'] == '33.8' and entry['reason'] == 'outside the range 50.0 .. 100.0' and entry['locked'] is False


def test_get_filter_blocks_without_a_log(house):
    result = ok(house.plugin, 'get_filter_blocks', limit=5)
    assert result['count'] == 0


def test_startup_announces_the_tools(house, indigo):
    assert ('mcp_tools_updated', None) in indigo.server.broadcasts
