"""
JSONAdaptor against the real module: include semantics, change detection, cache
keying, and no process-wide side effects.
"""

import json
import logging

from conftest import FakeDevice
from json_adaptor import JSONAdaptor, TYPE_CONVERTERS


def adaptor():
    return JSONAdaptor(logging.getLogger("Plugin"), False, False, False)


def test_none_means_all_states_and_empty_means_none():
    a = adaptor()
    dev = FakeDevice("Lamp", sensorValue=1.0, model="M")
    assert a.diff_to_json(dev, [], False) is None
    everything = a.diff_to_json(dev, None, False)
    assert everything['sensorValue'] == 1.0 and everything['model'] == 'M'
    only = a.diff_to_json(dev, ['model'], False)
    assert 'sensorValue' not in only and only['model'] == 'M'


def test_only_changed_keys_are_sent():
    a = adaptor()
    dev = FakeDevice("Lamp", sensorValue=1.0, model="M")
    a.diff_to_json(dev, ['sensorValue', 'model'], True)
    assert a.diff_to_json(dev, ['sensorValue', 'model'], True) is None
    dev.sensorValue = 2.0
    diff = a.diff_to_json(dev, ['sensorValue', 'model'], True)
    assert diff['sensorValue'] == 2.0 and 'model' not in diff


def test_case_only_and_empty_string_changes_are_sent_now():
    """Low item: a change only in letter case, or to "", waited for the next heartbeat."""
    a = adaptor()
    dev = FakeDevice("Lamp", status="On")
    a.diff_to_json(dev, ['status'], True)
    dev.status = "ON"
    assert a.diff_to_json(dev, ['status'], True)['status'] == "ON"
    dev.status = ""
    assert a.diff_to_json(dev, ['status'], True)['status'] == ""


def test_cache_is_keyed_by_id_and_never_evicts():
    """Low item: a 1000-entry cap below production's device count evicted ~12,000
    entries a day, each eviction re-sending every included state."""
    a = adaptor()
    devices = [FakeDevice(f"Device {i}", sensorValue=float(i)) for i in range(1500)]
    for dev in devices:
        a.diff_to_json(dev, ['sensorValue'], True)
    assert len(a.cache) == 1500
    assert a.diff_to_json(devices[0], ['sensorValue'], True) is None  # still cached: nothing re-sent

    renamed = devices[1]
    renamed.name = "Renamed"
    assert a.diff_to_json(renamed, ['sensorValue'], True) is None

    a.prune_cache([dev.id for dev in devices[:10]])
    assert len(a.cache) == 10


def test_json_encoder_is_not_patched_process_wide():
    """Low item: json.JSONEncoder.default was replaced for the whole process."""
    adaptor()
    assert json.JSONEncoder.default.__qualname__ == 'JSONEncoder.default'
    assert json.JSONEncoder.default.__module__ == 'json.encoder'


def test_int_converter_accepts_integral_floats():
    assert TYPE_CONVERTERS['integer']('3.0') == 3
    assert TYPE_CONVERTERS['int']('7') == 7


def test_liveness_fields_ride_along():
    a = adaptor()
    dev = FakeDevice("Lamp", sensorValue=1.0)
    diff = a.diff_to_json(dev, ['sensorValue'], False)
    assert 'secondsSinceLastSuccessfulComm' in diff
    assert diff['name'] == 'Lamp' and diff['id'] == float(dev.id)


def test_value_its_column_type_cannot_hold_is_left_out():
    """Issue unraid-scripts-configs#46: once InfluxDB has said a column is a float, a
    state reported as '' is left out of the point instead of costing the whole point."""
    a = adaptor()
    a.typecache['state.gps_accuracy'] = 'float'
    dev = FakeDevice("Car", states={'gps_accuracy': 3.0, 'latitude': 42.2})
    assert a.diff_to_json(dev, None, True)['state.gps_accuracy'] == 3.0

    dev.states = {'gps_accuracy': '', 'latitude': 42.3}
    diff = a.diff_to_json(dev, None, True)
    assert 'state.gps_accuracy' not in diff
    assert diff['state.latitude'] == 42.3

    # a value that converts is sent as the column's type
    dev.states = {'gps_accuracy': '5', 'latitude': 42.3}
    assert a.diff_to_json(dev, None, True)['state.gps_accuracy'] == 5.0

    # only the unwritable value changed: no point at all
    dev.states = {'gps_accuracy': '', 'latitude': 42.3}
    assert a.diff_to_json(dev, None, True) is None
    # a new number after it is sent at once, not at the next heartbeat
    dev.states = {'gps_accuracy': 4.0, 'latitude': 42.3}
    assert a.diff_to_json(dev, None, True)['state.gps_accuracy'] == 4.0


def test_string_columns_take_any_value():
    a = adaptor()
    a.typecache['status'] = 'str'
    dev = FakeDevice("Lamp", status=5.0)
    assert a.diff_to_json(dev, ['status'], False)['status'] == '5.0'
