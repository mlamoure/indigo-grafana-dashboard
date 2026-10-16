"""
influxlog_query_history (mcp_api/history.py): reading back what devices and
variables did.  The pure analysis is tested directly; the tool end to end runs
through plugin.handle_mcp_tool_invoke against FakeHistoryClient, which answers
only the InfluxQL statements HistoryReader builds (tests/live runs the same
statements against real InfluxDB 1.8 and 3).
"""

import datetime
import json
import threading
import time
import types

import pytest

from conftest import FakeDevice, FakeVariable
from fake_influx import FakeHistoryClient, InfluxConnectionError, http_error

import mcp_api.history as history
from mcp_api.errors import ToolError
from mcp_api.history import (bucket_interval, bucket_offset, bucketed_time_in_state, change_points, classify,
                             find_gaps, format_duration, gaps_from_buckets, numeric_summary, parse_window,
                             time_in_state)

SECRET = 's3cret-token-value'  # BASE_PREFS' password
HOUR = 3600
DAY = 86400


def invoke(plugin, tool, **arguments):
    """Call a tool the way MCP Advanced Tools does; wait for the worker thread."""
    import indigo
    action = types.SimpleNamespace(props={'tool': tool, 'arguments': json.dumps(arguments)})
    before = len(indigo.completion_handlers)
    reply = plugin.handle_mcp_tool_invoke(action, caller_waiting_for_result=True)
    if reply is None:
        handler = indigo.completion_handlers[before]
        deadline = time.monotonic() + 10
        while handler.result is None and time.monotonic() < deadline:
            time.sleep(0.01)
        reply = handler.result
    assert isinstance(reply, str), reply
    assert SECRET not in reply
    return json.loads(reply)


def ok(plugin, **arguments):
    reply = invoke(plugin, 'query_history', **arguments)
    assert reply['status'] == 'ok', reply
    return reply['result']


def error(plugin, **arguments):
    reply = invoke(plugin, 'query_history', **arguments)
    assert reply['status'] == 'error', reply
    return reply['error']


def state(result, index=0, key=None):
    entry = result['results'][index]
    if key is None:
        return entry
    return next(s for s in entry['states'] if s['state'] == key)


@pytest.fixture
def house(indigo, make_plugin):
    office = indigo.devices.add(FakeDevice("Office Temperature", sensorValue=72.0))
    lamp = indigo.devices.add(FakeDevice("Hall Lamp", onState=False, states={'onOffState': False}))
    thermostat = indigo.devices.add(FakeDevice("Upstairs Thermostat", heatSetpoint=68.0,
                                               states={'setpointHeat': 68.0, 'hvac_state': 'heat'}))
    meter = indigo.devices.add(FakeDevice("Garage Meter", energyCurLevel=120.0))
    dimmer = indigo.devices.add(FakeDevice("Den Dimmer", onState=True, brightness=40.0, model="Dimmer X"))
    mode = indigo.variables.add(FakeVariable("House Mode", "home"))
    target = indigo.variables.add(FakeVariable("Target Temperature", "70"))
    plugin = make_plugin(listIncStates=['sensorValue', 'onState', 'heatSetpoint', 'state.hvac_state', 'model'],
                         listExclDevices=[meter.id], listIncDevices=[dimmer.id])
    client = FakeHistoryClient()
    plugin.newClient = lambda settings: client
    now = int(time.time())
    return types.SimpleNamespace(plugin=plugin, client=client, now=now, office=office, lamp=lamp,
                                 thermostat=thermostat, meter=meter, dimmer=dimmer, mode=mode, target=target)


def heartbeats(client, measurement, tags, start, end, step=900, **fields_at):
    """A point every `step` seconds; fields_at maps field -> function(t) -> value."""
    t = start
    while t <= end:
        client.add(measurement, tags, t, **{field: fn(t) for field, fn in fields_at.items()})
        t += step


# --- pure analysis ---------------------------------------------------------------

def test_format_duration():
    assert format_duration(30) == "30s"
    assert format_duration(45 * 60) == "45m"
    assert format_duration(6 * HOUR + 12 * 60) == "6h 12m"
    assert format_duration(2 * DAY + 3 * HOUR + 59) == "2d 3h"


