"""
connect(): issue #12 items 3 (1.x retention), 5 (non-admin users), 9 (invalid
port) and the never-on-the-callback-thread rule.
"""

import logging
import threading

import pytest

from fake_influx import FakeInfluxClient, InfluxConnectionError, InfluxQueryError, http_error

NOT_ADMIN = http_error(403, "error authorizing query: indigo not authorized to execute statement 'CREATE DATABASE "
                            "indigo', requires admin privilege")


def connect_with(make_plugin, client, **prefs):
    plugin = make_plugin(**prefs)
    plugin.newClient = lambda settings: client
    plugin.connect()
    return plugin


def warnings(caplog):
    return [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]


def test_new_v1_database_gets_indigo_policy_as_default(make_plugin):
    """Item 3: 'indigo_policy' was created without DEFAULT, so data went to
    'autogen' (kept forever) and the setting never applied."""
    client = FakeInfluxClient()
    plugin = connect_with(make_plugin, client, InfluxRetention='24')

    assert plugin.connected
    assert ('CREATE DATABASE', 'indigo') in client.ddl
    assert ('CREATE RETENTION POLICY', 'indigo_policy', '720d', True) in client.ddl


def test_keep_forever_is_inf(make_plugin):
    """Item 3: '-1' arrived as a string, never matched == -1, and became -30d."""
    client = FakeInfluxClient()
    connect_with(make_plugin, client, InfluxRetention='-1')
    assert ('CREATE RETENTION POLICY', 'indigo_policy', 'INF', True) in client.ddl


def test_existing_install_keeps_autogen_and_warns_once(make_plugin, caplog):
    """Decision 2026-10-14: an install with a non-default indigo_policy (every
    install before 2026.11.0) keeps writing to autogen; the user is told how to
    opt in.  Switching the default would hide all history from Grafana panels."""
    client = FakeInfluxClient()
    client.policies = [{'name': 'autogen', 'duration': '0s', 'default': True},
                       {'name': 'indigo_policy', 'duration': '4320h0m0s', 'default': False}]
    with caplog.at_level(logging.WARNING, logger="Plugin"):
        plugin = connect_with(make_plugin, client, InfluxRetention='24')
        plugin.connect(force=True)

    assert plugin.connected
    assert not [d for d in client.ddl if 'RETENTION' in d[0]]
    notices = [m for m in warnings(caplog) if 'ALTER RETENTION POLICY "indigo_policy" ON "indigo" DURATION 720d DEFAULT' in m]
    assert len(notices) == 1


def test_default_policy_is_altered_when_the_setting_changes(make_plugin):
    client = FakeInfluxClient()
    client.policies = [{'name': 'autogen', 'duration': '0s', 'default': False},
                       {'name': 'indigo_policy', 'duration': '4320h0m0s', 'default': True}]  # 6 months
    connect_with(make_plugin, client, InfluxRetention='24')
    assert ('ALTER RETENTION POLICY', 'indigo_policy', '720d', True) in client.ddl


def test_default_policy_with_the_right_duration_is_left_alone(make_plugin):
    client = FakeInfluxClient()
    client.policies = [{'name': 'indigo_policy', 'duration': '17280h0m0s', 'default': True}]
    connect_with(make_plugin, client, InfluxRetention='24')
    assert not [d for d in client.ddl if 'RETENTION' in d[0]]


def test_non_admin_user_connects(make_plugin, caplog):
    """Item 5: CREATE DATABASE was mandatory, so a user without admin rights
    could never connect and retried quietly forever."""
    client = FakeInfluxClient()
    client.create_database_error = NOT_ADMIN
    client.retention_error = http_error(403, "requires admin privilege")
    with caplog.at_level(logging.WARNING, logger="Plugin"):
        plugin = connect_with(make_plugin, client)

    assert plugin.connected
    assert any('admin rights' in m for m in warnings(caplog))


def test_wrong_password_stops_attempts(make_plugin):
    client = FakeInfluxClient()
    client.create_database_error = http_error(401, 'authorization failed')
    plugin = connect_with(make_plugin, client)

    assert not plugin.connected
    assert plugin.StopConnectionAttempts
    assert plugin.connectionState == 'stopped_auth_failure'


def test_no_write_permission_stops_attempts(make_plugin):
    client = FakeInfluxClient()
    client.check_write_error = http_error(403, '"indigo" user is not authorized to write to database "indigo"')
    plugin = connect_with(make_plugin, client)
    assert plugin.connectionState == 'stopped_auth_failure'


def test_missing_database_retries(make_plugin):
    client = FakeInfluxClient()
    client.create_database_error = NOT_ADMIN
    client.check_write_error = http_error(404, 'database not found: "indigo"')
    plugin = connect_with(make_plugin, client)

    assert not plugin.connected
    assert not plugin.StopConnectionAttempts
    assert plugin.connectionState == 'retrying'


def test_v3_skips_ddl(make_plugin):
    client = FakeInfluxClient('3.12.0', 'InfluxDB 3 Core')
    plugin = connect_with(make_plugin, client, InfluxVersion='3')
    assert plugin.connected
    assert client.ddl == []


def test_v3_bad_token_stops(make_plugin):
    client = FakeInfluxClient('3.12.0', 'InfluxDB 3 Core')
    client.ping_error = http_error(401, 'the request was not authenticated')
    plugin = connect_with(make_plugin, client, InfluxVersion='3')
    assert plugin.connectionState == 'stopped_auth_failure'


