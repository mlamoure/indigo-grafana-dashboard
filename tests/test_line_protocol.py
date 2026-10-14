"""
The in-house line-protocol encoder must match influxdb-python 5.3.2's
line_protocol.make_lines byte for byte: production InfluxDB already has typed
columns, so any drift shows up as type conflicts.  The only differences allowed
are the deliberate ones (NaN / infinity skipped, field-less points skipped).

influxdb==5.3.2 is a test-only dependency (requirements.txt) until this
comparison has passed for one release; then the expected lines become fixtures.
"""

import datetime
import math

import pytest

from influx_client import encode_field_value, encode_points, escape_key, make_line, to_nanoseconds

reference = pytest.importorskip("influxdb.line_protocol")

UTC = datetime.timezone.utc
EASTERN = datetime.timezone(datetime.timedelta(hours=-4))
T0 = datetime.datetime(2026, 10, 14, 12, 30, 15, 123456, tzinfo=UTC)

STRINGS = [
    "plain", "", " ", "with space", 'with "quotes"', "comma,separated", "equals=sign", "line\nbreak",
    "back\\slash", "trailing backslash\\", "tab\tchar", "unicode °F café ☃", "emoji 🌡️", "'single'",
    '\\"both\\"', "null", "None", "true", "1.5", "-0", "a=b,c d\\e\"f\ng",
]

NUMBERS = [0, 1, -1, 42, 2 ** 40, -(2 ** 31), 0.0, -0.0, 0.1, 1.5, -273.15, 1e-7, 1e20, 123456789.123456789,
           69.1, 33.8, 946771200.0, 1760440000.0]

TAG_VALUES = ["Living Room Lamp", "Front Porch, Left", "a=b", "Ünïcödé Sensor", "trailing\\", "line\nbreak",
              "  padded  ", "Cooler (CFX5)", 'say "hi"', "back\\slash middle"]


def device_point(name, fields, folder=None, measurement='device_changes', time=T0):
    tags = {'name': name, 'folderId': '0' if folder is None else '123'}
    if folder is not None:
        tags['folder'] = folder
    return {'measurement': measurement, 'tags': tags, 'fields': fields, 'time': time}


def corpus():
    points = []
    # one point per string value, as a state value and as a name
    for index, text in enumerate(STRINGS):
        points.append(device_point(f"Device {index}", {'state.displayText': text, 'model': text, 'id': float(index)}))
    # numbers as ints, floats and their .num companions
    for index, number in enumerate(NUMBERS):
        points.append(device_point("Numeric Device", {'sensorValue': number, 'sensorValue.num': float(number),
                                                      'batteryLevel': int(number) if isinstance(number, int) else number}))
    # bools, liveness fields, mixed types in one point
    points.append(device_point("Living Room Lamp", {
        'onState': True, 'state.onOffState': False, 'onState.num': 1.0, 'brightness': 75,
        'lastChanged': 1760440000.0, 'secondsSinceLastChanged': 12.345, 'lastSuccessfulComm': 1760440011.0,
        'secondsSinceLastSuccessfulComm': 1.0, 'deviceTypeId': 'relay', 'name': 'Living Room Lamp',
    }, folder="Living Room"))
    # awkward tag values and folder names
    for index, tag in enumerate(TAG_VALUES):
        points.append(device_point(tag, {'value': index}, folder=tag))
    # awkward field keys and measurement names
    points.append({'measurement': 'thermostat_changes', 'tags': {'name': 'Upstairs Nest'},
                   'fields': {'state.hvacOperationMode': 'heat', 'setpointHeat': 68.0, 'key with space': 1,
                              'key,comma': 2, 'key=eq': 3, 'key\\back': 4}, 'time': T0})
    points.append({'measurement': 'weird measurement,with=chars', 'tags': {}, 'fields': {'x': 1.0}, 'time': T0})
    # variables
    for index, value in enumerate(["42", "on", "", "3.14", 'quote"d', "multi\nline"]):
        fields = {'name': f"Var{index}", 'value': value}
        try:
            fields['value.num'] = float(value)
        except ValueError:
            pass
        points.append({'measurement': 'variable_changes', 'tags': {'varname': f"Var{index}"}, 'fields': fields,
                       'time': T0})
    # empty tag values and None fields are skipped by both encoders
    points.append({'measurement': 'device_changes', 'tags': {'name': 'x', 'folder': ''},
                   'fields': {'a': None, 'b': 1.0}, 'time': T0})
    # timestamps: aware (UTC and not), naive (= UTC), microsecond edge, integer ns, none
    points.append(device_point("tz", {'v': 1.0}, time=T0.astimezone(EASTERN)))
    points.append(device_point("naive", {'v': 1.0}, time=datetime.datetime(2026, 1, 2, 3, 4, 5, 6)))
    points.append(device_point("epoch", {'v': 1.0}, time=datetime.datetime(1970, 1, 1, tzinfo=UTC)))
    points.append(device_point("pre-epoch", {'v': 1.0}, time=datetime.datetime(1969, 12, 31, 23, 59, 59, 999999, tzinfo=UTC)))
    points.append(device_point("int time", {'v': 1.0}, time=1760440000123456789))
    points.append(device_point("no time", {'v': 1.0}, time=None))
    points.append(device_point("now", {'v': 1.0}, time=datetime.datetime.now(UTC)))
    return points


