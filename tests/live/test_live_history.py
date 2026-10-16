"""
Live test of influxlog_query_history (mcp_api/history.py) against real servers:
run by tests/live/run_influx_matrix.sh with the rest of tests/live.  Skipped
unless INFLUX_LIVE=1.

Proves the InfluxQL HistoryReader builds on InfluxDB 1.8 and 3 (::tag on a name
that 1.x also stores as a field, epoch seconds, GROUP BY time with an offset,
ORDER BY time DESC, != on numbers, retention policies on 1.x) and the tool end
to end through handle_mcp_tool_invoke, including credentials that may only write.
"""

import datetime
import json
import os
import time
import types
import uuid

import pytest
import requests

from conftest import FakeDevice, FakeVariable
from influx_client import InfluxClient, make_line
from mcp_api.history import HistoryReader, bucket_offset

pytestmark = pytest.mark.skipif(os.environ.get('INFLUX_LIVE') != '1', reason="live InfluxDB matrix only")

UTC = datetime.timezone.utc
PORT_18 = int(os.environ.get('INFLUX18_PORT', '0'))
ADMIN = (os.environ.get('INFLUX18_ADMIN', ''), os.environ.get('INFLUX18_ADMIN_PASSWORD', ''))
PORT_3 = int(os.environ.get('INFLUX3_PORT', '0'))
TOKEN_3 = os.environ.get('INFLUX3_TOKEN', '')
V3_DB = 'igd_live'  # shared with test_live_influx.py (InfluxDB 3 Core allows five databases)
HOUR = 3600


def unique(prefix):
    return f"{prefix} {uuid.uuid4().hex[:8]}"


def admin18(database=''):
    return InfluxClient('127.0.0.1', PORT_18, username=ADMIN[0], password=ADMIN[1], database=database)


def client3(database=V3_DB, token=None):
    return InfluxClient('127.0.0.1', PORT_3, username='indigo', password=token or TOKEN_3, database=database)


def server_setup(server, database=None):
    """(database, plugin prefs, client) for a server, creating a 1.x database."""
    if server == '1.8':
        database = database or unique('igd_hist').replace(' ', '_')
        admin18().create_database(database)
        prefs = dict(InfluxHTTPPort=str(PORT_18), InfluxUser=ADMIN[0], InfluxPassword=ADMIN[1], InfluxVersion='1')
        return database, prefs, admin18(database)
    prefs = dict(InfluxHTTPPort=str(PORT_3), InfluxUser='indigo', InfluxPassword=TOKEN_3, InfluxVersion='3')
    return V3_DB, prefs, client3()


def write(server, database, points, policy=None):
    """Write points shaped as the plugin writes them (on InfluxDB 1.x the device
    name is a tag and a field; on 3 the field is dropped, as SendToInflux does)."""
    lines = []
    for p in points:
        fields = dict(p['fields'])
        if server == '3':
            fields = {k: v for k, v in fields.items() if k not in p['tags']}
        lines.append(make_line(p['measurement'], p['tags'], fields, p['time']))
    body = ('\n'.join(lines) + '\n').encode()
    if server == '1.8':
        params = {'db': database}
        if policy:
            params['rp'] = policy
        response = requests.post(f"http://127.0.0.1:{PORT_18}/write", params=params, data=body, auth=ADMIN, timeout=10)
    else:
        response = requests.post(f"http://127.0.0.1:{PORT_3}/write", params={'db': database}, data=body,
                                 auth=('indigo', TOKEN_3), timeout=10)
    assert response.status_code in (200, 204), response.text


def at(seconds_ago):
    return datetime.datetime.fromtimestamp(int(time.time()) - seconds_ago, UTC)


def device_point(name, seconds_ago, measurement='device_changes', **fields):
    return {'measurement': measurement, 'tags': {'name': name, 'folderId': '0'},
            'fields': dict(fields, name=name, id=1234.0), 'time': at(seconds_ago)}


def invoke(plugin, **arguments):
    import indigo
    action = types.SimpleNamespace(props={'tool': 'query_history', 'arguments': json.dumps(arguments)})
    before = len(indigo.completion_handlers)
    reply = plugin.handle_mcp_tool_invoke(action, caller_waiting_for_result=True)
    if reply is None:
        handler = indigo.completion_handlers[before]
        deadline = time.monotonic() + 30
        while handler.result is None and time.monotonic() < deadline:
            time.sleep(0.05)
        reply = handler.result
    return json.loads(reply)


