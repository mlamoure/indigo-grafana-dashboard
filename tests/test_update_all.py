"""
Heartbeats and inclusion: issue #12 items 6 (Disabled sent a heartbeat every
poll; legacy 'smart' raised TypeError) and 8 (an empty include list sent every
state of every device).
"""

import datetime

import pytest

from conftest import FakeDevice, FakeVariable


def started(make_plugin, **prefs):
    plugin = make_plugin(**prefs)
    plugin.connected = True
    plugin.everConnected = True
    return plugin


def queued(plugin):
    points = []
    while not plugin.write_queue.empty():
        points.append(plugin.write_queue.get_nowait())
    return points


@pytest.fixture
def stale(indigo):
    old = datetime.datetime.now() - datetime.timedelta(days=2)
    dev = indigo.devices.add(FakeDevice("Quiet Sensor", sensorValue=21.0, lastChanged=old))
    var = indigo.variables.add(FakeVariable("Mode", "home"))
    return dev, var, old


def stop_writer(plugin):
    plugin.writer_stop.set()
    plugin.writer_thread.join(timeout=5)


def test_disabled_frequency_sends_no_heartbeats(make_plugin, stale):
    """Item 6: timedelta(minutes=-1) is always in the past, so 'Disabled' sent a
    heartbeat for every device and variable on every 60-second poll."""
    dev, var, old = stale
    plugin = started(make_plugin, MinimumUpdateFrequency='-1', listIncStates=['sensorValue'])
    stop_writer(plugin)
    plugin.UpdateAll()  # registers
    plugin.deviceLastUpdated[dev.id] = old
    plugin.variableLastUpdated[var.id] = old
    plugin.UpdateAll()
    plugin.UpdateAll()
    assert queued(plugin) == []


def test_frequency_sends_heartbeats_when_due(make_plugin, stale):
    dev, var, old = stale
    plugin = started(make_plugin, MinimumUpdateFrequency='15', listIncStates=['sensorValue'])
    stop_writer(plugin)
    plugin.UpdateAll()
    plugin.variableLastUpdated[var.id] = old
    plugin.UpdateAll()
    measurements = sorted(p['measurement'] for p in queued(plugin))
    assert measurements == ['device_changes', 'variable_changes']
    plugin.UpdateAll()  # not due again yet
    assert queued(plugin) == []


@pytest.mark.parametrize("hour,minute,expect", [(12, 0, 0), (23, 50, 2), (0, 5, 2)])
def test_legacy_smart_frequency(make_plugin, stale, monkeypatch, hour, minute, expect):
    """Item 6: outside its midnight window 'smart' raised TypeError and aborted UpdateAll."""
    import plugin as plugin_module
    dev, var, old = stale
    plugin = started(make_plugin, MinimumUpdateFrequency='smart', listIncStates=['sensorValue'])
    stop_writer(plugin)
    plugin.UpdateAll()
    plugin.variableLastUpdated[var.id] = old

    # the day after `old` (two days ago), so the heartbeat is due whatever the real date
    fixed = datetime.datetime.combine((old + datetime.timedelta(days=1)).date(), datetime.time(hour, minute))

    class FixedDateTime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed if tz is None else fixed.replace(tzinfo=tz)

    monkeypatch.setattr(plugin_module.datetime, 'datetime', FixedDateTime)
    plugin.UpdateAll()
    assert len(queued(plugin)) == expect


def test_empty_include_list_sends_nothing_for_ordinary_devices(make_plugin, indigo):
    """Item 8: json_adaptor treated [] as 'all', so an emptied global include
    list sent every state of every device."""
    plain = indigo.devices.add(FakeDevice("Plain", sensorValue=1.0, model="X"))
    included = indigo.devices.add(FakeDevice("Included", sensorValue=2.0, model="Y"))
    plugin = started(make_plugin, listIncStates=[], listIncDevices=[included.id])
    stop_writer(plugin)

    assert plugin.DeviceToInflux(None, plain, False) == (False, False)
    sent, _ = plugin.DeviceToInflux(None, included, False)
    assert sent
    fields = queued(plugin)[0]['fields']
    assert fields['sensorValue'] == 2.0 and fields['model'] == 'Y'


def test_empty_include_list_still_connects_after_restart(make_plugin, caplog):
    """Item 8: startup() also marked the plugin unconfigured, so it silently
    never connected until the dialog was saved again."""
    import logging
    with caplog.at_level(logging.WARNING, logger="Plugin"):
        plugin = make_plugin(listIncStates=[])
    assert plugin.configured
    assert plugin.StatesIncludeList == []
    assert any('include-states list is empty' in r.getMessage() for r in caplog.records)


def test_excluded_device_never_sends(make_plugin, indigo):
    dev = indigo.devices.add(FakeDevice("Noisy", sensorValue=1.0))
    plugin = started(make_plugin, listExclDevices=[dev.id], listIncStates=['sensorValue'])
    stop_writer(plugin)
    plugin.deviceUpdated(dev, dev)
    plugin.UpdateAll()
    assert queued(plugin) == []


def test_deleted_device_state_is_forgotten(make_plugin, indigo):
    dev = indigo.devices.add(FakeDevice("Gone", sensorValue=1.0))
    plugin = started(make_plugin, listIncStates=['sensorValue'])
    stop_writer(plugin)
    plugin.DeviceToInflux(None, dev, True)
    plugin.deviceLastUpdated[dev.id] = datetime.datetime.now()
    assert dev.id in plugin.adaptor.cache
    plugin.deviceDeleted(dev)
    assert dev.id not in plugin.adaptor.cache
    assert dev.id not in plugin.deviceLastUpdated
