"""
InfluxClient against canned HTTP responses.  The bodies are the ones real
servers returned (influxdb:1.8 = 1.8.10, influxdb:3-core = 3.12.0) when probed
on 2026-10-14; tests/live/ runs the same calls against real containers.
"""

import json
from urllib.parse import parse_qs, urlsplit

import pytest
import requests
from requests.adapters import BaseAdapter

from influx_client import (InfluxClient, InfluxConnectionError, InfluxHTTPError, InfluxQueryError,
                           decode_error, parse_duration_seconds)

# --- real response bodies --------------------------------------------------------
V1_TYPE_CONFLICT = ('{"error":"partial write: field type conflict: input field \\"f\\" on measurement \\"m\\" '
                    'is type float, already exists as type integer dropped=1"}\n')
V1_AUTH = '{"error":"authorization failed"}\n'
V1_NOT_ADMIN = ('{"error":"error authorizing query: indigo not authorized to execute statement \'CREATE DATABASE '
                'indigo\', requires admin privilege"}\n')
V1_NO_DB = '{"error":"database not found: \\"nope\\""}\n'
V1_RP_EXISTS = '{"results":[{"statement_id":0,"error":"retention policy already exists"}]}\n'
V1_SHOW_RP = ('{"results":[{"statement_id":0,"series":[{"columns":["name","duration","shardGroupDuration",'
              '"replicaN","default"],"values":[["autogen","0s","168h0m0s",1,false],["indigo_policy","17280h0m0s",'
              '"168h0m0s",1,true]]}]}]}\n')
V3_TYPE_CONFLICT = ('{"error":"line protocol parsing error","data":{"error_message":"invalid column type for column '
                    '\'f\', expected iox::column_type::field::integer, got iox::column_type::field::float",'
                    '"line_number":2,"original_line":"m2 f=2.5 2000000000"}}')
V3_AUTH = '{"error": "the request was not authenticated"}'
V3_PING = '{"product_name":"InfluxDB 3 Core","version":"3.12.0","revision":"3ba97c65f1"}'
V3_DDL = '{"results":[{"statement_id":0,"error":"datafusion error: This feature is not implemented: CREATE DATABASE"}]}'


class FakeAdapter(BaseAdapter):
    """Answers requests from a queue of (status, body, headers); records them."""

    def __init__(self, responses):
        super().__init__()
        self.responses = list(responses)
        self.requests = []

    def send(self, request, **kwargs):
        self.requests.append((request, kwargs))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        status, body, headers = (item + ({},))[:3] if len(item) == 2 else item
        response = requests.Response()
        response.status_code = status
        response._content = body.encode('utf-8') if isinstance(body, str) else body
        response.headers.update(headers)
        response.request = request
        response.url = request.url
        return response

    def close(self):
        pass


def client_with(responses, **kwargs):
    defaults = dict(host='influx.example.com', port=8086, ssl=False, username='indigo', password='pw', database='indigo')
    defaults.update(kwargs)
    client = InfluxClient(**defaults)
    adapter = FakeAdapter(responses)
    client.session.mount('http://', adapter)
    client.session.mount('https://', adapter)
    return client, adapter


def test_write_sends_line_protocol_with_basic_auth():
    client, adapter = client_with([(204, '')])
    count = client.write_points([{'measurement': 'm', 'tags': {'name': 'a b'}, 'fields': {'v': 1.5}, 'time': 10}])
    assert count == 1
    request, kwargs = adapter.requests[0]
    assert request.method == 'POST'
    assert request.url == 'http://influx.example.com:8086/write?db=indigo'
    assert request.body == b'm,name=a\\ b v=1.5 10\n'
    assert request.headers['Content-Type'] == 'application/octet-stream'
    assert request.headers['Authorization'].startswith('Basic ')
    assert 'precision' not in request.url
    assert kwargs['timeout'] == 5


def test_ssl_selects_https_and_verifies():
    client, adapter = client_with([(204, '')], ssl=True, port=443)
    client.write_points([{'measurement': 'm', 'fields': {'v': 1}}])
    request, kwargs = adapter.requests[0]
    assert request.url.startswith('https://influx.example.com:443/')
    assert kwargs['verify'] is True


def test_nothing_to_write_makes_no_request():
    client, adapter = client_with([])
    assert client.write_points([{'measurement': 'm', 'fields': {'v': float('nan')}}]) == 0
    assert adapter.requests == []


def test_v1_type_conflict_is_decoded():
    client, _ = client_with([(400, V1_TYPE_CONFLICT)])
    with pytest.raises(InfluxHTTPError) as raised:
        client.write_points([{'measurement': 'm', 'fields': {'f': 1.5}}])
    err = raised.value
    assert err.status_code == 400
    # decoded: real quotes, not the JSON-escaped \" the old regex choked on
    assert 'input field "f" on measurement "m" is type float, already exists as type integer' in err.message


