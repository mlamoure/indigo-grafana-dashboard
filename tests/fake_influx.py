"""A scriptable stand-in for influx_client.InfluxClient, for plugin-level tests."""

import copy

from influx_client import InfluxConnectionError, InfluxHTTPError, InfluxQueryError

# messages as decoded from real server responses (see test_influx_client.py)
V1_CONFLICT = ('partial write: field type conflict: input field "sensorValue" on measurement "device_changes" '
               'is type float, already exists as type string dropped=1')
V3_CONFLICT = ("line protocol parsing error: invalid column type for column 'sensorValue', expected "
               "iox::column_type::field::string, got iox::column_type::field::float")
V3_TAG_AND_FIELD = "line protocol parsing error: invalid line protocol - 'name' is used as both a tag and a field"


def http_error(status, message, point_index=None, line_number=None):
    err = InfluxHTTPError(message, status, line_number)
    err.point_index = point_index
    return err


class FakeInfluxClient:
    def __init__(self, version='1.8.10', build='OSS'):
        self.info = {'version': version, 'build': build}
        self.ping_error = None
        self.create_database_error = None
        self.check_write_error = None
        self.retention_error = None
        self.policies = [{'name': 'autogen', 'duration': '0s', 'default': True}]
        self.existing_databases = []  # SHOW DATABASES before the plugin's CREATE DATABASE
        self.write_errors = []     # one entry per write call: an exception, or None for success
        self.writes = []           # deep copies of every batch sent (successful or not)
        self.successful = []       # deep copies of the batches that were accepted
        self.ddl = []
        self.closed = False

    def ping(self):
        if self.ping_error:
            raise self.ping_error
        return dict(self.info)

    def create_database(self, name):
        self.ddl.append(('CREATE DATABASE', name))
        if self.create_database_error:
            raise self.create_database_error

    def databases(self):
        return list(self.existing_databases)

    def check_write_access(self):
        if self.check_write_error:
            raise self.check_write_error

    def retention_policies(self, database):
        if self.retention_error:
            raise self.retention_error
        return [dict(p) for p in self.policies]

    def create_retention_policy(self, name, database, duration, default=False):
        self.ddl.append(('CREATE RETENTION POLICY', name, duration, default))
        if default:
            for policy in self.policies:
                policy['default'] = False
        self.policies.append({'name': name, 'duration': duration, 'default': default})

    def alter_retention_policy(self, name, database, duration, default=False):
        self.ddl.append(('ALTER RETENTION POLICY', name, duration, default))

    def write_points(self, points):
        batch = copy.deepcopy(points)
        self.writes.append(batch)
        if self.write_errors:
            err = self.write_errors.pop(0)
            if err is not None:
                raise err
        self.successful.append(batch)
        return len(points)

    def close(self):
        self.closed = True

    @property
    def written_points(self):
        """Every point of the write calls that were accepted."""
        return [point for batch in self.successful for point in batch]


def connected_plugin(make_plugin, client=None, **prefs):
    """A started plugin, connected to a FakeInfluxClient through the real connect()."""
    plugin = make_plugin(**prefs)
    client = client or FakeInfluxClient()
    plugin.newClient = lambda settings: client
    plugin.connect()
    assert plugin.connected, plugin.lastConnectError
    return plugin, client


__all__ = ['FakeInfluxClient', 'connected_plugin', 'http_error', 'InfluxConnectionError', 'InfluxHTTPError',
           'InfluxQueryError', 'V1_CONFLICT', 'V3_CONFLICT', 'V3_TAG_AND_FIELD']
