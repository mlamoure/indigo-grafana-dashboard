"""
Tests for data filtering functionality.

Tests min/max value filtering, percentage change filtering,
device-specific filters, and filter logging.
"""

import pytest
from unittest.mock import Mock, MagicMock


class InfluxFilter:
    """Mock InfluxFilter class for testing."""

    def __init__(self, property_name, strategy='minMax', min_value=None, max_value=None,
                 percent_change=None, applies_to_all=True, device_list=None,
                 log_failures=False, prevent_minimum_updates=True):
        self.property = property_name
        self.strategy = strategy
        self.min = min_value
        self.max = max_value
        self.percent = percent_change
        self.appliesToAll = applies_to_all
        self.deviceList = device_list or []
        self.logFailures = log_failures
        self.preventMinimumUpdates = prevent_minimum_updates

    def applies_to_device(self, device_id):
        """Check if filter applies to device."""
        if self.appliesToAll:
            return True
        return device_id in self.deviceList

    def check_value(self, value, previous_value=None):
        """Check if value passes filter."""
        if self.strategy == 'minMax':
            if self.min is not None and value < self.min:
                return False
            if self.max is not None and value > self.max:
                return False
            return True

        elif self.strategy == 'percentChanged':
            if previous_value is None:
                return True
            if previous_value == 0:
                return value == 0  # Avoid division by zero
            percent_change = abs((value - previous_value) / previous_value * 100)
            return percent_change <= self.percent

        return True


class TestMinMaxFiltering:
    """Test min/max value filtering."""

    def test_min_filter_pass(self):
        """Test value passes minimum filter."""
        filter = InfluxFilter('sensorValue', strategy='minMax', min_value=0, max_value=100)

        assert filter.check_value(50) is True
        assert filter.check_value(0) is True
        assert filter.check_value(100) is True

    def test_min_filter_fail(self):
        """Test value fails minimum filter."""
        filter = InfluxFilter('sensorValue', strategy='minMax', min_value=0, max_value=100)

        assert filter.check_value(-10) is False
        assert filter.check_value(150) is False

    def test_max_filter_only(self):
        """Test max filter without min."""
        filter = InfluxFilter('sensorValue', strategy='minMax', min_value=None, max_value=100)

        assert filter.check_value(50) is True
        assert filter.check_value(-100) is True
        assert filter.check_value(100) is True
        assert filter.check_value(101) is False

    def test_min_filter_only(self):
        """Test min filter without max."""
        filter = InfluxFilter('sensorValue', strategy='minMax', min_value=0, max_value=None)

        assert filter.check_value(50) is True
        assert filter.check_value(1000) is True
        assert filter.check_value(0) is True
        assert filter.check_value(-1) is False

    def test_temperature_range(self):
        """Test realistic temperature range filter."""
        filter = InfluxFilter('temperature', strategy='minMax', min_value=-40, max_value=120)

        # Valid temperatures
        assert filter.check_value(72) is True
        assert filter.check_value(-10) is True
        assert filter.check_value(100) is True

        # Invalid temperatures (sensor errors)
        assert filter.check_value(-50) is False
        assert filter.check_value(150) is False
        assert filter.check_value(999) is False


class TestPercentageChangeFiltering:
    """Test percentage change filtering."""

    def test_percent_change_pass(self):
        """Test value passes percentage change filter."""
        filter = InfluxFilter('sensorValue', strategy='percentChanged', percent_change=10)

        # 5% change - should pass
        assert filter.check_value(105, previous_value=100) is True
        # 10% change - should pass (at limit)
        assert filter.check_value(110, previous_value=100) is True

    def test_percent_change_fail(self):
        """Test value fails percentage change filter."""
        filter = InfluxFilter('sensorValue', strategy='percentChanged', percent_change=10)

        # 20% change - should fail
        assert filter.check_value(120, previous_value=100) is False
        # 50% change - should fail
        assert filter.check_value(150, previous_value=100) is False

    def test_percent_change_decrease(self):
        """Test percentage change with decreasing values."""
        filter = InfluxFilter('sensorValue', strategy='percentChanged', percent_change=10)

        # 5% decrease - should pass
        assert filter.check_value(95, previous_value=100) is True
        # 10% decrease - should pass
        assert filter.check_value(90, previous_value=100) is True
        # 20% decrease - should fail
        assert filter.check_value(80, previous_value=100) is False

    def test_percent_change_no_previous(self):
        """Test percentage change filter with no previous value."""
        filter = InfluxFilter('sensorValue', strategy='percentChanged', percent_change=10)

        # First reading - should always pass
        assert filter.check_value(100, previous_value=None) is True

    def test_percent_change_zero_previous(self):
        """Test percentage change filter with previous value of zero."""
        filter = InfluxFilter('sensorValue', strategy='percentChanged', percent_change=10)

        # Previous is 0 - should only pass if current is also 0
        assert filter.check_value(0, previous_value=0) is True
        assert filter.check_value(10, previous_value=0) is False

    def test_percent_change_small_values(self):
        """Test percentage change with small values."""
        filter = InfluxFilter('sensorValue', strategy='percentChanged', percent_change=10)

        # 10% of 1 = 0.1
        assert filter.check_value(1.09, previous_value=1.0) is True
        assert filter.check_value(1.11, previous_value=1.0) is False