def test_classify():
    assert classify([True, False]) == 'boolean'
    assert classify([1.0, 2]) == 'numeric'
    assert classify(['heat', 'off']) == 'text'
    assert classify([1.0, 'x']) == 'text'


def test_change_points_seeded_by_the_value_before_the_window():
    points = [(10, 'off'), (20, 'on'), (30, 'on'), (40, 'off')]
    assert change_points(points) == [(20, 'on'), (40, 'off')]
    assert change_points(points, before=(5, 'on')) == [(10, 'off'), (20, 'on'), (40, 'off')]


def test_time_in_state():
    points = [(100, True), (300, False)]
    held, unknown = time_in_state(points, (50, False), 0, 1000)
    assert held == {False: 100 + 700, True: 200} and unknown == 0
    held, unknown = time_in_state(points, None, 0, 1000)
    assert held == {True: 200, False: 700} and unknown == 100


def test_bucketed_time_in_state_splits_at_bucket_edges():
    rows = bucketed_time_in_state([(1800, True), (5400, False)], (0, False), 0, 7200, HOUR, 0)
    assert rows == [(0, {False: 1800, True: 1800}), (3600, {True: 1800, False: 1800})]


def test_numeric_summary_and_trend():
    summary = numeric_summary([(0, 68.0), (10, 66.5), (20, 72.25)], 30)
    assert (summary['min'], summary['max'], summary['current'], summary['first']) == (66.5, 72.25, 72.25, 68.0)
    assert summary['trend'] == 'rising' and summary['change'] == 4.25 and summary['mean'] == 68.917
    assert numeric_summary([(0, 70.0), (10, 70.05)], 10)['trend'] == 'steady'
    assert numeric_summary([(0, 70.0), (10, 69.0)], 10)['trend'] == 'falling'


def test_mean_is_weighted_by_time():
    """A burst of changes doesn't outweigh hours at one value."""
    burst = [(0, 60.0)] + [(3600 + i, 80.0) for i in range(10)]
    assert history.time_weighted_mean(burst, 3610) == pytest.approx(60.0, abs=0.06)
    assert numeric_summary(burst, 3610)['mean'] == pytest.approx(60.0, abs=0.06)
    assert history.time_weighted_mean([(5, 42.0)], 5) == 42.0


def test_find_gaps_includes_the_edges():
    assert find_gaps([100, 200, 900, 950], 0, 1000, 300) == [(200, 900)]
    assert find_gaps([500], 0, 1000, 300) == [(0, 500), (500, 1000)]
    assert find_gaps([], 0, 1000, 300) == [(0, 1000)]


def test_gaps_from_buckets_needs_two_empty_buckets():
    present = {0, 100, 300, 400, 500, 800}
    # 200 alone is one empty bucket (no gap); 600-799 is two
    assert gaps_from_buckets(present, 0, 1000, 100, 0) == [(600, 800)]
    assert gaps_from_buckets({0}, 0, 300, 100, 0) == [(100, 300)]


def test_parse_window_forms():
    now = datetime.datetime(2026, 10, 16, 12, 0).astimezone()
    w = parse_window(now=now)
    assert w.end == now and w.end - w.start == datetime.timedelta(hours=24)
    w = parse_window(days=7, now=now)
    assert w.end - w.start == datetime.timedelta(days=7)
    w = parse_window(start="2026-10-15T02:00", hours=2, now=now)
    assert (w.start.hour, w.end.hour) == (2, 4) and w.start.utcoffset() == now.utcoffset()
    w = parse_window(start="2026-10-15", end="2026-10-16T00:00", now=now)
    assert w.seconds == DAY
    w = parse_window(end="2026-10-15T06:00", hours=1, now=now)
    assert w.start.hour == 5
    w = parse_window(start="2026-10-16T10:00", now=now)
    assert w.end == now  # the end never runs past now
    w = parse_window(start="2026-10-15T02:00:00Z", end="2026-10-15T04:00:00+00:00", now=now)
    assert w.seconds == 2 * HOUR


