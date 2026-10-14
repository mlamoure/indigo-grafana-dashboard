"""
The write path (issue #12 items 2, 4, 10, 14 and the writer-thread item):
errors are classified by HTTP status, type conflicts are corrected from the
decoded message on both servers, and nothing queued is thrown away because the
connection dropped.
"""

import logging
import threading
import time

import pytest

import plugin as plugin_module
from fake_influx import (FakeInfluxClient, InfluxConnectionError, V1_CONFLICT, V3_CONFLICT, V3_TAG_AND_FIELD,
                         connected_plugin, http_error)
from plugin import WRITE_HALT, WRITE_OK, WRITE_RETRY


def stop_writer(plugin):
    plugin.writer_stop.set()
    plugin.writer_thread.join(timeout=5)
    plugin.writer_stop.clear()


def point(device, **fields):
    return {'measurement': 'device_changes', 'tags': {'name': device}, 'fields': dict(fields), 'time': 1}


@pytest.fixture
def setup(make_plugin, monkeypatch):
    def factory(**prefs):
        client = FakeInfluxClient('3.12.0', 'InfluxDB 3 Core') if prefs.get('InfluxVersion') == '3' else None
        plugin, client = connected_plugin(make_plugin, client, **prefs)
        stop_writer(plugin)
        reconnects = []
        monkeypatch.setattr(plugin, 'requestReconnect', lambda *a, **k: reconnects.append((a, k)))
        return plugin, client, reconnects
    return factory


@pytest.mark.parametrize("status", [401, 403])
def test_auth_errors_halt_without_retry_storm(setup, caplog, status):
    """Item 4: a revoked or rotated token used to be logged at debug, the batch
    re-sent one point at a time (up to 500 requests) and the plugin still
    reported itself connected."""
    plugin, client, _ = setup()
    client.write_errors = [http_error(status, 'authorization failed')] * 10
    batch = [point(f"d{i}", v=float(i)) for i in range(20)]

    with caplog.at_level(logging.ERROR, logger="Plugin"):
        assert plugin.writeBatch(client, batch) == WRITE_HALT

    assert len(client.writes) == 1
    assert not plugin.connected
    assert plugin.StopConnectionAttempts
    assert plugin.connectionState == 'stopped_auth_failure'
    assert any("refused the plugin's credentials" in r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR)
    assert not plugin.acceptingPoints()  # producers stop until the user fixes it


@pytest.mark.parametrize("error", [http_error(404, 'database not found: "indigo"'), http_error(503, 'unavailable'),
                                   InfluxConnectionError('ConnectionError: refused')])
def test_transient_failures_keep_the_batch_and_reconnect(setup, error):
    plugin, client, reconnects = setup()
    client.write_errors = [error]

    assert plugin.writeBatch(client, [point('a', v=1.0), point('b', v=2.0)]) == WRITE_RETRY

    assert len(client.writes) == 1  # no per-point fan-out
    assert not plugin.connected
    assert reconnects
    assert plugin.acceptingPoints()  # producers keep buffering through the outage


def test_v1_type_conflict_is_corrected_and_only_dropped_points_resent(setup):
    """Item 2: the 1.x regex ran on the raw JSON body (escaped quotes) and never
    matched, so the conflicting device's points were dropped on every write."""
    plugin, client, _ = setup()
    client.write_errors = [http_error(400, V1_CONFLICT), None]
    batch = [point('thermo', sensorValue=69.5), point('lamp', onState=True)]

    assert plugin.writeBatch(client, batch) == WRITE_OK

    assert plugin.adaptor.typecache['sensorValue'] == 'string'
    resent = client.writes[1]
    assert resent == [point('thermo', sensorValue='69.5')]  # 1.x already stored the rest
    assert plugin.stats.snapshot()['points_dropped']['rejected'] == 0


def test_v3_type_conflict_is_corrected_and_whole_batch_resent(setup):
    """InfluxDB 3 rejects the whole batch on the first bad line."""
    plugin, client, _ = setup(InfluxVersion='3')
    client.write_errors = [http_error(400, V3_CONFLICT, point_index=0, line_number=1), None]
    batch = [point('thermo', sensorValue=69.5), point('lamp', onState=True)]

    assert plugin.writeBatch(client, batch) == WRITE_OK

    assert client.writes[1] == [point('thermo', sensorValue='69.5'), point('lamp', onState=True)]
    assert plugin.adaptor.typecache['sensorValue'] == 'str'