# --- the statements ----------------------------------------------------------------

@pytest.mark.parametrize("server", ['1.8', '3'])
def test_reader_statements(server):
    database, prefs, client = server_setup(server)
    name = unique("Hist Sensor")
    write(server, database, [
        device_point(name, 3 * 86400, sensorValue=59.0),
        device_point(name, 3 * HOUR, sensorValue=60.0, onState=False, **{'state.hvac_state': 'heat'}),
        device_point(name, 2 * HOUR, sensorValue=62.0, onState=True, **{'state.hvac_state': 'off'}),
        device_point(name, 1 * HOUR, sensorValue=64.0, onState=False, **{'state.hvac_state': 'off'}),
    ])
    reader = HistoryReader(client, database, '1' if server == '1.8' else '3')
    now = int(time.time())
    args = ('device_changes', 'name', name)

    points, truncated = reader.points(*args, 'sensorValue', now - 4 * HOUR, now)
    assert [v for _, v in points] == [60.0, 62.0, 64.0] and not truncated
    assert reader.points(*args, 'sensorValue', now - 4 * HOUR, now, limit=2)[1] is True
    assert reader.points(*args, 'onState', now - 4 * HOUR, now)[0][1][1] is True
    assert reader.last_before(*args, 'sensorValue', now - 4 * HOUR)[1] == 59.0
    assert reader.last_different(*args, 'sensorValue', 64.0, now)[1] == 62.0
    assert reader.last_different(*args, 'sensorValue', 64.0, now - 2 * HOUR - 60)[1] == 60.0

    offset = bucket_offset(HOUR, now)
    rows = reader.buckets(*args, 'sensorValue', now - 4 * HOUR, now, HOUR, offset)
    assert sum(r[4] for r in rows) == 3 and min(r[1] for r in rows) == 60.0 and max(r[3] for r in rows) == 64.0
    assert all((r[0] - offset) % HOUR == 0 for r in rows)
    present = reader.present_buckets(*args, 'sensorValue', now - 4 * HOUR, now, HOUR, offset)
    assert len(present) in (3, 4) and present <= {r[0] for r in rows} | present

    figures = reader.aggregate(*args, 'sensorValue', now - 4 * HOUR, now)
    assert figures['count'] == 3 and figures['first'][1] == 60.0 and figures['last'][1] == 64.0
    assert figures['numbers'] == {'min': 60.0, 'max': 64.0, 'mean': 62.0}
    text = reader.aggregate(*args, 'state.hvac_state', now - 4 * HOUR, now)
    assert text['count'] == 3 and text['numbers'] is None and text['last'][1] == 'off'

    # an apostrophe, a double quote (InfluxDB 3 refuses one inside a string literal)
    # and a backslash (InfluxDB 1.x stores the plugin's escaped one doubled)
    for odd in (unique("Bob's Lamp"), unique('TV 65" (Den)'), unique('Back\\slash "q"'), unique('Back\\slash')):
        write(server, database, [device_point(odd, HOUR, onState=True)])
        assert len(reader.points('device_changes', 'name', odd, 'onState', now - 2 * HOUR, now)[0]) == 1, odd


def test_v1_reads_every_retention_policy():
    database, prefs, client = server_setup('1.8')
    admin18().create_retention_policy('indigo_policy', database, '720d', default=True)
    name = unique("Split Sensor")
    write('1.8', database, [device_point(name, 3 * HOUR, sensorValue=1.0)], policy='autogen')
    write('1.8', database, [device_point(name, 2 * HOUR, sensorValue=2.0)])  # the default: indigo_policy
    reader = HistoryReader(client, database, '1')
    assert set(reader.sources()) == {'autogen', 'indigo_policy'}
    now = int(time.time())
    points, _ = reader.points('device_changes', 'name', name, 'sensorValue', now - 4 * HOUR, now)
    assert [v for _, v in points] == [1.0, 2.0]


# --- the tool, end to end -------------------------------------------------------------