@pytest.mark.parametrize("arguments,fragment", [
    ({'hours': 1, 'days': 1}, "not both"),
    ({'hours': 0}, "hours"),
    ({'days': 400}, "days"),
    ({'hours': True}, "hours"),
    ({'start': "yesterday"}, "ISO 8601"),
    ({'start': "2026-10-15T04:00", 'end': "2026-10-15T02:00"}, "start before"),
    ({'start': "2026-10-17T00:00"}, "start before"),
    ({'start': "2026-10-15T02:00", 'end': "2026-10-15T02:01"}, "5 minutes"),
    ({'start': "2024-01-01", 'end': "2026-10-15"}, "366 days"),
    ({'start': "2026-10-15T02:00", 'end': "2026-10-15T04:00", 'hours': 1}, "not all three"),
])
def test_parse_window_rejects(arguments, fragment):
    now = datetime.datetime(2026, 10, 16, 12, 0).astimezone()
    with pytest.raises(ToolError) as e:
        parse_window(now=now, **arguments)
    assert e.value.error_type == 'validation' and fragment in e.value.message


def test_bucket_interval():
    assert bucket_interval(DAY, "auto") == (900, None)
    assert bucket_interval(366 * DAY, "auto") == (172800, None)  # 183 two-day buckets
    assert bucket_interval(7 * DAY, "hour") == (HOUR, None)
    interval, note = bucket_interval(60 * DAY, "hour")
    assert interval == 21600 and "6h" in note


def test_day_buckets_start_at_local_midnight():
    at = int(time.time())
    offset = bucket_offset(DAY, at)
    start = history.bucket_start(at, DAY, offset)
    local = datetime.datetime.fromtimestamp(start).astimezone()
    assert (local.hour, local.minute) == (0, 0)


# --- the tool: numbers -------------------------------------------------------------

def test_numeric_state_summary_changes_and_no_gaps(house):
    c, now = house.client, house.now
    heartbeats(c, 'device_changes', {'name': 'Office Temperature'}, now - 2 * DAY, now - 60,
               sensorValue=lambda t: 66.0 if t < now - DAY + 4 * HOUR else 72.0)
    result = ok(house.plugin, devices=["Office Temperature"], states=["sensorValue"])

    entry = state(result)
    assert entry['device'] == {'id': house.office.id, 'name': 'Office Temperature'}
    assert entry['measurement'] == 'device_changes' and entry['mode'] == 'global_states'
    s = state(result, key='sensorValue')
    assert s['type'] == 'numeric' and s['points'] >= 95
    assert (s['summary']['min'], s['summary']['max'], s['summary']['trend']) == (66.0, 72.0, 'rising')
    assert s['changes_total'] == 1 and s['changes'][0]['value'] == 72.0
    assert entry['gaps']['count'] == 0 and entry['gaps']['threshold'] == '30m' and 'gaps' not in s
    assert result['minimum_update_frequency_minutes'] == 15
    assert result['window']['hours'] == 24.0
    # every query ran on the worker thread, never on Indigo's callback thread
    assert set(c.threads) == {'InfluxToolWorker'}
    assert all('"name"::tag = \'Office Temperature\'' in q for q in c.statements)
    assert c.closed


def test_gaps_are_listed_longest_first(house):
    c, now = house.client, house.now
    heartbeats(c, 'device_changes', {'name': 'Office Temperature'}, now - DAY - 600, now - 10 * HOUR,
               sensorValue=lambda t: 70.0 + (t % 7))
    heartbeats(c, 'device_changes', {'name': 'Office Temperature'}, now - 7 * HOUR, now - 2 * HOUR,
               sensorValue=lambda t: 70.0 + (t % 5))
    gaps = state(ok(house.plugin, devices=[house.office.id], states=["sensorValue"]))['gaps']
    assert gaps['count'] == 2
    assert gaps['longest_first'][0]['duration'].startswith('3h') or gaps['longest_first'][0]['duration'].startswith('2h')
    assert all(g['duration'] for g in gaps['longest_first'])