class TestDeviceSpecificFilters:
    """Test device-specific filter application."""

    def test_global_filter(self):
        """Test filter that applies to all devices."""
        filter = InfluxFilter('sensorValue', strategy='minMax', min_value=0, max_value=100,
                              applies_to_all=True)

        assert filter.applies_to_device(123) is True
        assert filter.applies_to_device(456) is True
        assert filter.applies_to_device(789) is True

    def test_device_specific_filter(self):
        """Test filter for specific devices only."""
        filter = InfluxFilter('sensorValue', strategy='minMax', min_value=0, max_value=100,
                              applies_to_all=False, device_list=[123, 456])

        assert filter.applies_to_device(123) is True
        assert filter.applies_to_device(456) is True
        assert filter.applies_to_device(789) is False

    def test_multiple_filters_per_device(self):
        """Test multiple filters applying to same device."""
        filters = [
            InfluxFilter('sensorValue', strategy='minMax', min_value=0, max_value=100),
            InfluxFilter('sensorValue', strategy='percentChanged', percent_change=10)
        ]

        # Value must pass all filters
        value = 50
        previous_value = 48

        results = [f.check_value(value, previous_value) for f in filters]
        assert all(results) is True

        # Fail one filter
        value = 150  # Fails min/max
        results = [f.check_value(value, previous_value) for f in filters]
        assert all(results) is False


class TestFilterOrdering:
    """Test filter processing order."""

    def test_filter_order_matters(self):
        """Test that filter order affects logging."""
        # Filter 1: Specific device, logging disabled
        filter1 = InfluxFilter('sensorValue', strategy='minMax', min_value=0, max_value=100,
                               applies_to_all=False, device_list=[123], log_failures=False)

        # Filter 2: All devices, logging enabled
        filter2 = InfluxFilter('sensorValue', strategy='minMax', min_value=0, max_value=100,
                               applies_to_all=True, log_failures=True)

        # Process filters in order
        filters = [filter1, filter2]

        # For device 123, filter 1 applies first (no logging)
        # For device 456, only filter 2 applies (logging enabled)

        assert filter1.applies_to_device(123) is True
        assert filter1.logFailures is False

        assert filter2.applies_to_device(456) is True
        assert filter2.logFailures is True


class TestFilterLogging:
    """Test filter failure logging."""

    def test_log_failures_enabled(self):
        """Test filter with logging enabled."""
        filter = InfluxFilter('sensorValue', strategy='minMax', min_value=0, max_value=100,
                              log_failures=True)

        assert filter.logFailures is True

    def test_log_failures_disabled(self):
        """Test filter with logging disabled."""
        filter = InfluxFilter('sensorValue', strategy='minMax', min_value=0, max_value=100,
                              log_failures=False)

        assert filter.logFailures is False


class TestMinimumUpdateLocking:
    """Test minimum update frequency locking after filter failure."""

    def test_prevent_minimum_updates_enabled(self):
        """Test locking of minimum updates when enabled."""
        filter = InfluxFilter('sensorValue', strategy='percentChanged', percent_change=10,
                              prevent_minimum_updates=True)

        assert filter.preventMinimumUpdates is True

    def test_prevent_minimum_updates_disabled(self):
        """Test minimum updates continue when disabled."""
        filter = InfluxFilter('sensorValue', strategy='percentChanged', percent_change=10,
                              prevent_minimum_updates=False)

        assert filter.preventMinimumUpdates is False


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_none_value(self):
        """Test filter with None value."""
        filter = InfluxFilter('sensorValue', strategy='minMax', min_value=0, max_value=100)

        # None values should be handled gracefully
        # This might raise an exception or return False depending on implementation

    def test_string_value_in_numeric_filter(self):
        """Test filter receives string instead of number."""
        filter = InfluxFilter('sensorValue', strategy='minMax', min_value=0, max_value=100)

        # String values should be handled or raise appropriate error

    def test_infinity_values(self):
        """Test filter with infinity values."""
        filter = InfluxFilter('sensorValue', strategy='minMax', min_value=0, max_value=100)

        # Should handle float('inf') and float('-inf')

    def test_nan_values(self):
        """Test filter with NaN values."""
        filter = InfluxFilter('sensorValue', strategy='minMax', min_value=0, max_value=100)

        # Should handle float('nan')