@pytest.mark.parametrize("port", ['', 'abc', '0', '70000', ' '])
def test_invalid_port_never_crashes(make_plugin, caplog, port):
    """Item 9: int(port) ran outside the try, crashing closedPrefsConfigUi,
    runConcurrentThread and startup()."""
    plugin = make_plugin(InfluxHTTPPort=port)
    plugin.newClient = lambda settings: pytest.fail("must not build a client for invalid settings")
    with caplog.at_level(logging.ERROR, logger="Plugin"):
        plugin.connect()
        plugin.connect()
    assert plugin.connectionState == 'invalid_config'
    assert len([r for r in caplog.records if 'not valid' in r.getMessage()]) == 1


def test_unreachable_server_logs_once_then_quietly(make_plugin, caplog):
    client = FakeInfluxClient()
    client.ping_error = InfluxConnectionError('ConnectTimeout: timed out')
    with caplog.at_level(logging.ERROR, logger="Plugin"):
        plugin = connect_with(make_plugin, client)
        plugin.connect()
        plugin.connect()
    assert plugin.connectionState == 'retrying'
    assert plugin.ConnectionRetryCount == 3
    assert len([r for r in caplog.records if r.levelno == logging.ERROR]) == 1


def test_version_mismatch_is_reported(make_plugin, caplog):
    client = FakeInfluxClient('3.12.0', 'InfluxDB 3 Core')
    client.create_database_error = InfluxQueryError('This feature is not implemented: CREATE DATABASE')
    client.retention_error = InfluxQueryError('not implemented')
    with caplog.at_level(logging.WARNING, logger="Plugin"):
        connect_with(make_plugin, client, InfluxVersion='1')
    assert any("Select 'InfluxDB 3'" in m for m in warnings(caplog))


def test_startup_never_connects_on_the_calling_thread(make_plugin):
    """No network I/O in Indigo callbacks: the first connect happens in
    runConcurrentThread."""
    plugin = make_plugin(start=False)
    plugin.newClient = lambda settings: pytest.fail("startup() must not connect")
    plugin.startup()
    assert not plugin.connected


def test_concurrent_thread_connects_then_polls(make_plugin):
    client = FakeInfluxClient()
    plugin = make_plugin()
    plugin.newClient = lambda settings: client
    plugin.runConcurrentThread()  # the fake sleep() raises StopThread after one pass
    assert plugin.connected


def test_a_connect_error_in_the_loop_does_not_kill_the_thread(make_plugin, caplog):
    plugin = make_plugin()

    def explode():
        raise RuntimeError("unexpected")

    plugin.connect = explode
    with caplog.at_level(logging.ERROR, logger="Plugin"):
        plugin.runConcurrentThread()  # returns normally after StopThread
    assert any("background thread" in r.getMessage() for r in caplog.records)


def test_reconnect_runs_on_a_worker_thread(make_plugin):
    client = FakeInfluxClient()
    plugin = make_plugin()
    seen = []
    done = threading.Event()

    def fake_new_client(settings):
        seen.append(threading.current_thread().name)
        done.set()
        return client

    plugin.newClient = fake_new_client
    plugin.requestReconnect("settings changed")
    assert done.wait(5)
    assert seen == ['InfluxConnect']


def test_existing_database_without_indigo_policy_is_left_alone(make_plugin, caplog):
    """Review finding: 'no indigo_policy' is not 'new install' - a database other
    tools share must not get its default policy switched."""
    client = FakeInfluxClient()
    client.existing_databases = ['indigo', 'telegraf']
    with caplog.at_level(logging.WARNING, logger="Plugin"):
        plugin = connect_with(make_plugin, client, InfluxRetention='24')
    assert plugin.connected
    assert not [d for d in client.ddl if 'RETENTION' in d[0]]
    assert any('CREATE RETENTION POLICY "indigo_policy" ON "indigo" DURATION 720d REPLICATION 1 DEFAULT' in m
               for m in warnings(caplog))


def test_success_clears_a_stale_auth_stop(make_plugin):
    """Review finding: a 401 from the client a reconnect was replacing set
    StopConnectionAttempts; a successful connect must clear it."""
    plugin = make_plugin()
    plugin.newClient = lambda settings: FakeInfluxClient()
    plugin.StopConnectionAttempts = True
    plugin.connect(force=True)  # what requestReconnect's worker does after resetting...
    assert not plugin.connected  # ...without the reset the stop flag blocks it
    plugin.StopConnectionAttempts = False
    plugin.connect(force=True)
    assert plugin.connected and plugin.acceptingPoints()


def test_a_replaced_clients_401_does_not_stop_the_new_connection(make_plugin):
    plugin = make_plugin()
    old, new = FakeInfluxClient(), FakeInfluxClient()
    clients = [old, new]
    plugin.newClient = lambda settings: clients.pop(0)
    plugin.connect()
    plugin.connected = False  # a reconnect is in progress
    old.write_errors = [http_error(401, 'authorization failed')]
    from plugin import WRITE_HALT
    assert plugin.writeBatch(old, [{'measurement': 'm', 'tags': {}, 'fields': {'v': 1.0}, 'time': 1}]) == WRITE_HALT
    assert not plugin.StopConnectionAttempts
    plugin.connect(force=True)
    assert plugin.connected and plugin.connection is new
