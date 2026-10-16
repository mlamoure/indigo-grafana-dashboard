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


__all__ = ['FakeInfluxClient', 'FakeHistoryClient', 'connected_plugin', 'http_error', 'InfluxConnectionError', 'InfluxHTTPError',
           'InfluxQueryError', 'V1_CONFLICT', 'V3_CONFLICT', 'V3_TAG_AND_FIELD']


# --- history reads (mcp_api/history.py) ------------------------------------------

import re as _re

_STATEMENT = _re.compile(
    r'^SELECT (?P<select>.+?) FROM (?P<source>(?:"[^"]+"\.)?"[^"]+")(?: WHERE (?P<where>.+?))?'
    r'(?: GROUP BY time\((?P<interval>\d+)s, (?P<offset>\d+)s\) fill\(none\))?'
    r'(?P<desc> ORDER BY time DESC)?(?: LIMIT (?P<limit>\d+))?$')
_TAG = _re.compile(r'^"(?P<key>[^"]+)"::tag = \'(?P<value>(?:[^\'\\]|\\.)*)\'$')
_TAG_REGEX = _re.compile(r'^"(?P<key>[^"]+)"::tag =~ /\^(?P<body>.*)\$/$')
_TIME = _re.compile(r'^time (?P<op>>=|<=) (?P<t>\d+)s$')
_NOT_EQUAL = _re.compile(r'^"(?P<field>[^"]+)" != (?P<literal>.+)$')
_AGGREGATE = _re.compile(r'^(?P<fn>min|max|mean|count|first|last)\("(?P<field>[^"]+)"\)$')


def _unescape(text):
    return _re.sub(r'\\(.)', r'\1', text)


def _parse_literal(text):
    if text in ('true', 'false'):
        return text == 'true'
    if text.startswith("'"):
        return _unescape(text[1:-1])
    return float(text)


class FakeHistoryClient:
    """Answers the InfluxQL statements history.HistoryReader builds - and only
    those (anything else raises, so a drifting statement fails the test) - from
    points held in memory.  tests/live runs the same statements against real
    InfluxDB 1.8 and 3 servers."""

    def __init__(self, policies=None):
        self.points = []           # (policy, measurement, tags, time, fields)
        self.policies = policies   # InfluxDB 1.x retention policy names, or None
        self.statements = []
        self.threads = []
        self.query_error = None
        self.timeout = None
        self.closed = False

    def add(self, measurement, tags, t, policy=None, **fields):
        if measurement != 'variable_changes':
            fields.setdefault('id', 1.0)  # the plugin puts the device id on every device point
        self.points.append((policy, measurement, dict(tags), int(t), fields))

    def retention_policies(self, database):
        return [{'name': name, 'default': index == 0} for index, name in enumerate(self.policies or [])]

    def close(self):
        self.closed = True

    def query(self, statement, database=None, epoch=None):
        import threading
        self.statements.append(statement)
        self.threads.append(threading.current_thread().name)
        if self.query_error:
            raise self.query_error
        assert epoch == 's', statement
        match = _STATEMENT.match(statement)
        assert match, f"unexpected statement: {statement}"

        source = [part.strip('"') for part in match['source'].split('"."')]
        policy, measurement = (source[0], source[1]) if len(source) == 2 else (None, source[0])
        rows = [p for p in self.points if p[1] == measurement and (p[0] == policy or (policy is None and self.policies is None))]

        for clause in (match['where'] or '').split(' AND '):
            if not clause:
                continue
            if m := _TAG.match(clause):
                assert '"' not in m['value'], "InfluxDB 3 refuses a double quote in a string literal"
                rows = [p for p in rows if p[2].get(m['key']) == _unescape(m['value'])]
            elif m := _TAG_REGEX.match(clause):
                rows = [p for p in rows if p[2].get(m['key']) == _unescape(m['body'])]
            elif m := _TIME.match(clause):
                t = int(m['t'])
                rows = [p for p in rows if (p[3] >= t if m['op'] == '>=' else p[3] <= t)]
            elif m := _NOT_EQUAL.match(clause):
                literal = _parse_literal(m['literal'])
                rows = [p for p in rows if m['field'] in p[4] and p[4][m['field']] != literal]
            else:
                raise AssertionError(f"unexpected clause {clause!r} in {statement}")
        rows.sort(key=lambda p: p[3], reverse=bool(match['desc']))

        selects = [part.strip() for part in match['select'].split(', ')]
        aggregates = [_AGGREGATE.match(part) for part in selects]
        if not any(aggregates):
            assert len(selects) == 1 and selects[0].startswith('"'), statement
            field = selects[0].strip('"')
            rows = [p for p in rows if p[4].get(field) is not None]
            if match['limit']:
                rows = rows[:int(match['limit'])]
            values = [[p[3], p[4][field]] for p in rows]
            return self._result(measurement, ['time', field], values)

        assert all(aggregates), statement
        groups = {}
        if match['interval']:
            interval, offset = int(match['interval']), int(match['offset'])
            for p in rows:
                groups.setdefault((p[3] - offset) // interval * interval + offset, []).append(p)
        else:
            groups[0] = rows
        values = []
        for start, members in sorted(groups.items()):
            row = [start]
            for m in aggregates:
                points = [(p[3], p[4][m['field']]) for p in members if p[4].get(m['field']) is not None]
                row.append(self._aggregate(m['fn'], points))
                if m['fn'] in ('first', 'last') and len(aggregates) == 1 and points and not match['interval']:
                    row[0] = (points[0] if m['fn'] == 'first' else points[-1])[0]  # a selector returns its point's time
            if match['interval'] and not any(v for v in row[1:]):
                continue  # fill(none): no empty buckets
            values.append(row)
        if not match['interval'] and not rows:
            values = []
        return self._result(measurement, ['time'] + [m['fn'] for m in aggregates], values)

    @staticmethod
    def _aggregate(fn, points):
        values = [v for _, v in points]
        if fn == 'count':
            return len(values)
        if not values:
            return None
        if fn == 'first':
            return values[0]
        if fn == 'last':
            return values[-1]
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
            raise InfluxQueryError(f"unsupported {fn} iterator type", 200)
        if fn == 'min':
            return min(values)
        if fn == 'max':
            return max(values)
        return sum(values) / len(values)

    @staticmethod
    def _result(measurement, columns, values):
        if not values:
            return [{'statement_id': 0}]
        return [{'statement_id': 0, 'series': [{'name': measurement, 'columns': columns, 'values': values}]}]
