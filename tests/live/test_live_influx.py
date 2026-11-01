"""
Live smoke test against real servers (issue #12): run by
tests/live/run_influx_matrix.sh, which starts influxdb:1.8 (auth on) and
influxdb:3-core, exports their ports and credentials, and removes them after.
Skipped unless INFLUX_LIVE=1.

Covers ping, DDL and retention on 1.x, batched writes through the plugin's own
writer thread, column types identical to what influxdb-python 5.3.2 created,
type-conflict recovery on both servers, 401/403/404 handling, and non-admin
users on 1.x.
"""

import datetime
import logging
import math
import os
import time
import uuid

import pytest

from influx_client import InfluxClient, InfluxHTTPError, parse_duration_seconds
from plugin import WRITE_HALT, WRITE_OK, WRITE_RETRY

pytestmark = pytest.mark.skipif(os.environ.get('INFLUX_LIVE') != '1', reason="live InfluxDB matrix only")

UTC = datetime.timezone.utc
PORT_18 = int(os.environ.get('INFLUX18_PORT', '0'))
ADMIN = (os.environ.get('INFLUX18_ADMIN', ''), os.environ.get('INFLUX18_ADMIN_PASSWORD', ''))
PORT_3 = int(os.environ.get('INFLUX3_PORT', '0'))
TOKEN_3 = os.environ.get('INFLUX3_TOKEN', '')


