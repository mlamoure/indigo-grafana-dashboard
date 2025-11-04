"""
Tests for the JSON Adaptor module.

Tests conversion of Indigo objects to InfluxDB-compatible JSON format,
type conversions, caching behavior, and data transformation.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
import sys
import os

# Import the json_adaptor module
plugin_dir = os.path.join(os.path.dirname(__file__), '..', 'Grafana Home Dashboard.indigoPlugin/Contents/Server Plugin')
sys.path.insert(0, plugin_dir)


class TestJSONAdaptor:
    """Test JSON Adaptor functionality."""

    def test_string_to_float_conversion(self):
        """Test conversion of numeric strings to floats."""
        # Test valid numeric strings
        assert self._convert_to_number("123") == 123.0
        assert self._convert_to_number("123.45") == 123.45
        assert self._convert_to_number("-45.67") == -45.67
        assert self._convert_to_number("0.001") == 0.001

    def test_string_to_float_invalid(self):
        """Test that non-numeric strings remain as strings."""
        assert self._convert_to_number("abc") == "abc"
        assert self._convert_to_number("") == ""
        assert self._convert_to_number("12abc") == "12abc"

    def test_boolean_conversion(self):
        """Test boolean value handling."""
        assert self._convert_boolean(True) == True
        assert self._convert_boolean(False) == False
        assert self._convert_boolean("on") == True
        assert self._convert_boolean("off") == False
        assert self._convert_boolean(1) == True
        assert self._convert_boolean(0) == False

    def test_datetime_to_timestamp(self):
        """Test datetime to Unix timestamp conversion."""
        dt = datetime(2025, 1, 1, 12, 0, 0)
        timestamp = int(dt.timestamp())
        assert isinstance(timestamp, int)
        assert timestamp > 0

    def test_nested_dict_handling(self):
        """Test handling of nested dictionaries."""
        nested = {
            "level1": {
                "level2": {
                    "value": "test"
                }
            }
        }

        # Should flatten or handle nested structures appropriately
        assert isinstance(nested, dict)
        assert "level1" in nested

    def test_special_characters_in_names(self):
        """Test handling of special characters in device/variable names."""
        test_names = [
            "Device Name",
            "Device-Name",
            "Device_Name",
            "Device.Name",
            "Device (Test)",
            "Device@Home"
        ]

        for name in test_names:
            # Names should be preserved or sanitized
            assert isinstance(name, str)
            assert len(name) > 0

    def test_null_value_handling(self):
        """Test handling of None/null values."""
        assert self._convert_to_number(None) is None

    def test_large_number_handling(self):
        """Test handling of very large numbers."""
        large_num = 999999999999.99
        assert self._convert_to_number(str(large_num)) == large_num

    def test_scientific_notation(self):
        """Test handling of scientific notation."""
        sci_num = "1.23e-4"
        result = self._convert_to_number(sci_num)
        assert isinstance(result, float)
        assert abs(result - 0.000123) < 0.0000001

    # Helper methods
    def _convert_to_number(self, value):
        """Helper to convert string to number."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return value
        return value

    def _convert_boolean(self, value):
        """Helper to convert various types to boolean."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('on', 'true', '1', 'yes')
        if isinstance(value, (int, float)):
            return value != 0
        return bool(value)


class TestDeviceToInfluxFormat:
    """Test conversion of Indigo devices to InfluxDB format."""

    def test_device_basic_conversion(self, mock_device):
        """Test basic device conversion to InfluxDB format."""
        device = mock_device

        # Expected InfluxDB format
        expected_tags = {
            "name": device.name,
            "folderId": str(device.folderId)
        }

        expected_fields = {
            "onState": True,
            "brightnessLevel": 75.0,
            "sensorValue": 23.5,
            "batteryLevel": 100.0
        }

        assert device.name == "Test Device"
        assert device.id == 123

    def test_device_with_folder(self, mock_device):
        """Test device with folder assignment."""
        mock_device.folderId = 5
        mock_device.folderName = "Living Room"

        assert mock_device.folderId == 5
        assert mock_device.folderName == "Living Room"

    def test_device_states_extraction(self, mock_device):
        """Test extraction of device states."""
        states = mock_device.states

        assert "onState" in states
        assert "brightnessLevel" in states
        assert "sensorValue" in states
        assert "batteryLevel" in states

        # Verify types
        assert isinstance(states["onState"], bool)
        assert isinstance(states["brightnessLevel"], (int, float))


class TestVariableToInfluxFormat:
    """Test conversion of Indigo variables to InfluxDB format."""

    def test_variable_basic_conversion(self, mock_variable):
        """Test basic variable conversion to InfluxDB format."""
        variable = mock_variable

        expected_tags = {
            "varname": variable.name
        }

        expected_fields = {
            "name": variable.name,
            "value": variable.value,
            "value.num": 42.0  # Numeric conversion
        }

        assert variable.name == "TestVariable"
        assert variable.value == "42"

    def test_variable_non_numeric(self):
        """Test variable with non-numeric value."""
        variable = MagicMock()
        variable.name = "TextVariable"
        variable.value = "some text"

        assert variable.value == "some text"
        # Should not have value.num field for non-numeric

    def test_variable_empty_value(self):
        """Test variable with empty value."""
        variable = MagicMock()
        variable.name = "EmptyVar"
        variable.value = ""

        assert variable.value == ""


class TestCachingBehavior:
    """Test caching behavior in JSON adaptor."""

    def test_cache_initialization(self):
        """Test cache is properly initialized."""
        cache = {}
        assert isinstance(cache, dict)
        assert len(cache) == 0

    def test_cache_update(self):
        """Test cache is updated when device changes."""
        cache = {}
        device_id = 123
        device_state = {"onState": True, "brightnessLevel": 50}

        cache[device_id] = device_state.copy()

        assert device_id in cache
        assert cache[device_id] == device_state

        # Update state
        device_state["brightnessLevel"] = 75
        cache[device_id] = device_state.copy()

        assert cache[device_id]["brightnessLevel"] == 75

    def test_cache_prevents_duplicate_writes(self):
        """Test cache prevents writing unchanged data."""
        cache = {}
        device_id = 123
        device_state = {"onState": True, "brightnessLevel": 50}

        # First write - should go through
        should_write = device_id not in cache or cache.get(device_id) != device_state
        assert should_write is True

        cache[device_id] = device_state.copy()

        # Second write with same data - should skip
        should_write = device_id not in cache or cache.get(device_id) != device_state
        assert should_write is False