def test_v3_type_conflict_names_the_offending_point():
    client, _ = client_with([(400, V3_TYPE_CONFLICT)])
    points = [{'measurement': 'm2', 'fields': {'v': float('nan')}},  # skipped: no line
              {'measurement': 'm2', 'fields': {'f': 2}},
              {'measurement': 'm2', 'fields': {'f': 2.5}}]
    with pytest.raises(InfluxHTTPError) as raised:
        client.write_points(points)
    err = raised.value
    assert err.line_number == 2
    assert err.point_index == 2  # line 2 is the third point: the first produced no line
    assert "invalid column type for column 'f', expected iox::column_type::field::integer" in err.message


@pytest.mark.parametrize("status,body", [(401, V1_AUTH), (401, V3_AUTH), (403, V1_NOT_ADMIN)])
def test_auth_errors(status, body):
    client, _ = client_with([(status, body)])
    with pytest.raises(InfluxHTTPError) as raised:
        client.write_points([{'measurement': 'm', 'fields': {'v': 1}}])
    assert raised.value.is_auth_error


def test_missing_database_is_404():
    client, _ = client_with([(404, V1_NO_DB)])
    with pytest.raises(InfluxHTTPError) as raised:
        client.write_points([{'measurement': 'm', 'fields': {'v': 1}}])
    assert raised.value.status_code == 404
    assert not raised.value.is_auth_error
    assert raised.value.message == 'database not found: "nope"'


def test_network_errors_become_connection_errors():
    client, _ = client_with([requests.exceptions.ConnectTimeout("timed out")])
    with pytest.raises(InfluxConnectionError) as raised:
        client.ping()
    assert raised.value.status_code is None


def test_ping_reads_versions_from_both_servers():
    client, _ = client_with([(204, '', {'X-Influxdb-Version': '1.8.10', 'X-Influxdb-Build': 'OSS'})])
    assert client.ping() == {'version': '1.8.10', 'build': 'OSS'}
    client, _ = client_with([(200, V3_PING, {'Content-Type': 'application/json'})])
    assert client.ping() == {'version': '3.12.0', 'build': 'InfluxDB 3 Core'}


def test_query_statement_errors_raise():
    client, _ = client_with([(200, V1_RP_EXISTS)])
    with pytest.raises(InfluxQueryError, match='retention policy already exists'):
        client.create_retention_policy('indigo_policy', 'indigo', '720d', default=True)
    client, _ = client_with([(200, V3_DDL)])
    with pytest.raises(InfluxQueryError, match='not implemented'):
        client.create_database('indigo')


def test_ddl_statements_are_quoted():
    client, adapter = client_with([(200, '{"results":[{"statement_id":0}]}')] * 3)
    client.create_database('my "db"')
    client.create_retention_policy('indigo_policy', 'indigo', '720d', default=True)
    client.alter_retention_policy('indigo_policy', 'indigo', 'INF', default=True)
    sent = [parse_qs(urlsplit(r.url).query)['q'][0] for r, _ in adapter.requests]
    assert sent == ['CREATE DATABASE "my \\"db\\""',
                    'CREATE RETENTION POLICY "indigo_policy" ON "indigo" DURATION 720d REPLICATION 1 DEFAULT',
                    'ALTER RETENTION POLICY "indigo_policy" ON "indigo" DURATION INF DEFAULT']
    assert all(r.method == 'POST' for r, _ in adapter.requests)


def test_retention_policies_are_parsed():
    client, _ = client_with([(200, V1_SHOW_RP)])
    policies = client.retention_policies('indigo')
    assert policies[1] == {'name': 'indigo_policy', 'duration': '17280h0m0s', 'shardGroupDuration': '168h0m0s',
                           'replicaN': 1, 'default': True}


def test_check_write_access_accepts_v3_empty_write_refusal():
    client, _ = client_with([(400, 'incoming write was empty')])
    client.check_write_access()  # token accepted, nothing written
    client, _ = client_with([(204, '')])
    client.check_write_access()
    client, _ = client_with([(403, '{"error":"\\"indigo\\" user is not authorized to write to database \\"x\\""}')])
    with pytest.raises(InfluxHTTPError):
        client.check_write_access()


def test_decode_error_handles_plain_text_and_lists():
    response = requests.Response()
    response.status_code = 400
    response._content = b'no db destination provided'
    assert decode_error(response) == ('no db destination provided', None)
    response._content = json.dumps({'error': 'parse', 'data': [{'error_message': 'a', 'line_number': 3},
                                                             {'error_message': 'b', 'line_number': 5}]}).encode()
    assert decode_error(response) == ('parse: a; b', 3)


@pytest.mark.parametrize("text,seconds", [('17280h0m0s', 17280 * 3600), ('0s', 0), ('INF', 0), ('720d', 720 * 86400),
                                          ('168h0m0s', 168 * 3600), ('1w2d', 9 * 86400)])
def test_parse_duration(text, seconds):
    assert parse_duration_seconds(text) == seconds


def test_ipv6_host_is_bracketed():
    client = InfluxClient('fd00::1', 8086)
    assert client.base_url == 'http://[fd00::1]:8086'
