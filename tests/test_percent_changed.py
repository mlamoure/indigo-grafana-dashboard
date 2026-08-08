"""
Tests for the percent-changed filter helpers introduced for issue #7.

Unlike the other files in this directory, these exercise the REAL functions from
plugin.py rather than re-implementing them locally. plugin.py imports `indigo` and
`influxdb`, neither of which exists off an Indigo server, so both are stubbed into
sys.modules before the import below.
"""

import os
import sys
import types

import pytest

PLUGIN_DIR = os.path.join(
    os.path.dirname(__file__), '..',
    'Grafana Home Dashboard.indigoPlugin/Contents/Server Plugin'
)
sys.path.insert(0, PLUGIN_DIR)


def _install_stubs():
    """Minimal stand-ins for the two modules only present on an Indigo server."""
    if 'indigo' not in sys.modules:
        indigo = types.ModuleType('indigo')

        # Real classes, not Mocks: json_adaptor calls isinstance() against these and
        # isinstance() raises TypeError when given a MagicMock as its second argument.
        indigo.Dict = type('Dict', (dict,), {})
        indigo.List = type('List', (list,), {})
        indigo.PluginBase = type('PluginBase', (object,), {})
        indigo.devices = []
        indigo.variables = []
        sys.modules['indigo'] = indigo

    if 'influxdb' not in sys.modules:
        influxdb = types.ModuleType('influxdb')
        influxdb.InfluxDBClient = type('InfluxDBClient', (object,), {})
        sys.modules['influxdb'] = influxdb

        exceptions = types.ModuleType('influxdb.exceptions')
        exceptions.InfluxDBClientError = type('InfluxDBClientError', (Exception,), {})
        sys.modules['influxdb.exceptions'] = exceptions
        influxdb.exceptions = exceptions


_install_stubs()

import plugin  # noqa: E402
from plugin import numeric_value, percent_changed  # noqa: E402
from json_adaptor import LIVENESS_FIELDS, LIVENESS_SENTINEL_FLOOR  # noqa: E402


class TestNumericValue:
    @pytest.mark.parametrize("value,expected", [
        (10, 10.0),
        (10.5, 10.5),
        ("10.5", 10.5),
        ("-3", -3.0),
        (0, 0.0),
    ])
    def test_coerces_numbers(self, value, expected):
        assert numeric_value(value) == expected

    @pytest.mark.parametrize("value", [None, "", "on", "n/a", object()])
    def test_rejects_non_numeric(self, value):
        assert numeric_value(value) is None

    @pytest.mark.parametrize("value", [True, False])
    def test_rejects_bools(self, value):
        """A False -> True flip is a divide-by-zero, not a percentage change.
        float(True) would silently be 1.0, so bools must be rejected explicitly."""
        assert numeric_value(value) is None


class TestPercentChanged:
    def test_basic_increase(self):
        assert percent_changed(100, 150) == pytest.approx(50.0)

    def test_basic_decrease(self):
        assert percent_changed(100, 50) == pytest.approx(-50.0)

    def test_no_change(self):
        """The frozen-sensor case: a dead device changes 0%, so it passes every
        percentChanged filter. This is why the liveness fields, not this filter,
        are what detect a dead sensor."""
        assert percent_changed(70.0, 70.0) == 0.0

    def test_magnitude_is_symmetric_with_the_old_expression(self):
        """The previous inline expression was ((old - new) / old) * 100, i.e. sign
        inverted. Only abs() is ever used, so magnitudes must match."""
        for previous, new in [(100, 150), (100, 50), (12.5, 3.2), (-40, -10)]:
            old_style = ((previous - new) / previous) * 100
            assert abs(percent_changed(previous, new)) == pytest.approx(abs(old_style))

    def test_zero_baseline_returns_none(self):
        """Previously raised ZeroDivisionError, was swallowed, and passed the value."""
        assert percent_changed(0, 50) is None
        assert percent_changed(0.0, 0.0) is None

    def test_negative_baseline(self):
        assert percent_changed(-100, -50) == pytest.approx(-50.0)

    @pytest.mark.parametrize("previous,new", [
        (None, 50),
        (50, None),
        ("on", 50),
        (50, "off"),
        (True, 50),
        (50, False),
    ])
    def test_unusable_operands_return_none(self, previous, new):
        """None means 'no opinion' - the caller lets the value through rather than
        blocking it on a comparison it could not make."""
        assert percent_changed(previous, new) is None

    def test_spike_exceeds_a_typical_threshold(self):
        assert abs(percent_changed(70.0, 200.0)) > 20