def ours(points):
    return '\n'.join(line for _, line in encode_points(points)) + '\n'


def test_corpus_is_byte_identical_to_influxdb_5_3_2():
    points = corpus()
    assert ours(points) == reference.make_lines({'points': points})


@pytest.mark.parametrize("point", corpus(), ids=lambda p: str(p['tags'].get('name', p['measurement']))[:30])
def test_each_point_matches(point):
    expected = reference.make_line(point['measurement'], tags=point['tags'], fields=point['fields'], time=point['time'])
    assert make_line(point['measurement'], point['tags'], point['fields'], point['time']) == expected


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_nan_and_infinity_are_skipped(bad):
    """Deliberate difference: 5.3.2 wrote nan/inf, which InfluxDB rejects along
    with the rest of the device's point."""
    fields = {'sensorValue': bad, 'onState': True, 'secondsSinceLastChanged': 3.5}
    expected_without = reference.make_line('device_changes', tags={'name': 'x'},
                                           fields={'onState': True, 'secondsSinceLastChanged': 3.5}, time=T0)
    assert make_line('device_changes', {'name': 'x'}, fields, T0) == expected_without
    # and 5.3.2 really did produce the unparseable token
    assert ('=nan' in reference.make_line('m', fields={'v': bad})) or ('=inf' in reference.make_line('m', fields={'v': bad})) \
        or ('=-inf' in reference.make_line('m', fields={'v': bad}))


def test_point_without_fields_is_skipped():
    """Deliberate difference: a field-less line is rejected by both servers (and
    InfluxDB 3 then rejects the whole batch)."""
    assert make_line('m', {'name': 'x'}, {'a': None}, T0) is None
    assert make_line('m', {'name': 'x'}, {'a': math.nan}, T0) is None
    points = [device_point("a", {'v': math.nan}), device_point("b", {'v': 1.0})]
    encoded = encode_points(points)
    assert [index for index, _ in encoded] == [1]


def test_field_value_encoding_rules():
    assert encode_field_value("a\"b\\c\nd") == '"a\\"b\\\\c\\nd"'
    assert encode_field_value(5) == '5i'
    assert encode_field_value(True) == 'True'
    assert encode_field_value(False) == 'False'
    assert encode_field_value(1.0) == '1.0'
    assert encode_field_value(None) is None
    assert encode_field_value(b"bytes") == '"bytes"'


def test_key_escaping():
    assert escape_key('a b,c=d\ne\\f') == 'a\\ b\\,c\\=d\\ne\\\\f'


def test_nanoseconds():
    assert to_nanoseconds(datetime.datetime(1970, 1, 1, 0, 0, 1, tzinfo=UTC)) == 10 ** 9
    assert to_nanoseconds(datetime.datetime(1970, 1, 1, 0, 0, 1)) == 10 ** 9  # naive = UTC
    assert to_nanoseconds(T0) == reference._convert_timestamp(T0)
    with pytest.raises(ValueError):
        to_nanoseconds("2026-10-14T00:00:00Z")
