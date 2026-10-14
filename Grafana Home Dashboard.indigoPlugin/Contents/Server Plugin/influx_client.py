#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""Small InfluxDB client: line-protocol encoding plus the few v1-API calls the
plugin makes (ping, DDL on InfluxDB 1.x, write).  Built on the `requests` that
ships with Indigo, so the plugin installs no packages of its own.

It replaces the archived influxdb-python client (influxdb==5.3.2, archived
2024-10).  The encoder reproduces that library's line_protocol.make_line byte
for byte - production InfluxDB servers already have typed columns, so any drift
would surface as type conflicts - with two deliberate differences:

  * NaN and +/-infinity field values are skipped.  5.3.2 wrote `nan` / `inf`,
    which both InfluxDB 1.x and 3 reject, losing the device's whole point.
  * A point left with no fields is skipped instead of encoded.  Both servers
    reject a field-less line, and InfluxDB 3 then rejects the entire batch.

5.3.2 escapes tag values with the same function as keys; the trailing-space
rule in its `_escape_tag_value` helper is never called by make_line, so it is
deliberately not reproduced here.  tests/test_line_protocol.py compares the two
encoders over a corpus of real device and variable points.
"""

import datetime
import math
import numbers
import re

import requests

DEFAULT_TIMEOUT = 5  # seconds, per HTTP request

_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)


################################################################################
# Line protocol
################################################################################

def _text(value):
	if isinstance(value, bytes):
		return value.decode('utf-8')
	if value is None:
		return ''
	return str(value)


def escape_key(value):
	"""Escape a measurement name, tag key, tag value or field key."""
	return (_text(value)
		.replace('\\', '\\\\')
		.replace(' ', '\\ ')
		.replace(',', '\\,')
		.replace('=', '\\=')
		.replace('\n', '\\n'))


def quote_string(value):
	"""A double-quoted string field value (also an InfluxQL identifier)."""
	return '"' + _text(value).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'


def encode_field_value(value):
	"""Encode one field value, or return None when the field must be skipped."""
	if value is None:
		return None
	if isinstance(value, bytes):
		value = value.decode('utf-8')
	if isinstance(value, str):
		return quote_string(value)
	if isinstance(value, int) and not isinstance(value, bool):
		return str(value) + 'i'
	if isinstance(value, bool):
		return str(value)

	try:
		number = float(value)
	except (TypeError, ValueError):
		encoded = str(value)
		return encoded if encoded != '' else None

	if math.isnan(number) or math.isinf(number):
		return None  # deliberate difference from 5.3.2, see module docstring
	return repr(number)


def to_nanoseconds(timestamp):
	"""Integer nanoseconds since the epoch.  A naive datetime counts as UTC; an
	integer is taken to be nanoseconds already."""
	if isinstance(timestamp, numbers.Integral):
		return int(timestamp)
	if isinstance(timestamp, datetime.datetime):
		if timestamp.tzinfo is None:
			timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
		delta = timestamp - _EPOCH
		return (delta.days * 86400 + delta.seconds) * 10 ** 9 + delta.microseconds * 10 ** 3
	raise ValueError(f"unsupported timestamp: {timestamp!r}")


def make_line(measurement, tags=None, fields=None, time=None):
	"""One line of line protocol, or None when the point has no usable fields."""
	line = escape_key(measurement)

	tag_list = []
	for tag_key in sorted((tags or {}).keys()):
		key = escape_key(tag_key)
		value = escape_key(tags[tag_key])
		if key != '' and value != '':
			tag_list.append(key + '=' + value)
	if tag_list:
		line += ',' + ','.join(tag_list)

	field_list = []
	for field_key in sorted((fields or {}).keys()):
		key = escape_key(field_key)
		value = encode_field_value(fields[field_key])
		if key != '' and value is not None:
			field_list.append(key + '=' + value)
	if not field_list:
		return None  # deliberate difference from 5.3.2, see module docstring
	line += ' ' + ','.join(field_list)

	if time is not None:
		line += ' ' + str(to_nanoseconds(time))

	return line


def encode_points(points):
	"""Encode point dicts ({measurement, tags, fields, time}).  Returns a list
	of (index into points, line) for the points that produced a line."""
	encoded = []
	for index, point in enumerate(points):
		line = make_line(point.get('measurement'), point.get('tags'), point.get('fields'), point.get('time'))
		if line is not None:
			encoded.append((index, line))
	return encoded


################################################################################
# Errors
################################################################################

class InfluxError(Exception):
	"""message is human readable; status_code is the HTTP status, or None when
	no response arrived."""

	def __init__(self, message, status_code=None, line_number=None):
		super().__init__(message)
		self.message = message
		self.status_code = status_code
		# InfluxDB 3 parse errors name the 1-based line that failed; write_points
		# maps it back to the index of the offending point
		self.line_number = line_number
		self.point_index = None

	def __str__(self):
		if self.status_code is None:
			return self.message
		return f"HTTP {self.status_code}: {self.message}"


class InfluxConnectionError(InfluxError):
	"""The server could not be reached, or did not answer in time."""


class InfluxHTTPError(InfluxError):
	"""The server answered with an unexpected HTTP status."""

	@property
	def is_auth_error(self):
		return self.status_code in (401, 403)


class InfluxQueryError(InfluxError):
	"""An InfluxQL statement failed (HTTP 200 carrying an error result)."""


def decode_error(response):
	"""(message, line_number) from an InfluxDB error response.

	InfluxDB 1.x:  {"error": "partial write: field type conflict: ..."}
	InfluxDB 3:    {"error": "line protocol parsing error",
	                "data": {"error_message": "...", "line_number": 2, ...}}
	               or plain text ("incoming write was empty")."""
	text = (response.text or '').strip()
	try:
		body = response.json()
	except ValueError:
		return (text[:1000] or f"HTTP {response.status_code}"), None

	if not isinstance(body, dict):
		return text[:1000], None

	message = str(body.get('error') or body.get('message') or text[:1000])
	line_number = None
	data = body.get('data')
	if isinstance(data, dict):
		detail = data.get('error_message')
		if detail:
			message = f"{message}: {detail}"
		if isinstance(data.get('line_number'), int):
			line_number = data['line_number']
	elif isinstance(data, list):
		details = [str(item.get('error_message')) for item in data if isinstance(item, dict) and item.get('error_message')]
		if details:
			message = f"{message}: {'; '.join(details)}"
		first = next((item for item in data if isinstance(item, dict) and isinstance(item.get('line_number'), int)), None)
		if first is not None:
			line_number = first['line_number']

	return message, line_number


################################################################################
# Retention durations (InfluxDB 1.x)
################################################################################

_DURATION_UNITS = {'w': 604800, 'd': 86400, 'h': 3600, 'm': 60, 's': 1}


def parse_duration_seconds(text):
	"""Seconds in an InfluxDB duration: '17280h0m0s' (SHOW RETENTION POLICIES),
	'720d', 'INF'.  0 means infinite, as InfluxDB reports it."""
	text = str(text).strip()
	if text.upper() == 'INF':
		return 0
	total = 0
	for amount, unit in re.findall(r'(\d+)([wdhms])(?!s)', text):
		total += int(amount) * _DURATION_UNITS[unit]
	return total


################################################################################
# Client
################################################################################

class InfluxClient:
	"""One connection's worth of settings over a requests.Session.  Calls raise
	InfluxConnectionError, InfluxHTTPError or InfluxQueryError."""

	def __init__(self, host, port, ssl=False, username='', password='', database='',
				 timeout=DEFAULT_TIMEOUT, user_agent=None):
		self.database = database
		self.timeout = timeout

		host = str(host).strip()
		if ':' in host and not host.startswith('['):
			host = '[' + host + ']'  # IPv6 literal
		self.base_url = f"{'https' if ssl else 'http'}://{host}:{int(port)}"

		self.session = requests.Session()
		self.session.verify = bool(ssl)
		self.session.headers['Accept'] = 'application/json'
		if user_agent:
			self.session.headers['User-Agent'] = user_agent
		if username or password:
			# InfluxDB 3's v1 API takes the token as the password
			self.session.auth = (username or '', password or '')

	def close(self):
		self.session.close()

	def _request(self, method, path, expected, params=None, data=None, headers=None):
		try:
			response = self.session.request(method, f"{self.base_url}/{path}", params=params, data=data,
											headers=headers, timeout=self.timeout)
		except requests.exceptions.RequestException as e:
			raise InfluxConnectionError(f"{type(e).__name__}: {e}") from e

		if response.status_code not in expected:
			message, line_number = decode_error(response)
			raise InfluxHTTPError(message, response.status_code, line_number)
		return response

	def ping(self):
		"""Reachability check.  InfluxDB 1.x answers 204 without checking
		credentials; InfluxDB 3 answers 200 and requires a valid token.
		Returns {'version', 'build'} as far as the server tells."""
		response = self._request('GET', 'ping', expected=(200, 204))
		info = {
			'version': response.headers.get('X-Influxdb-Version'),
			'build': response.headers.get('X-Influxdb-Build'),
		}
		if response.status_code == 200 and response.content:
			try:
				body = response.json()
				info['version'] = info['version'] or body.get('version')
				info['build'] = info['build'] or body.get('product_name')
			except ValueError:
				pass
		return info

	def query(self, statement, database=None):
		"""Run an InfluxQL statement (POST /query) and return its results list."""
		params = {'q': statement}
		if database:
			params['db'] = database
		response = self._request('POST', 'query', expected=(200,), params=params)
		try:
			results = response.json().get('results', [])
		except (ValueError, AttributeError):
			raise InfluxQueryError("unreadable /query response: " + (response.text or '')[:300], response.status_code)
		for result in results:
			if result.get('error'):
				raise InfluxQueryError(str(result['error']), response.status_code)
		return results

	def create_database(self, name):
		self.query('CREATE DATABASE ' + quote_string(name))

	def databases(self):
		"""Database names the user can see (SHOW DATABASES)."""
		names = []
		for result in self.query('SHOW DATABASES'):
			for series in result.get('series', []):
				names += [row[0] for row in series.get('values', [])]
		return names

	def retention_policies(self, database):
		"""[{'name', 'duration', 'shardGroupDuration', 'replicaN', 'default'}]"""
		results = self.query('SHOW RETENTION POLICIES ON ' + quote_string(database))
		policies = []
		for result in results:
			for series in result.get('series', []):
				columns = series.get('columns', [])
				for row in series.get('values', []):
					policies.append(dict(zip(columns, row)))
		return policies

	def create_retention_policy(self, name, database, duration, default=False):
		self.query(f"CREATE RETENTION POLICY {quote_string(name)} ON {quote_string(database)} "
				   f"DURATION {duration} REPLICATION 1" + (" DEFAULT" if default else ""))

	def alter_retention_policy(self, name, database, duration, default=False):
		self.query(f"ALTER RETENTION POLICY {quote_string(name)} ON {quote_string(database)} "
				   f"DURATION {duration}" + (" DEFAULT" if default else ""))

	def check_write_access(self):
		"""Prove the credentials may write to the database without writing a
		point: an empty write.  InfluxDB 1.x answers 204 (or 401/403/404);
		InfluxDB 3 checks the token first (401) and then refuses the empty body
		with a 400, which therefore means the token was accepted."""
		try:
			self._request('POST', 'write', expected=(200, 204), params={'db': self.database}, data=b'',
						  headers={'Content-Type': 'application/octet-stream'})
		except InfluxHTTPError as e:
			if e.status_code == 400 and 'empty' in e.message.lower():
				return
			raise

	def write_points(self, points):
		"""POST /write one batch.  Returns the number of lines sent.  On a parse
		error InfluxDB 3 names the failing line; the raised error's point_index
		then holds the index into points of the offending point."""
		encoded = encode_points(points)
		if not encoded:
			return 0

		body = ('\n'.join(line for _, line in encoded) + '\n').encode('utf-8')
		try:
			self._request('POST', 'write', expected=(200, 204), params={'db': self.database}, data=body,
						  headers={'Content-Type': 'application/octet-stream'})
		except InfluxError as e:
			if e.line_number is not None and 1 <= e.line_number <= len(encoded):
				e.point_index = encoded[e.line_number - 1][0]
			raise
		return len(encoded)