class TestPreviousFilterValue:
    """The baseline resolver has to bridge two key spaces: the JSON adaptor's
    flattened keys ('state.x', 'x.num') and Indigo's own state namespace."""

    class _FakeSelf:
        def __init__(self, lastWritten=None):
            self.DeviceLastWrittenValues = lastWritten or {}

    class _FakeDev:
        def __init__(self, dev_id=1, states=None):
            self.id = dev_id
            self.states = states or {}

    def _call(self, fake_self, origDev, dev, key):
        return plugin.Plugin.PreviousFilterValue(fake_self, origDev, dev, key)

    def test_prefers_origdev_state(self):
        origDev = self._FakeDev(states={'sensorValue': 70.0})
        dev = self._FakeDev()
        assert self._call(self._FakeSelf(), origDev, dev, 'sensorValue') == 70.0

    def test_strips_state_prefix(self):
        origDev = self._FakeDev(states={'onOffState': 1})
        dev = self._FakeDev()
        assert self._call(self._FakeSelf(), origDev, dev, 'state.onOffState') == 1

    def test_strips_num_suffix(self):
        origDev = self._FakeDev(states={'batteryLevel': 90})
        dev = self._FakeDev()
        assert self._call(self._FakeSelf(), origDev, dev, 'batteryLevel.num') == 90

    def test_strips_both(self):
        origDev = self._FakeDev(states={'hvac_state': 2})
        dev = self._FakeDev()
        assert self._call(self._FakeSelf(), origDev, dev, 'state.hvac_state.num') == 2

    def test_falls_back_to_last_written_when_no_origdev(self):
        """This is the polling path: UpdateAll() passes origDev=None."""
        fake_self = self._FakeSelf({1: {'sensorValue': 68.5}})
        dev = self._FakeDev(dev_id=1)
        assert self._call(fake_self, None, dev, 'sensorValue') == 68.5

    def test_falls_back_when_origdev_lacks_the_state(self):
        origDev = self._FakeDev(states={'somethingElse': 1})
        dev = self._FakeDev(dev_id=1)
        fake_self = self._FakeSelf({1: {'sensorValue': 68.5}})
        assert self._call(fake_self, origDev, dev, 'sensorValue') == 68.5

    def test_none_when_no_baseline_anywhere(self):
        """First poll after a restart. percent_changed() then returns None and the
        value is let through rather than blocked on an unknown comparison."""
        dev = self._FakeDev(dev_id=1)
        assert self._call(self._FakeSelf(), None, dev, 'sensorValue') is None

    def test_unknown_device_id_is_not_a_keyerror(self):
        fake_self = self._FakeSelf({99: {'sensorValue': 1.0}})
        dev = self._FakeDev(dev_id=1)
        assert self._call(fake_self, None, dev, 'sensorValue') is None


class TestLivenessConstants:
    def test_pairs_are_attribute_then_age(self):
        assert LIVENESS_FIELDS == (
            ('lastChanged', 'secondsSinceLastChanged'),
            ('lastSuccessfulComm', 'secondsSinceLastSuccessfulComm'),
        )

    def test_sentinel_floor_is_year_2000(self):
        """Indigo reports a 1970-ish placeholder for devices that never
        communicated; those must be omitted, not written as a maximally stale 0."""
        import datetime
        floor = datetime.datetime.fromtimestamp(LIVENESS_SENTINEL_FLOOR,
                                                datetime.timezone.utc)
        assert floor.year == 2000
        assert 0.0 < LIVENESS_SENTINEL_FLOOR
        assert LIVENESS_SENTINEL_FLOOR < 1000000000.0  # comfortably below "now"

    def test_liveness_fields_are_always_sent(self):
        """They must never be routed through the include-states gate: lastChanged
        moves on every device change and would emit a point per change."""
        for attribute, agefield in LIVENESS_FIELDS:
            assert attribute in plugin.ALWAYS_SENT_STATES
            assert agefield in plugin.ALWAYS_SENT_STATES

    def test_liveness_fields_are_not_in_default_states(self):
        for attribute, agefield in LIVENESS_FIELDS:
            assert attribute not in plugin.DEFAULT_STATES
            assert agefield not in plugin.DEFAULT_STATES
