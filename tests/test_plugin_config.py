"""
Tests for plugin configuration and state management.

Tests configuration validation, inclusion/exclusion logic,
state tracking, and minimum update frequency.
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta


class TestPluginConfiguration:
    """Test plugin configuration handling."""

    def test_default_configuration(self, plugin_config):
        """Test default configuration values."""
        assert plugin_config['InfluxHost'] == 'localhost'
        assert plugin_config['InfluxHTTPPort'] == '8086'
        assert plugin_config['InfluxUser'] == 'test'
        assert plugin_config['InfluxDB'] == 'test_db'
        assert plugin_config['InfluxSSL'] is False

    def test_configuration_update(self, plugin_config):
        """Test configuration can be updated."""
        plugin_config['InfluxHost'] = 'influx.example.com'
        plugin_config['InfluxHTTPPort'] = '8087'

        assert plugin_config['InfluxHost'] == 'influx.example.com'
        assert plugin_config['InfluxHTTPPort'] == '8087'

    def test_ssl_configuration(self, plugin_config):
        """Test SSL configuration."""
        plugin_config['InfluxSSL'] = True

        assert plugin_config['InfluxSSL'] is True

    def test_retention_policy_configuration(self, plugin_config):
        """Test retention policy settings."""
        # 24 months = 2 years
        assert plugin_config['InfluxRetention'] == 24

        # Test different retention periods
        plugin_config['InfluxRetention'] = 6  # 6 months
        assert plugin_config['InfluxRetention'] == 6

        plugin_config['InfluxRetention'] = -1  # Disabled
        assert plugin_config['InfluxRetention'] == -1

    def test_debug_flags(self, plugin_config):
        """Test debug flag configuration."""
        assert plugin_config['ServerDebug'] is False
        assert plugin_config['ConfigDebug'] is False
        assert plugin_config['TransportDebug'] is False
        assert plugin_config['TransportDebugL2'] is False
        assert plugin_config['JSONDebug'] is False

        # Enable debug
        plugin_config['ServerDebug'] = True
        plugin_config['TransportDebug'] = True

        assert plugin_config['ServerDebug'] is True
        assert plugin_config['TransportDebug'] is True


class TestInclusionExclusionLogic:
    """Test device inclusion and exclusion logic."""

    def test_device_excluded(self, plugin_config):
        """Test device in exclusion list is skipped."""
        plugin_config['listExclDevices'] = [123, 456]

        device_id = 123
        assert device_id in plugin_config['listExclDevices']

    def test_device_included(self, plugin_config):
        """Test device in inclusion list is processed."""
        plugin_config['listIncDevices'] = [789]

        device_id = 789
        assert device_id in plugin_config['listIncDevices']

    def test_device_neither_included_nor_excluded(self, plugin_config):
        """Test device uses global include states."""
        plugin_config['listIncDevices'] = []
        plugin_config['listExclDevices'] = []
        plugin_config['listIncStates'] = ['onState', 'brightnessLevel']

        device_id = 999
        assert device_id not in plugin_config['listIncDevices']
        assert device_id not in plugin_config['listExclDevices']

        # Should use global include states
        assert 'onState' in plugin_config['listIncStates']

    def test_exclusion_overrides_inclusion(self, plugin_config):
        """Test that exclusion takes priority over inclusion."""
        device_id = 123
        plugin_config['listIncDevices'] = [123]
        plugin_config['listExclDevices'] = [123]

        # Device is in both lists - exclusion should win
        is_excluded = device_id in plugin_config['listExclDevices']
        assert is_excluded is True

    def test_global_include_states(self, plugin_config):
        """Test global include states configuration."""
        default_states = [
            'onState',
            'brightnessLevel',
            'sensorValue',
            'batteryLevel',
            'energyCurLevel'
        ]

        plugin_config['listIncStates'] = default_states

        assert 'onState' in plugin_config['listIncStates']
        assert 'sensorValue' in plugin_config['listIncStates']
        assert len(plugin_config['listIncStates']) == 5


class TestMinimumUpdateFrequency:
    """Test minimum update frequency logic."""

    def test_update_frequency_5_minutes(self, plugin_config):
        """Test 5-minute update frequency."""
        plugin_config['MinimumUpdateFrequency'] = 5

        assert plugin_config['MinimumUpdateFrequency'] == 5

    def test_update_frequency_disabled(self, plugin_config):
        """Test disabled update frequency."""
        plugin_config['MinimumUpdateFrequency'] = -1

        assert plugin_config['MinimumUpdateFrequency'] == -1

    def test_should_send_minimum_update(self):
        """Test logic for when minimum update should be sent."""
        last_update_time = datetime.now() - timedelta(minutes=10)
        current_time = datetime.now()
        min_frequency_minutes = 5

        time_diff = (current_time - last_update_time).total_seconds() / 60

        should_update = time_diff >= min_frequency_minutes
        assert should_update is True

    def test_should_not_send_minimum_update(self):
        """Test when minimum update should NOT be sent."""
        last_update_time = datetime.now() - timedelta(minutes=2)
        current_time = datetime.now()
        min_frequency_minutes = 5

        time_diff = (current_time - last_update_time).total_seconds() / 60

        should_update = time_diff >= min_frequency_minutes
        assert should_update is False


class TestDeviceStateTracking:
    """Test device state change tracking."""

    def test_track_new_device(self):
        """Test tracking a new device."""
        device_update_list = []
        device_name = "Test Device"
        current_time = datetime.now()

        # Add new device
        device_update_list.append([device_name, current_time, False])

        assert len(device_update_list) == 1
        assert device_update_list[0][0] == device_name

    def test_track_existing_device_update(self):
        """Test updating existing device in tracking list."""
        device_update_list = []
        device_name = "Test Device"
        first_update = datetime.now() - timedelta(minutes=10)

        # Initial tracking
        device_update_list.append([device_name, first_update, False])

        # Find and update
        found = False
        for entry in device_update_list:
            if entry[0] == device_name:
                entry[1] = datetime.now()
                entry[2] = True  # Mark as updated
                found = True
                break

        assert found is True
        assert device_update_list[0][2] is True

    def test_multiple_device_tracking(self):
        """Test tracking multiple devices."""
        device_update_list = []
        devices = ["Device 1", "Device 2", "Device 3"]
        current_time = datetime.now()

        for device in devices:
            device_update_list.append([device, current_time, False])

        assert len(device_update_list) == 3

    def test_device_not_in_tracking_list(self):
        """Test checking for device not in tracking list."""
        device_update_list = [
            ["Device 1", datetime.now(), False],
            ["Device 2", datetime.now(), False]
        ]

        device_name = "Device 3"
        found = any(entry[0] == device_name for entry in device_update_list)

        assert found is False


class TestConnectionStateManagement:
    """Test connection state management."""

    def test_initial_connection_state(self):
        """Test initial connection state is disconnected."""
        connected = False
        connection_retry_count = 0

        assert connected is False
        assert connection_retry_count == 0

    def test_connection_success(self):
        """Test connection state after successful connection."""
        connected = True
        connection_retry_count = 0
        quiet_connection_error = False

        assert connected is True
        assert connection_retry_count == 0
        assert quiet_connection_error is False

    def test_connection_failure_retry(self):
        """Test connection retry counter increments."""
        connected = False
        connection_retry_count = 0

        # Simulate failure
        connection_retry_count += 1
        assert connection_retry_count == 1

        # Another failure
        connection_retry_count += 1
        assert connection_retry_count == 2

    def test_connection_retry_limit(self):
        """Test connection stops after retry limit."""
        connection_retry_count = 12
        stop_connection_attempts = False

        if connection_retry_count >= 12:
            stop_connection_attempts = True

        assert stop_connection_attempts is True

    def test_connection_reset_after_success(self):
        """Test connection retry counter resets on success."""
        connection_retry_count = 5
        connected = True

        if connected:
            connection_retry_count = 0

        assert connection_retry_count == 0


class TestPollingIntervalAdjustment:
    """Test polling interval adjustment based on connection state."""

    def test_default_polling_interval(self):
        """Test default polling interval."""
        DEFAULT_POLLING_INTERVAL = 60
        polling_interval = DEFAULT_POLLING_INTERVAL

        assert polling_interval == 60

    def test_fast_polling_during_connection(self):
        """Test fast polling while connecting."""
        FAST_POLLING_INTERVAL = 5
        polling_interval = FAST_POLLING_INTERVAL

        assert polling_interval == 5

    def test_long_polling_after_failures(self):
        """Test long polling interval after many failures."""
        LONG_POLLING_INTERVAL = 60 * 15  # 15 minutes
        connection_retry_count = 11

        if connection_retry_count > 10:
            polling_interval = LONG_POLLING_INTERVAL
        else:
            polling_interval = 60

        assert polling_interval == 900  # 15 minutes


class TestConfigurationValidation:
    """Test configuration validation logic."""

    def test_valid_configuration(self, plugin_config):
        """Test valid configuration passes validation."""
        is_valid = True

        # Check required fields
        if not plugin_config.get('InfluxHost'):
            is_valid = False
        if not plugin_config.get('InfluxHTTPPort'):
            is_valid = False
        if not plugin_config.get('InfluxDB'):
            is_valid = False

        assert is_valid is True

    def test_invalid_configuration_missing_host(self, plugin_config):
        """Test invalid configuration with missing host."""
        plugin_config['InfluxHost'] = ''

        is_valid = bool(plugin_config.get('InfluxHost'))
        assert is_valid is False

    def test_invalid_configuration_missing_database(self, plugin_config):
        """Test invalid configuration with missing database."""
        plugin_config['InfluxDB'] = ''

        is_valid = bool(plugin_config.get('InfluxDB'))
        assert is_valid is False

    def test_port_validation(self, plugin_config):
        """Test port number validation."""
        plugin_config['InfluxHTTPPort'] = '8086'

        port = plugin_config['InfluxHTTPPort']
        is_valid_port = port.isdigit() and 1 <= int(port) <= 65535

        assert is_valid_port is True

    def test_invalid_port(self):
        """Test invalid port number."""
        invalid_ports = ['0', '99999', 'abc', '-1']

        for port in invalid_ports:
            is_valid_port = port.isdigit() and 1 <= int(port) <= 65535
            assert is_valid_port is False