def test_a_quiet_state_on_a_busy_device_is_not_a_gap(house):
    """An unchanged state is re-sent only on the heartbeat, and every change of
    another state postpones that; gaps are about the device going silent."""
    c, now = house.client, house.now
    tags = {'name': 'Hall Lamp'}
    c.add('device_changes', tags, now - DAY + 60, onState=False)
    heartbeats(c, 'device_changes', tags, now - DAY + 300, now - 60, step=300, energyCurLevel=lambda t: float(t % 9))
    entry = state(ok(house.plugin, devices=["Hall Lamp"], states=["onState"]))
    on = next(s for s in entry['states'] if s['state'] == 'onState')
    assert on['points'] == 1 and on['time_in_state'][0]['value'] is False
    assert entry['gaps']['count'] == 0


def test_variable_gaps_come_from_its_value(house):
    c, now = house.client, house.now
    heartbeats(c, 'variable_changes', {'varname': 'House Mode'}, now - DAY + 60, now - 8 * HOUR, value=lambda t: 'home')
    entry = ok(house.plugin, variables=["House Mode"])['results'][0]
    assert entry['gaps']['count'] == 1 and entry['gaps']['longest_first'][0]['duration'].startswith('8h')


def test_flat_line_says_when_the_value_last_differed(house):
    c, now = house.client, house.now
    c.add('device_changes', {'name': 'Office Temperature'}, now - 5 * DAY, sensorValue=69.1)
    heartbeats(c, 'device_changes', {'name': 'Office Temperature'}, now - 4 * DAY, now - 60, sensorValue=lambda t: 72.0)
    s = state(ok(house.plugin, devices=["Office Temperature"], states=["sensorValue"]), key='sensorValue')
    assert s['summary']['trend'] == 'steady'
    assert s['flat']['last_different']['value'] == 69.1
    assert 'stuck or offline' in s['flat']['hint']
    assert any('!= 72.0' in q for q in house.client.statements)


def test_flat_line_with_no_different_value(house):
    heartbeats(house.client, 'device_changes', {'name': 'Office Temperature'}, house.now - DAY + 60, house.now - 60,
               sensorValue=lambda t: 72.0)
    s = state(ok(house.plugin, devices=["Office Temperature"], states=["sensorValue"]), key='sensorValue')
    assert s['flat']['last_different'] is None