def test_v3_uncorrectable_line_is_dropped_by_line_number(setup):
    plugin, client, _ = setup(InfluxVersion='3')
    client.write_errors = [http_error(400, V3_TAG_AND_FIELD, point_index=1, line_number=2), None]
    batch = [point('a', v=1.0), point('bad', name='bad'), point('c', v=3.0)]

    assert plugin.writeBatch(client, batch) == WRITE_OK

    assert len(client.writes) == 2  # one round trip per bad line, not one per point
    assert client.written_points == [point('a', v=1.0), point('c', v=3.0)]
    assert plugin.stats.snapshot()['points_dropped']['rejected'] == 1


def test_v1_partial_write_other_reasons_counts_the_dropped(setup):
    plugin, client, _ = setup()
    client.write_errors = [http_error(400, 'partial write: points beyond retention policy dropped=2')]

    assert plugin.writeBatch(client, [point('a', v=1.0), point('b', v=2.0), point('c', v=3.0)]) == WRITE_OK

    assert len(client.writes) == 1
    assert plugin.stats.snapshot()['points_dropped']['rejected'] == 2


def test_whole_batch_400_without_line_number_falls_back_per_point(setup):
    plugin, client, _ = setup()
    client.write_errors = [http_error(400, "unable to parse 'x': invalid field format"), None,
                           http_error(400, "unable to parse 'x': invalid field format"), None]
    batch = [point('a', v=1.0), point('b', v=2.0), point('c', v=3.0)]

    assert plugin.writeBatch(client, batch) == WRITE_OK

    assert client.written_points == [point('a', v=1.0), point('c', v=3.0)]
    assert plugin.stats.snapshot()['points_dropped']['rejected'] == 1


def test_writer_pauses_while_disconnected_and_loses_nothing(make_plugin):
    """Item 10: a network error dropped the in-flight batch, and while
    disconnected the writer drained and discarded the queue."""
    plugin, client = connected_plugin(make_plugin)
    plugin.requestReconnect = lambda *a, **k: None   # the test plays the reconnect
    client.write_errors = [InfluxConnectionError('ConnectionError: reset')]

    for i in range(5):
        plugin.SendToInflux({'name': f"d{i}"}, {'v': float(i)})

    deadline = time.monotonic() + 5
    while plugin.connected and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not plugin.connected

    # still buffering during the outage, and the writer leaves the queue alone
    for i in range(5, 8):
        plugin.SendToInflux({'name': f"d{i}"}, {'v': float(i)})
    time.sleep(1.5)
    assert len(client.successful) == 0

    plugin.connected = True  # connection restored
    deadline = time.monotonic() + 5
    while len(client.written_points) < 8 and time.monotonic() < deadline:
        time.sleep(0.05)
    names = sorted(p['tags']['name'] for p in client.written_points)
    assert names == [f"d{i}" for i in range(8)]


def test_writer_thread_survives_unexpected_errors(make_plugin, monkeypatch, caplog):
    plugin, client = connected_plugin(make_plugin)
    calls = []

    def flaky(c, batch):
        calls.append(len(batch))
        if len(calls) == 1:
            raise RuntimeError("boom")
        return WRITE_OK

    monkeypatch.setattr(plugin, 'writeBatch', flaky)
    with caplog.at_level(logging.ERROR, logger="Plugin"):
        plugin.SendToInflux({'name': 'a'}, {'v': 1.0})
        deadline = time.monotonic() + 5
        while not calls and time.monotonic() < deadline:
            time.sleep(0.05)
        plugin.SendToInflux({'name': 'b'}, {'v': 2.0})
        deadline = time.monotonic() + 5
        while len(calls) < 2 and time.monotonic() < deadline:
            time.sleep(0.05)

    assert plugin.writer_thread.is_alive()
    assert len(calls) >= 2
    assert any("writer thread" in r.getMessage() for r in caplog.records)


def test_queue_full_is_counted(setup, monkeypatch):
    plugin, client, _ = setup()
    monkeypatch.setattr(plugin_module, 'INFLUX_QUEUE_MAX', 2)
    import queue
    plugin.write_queue = queue.Queue(maxsize=2)
    for i in range(5):
        plugin.SendToInflux({'name': f"d{i}"}, {'v': float(i)})
    assert plugin.stats.snapshot()['points_dropped']['queue_full'] == 3


def test_nothing_is_accepted_before_the_first_connection(make_plugin):
    plugin = make_plugin()
    stop_writer(plugin)
    plugin.SendToInflux({'name': 'a'}, {'v': 1.0})
    assert plugin.write_queue.qsize() == 0


def test_v3_drops_fields_that_duplicate_tags(setup):
    plugin, client, _ = setup(InfluxVersion='3')
    plugin.SendToInflux({'name': 'Lamp', 'folderId': '0'}, {'name': 'Lamp', 'onState': True})
    queued = plugin.write_queue.get_nowait()
    assert queued['fields'] == {'onState': True}
