"""
Pytest configuration and fixtures for Indigo Grafana Dashboard Plugin tests.

This module provides fixtures and mocks for testing the plugin without
requiring a running Indigo environment.
"""

import pytest
from unittest.mock import Mock, MagicMock
import sys
import os

# Add plugin directory to path
plugin_dir = os.path.join(os.path.dirname(__file__), '..', 'Grafana Home Dashboard.indigoPlugin/Contents/Server Plugin')
sys.path.insert(0, plugin_dir)


@pytest.fixture
def mock_indigo():
    """Mock Indigo module with necessary classes and functions."""
    indigo = MagicMock()

    # Mock PluginBase
    indigo.PluginBase = Mock

    # Mock Dict
    indigo.Dict = dict

    # Mock devices
    indigo.devices = []

    # Mock variables
    indigo.variables = []

    return indigo


@pytest.fixture
def mock_influxdb_client():
    """Mock InfluxDB client."""
    client = MagicMock()
    client.write_points.return_value = True
    client.ping.return_value = True
    client.create_database.return_value = True
    client.get_list_database.return_value = []
    return client


@pytest.fixture
def plugin_config():
    """Standard plugin configuration for tests."""
    return {
        'InfluxHost': 'localhost',
        'InfluxSSL': False,
        'InfluxHTTPPort': '8086',
        'InfluxUser': 'test',
        'InfluxPassword': 'test',
        'InfluxDB': 'test_db',
        'InfluxRetention': 24,
        'MinimumUpdateFrequency': 5,
        'ServerDebug': False,
        'ConfigDebug': False,
        'TransportDebug': False,
        'TransportDebugL2': False,
        'JSONDebug': False,
        'listIncStates': [],
        'listIncDevices': [],
        'listExclDevices': []
    }


@pytest.fixture
def mock_device():
    """Create a mock Indigo device."""
    device = MagicMock()
    device.id = 123
    device.name = "Test Device"
    device.states = {
        'onState': True,
        'brightnessLevel': 75,
        'sensorValue': 23.5,
        'batteryLevel': 100
    }
    device.folderId = 0
    return device


@pytest.fixture
def mock_variable():
    """Create a mock Indigo variable."""
    variable = MagicMock()
    variable.id = 456
    variable.name = "TestVariable"
    variable.value = "42"
    return variable