def unique(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# InfluxDB 3 Core allows 5 databases per server, so v3 tests share fixed databases
# and keep apart by measurement name.  (On InfluxDB 3 a write - even the empty
# probe of check_write_access - creates a missing database.)
V3_DB = 'igd_live'


def admin18(database=''):
    return InfluxClient('127.0.0.1', PORT_18, username=ADMIN[0], password=ADMIN[1], database=database)


def client3(database, token=None):
    return InfluxClient('127.0.0.1', PORT_3, username='indigo', password=token or TOKEN_3, database=database)


def field_types(client, database, measurement):
    results = client.query(f'SHOW FIELD KEYS FROM "{measurement}"', database=database)
    return {row[0]: row[1] for series in results[0].get('series', []) for row in series['values']}


def count(client, database, measurement, field):
    results = client.query(f'SELECT count("{field}") FROM "{measurement}"', database=database)
    series = results[0].get('series')
    return series[0]['values'][0][1] if series else 0


def wait_for(predicate, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.25)
    return False


def corpus(now=None):
    """Device and variable points shaped like the plugin's (as SendToInflux builds them)."""
    now = now or datetime.datetime.now(UTC)
    tick = datetime.timedelta(milliseconds=1)
    points = []
    texts = ["plain", 'with "quotes"', "comma,space and=eq", "line\nbreak", "back\\slash", "unicode °F café", ""]
    for index, text in enumerate(texts):
        points.append({'measurement': 'device_changes',
                       'tags': {'name': f"Device {index}, test", 'folderId': '0'},
                       'fields': {'model': text, 'sensorValue': 20.0 + index, 'onState': index % 2 == 0,
                                  'id': float(1000 + index), 'lastChanged': 1760440000.0,
                                  'secondsSinceLastChanged': 12.5},
                       'time': now + tick * index})
    points.append({'measurement': 'thermostat_changes', 'tags': {'name': 'Upstairs Nest', 'folder': 'HVAC', 'folderId': '9'},
                   'fields': {'setpointHeat': 68.0, 'state.hvac_state': 'heat', 'brightness': 75},
                   'time': now + tick * 20})
    points.append({'measurement': 'variable_changes', 'tags': {'varname': 'Mode'},
                   'fields': {'value': 'home', 'value.num': 1.0}, 'time': now + tick * 21})
    return points


# --- connection and DDL ----------------------------------------------------------

def test_ping_reports_versions():
    assert admin18().ping()['version'].startswith('1.8')
    assert client3('x').ping()['version'].startswith('3.')


def test_v1_new_database_gets_default_retention_and_alter(make_plugin):
    database = unique('igd_rp')
    plugin = make_plugin(InfluxHost='127.0.0.1', InfluxHTTPPort=str(PORT_18), InfluxUser=ADMIN[0],
                         InfluxPassword=ADMIN[1], InfluxDB=database, InfluxRetention='24', InfluxVersion='1')
    plugin.connect()
    assert plugin.connected, plugin.lastConnectError

    policies = {p['name']: p for p in admin18().retention_policies(database)}
    assert policies['indigo_policy']['default'] is True
    assert parse_duration_seconds(policies['indigo_policy']['duration']) == 720 * 86400

    plugin.InfluxRetention = '-1'
    plugin.connect(force=True)
    policies = {p['name']: p for p in admin18().retention_policies(database)}
    assert policies['indigo_policy']['duration'] == '0s'  # INF
    assert policies['indigo_policy']['default'] is True


def test_v1_existing_install_is_left_on_autogen(make_plugin, caplog):
    database = unique('igd_legacy')
    admin = admin18()
    admin.create_database(database)
    admin.create_retention_policy('indigo_policy', database, '180d', default=False)  # what releases < 2026.11 did
    plugin = make_plugin(InfluxHost='127.0.0.1', InfluxHTTPPort=str(PORT_18), InfluxUser=ADMIN[0],
                         InfluxPassword=ADMIN[1], InfluxDB=database, InfluxVersion='1')
    with caplog.at_level(logging.WARNING, logger="Plugin"):
        plugin.connect()
    assert plugin.connected
    policies = {p['name']: p for p in admin.retention_policies(database)}
    assert policies['autogen']['default'] is True
    assert policies['indigo_policy']['default'] is False
    assert any('ALTER RETENTION POLICY' in r.getMessage() for r in caplog.records)


def test_v1_non_admin_user_connects_and_writes(make_plugin):
    database = unique('igd_user')
    user = unique('writer')
    admin = admin18()
    admin.create_database(database)
    admin.query(f"CREATE USER \"{user}\" WITH PASSWORD 'pw-{user}'")
    admin.query(f'GRANT WRITE ON "{database}" TO "{user}"')

    plugin = make_plugin(InfluxHost='127.0.0.1', InfluxHTTPPort=str(PORT_18), InfluxUser=user,
                         InfluxPassword=f"pw-{user}", InfluxDB=database, InfluxVersion='1')
    plugin.connect()
    assert plugin.connected, plugin.lastConnectError
    assert plugin.writeBatch(plugin.connection, corpus()) == WRITE_OK
    assert count(admin, database, 'device_changes', 'sensorValue') == 7


@pytest.mark.parametrize("server", ['1.8', '3'])
def test_wrong_password_stops(make_plugin, server):
    database = unique('igd_auth') if server == '1.8' else V3_DB
    if server == '1.8':
        prefs = dict(InfluxHTTPPort=str(PORT_18), InfluxUser=ADMIN[0], InfluxPassword='wrong', InfluxVersion='1')
    else:
        prefs = dict(InfluxHTTPPort=str(PORT_3), InfluxUser='indigo', InfluxPassword='apiv3_wrong', InfluxVersion='3')
    plugin = make_plugin(InfluxHost='127.0.0.1', InfluxDB=database, **prefs)
    plugin.connect()
    assert plugin.connectionState == 'stopped_auth_failure'


@pytest.mark.parametrize("server", ['1.8', '3'])
def test_rejected_credentials_on_write_halt_without_a_retry_storm(make_plugin, server):
    database = unique('igd_401') if server == '1.8' else V3_DB
    if server == '1.8':
        admin18().create_database(database)
        good = dict(InfluxHTTPPort=str(PORT_18), InfluxUser=ADMIN[0], InfluxPassword=ADMIN[1], InfluxVersion='1')
        bad = InfluxClient('127.0.0.1', PORT_18, username=ADMIN[0], password='rotated', database=database)
    else:
        good = dict(InfluxHTTPPort=str(PORT_3), InfluxUser='indigo', InfluxPassword=TOKEN_3, InfluxVersion='3')
        bad = client3(database, token='apiv3_revoked')
    plugin = make_plugin(InfluxHost='127.0.0.1', InfluxDB=database, **good)
    plugin.connect()
    assert plugin.connected
    plugin.connection = bad  # the token is rotated under a running plugin

    assert plugin.writeBatch(bad, corpus()) == WRITE_HALT
    assert plugin.connectionState == 'stopped_auth_failure'
    assert plugin.stats.snapshot()['last_error']['status'] == 401


def test_v1_missing_database_is_a_transient_failure(make_plugin):
    database = unique('igd_404')
    admin = admin18()
    admin.create_database(database)
    plugin = make_plugin(InfluxHost='127.0.0.1', InfluxHTTPPort=str(PORT_18), InfluxUser=ADMIN[0],
                         InfluxPassword=ADMIN[1], InfluxDB=database, InfluxVersion='1')
    plugin.connect()
    plugin.requestReconnect = lambda *a, **k: None
    admin.query(f'DROP DATABASE "{database}"')
    assert plugin.writeBatch(plugin.connection, corpus()) == WRITE_RETRY
    assert not plugin.connected and not plugin.StopConnectionAttempts


# --- writes, types, conflicts ------------------------------------------------------

@pytest.mark.parametrize("server", ['1.8', '3'])
def test_column_types_match_influxdb_5_3_2(server):
    """The same points written by the archived client and by ours create the same
    columns with the same types, and read back the same values."""
    influxdb = pytest.importorskip('influxdb')
    old_db, new_db = unique('igd_old'), unique('igd_new')
    points = corpus(datetime.datetime(2026, 10, 14, 12, 0, tzinfo=UTC))

    if server == '1.8':
        admin = admin18()
        admin.create_database(old_db)
        admin.create_database(new_db)
        legacy = influxdb.InfluxDBClient('127.0.0.1', PORT_18, ADMIN[0], ADMIN[1], old_db)
        ours = InfluxClient('127.0.0.1', PORT_18, username=ADMIN[0], password=ADMIN[1], database=new_db)
        reader = admin
    else:
        old_db, new_db = 'igd_old', 'igd_new'
        legacy = influxdb.InfluxDBClient('127.0.0.1', PORT_3, 'indigo', TOKEN_3, old_db)
        ours = client3(new_db)
        reader = client3(new_db)

    assert legacy.write_points(points)
    assert ours.write_points(points) == len(points)

    for measurement in ('device_changes', 'thermostat_changes', 'variable_changes'):
        assert field_types(reader, new_db, measurement) == field_types(reader, old_db, measurement), measurement
        old_rows = reader.query(f'SELECT * FROM "{measurement}"', database=old_db)[0]['series']
        new_rows = reader.query(f'SELECT * FROM "{measurement}"', database=new_db)[0]['series']
        assert new_rows == old_rows, measurement


@pytest.mark.parametrize("server", ['1.8', '3'])
def test_type_conflict_is_recovered(make_plugin, server):
    """1.x: the regex never matched the escaped JSON body (item 2), so the point
    was dropped on every write.  3: the whole batch is rejected on the first bad line."""
    measurement = unique('conflict')
    if server == '1.8':
        database = unique('igd_conflict')
        admin18().create_database(database)
        prefs = dict(InfluxHTTPPort=str(PORT_18), InfluxUser=ADMIN[0], InfluxPassword=ADMIN[1], InfluxVersion='1')
        reader = admin18()
    else:
        database = V3_DB
        prefs = dict(InfluxHTTPPort=str(PORT_3), InfluxUser='indigo', InfluxPassword=TOKEN_3, InfluxVersion='3')
        reader = client3(database)
    plugin = make_plugin(InfluxHost='127.0.0.1', InfluxDB=database, **prefs)
    plugin.connect()
    assert plugin.connected, plugin.lastConnectError

    now = datetime.datetime.now(UTC)
    # someone created the column as a string first
    plugin.connection.write_points([{'measurement': measurement, 'tags': {'name': 'Seed'},
                                     'fields': {'sensorValue': 'n/a'}, 'time': now}])
    batch = [{'measurement': measurement, 'tags': {'name': f"Thermo {i}"},
              'fields': {'sensorValue': 60.0 + i, 'onState': True}, 'time': now + datetime.timedelta(seconds=i + 1)}
             for i in range(3)]

    assert plugin.writeBatch(plugin.connection, batch) == WRITE_OK

    assert plugin.adaptor.typecache['sensorValue'] in ('string', 'str')
    assert field_types(reader, database, measurement)['sensorValue'] == 'string'
    assert count(reader, database, measurement, 'sensorValue') == 4
    assert count(reader, database, measurement, 'onState') == 3
    assert plugin.stats.snapshot()['points_dropped']['rejected'] == 0


@pytest.mark.parametrize("server", ['1.8', '3'])
def test_unconvertible_value_costs_only_its_field(make_plugin, server):
    """unraid-scripts-configs#46: a float state reported as '' cost the whole point."""
    measurement = unique('unconvertible')
    if server == '1.8':
        database = unique('igd_unconv')
        admin18().create_database(database)
        prefs = dict(InfluxHTTPPort=str(PORT_18), InfluxUser=ADMIN[0], InfluxPassword=ADMIN[1], InfluxVersion='1')
        reader = admin18()
    else:
        database = V3_DB
        prefs = dict(InfluxHTTPPort=str(PORT_3), InfluxUser='indigo', InfluxPassword=TOKEN_3, InfluxVersion='3')
        reader = client3(database)
    plugin = make_plugin(InfluxHost='127.0.0.1', InfluxDB=database, **prefs)
    plugin.connect()
    assert plugin.connected, plugin.lastConnectError

    now = datetime.datetime.now(UTC)
    plugin.connection.write_points([{'measurement': measurement, 'tags': {'name': 'Car'},
                                     'fields': {'gps_accuracy': 3.0, 'latitude': 42.0}, 'time': now}])
    batch = [{'measurement': measurement, 'tags': {'name': 'Car'},
              'fields': {'gps_accuracy': '', 'latitude': 42.1}, 'time': now + datetime.timedelta(seconds=1)},
             {'measurement': measurement, 'tags': {'name': 'Phone'},
              'fields': {'gps_accuracy': '7', 'latitude': 42.2}, 'time': now + datetime.timedelta(seconds=2)}]

    assert plugin.writeBatch(plugin.connection, batch) == WRITE_OK

    assert field_types(reader, database, measurement)['gps_accuracy'] == 'float'
    assert count(reader, database, measurement, 'latitude') == 3
    assert count(reader, database, measurement, 'gps_accuracy') == 2  # the seed and the Phone's 7.0
    assert plugin.stats.snapshot()['points_dropped']['rejected'] == 0


def test_v3_bad_line_is_dropped_and_the_rest_written(make_plugin):
    database, measurement = V3_DB, unique('badline')
    plugin = make_plugin(InfluxHost='127.0.0.1', InfluxHTTPPort=str(PORT_3), InfluxUser='indigo',
                         InfluxPassword=TOKEN_3, InfluxDB=database, InfluxVersion='3')
    plugin.connect()
    now = datetime.datetime.now(UTC)
    batch = [{'measurement': measurement, 'tags': {'name': f"D{i}"}, 'fields': {'v': float(i)},
              'time': now + datetime.timedelta(seconds=i)} for i in range(4)]
    batch[2]['fields']['name'] = 'D2'  # tag and field at once: IOx refuses the line
    assert plugin.writeBatch(plugin.connection, batch) == WRITE_OK
    assert count(client3(database), database, measurement, 'v') == 3
    assert plugin.stats.snapshot()['points_dropped']['rejected'] == 1


@pytest.mark.parametrize("server", ['1.8', '3'])
def test_nan_does_not_cost_the_point(server):
    measurement = unique('nan')
    if server == '1.8':
        database = unique('igd_nan')
        admin18().create_database(database)
        client = InfluxClient('127.0.0.1', PORT_18, username=ADMIN[0], password=ADMIN[1], database=database)
    else:
        database = V3_DB
        client = client3(database)
    client.write_points([{'measurement': measurement, 'tags': {'name': 'Sensor'},
                          'fields': {'sensorValue': math.nan, 'secondsSinceLastChanged': 5.0},
                          'time': datetime.datetime.now(UTC)}])
    assert count(client, database, measurement, 'secondsSinceLastChanged') == 1


@pytest.mark.parametrize("server", ['1.8', '3'])
def test_points_flow_through_the_writer_thread_in_batches(make_plugin, server):
    measurement = unique('flow')
    if server == '1.8':
        database = unique('igd_flow')
        prefs = dict(InfluxHTTPPort=str(PORT_18), InfluxUser=ADMIN[0], InfluxPassword=ADMIN[1], InfluxVersion='1')
        reader = admin18()
    else:
        database = V3_DB
        prefs = dict(InfluxHTTPPort=str(PORT_3), InfluxUser='indigo', InfluxPassword=TOKEN_3, InfluxVersion='3')
        reader = client3(database)
    plugin = make_plugin(InfluxHost='127.0.0.1', InfluxDB=database, **prefs)
    plugin.connect()
    assert plugin.connected

    for i in range(1200):
        plugin.SendToInflux({'name': f"Device {i % 40}", 'folderId': '0'}, {'sensorValue': float(i), 'id': float(i % 40)},
                            measurement=measurement)

    assert wait_for(lambda: plugin.stats.snapshot()['points_written'] >= 1200, timeout=60)
    assert plugin.stats.snapshot()['batches_written'] < 20  # coalesced, not per point
    assert count(reader, database, measurement, 'sensorValue') == 1200


def test_v3_write_access_check():
    client3(V3_DB).check_write_access()
    with pytest.raises(InfluxHTTPError) as raised:
        client3('x', token='apiv3_nope').check_write_access()
    assert raised.value.status_code == 401


def test_v1_existing_database_without_the_policy_is_left_alone(make_plugin, caplog):
    """A database that existed before the plugin connected (shared with other
    writers) keeps its default retention policy."""
    database = unique('igd_shared')
    admin = admin18()
    admin.create_database(database)
    plugin = make_plugin(InfluxHost='127.0.0.1', InfluxHTTPPort=str(PORT_18), InfluxUser=ADMIN[0],
                         InfluxPassword=ADMIN[1], InfluxDB=database, InfluxVersion='1')
    with caplog.at_level(logging.WARNING, logger="Plugin"):
        plugin.connect()
    assert plugin.connected
    policies = {p['name']: p for p in admin.retention_policies(database)}
    assert set(policies) == {'autogen'} and policies['autogen']['default'] is True
    assert any('CREATE RETENTION POLICY' in r.getMessage() for r in caplog.records)