def test_numeric_series_per_day_from_influxdb(house):
    c, now = house.client, house.now
    heartbeats(c, 'device_changes', {'name': 'Office Temperature'}, now - 3 * DAY, now - 60, step=HOUR,
               sensorValue=lambda t: 60.0 + (t // HOUR) % 10)
    s = state(ok(house.plugin, devices=["Office Temperature"], states=["sensorValue"], days=3, bucket="day"),
              key='sensorValue')
    series = s['series']
    assert series['bucket'] == '1d' and series['columns'] == ['start', 'min', 'mean', 'max', 'points']
    assert 3 <= len(series['rows']) <= 4
    for start, low, mean, high, count in series['rows']:
        assert datetime.datetime.fromisoformat(start).hour == 0  # local midnight
        assert low <= mean <= high and count > 0
    assert any('GROUP BY time(86400s' in q for q in c.statements)


def test_many_numeric_changes_leave_the_list_out(house):
    heartbeats(house.client, 'device_changes', {'name': 'Office Temperature'}, house.now - DAY + 60, house.now - 60,
               step=600, sensorValue=lambda t: float(t % 13))
    s = state(ok(house.plugin, devices=["Office Temperature"], states=["sensorValue"], max_changes=5), key='sensorValue')
    assert s['changes_total'] > 5 and 'changes' not in s


# --- on/off and text -----------------------------------------------------------------

def test_boolean_changes_and_time_in_state(house):
    c, now = house.client, house.now
    tags = {'name': 'Hall Lamp'}
    c.add('device_changes', tags, now - 30 * HOUR, onState=False)
    on, off = now - 10 * HOUR, now - 8 * HOUR
    heartbeats(c, 'device_changes', tags, now - DAY + 300, now - 60,
               onState=lambda t: on <= t < off)
    c.add('device_changes', tags, on, onState=True)
    c.add('device_changes', tags, off, onState=False)

    s = state(ok(house.plugin, devices=["Hall Lamp"], states=["onState"]), key='onState')
    assert s['type'] == 'boolean' and s['value_at_start'] is False and s['current'] is False
    assert [x['value'] for x in s['changes']] == [True, False] and s['changes_total'] == 2
    held = {x['value']: x for x in s['time_in_state']}
    assert held[True]['seconds'] == 2 * HOUR and held[True]['duration'] == '2h'
    assert held[False]['seconds'] == 22 * HOUR
    assert 'unknown_before_first_point' not in s


def test_boolean_series_hours_on_per_bucket(house):
    c, now = house.client, house.now
    tags = {'name': 'Hall Lamp'}
    c.add('device_changes', tags, now - 3 * DAY, onState=False)
    c.add('device_changes', tags, now - 30 * HOUR, onState=True)
    c.add('device_changes', tags, now - 27 * HOUR, onState=False)
    s = state(ok(house.plugin, devices=["Hall Lamp"], states=["onState"], days=2, bucket="day"), key='onState')
    rows = s['series']['rows']
    assert s['series']['columns'] == ['start', 'seconds_by_value']
    assert sum(row[1].get('true', 0) for row in rows) == 3 * HOUR
    assert sum(sum(row[1].values()) for row in rows) == 2 * DAY


def test_many_toggles_keep_the_newest(house):
    c, now = house.client, house.now
    for i in range(30):
        c.add('device_changes', {'name': 'Hall Lamp'}, now - DAY + 600 + i * 600, onState=bool(i % 2))
    s = state(ok(house.plugin, devices=["Hall Lamp"], states=["onState"], max_changes=10), key='onState')
    assert len(s['changes']) == 10 and s['changes_total'] == 29
    assert '10 of 29' in s['changes_truncated']
    assert s['unknown_before_first_point'] == '10m'


def test_thermostat_reads_its_own_measurement_and_a_bare_state_key(house):
    c, now = house.client, house.now
    tags = {'name': 'Upstairs Thermostat'}
    heartbeats(c, 'thermostat_changes', tags, now - DAY + 60, now - 60,
               **{'state.hvac_state': lambda t: 'heat' if t < now - 6 * HOUR else 'off', 'heatSetpoint': lambda t: 68.0})
    result = ok(house.plugin, devices=["Upstairs Thermostat"], states=["hvac_state", "heatSetpoint"])
    assert state(result)['measurement'] == 'thermostat_changes'
    hvac = state(result, key='state.hvac_state')
    assert hvac['note'] == 'read as state.hvac_state' and hvac['type'] == 'text'
    assert hvac['changes'] == [{'time': hvac['changes'][0]['time'], 'value': 'off'}]
    assert all('"thermostat_changes"' in q for q in c.statements)


def test_variables_text_and_numeric(house):
    c, now = house.client, house.now
    c.add('variable_changes', {'varname': 'House Mode'}, now - 2 * DAY, value='away', name='House Mode')
    c.add('variable_changes', {'varname': 'House Mode'}, now - 5 * HOUR, value='home', name='House Mode')
    heartbeats(c, 'variable_changes', {'varname': 'Target Temperature'}, now - DAY + 60, now - 60,
               **{'value': lambda t: '70', 'value.num': lambda t: 70.0 if t < now - HOUR else 71.0})
    result = ok(house.plugin, variables=["House Mode", house.target.id])
    mode = result['results'][0]
    assert mode['variable'] == {'id': house.mode.id, 'name': 'House Mode'}
    assert mode['measurement'] == 'variable_changes'
    assert mode['history']['state'] == 'value' and mode['history']['value_at_start'] == 'away'
    assert {x['value'] for x in mode['history']['time_in_state']} == {'away', 'home'}
    target = result['results'][1]['history']
    assert target['state'] == 'value.num' and target['summary']['max'] == 71.0
    assert all('"varname"::tag' in q for q in c.statements)


# --- default states ------------------------------------------------------------------

def test_default_states_are_the_logged_ones_without_metadata(house):
    c, now = house.client, house.now
    c.add('device_changes', {'name': 'Den Dimmer'}, now - HOUR, onState=True, brightness=40.0)
    result = ok(house.plugin, devices=["Den Dimmer"])
    keys = [s['state'] for s in state(result)['states']]
    assert keys[0] == 'onState' and 'brightness' in keys
    assert len(keys) <= history.DEFAULT_STATE_COUNT
    for unwanted in ('model', 'model.num', 'name', 'id', 'id.num', 'lastChanged', 'onState.num', 'brightness.num',
                     'state.onOffState', 'enabled', 'configured', 'folderId'):
        assert unwanted not in keys


def test_excluded_device_without_states_explains(house):
    result = ok(house.plugin, devices=["Garage Meter"])
    entry = state(result)
    assert entry['mode'] == 'excluded' and entry['states'] == []
    assert 'excluded' in entry['notes'][0]
    assert house.client.statements == []


# --- no data ---------------------------------------------------------------------------

def test_no_data_says_the_state_is_not_logged(house):
    s = state(ok(house.plugin, devices=["Office Temperature"], states=["batteryLevel"]), key='batteryLevel')
    assert s['points'] == 0
    reasons = s['no_data']['reasons']
    assert any('not in the global include list' in r for r in reasons)
    assert any('does not have this state' in r for r in reasons)
    assert s['no_data']['last_logged_before_window'] is None
    assert 'not a current state' in s['note']


def test_no_data_for_an_excluded_device_with_older_history(house):
    house.client.add('device_changes', {'name': 'Garage Meter'}, house.now - 3 * DAY, energyCurLevel=99.0)
    s = state(ok(house.plugin, devices=["Garage Meter"], states=["energyCurLevel"]), key='energyCurLevel')
    assert any('device is excluded' in r for r in s['no_data']['reasons'])
    assert s['no_data']['last_logged_before_window']['value'] == 99.0


def test_no_data_names_the_filter_that_blocks_the_current_value(house, make_plugin, indigo):
    plugin = make_plugin(listIncStates=['sensorValue'], MinimumUpdateFrequency='-1',
                         listFilterList=[['sensorValue', 'minMax', 0.0, 50.0, 0.0, True, [], True, False, '']])
    plugin.newClient = lambda settings: house.client
    with open(plugin.FilterLogFileLoc, 'w') as f:
        f.write("2026-10-16 08:00: Filter block (sensorValue (all devices) min: 0.0, max: 50.0): a value (72.0) for "
                "state/property 'sensorValue' on device 'Office Temperature' was not in the configured range "
                "(0.0, 50.0) and will not be sent to InfluxDB\n")
    house.client.add('device_changes', {'name': 'Office Temperature'}, house.now - 2 * DAY, sensorValue=40.0)
    result = ok(plugin, devices=["Office Temperature"], states=["sensorValue"])
    reasons = state(result, key='sensorValue')['no_data']['reasons']
    assert any("blocked by filter 1" in r for r in reasons)
    assert any("filter.log holds 1 blocked value" in r for r in reasons)
    assert any("heartbeats are off" in r for r in reasons)
    assert result['minimum_update_frequency_minutes'] is None
    assert 'gaps are not reported' in result['notes'][0]


# --- InfluxDB 1.x retention policies ------------------------------------------------------

def test_v1_reads_every_retention_policy_and_merges(house):
    c, now = house.client, house.now
    c.policies = ['indigo_policy', 'autogen']
    c.add('device_changes', {'name': 'Office Temperature'}, now - 3 * HOUR, policy='autogen', sensorValue=60.0)
    c.add('device_changes', {'name': 'Office Temperature'}, now - 2 * HOUR, policy='indigo_policy', sensorValue=62.0)
    c.add('device_changes', {'name': 'Office Temperature'}, now - 1 * HOUR, policy='autogen', sensorValue=64.0)
    s = state(ok(house.plugin, devices=["Office Temperature"], states=["sensorValue"], bucket="hour"),
              key='sensorValue')
    assert s['points'] == 3 and s['summary']['first'] == 60.0 and s['summary']['current'] == 64.0
    assert [x['value'] for x in s['changes']] == [62.0, 64.0]
    assert sum(row[4] for row in s['series']['rows']) == 3
    assert any('"autogen"."device_changes"' in q for q in c.statements)
    assert any('"indigo_policy"."device_changes"' in q for q in c.statements)


def test_v3_reads_the_measurement_without_a_policy(house, make_plugin):
    plugin = make_plugin(InfluxVersion='3')
    plugin.newClient = lambda settings: house.client
    house.client.policies = ['should-not-be-used']
    house.client.add('device_changes', {'name': 'Office Temperature'}, house.now - HOUR, policy=None, sensorValue=1.0)
    house.client.policies = None
    ok(plugin, devices=["Office Temperature"], states=["sensorValue"])
    assert all(' FROM "device_changes"' in q for q in house.client.statements)


# --- big windows ---------------------------------------------------------------------------

def test_too_many_points_falls_back_to_influxdb_aggregates(house, monkeypatch):
    monkeypatch.setattr(history, 'RAW_POINT_CAP', 10)
    c, now = house.client, house.now
    heartbeats(c, 'device_changes', {'name': 'Office Temperature'}, now - DAY + 60, now - 10 * HOUR,
               sensorValue=lambda t: 60.0 + (t // 900) % 4)
    heartbeats(c, 'device_changes', {'name': 'Office Temperature'}, now - 6 * HOUR, now - 60,
               sensorValue=lambda t: 70.0)
    result = ok(house.plugin, devices=["Office Temperature"], states=["sensorValue"], bucket="auto")
    s = state(result, key='sensorValue')
    assert s['points'] > 10 and 'too many to list' in s['truncated']
    assert s['summary']['current'] == 70.0 and s['summary']['min'] == 60.0 and s['summary']['max'] == 70.0
    assert 'mean_of_points' in s['summary'] and 'mean' not in s['summary']
    assert 'changes' not in s and s['series']['rows']
    gaps = state(result)['gaps']
    assert gaps['count'] == 1  # the 4-hour hole, found from empty buckets


def test_too_many_text_points_reports_what_it_can(house, monkeypatch):
    monkeypatch.setattr(history, 'RAW_POINT_CAP', 5)
    heartbeats(house.client, 'device_changes', {'name': 'Hall Lamp'}, house.now - DAY + 60, house.now - 60,
               onState=lambda t: bool((t // 900) % 2))
    s = state(ok(house.plugin, devices=["Hall Lamp"], states=["onState"]), key='onState')
    assert 'too many to list' in s['truncated'] and s['type'] == 'boolean' and 'summary' not in s
    assert s['points'] == 96 and isinstance(s['current'], bool)


def test_time_budget_skips_the_rest(house, monkeypatch):
    monkeypatch.setattr(history, 'TIME_BUDGET', -1)
    result = ok(house.plugin, devices=["Office Temperature"], states=["sensorValue", "onState"])
    assert all('ran out of time' in s['skipped'] for s in state(result)['states'])


# --- errors ------------------------------------------------------------------------------------

def test_credentials_that_cannot_read(house):
    house.client.query_error = http_error(401, 'unauthorized access')
    err = error(house.plugin, devices=["Office Temperature"], states=["sensorValue"])
    assert err['type'] == 'conflict' and 'read access' in err['message'] and err['details']['status_code'] == 401
    assert house.client.closed


def test_unreachable_influxdb(house):
    house.client.query_error = InfluxConnectionError('ConnectTimeout: timed out')
    err = error(house.plugin, devices=["Office Temperature"], states=["sensorValue"])
    assert err['type'] == 'internal' and 'could not be reached' in err['message']


def test_a_statement_error_stays_with_its_state(house):
    from fake_influx import InfluxQueryError
    house.client.query_error = InfluxQueryError('field type conflict', 200)
    s = state(ok(house.plugin, devices=["Office Temperature"], states=["sensorValue"]), key='sensorValue')
    assert 'field type conflict' in s['error']


def test_not_configured(make_plugin, indigo):
    plugin = make_plugin(start=False)
    plugin.configured = False
    indigo.devices.add(FakeDevice("Office Temperature", sensorValue=1.0))
    err = error(plugin, devices=["Office Temperature"])
    assert err['type'] == 'conflict'


@pytest.mark.parametrize("arguments,fragment", [
    ({}, "give devices and/or variables"),
    ({'devices': []}, "non-empty list"),
    ({'devices': ["A", "B", "C", "D", "E", "F"]}, "at most 5"),
    ({'variables': ["House Mode"], 'states': ["value"]}, "states apply to devices"),
    ({'devices': ["Office Temperature"], 'states': "sensorValue"}, "list of state keys"),
    ({'devices': ["Office Temperature"], 'states': [str(i) for i in range(9)]}, "at most 8"),
    ({'devices': ["Office Temperature"], 'bucket': "week"}, "bucket"),
    ({'devices': ["Office Temperature"], 'max_changes': 0}, "max_changes"),
    ({'devices': ["Office Temperature"], 'hours': 1, 'days': 1}, "not both"),
])
def test_validation(house, arguments, fragment):
    err = error(house.plugin, **arguments)
    assert err['type'] == 'validation' and fragment in err['message']
    assert house.client.statements == []


def test_unknown_device_suggests(house):
    err = error(house.plugin, devices=["Office Temprature"])
    assert err['type'] == 'not_found' and 'Office Temperature' in err['details']['did_you_mean']
    err = error(house.plugin, variables=["House Mood"])
    assert err['type'] == 'not_found' and 'House Mode' in err['details']['did_you_mean']


def test_too_many_series(house):
    err = error(house.plugin, devices=["Office Temperature", "Hall Lamp", "Upstairs Thermostat"],
                states=["a", "b", "c", "d", "e", "f"])
    assert err['type'] == 'validation' and '18' in err['message']


def test_a_name_with_an_apostrophe_is_escaped(house, indigo):
    odd = indigo.devices.add(FakeDevice("Bob's Reading Lamp", onState=True))
    house.client.add('device_changes', {'name': odd.name}, house.now - HOUR, onState=True)
    s = state(ok(house.plugin, devices=[odd.id], states=["onState"]), key='onState')
    assert s['points'] == 1
    assert any("\"name\"::tag = 'Bob\\'s Reading Lamp'" in q for q in house.client.statements)


def test_a_name_with_a_double_quote_matches_by_anchored_regex(house, indigo):
    """InfluxDB 3 refuses a double quote inside a string literal ("invalid escape
    sequence"), and a name like TV 65" is ordinary."""
    tv = indigo.devices.add(FakeDevice('Den TV 65" (Sony) 1.5+', onState=True))
    house.client.add('device_changes', {'name': tv.name}, house.now - HOUR, onState=True)
    s = state(ok(house.plugin, devices=[tv.id], states=["onState"]), key='onState')
    assert s['points'] == 1
    assert any('"name"::tag =~ /^Den TV 65" \\(Sony\\) 1\\.5\\+$/' in q for q in house.client.statements)


def test_v1_matches_a_backslash_as_stored(house):
    reader = history.HistoryReader(house.client, 'indigo', '1')
    assert reader._tag_match('name', 'A\\B') == '"name"::tag = \'A\\\\\\\\B\''
    assert history.HistoryReader(house.client, 'indigo', '3')._tag_match('name', 'A\\B') == '"name"::tag = \'A\\\\B\''


def test_validation_runs_before_any_thread(house):
    """Bad arguments come back synchronously, on the callback thread."""
    import indigo
    action = types.SimpleNamespace(props={'tool': 'query_history', 'arguments': json.dumps({'devices': ["Nope"]})})
    reply = house.plugin.handle_mcp_tool_invoke(action, caller_waiting_for_result=True)
    assert isinstance(reply, str) and json.loads(reply)['status'] == 'error'
    assert indigo.completion_handlers == []
    assert threading.active_count() >= 1
