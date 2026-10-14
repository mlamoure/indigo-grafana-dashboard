"""
Tests for the percent-changed filter helpers introduced for issue #7.  They
exercise the real functions from plugin.py; conftest.py supplies the fake indigo.
"""

import pytest

import plugin
from plugin import numeric_value, percent_changed
from json_adaptor import LIVENESS_FIELDS, LIVENESS_SENTINEL_FLOOR


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

    def test_sentinel_floor_covers_the_placeholder_in_every_timezone(self):
        """Indigo's never-communicated placeholder is 2000-01-01 LOCAL time, so its
        epoch depends on the server's UTC offset. Observed as 946702800 on this US
        Eastern server. The floor must sit above the latest possible rendering
        (UTC-12) or those devices report as ~26 years stale and pin the top of every
        staleness panel."""
        placeholder_utc = 946684800.0  # 2000-01-01T00:00:00Z
        latest_local = placeholder_utc + 12 * 3600  # same wall-clock at UTC-12
        observed_us_eastern = 946702800.0

        assert LIVENESS_SENTINEL_FLOOR > latest_local
        assert LIVENESS_SENTINEL_FLOOR > observed_us_eastern
        assert LIVENESS_SENTINEL_FLOOR > placeholder_utc

    def test_sentinel_floor_stays_below_any_real_observation(self):
        """A floor set too high would silently drop genuinely old-but-real
        timestamps. 2001 onwards must survive."""
        year_2001 = 978307200.0
        assert LIVENESS_SENTINEL_FLOOR < year_2001

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
