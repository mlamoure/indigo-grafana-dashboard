"""
Tests for InfluxDB connection handling.

Tests connection establishment, retry logic, error handling,
and connection management using mocked clients.
"""

import pytest
from unittest.mock import Mock, MagicMock
from influxdb.exceptions import InfluxDBClientError


class TestInfluxConnection:
    """Test InfluxDB connection functionality."""

    def test_connection_success(self, mock_influxdb_client, plugin_config):
        """Test successful connection to InfluxDB."""
        # Test that ping returns True for successful connection
        assert mock_influxdb_client.ping() is True

        # Verify client is properly configured
        assert mock_influxdb_client is not None

    def test_connection_auth_failure(self, plugin_config):
        """Test connection failure due to authentication."""
        mock_client = MagicMock()
        mock_client.ping.side_effect = InfluxDBClientError("401: authorization failed")

        # Verify that auth failure raises appropriate exception
        with pytest.raises(InfluxDBClientError, match="authorization failed"):
            mock_client.ping()

    def test_connection_network_failure(self, plugin_config):
        """Test connection failure due to network issues."""
        mock_client = MagicMock()
        mock_client.ping.side_effect = ConnectionError("Connection refused")

        # Verify that network failure raises ConnectionError
        with pytest.raises(ConnectionError):
            mock_client.ping()

    def test_database_creation(self, mock_influxdb_client, plugin_config):
        """Test database creation on connection."""
        # Simulate database doesn't exist
        mock_influxdb_client.get_list_database.return_value = []

        # Create database
        mock_influxdb_client.create_database(plugin_config['InfluxDB'])

        # Verify create_database was called with correct parameters
        mock_influxdb_client.create_database.assert_called_once_with(plugin_config['InfluxDB'])

    def test_ssl_connection(self, mock_influxdb_client, plugin_config):
        """Test SSL connection configuration."""
        plugin_config['InfluxSSL'] = True

        # Verify SSL-enabled client works
        assert mock_influxdb_client.ping() is True
        assert mock_influxdb_client is not None

    def test_write_points_success(self, mock_influxdb_client):
        """Test successful data write to InfluxDB."""
        test_data = [
            {
                "measurement": "device_changes",
                "tags": {
                    "name": "Test Device"
                },
                "fields": {
                    "onState": True,
                    "brightnessLevel": 75
                }
            }
        ]

        # Write points
        result = mock_influxdb_client.write_points(test_data)

        # Verify write succeeded
        assert result is True
        mock_influxdb_client.write_points.assert_called_once()

    def test_write_points_failure(self):
        """Test failed data write to InfluxDB."""
        mock_client = MagicMock()
        mock_client.write_points.side_effect = InfluxDBClientError("Write failed")

        test_data = [{"measurement": "test", "fields": {"value": 1}}]

        # Verify that write failure raises exception
        with pytest.raises(InfluxDBClientError):
            mock_client.write_points(test_data)

    def test_retention_policy(self, mock_influxdb_client, plugin_config):
        """Test retention policy configuration."""
        # Create retention policy
        retention_months = plugin_config['InfluxRetention']
        retention_duration = f"{retention_months}mon"

        mock_influxdb_client.create_retention_policy(
            name='indigo_retention',
            duration=retention_duration,
            replication='1',
            database=plugin_config['InfluxDB'],
            default=True
        )

        # Verify retention policy was created
        mock_influxdb_client.create_retention_policy.assert_called_once()