@pytest.mark.parametrize("server", ['1.8', '3'])
def test_query_history_end_to_end(make_plugin, indigo, server):
    database, prefs, client = server_setup(server)
    sensor = indigo.devices.add(FakeDevice(unique("Live Sensor"), sensorValue=64.0))
    lamp = indigo.devices.add(FakeDevice(unique("Live Lamp"), onState=False))
    thermostat = indigo.devices.add(FakeDevice(unique("Live Thermostat"), heatSetpoint=68.0,
                                               states={'setpointHeat': 68.0, 'hvac_state': 'off'}))
    variable = indigo.variables.add(FakeVariable(unique("Live Mode"), "home"))
    points = []
    for i in range(24):
        ago = 23 * HOUR - i * HOUR + 600
        points.append(device_point(sensor.name, ago, sensorValue=60.0 + i % 5))
        points.append(device_point(thermostat.name, ago, 'thermostat_changes', heatSetpoint=68.0,
                                   **{'state.hvac_state': 'heat' if i < 20 else 'off'}))
    points += [device_point(lamp.name, 30 * HOUR, onState=False), device_point(lamp.name, 5 * HOUR, onState=True),
               device_point(lamp.name, 3 * HOUR, onState=False)]
    points += [{'measurement': 'variable_changes', 'tags': {'varname': variable.name},
                'fields': {'name': variable.name, 'value': value}, 'time': at(ago)}
               for value, ago in (('away', 30 * HOUR), ('home', 4 * HOUR))]
    write(server, database, points)

    plugin = make_plugin(InfluxHost='127.0.0.1', InfluxDB=database, MinimumUpdateFrequency='60',
                         listIncStates=['sensorValue', 'onState', 'heatSetpoint', 'state.hvac_state'], **prefs)
    reply = invoke(plugin, devices=[sensor.name, lamp.id, thermostat.name], variables=[variable.name],
                   states=['sensorValue', 'onState', 'hvac_state'], bucket='hour')
    assert reply['status'] == 'ok', reply
    results = reply['result']['results']

    reading = next(s for s in results[0]['states'] if s['state'] == 'sensorValue')
    assert reading['points'] == 24 and reading['summary']['min'] == 60.0 and reading['summary']['max'] == 64.0
    assert sum(row[4] for row in reading['series']['rows']) == 24
    assert results[0]['gaps']['count'] == 0 and 'gaps' not in reading

    on = next(s for s in results[1]['states'] if s['state'] == 'onState')
    assert on['value_at_start'] is False and [c['value'] for c in on['changes']] == [True, False]
    assert next(x for x in on['time_in_state'] if x['value'] is True)['seconds'] == 2 * HOUR

    assert results[2]['measurement'] == 'thermostat_changes'
    hvac = next(s for s in results[2]['states'] if s['state'] == 'state.hvac_state')
    assert [c['value'] for c in hvac['changes']] == ['off']

    mode = results[3]['history']
    assert mode['value_at_start'] == 'away' and mode['changes'][0]['value'] == 'home'


@pytest.mark.parametrize("server", ['1.8', '3'])
def test_credentials_that_may_only_write(make_plugin, indigo, server):
    sensor = indigo.devices.add(FakeDevice(unique("Locked Sensor"), sensorValue=1.0))
    if server == '1.8':
        database, _, _ = server_setup('1.8')
        user = unique('writer').replace(' ', '_')
        admin18().query(f"CREATE USER \"{user}\" WITH PASSWORD 'pw-{user}'")
        admin18().query(f'GRANT WRITE ON "{database}" TO "{user}"')
        prefs = dict(InfluxHTTPPort=str(PORT_18), InfluxUser=user, InfluxPassword=f"pw-{user}", InfluxVersion='1')
    else:
        database = V3_DB  # InfluxDB 3 Core has no write-only tokens: a refused token gives the same answer
        prefs = dict(InfluxHTTPPort=str(PORT_3), InfluxUser='indigo', InfluxPassword='apiv3_revoked', InfluxVersion='3')
    plugin = make_plugin(InfluxHost='127.0.0.1', InfluxDB=database, **prefs)
    reply = invoke(plugin, devices=[sensor.name], states=['sensorValue'])
    assert reply['status'] == 'error', reply
    assert reply['error']['type'] == 'conflict' and 'read access' in reply['error']['message']
    assert reply['error']['details']['status_code'] in (401, 403)
