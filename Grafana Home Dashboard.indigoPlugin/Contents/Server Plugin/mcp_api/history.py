"""
influxlog_query_history: what devices and variables did over a time window, read
back from the data this plugin logged to InfluxDB.

Read-only.  The tool opens its own client with the plugin's connection settings
(never the writer's session) and runs on a worker thread (AsyncResult), because
Indigo's callback thread must never wait on the network.  The same InfluxQL runs
on InfluxDB 1.x and on InfluxDB 3's v1 API; the password or token never appears
in any output.

Layers:
  * parse_window          - the time window (last N hours/days, or start/end)
  * HistoryReader         - every InfluxQL statement, in one place (tests/live
                            runs them against both servers)
  * pure analysis         - summaries, changes, time in state, gaps, buckets
  * HistoryQuery          - picks the measurement and the states, explains a
                            series with no data, and builds the reply
"""

import datetime
import math
import time

from influx_client import InfluxConnectionError, InfluxError, InfluxHTTPError, quote_string

from .errors import ToolError
from .filter_log import read_records
from .resolvers import device_ref, resolve_device, resolve_variable, suggestions
from .tool_dispatcher import AsyncResult

MAX_DEVICES = 5
MAX_VARIABLES = 5
MAX_STATES = 8           # states named per call (they apply to every device given)
MAX_SERIES = 16          # device x state pairs plus variables
DEFAULT_STATE_COUNT = 6  # states picked per device when the caller names none
DEFAULT_WINDOW = datetime.timedelta(hours=24)
MIN_WINDOW = datetime.timedelta(minutes=5)
MAX_WINDOW = datetime.timedelta(days=366)
RAW_POINT_CAP = 50000    # points read per series; past it the summary comes from InfluxDB aggregates
DEFAULT_MAX_CHANGES = 50
MAX_CHANGES = 500
MAX_BUCKETS = 400
AUTO_BUCKETS = 200
BUCKET_STEPS = (300, 900, 1800, 3600, 7200, 10800, 21600, 43200, 86400, 172800, 604800)
NAMED_BUCKETS = {"15m": 900, "hour": 3600, "day": 86400}
MAX_GAPS = 20
TREND_THRESHOLD = 0.1    # a smaller first-to-last change reads as steady (sensor noise floor)
FLAT_MIN_POINTS = 3
HTTP_TIMEOUT = 20        # seconds per InfluxDB request
TIME_BUDGET = 50         # seconds for the whole call; the manifest allows 60

# Static description and housekeeping keys: logged by some include lists, never
# worth a history.  Left out of the default states (they can still be named).
METADATA_KEYS = frozenset((
	'model', 'subModel', 'deviceTypeId', 'address', 'description', 'protocol', 'pluginId', 'displayStateId',
	'displayStateImageSel', 'displayStateValRaw', 'displayStateValUi', 'folderId', 'configured', 'enabled',
	'remoteDisplay', 'errorState', 'buttonGroupCount', 'version', 'ownerProps', 'globalProps', 'pluginProps',
	'sharedProps', 'supportsAllOff', 'supportsAllLightsOnOff', 'supportsStatusRequest',
))
PREFERRED_KEYS = ('sensorValue', 'onState', 'brightness', 'energyCurLevel', 'energyAccumTotal', 'batteryLevel',
				  'heatSetpoint', 'coolSetpoint', 'state.hvac_state', 'state.temperatureInput1',
				  'state.humidityInput1', 'state.onOffState')


################################################################################
# Small helpers
################################################################################

def _local(epoch_seconds):
	return datetime.datetime.fromtimestamp(epoch_seconds, datetime.timezone.utc).astimezone()


def iso_time(epoch_seconds):
	return _local(epoch_seconds).isoformat(timespec="seconds")


def _iso_datetime(value):
	if isinstance(value, datetime.datetime):
		if value.tzinfo is None:
			value = value.astimezone()
		return value.isoformat(timespec="seconds")
	return None if value is None else str(value)


def format_duration(seconds):
	"""'2d 3h', '6h 12m', '45m', '30s'."""
	seconds = int(round(seconds))
	days, rest = divmod(seconds, 86400)
	hours, rest = divmod(rest, 3600)
	minutes, secs = divmod(rest, 60)
	if days:
		return f"{days}d {hours}h" if hours else f"{days}d"
	if hours:
		return f"{hours}h {minutes}m" if minutes else f"{hours}h"
	if minutes:
		return f"{minutes}m"
	return f"{secs}s"


def _number(value):
	return isinstance(value, (int, float)) and not isinstance(value, bool)


def _round(value):
	if not _number(value) or not math.isfinite(value):
		return value
	return round(value, 3)


def _literal(value):
	"""An InfluxQL literal for a field comparison."""
	if isinstance(value, bool):
		return 'true' if value else 'false'
	if _number(value):
		return repr(float(value))
	return "'" + str(value).replace('\\', '\\\\').replace("'", "\\'") + "'"


def _regex(value):
	"""value as an InfluxQL regex body matching exactly that text."""
	return ''.join('\\' + c if c in '\\.^$*+?()[]{}|/' else c for c in value)


def classify(values):
	"""'numeric', 'boolean' or 'text' for a list of non-None values."""
	if values and all(isinstance(v, bool) for v in values):
		return 'boolean'
	if values and all(_number(v) for v in values):
		return 'numeric'
	return 'text'


################################################################################
# Window
################################################################################

class Window:
	def __init__(self, start, end):
		self.start = start
		self.end = end
		self.start_s = int(math.floor(start.timestamp()))
		self.end_s = int(math.floor(end.timestamp()))

	@property
	def seconds(self):
		return self.end_s - self.start_s

	def describe(self):
		return {"start": iso_time(self.start_s), "end": iso_time(self.end_s), "hours": round(self.seconds / 3600, 2)}


def _parse_time(value, name):
	if value is None:
		return None
	if not isinstance(value, str) or not value.strip():
		raise ToolError("validation", f"{name} must be an ISO 8601 date or time, e.g. 2026-10-15T02:00 or 2026-10-15")
	text = value.strip()
	try:
		parsed = datetime.datetime.fromisoformat(text)
	except ValueError:
		try:
			parsed = datetime.datetime.combine(datetime.date.fromisoformat(text), datetime.time())
		except ValueError:
			raise ToolError("validation", f"{name} {value!r} is not an ISO 8601 date or time "
										  f"(e.g. 2026-10-15T02:00, 2026-10-15T02:00-04:00 or 2026-10-15)") from None
	if parsed.tzinfo is None:
		parsed = parsed.astimezone()  # a time without an offset is the Indigo server's local time
	return parsed


def _span(hours, days):
	if hours is not None and days is not None:
		raise ToolError("validation", "give hours or days, not both")
	if hours is not None:
		if not _number(hours) or not 0 < hours <= 8784:
			raise ToolError("validation", "hours must be a number greater than 0 and at most 8784 (366 days)")
		return datetime.timedelta(hours=hours)
	if days is not None:
		if not _number(days) or not 0 < days <= 366:
			raise ToolError("validation", "days must be a number greater than 0 and at most 366")
		return datetime.timedelta(days=days)
	return None


def parse_window(hours=None, days=None, start=None, end=None, now=None):
	"""Last `hours`/`days` (default 24 hours) up to now, or an explicit start
	and/or end; with only one of them, hours/days measure from it."""
	now = now or datetime.datetime.now().astimezone()
	span = _span(hours, days)
	start_at = _parse_time(start, "start")
	end_at = _parse_time(end, "end")

	if start_at is not None and end_at is not None:
		if span is not None:
			raise ToolError("validation", "give start and end, or one of them with hours/days - not all three")
	elif start_at is not None:
		end_at = min(start_at + span, now) if span is not None else now
	elif end_at is not None:
		start_at = end_at - (span or DEFAULT_WINDOW)
	else:
		end_at = now
		start_at = now - (span or DEFAULT_WINDOW)

	end_at = min(end_at, now)
	if start_at >= end_at:
		raise ToolError("validation", "the window must start before it ends, and before now")
	if end_at - start_at < MIN_WINDOW:
		raise ToolError("validation", "the window must be at least 5 minutes long")
	if end_at - start_at > MAX_WINDOW:
		raise ToolError("validation", "the window can be at most 366 days long")
	return Window(start_at, end_at)


def bucket_interval(window_seconds, bucket):
	"""(interval seconds, note or None) for bucket 'auto', '15m', 'hour' or 'day'."""
	if bucket == "auto":
		for step in BUCKET_STEPS:
			if window_seconds / step <= AUTO_BUCKETS:
				return step, None
		return BUCKET_STEPS[-1], None
	step = NAMED_BUCKETS[bucket]
	if window_seconds / step <= MAX_BUCKETS:
		return step, None
	wider = next((s for s in BUCKET_STEPS if s > step and window_seconds / s <= MAX_BUCKETS), BUCKET_STEPS[-1])
	return wider, f"{bucket} buckets would be more than {MAX_BUCKETS}; using {format_duration(wider)} buckets"


def bucket_offset(interval, at):
	"""GROUP BY time(interval, offset) so that hour and day buckets start on the
	Indigo server's local hour / midnight (InfluxDB aligns buckets to UTC)."""
	utc_offset = int(_local(at).utcoffset().total_seconds())
	return (-utc_offset) % interval


def bucket_start(t, interval, offset):
	return (t - offset) // interval * interval + offset


################################################################################
# Pure analysis over (epoch seconds, value) points, oldest first
################################################################################

def change_points(points, before=None):
	"""The points where the value differs from the one in effect before it.
	`before` is the last (time, value) logged before the window, if any."""
	changes = []
	previous = before[1] if before is not None else (points[0][1] if points else None)
	for t, value in points:
		if value != previous:
			changes.append((t, value))
		previous = value
	return changes


def time_in_state(points, before, start_s, end_s):
	"""({value: seconds}, unknown seconds): how long each value held in the window.
	Without a value logged before the window, the stretch up to the first point
	is unknown."""
	held = {}
	current = before[1] if before is not None else None
	cursor = start_s
	unknown = 0
	for t, value in points:
		t = max(t, start_s)
		if current is None:
			unknown += t - cursor
		else:
			held[current] = held.get(current, 0) + (t - cursor)
		cursor = t
		current = value
	if current is None:
		unknown += end_s - cursor
	else:
		held[current] = held.get(current, 0) + max(0, end_s - cursor)
	return held, unknown


def bucketed_time_in_state(points, before, start_s, end_s, interval, offset):
	"""[(bucket start, {value: seconds})] - time in each value per bucket."""
	segments = []
	current = before[1] if before is not None else None
	cursor = start_s
	for t, value in points:
		t = max(t, start_s)
		if current is not None and t > cursor:
			segments.append((cursor, t, current))
		cursor = t
		current = value
	if current is not None and end_s > cursor:
		segments.append((cursor, end_s, current))

	buckets = {}
	for seg_start, seg_end, value in segments:
		t = seg_start
		while t < seg_end:
			bucket = bucket_start(t, interval, offset)
			stop = min(seg_end, bucket + interval)
			slot = buckets.setdefault(bucket, {})
			slot[value] = slot.get(value, 0) + (stop - t)
			t = stop
	return sorted(buckets.items())


def time_weighted_mean(points, end_s):
	"""Mean of the value over time (each value holds until the next point, the
	last until end_s): a burst of changes doesn't outweigh hours of heartbeats."""
	total = weight = 0.0
	for (t, value), (next_t, _) in zip(points, points[1:] + [(max(end_s, points[-1][0]), None)]):
		total += value * (next_t - t)
		weight += next_t - t
	if not weight:
		return sum(v for _, v in points) / len(points)
	return total / weight


def numeric_summary(points, end_s):
	first_t, first = points[0]
	last_t, last = points[-1]
	low = min(points, key=lambda p: p[1])
	high = max(points, key=lambda p: p[1])
	change = last - first
	if abs(change) < TREND_THRESHOLD:
		trend = "steady"
	elif change > 0:
		trend = "rising"
	else:
		trend = "falling"
	return {
		"current": last, "current_at": iso_time(last_t), "first": first, "first_at": iso_time(first_t),
		"min": low[1], "min_at": iso_time(low[0]), "max": high[1], "max_at": iso_time(high[0]),
		"mean": _round(time_weighted_mean(points, end_s)), "change": _round(change), "trend": trend,
	}


def find_gaps(timestamps, start_s, end_s, threshold):
	"""[(from, to)]: stretches longer than threshold seconds without a point."""
	gaps = []
	previous = start_s
	for t in timestamps:
		if t - previous > threshold:
			gaps.append((previous, t))
		previous = max(previous, t)
	if end_s - previous > threshold:
		gaps.append((previous, end_s))
	return gaps


def gaps_from_buckets(present, start_s, end_s, interval, offset, min_buckets=2):
	"""Gaps as runs of at least min_buckets empty buckets, for windows with too
	many points to read.  With buckets half the gap threshold long, a run of two
	is a silence of at least the threshold, and every silence of 1.5 thresholds
	or more is found."""
	gaps = []
	bucket = bucket_start(start_s, interval, offset)
	run, length = None, 0
	while bucket < end_s:
		if bucket in present:
			if run is not None and length >= min_buckets:
				gaps.append((run, bucket))
			run, length = None, 0
		else:
			if run is None:
				run = max(bucket, start_s)
			length += 1
		bucket += interval
	if run is not None and length >= min_buckets:
		gaps.append((run, end_s))
	return gaps


def describe_gaps(gaps, threshold):
	total = sum(b - a for a, b in gaps)
	listed = sorted(gaps, key=lambda g: g[0] - g[1])[:MAX_GAPS]  # the longest first
	return {
		"threshold": format_duration(threshold),
		"count": len(gaps),
		"total": format_duration(total),
		"longest_first": [{"from": iso_time(a), "to": iso_time(b), "duration": format_duration(b - a)}
						  for a, b in listed],
	}


################################################################################
# InfluxQL
################################################################################

class HistoryReader:
	"""Every statement the tool runs.  On InfluxDB 1.x the data can sit in more
	than one retention policy (data from before the plugin made `indigo_policy`
	the default stays in `autogen`), so each read covers every policy and the
	results are merged; InfluxDB 3 has none."""

	def __init__(self, client, database, version):
		self.client = client
		self.database = database
		self.v1 = str(version) == '1'
		self._sources = None
		self.notes = []
		self.queries = 0

	def sources(self):
		if self._sources is None:
			self._sources = [None]
			if self.v1:
				try:
					names = [p['name'] for p in self.client.retention_policies(self.database)]
					if names:
						self._sources = names
				except InfluxError as e:
					if isinstance(e, InfluxHTTPError) and e.is_auth_error:
						raise
					self.notes.append(f"could not list the retention policies ({e}); read the default policy only")
		return self._sources

	def _from(self, measurement, policy):
		if policy is None:
			return quote_string(measurement)
		return quote_string(policy) + '.' + quote_string(measurement)

	def _tag_match(self, tag_key, tag_value):
		value = str(tag_value)
		if self.v1:
			value = value.replace('\\', '\\\\')  # 1.x keeps the plugin's escaped `\\` as two backslashes
		key = f"{quote_string(tag_key)}::tag"
		if '"' in value:
			# InfluxDB 3 (3.10-3.12) refuses a double quote inside a string literal
			# ("invalid escape sequence"); an anchored regex matches the same name
			# on both servers
			return f"{key} =~ /^{_regex(value)}$/"
		return f"{key} = {_literal(value)}"

	def _where(self, tag_key, tag_value, start_s=None, end_s=None, extra=None):
		clauses = [self._tag_match(tag_key, tag_value)]
		if start_s is not None:
			clauses.append(f"time >= {int(start_s)}s")
		if end_s is not None:
			clauses.append(f"time <= {int(end_s)}s")
		if extra:
			clauses.append(extra)
		return " WHERE " + " AND ".join(clauses)

	def _rows(self, statement):
		self.queries += 1
		rows = []
		for result in self.client.query(statement, database=self.database, epoch='s'):
			for series in result.get('series', []) or []:
				columns = series.get('columns', [])
				for values in series.get('values', []) or []:
					rows.append(dict(zip(columns, values)))
		return rows

	def points(self, measurement, tag_key, tag_value, field, start_s, end_s, limit=None):
		"""([(t, value)], truncated): the field's points in the window, oldest first."""
		limit = RAW_POINT_CAP if limit is None else limit
		points, truncated = [], False
		for policy in self.sources():
			rows = self._rows(f"SELECT {quote_string(field)} FROM {self._from(measurement, policy)}"
							  f"{self._where(tag_key, tag_value, start_s, end_s)} LIMIT {limit + 1}")
			if len(rows) > limit:
				truncated = True
			points += [(int(r['time']), r[field]) for r in rows if r.get(field) is not None]
		points.sort(key=lambda p: p[0])
		if len(points) > limit:
			truncated = True
			points = points[:limit]
		return points, truncated

	def last_before(self, measurement, tag_key, tag_value, field, before_s):
		"""(t, value) of the last point before before_s, or None."""
		best = None
		for policy in self.sources():
			rows = self._rows(f"SELECT {quote_string(field)} FROM {self._from(measurement, policy)}"
							  f"{self._where(tag_key, tag_value, end_s=before_s - 1)} ORDER BY time DESC LIMIT 1")
			for r in rows:
				if r.get(field) is not None and (best is None or int(r['time']) > best[0]):
					best = (int(r['time']), r[field])
		return best

	def last_different(self, measurement, tag_key, tag_value, field, value, before_s):
		"""(t, value) of the last point before before_s whose value differs, or None."""
		best = None
		extra = f"{quote_string(field)} != {_literal(value)}"
		for policy in self.sources():
			rows = self._rows(f"SELECT {quote_string(field)} FROM {self._from(measurement, policy)}"
							  f"{self._where(tag_key, tag_value, end_s=before_s - 1, extra=extra)} "
							  f"ORDER BY time DESC LIMIT 1")
			for r in rows:
				if r.get(field) is not None and (best is None or int(r['time']) > best[0]):
					best = (int(r['time']), r[field])
		return best

	def buckets(self, measurement, tag_key, tag_value, field, start_s, end_s, interval, offset):
		"""[(bucket start, min, mean, max, count)] computed by InfluxDB, merged
		across retention policies (the mean weighted by count)."""
		merged = {}
		f = quote_string(field)
		for policy in self.sources():
			rows = self._rows(f"SELECT min({f}), mean({f}), max({f}), count({f}) FROM {self._from(measurement, policy)}"
							  f"{self._where(tag_key, tag_value, start_s, end_s)} "
							  f"GROUP BY time({interval}s, {offset}s) fill(none)")
			for r in rows:
				if not r.get('count'):
					continue
				t = int(r['time'])
				if t in merged:
					low, total, high, count = merged[t]
					merged[t] = (min(low, r['min']), total + r['mean'] * r['count'], max(high, r['max']),
								 count + r['count'])
				else:
					merged[t] = (r['min'], r['mean'] * r['count'], r['max'], r['count'])
		return [(t, low, total / count, high, count) for t, (low, total, high, count) in sorted(merged.items())]

	def present_buckets(self, measurement, tag_key, tag_value, field, start_s, end_s, interval, offset):
		"""Start times of the buckets that hold at least one point."""
		present = set()
		f = quote_string(field)
		for policy in self.sources():
			rows = self._rows(f"SELECT count({f}) FROM {self._from(measurement, policy)}"
							  f"{self._where(tag_key, tag_value, start_s, end_s)} "
							  f"GROUP BY time({interval}s, {offset}s) fill(none)")
			present |= {int(r['time']) for r in rows if r.get('count')}
		return present

	def aggregate(self, measurement, tag_key, tag_value, field, start_s, end_s):
		"""Figures computed by InfluxDB, for a window with too many points to
		read: {count, first: (t, v), last: (t, v), numbers: {min, max, mean} or
		None when the field is not numeric (InfluxDB refuses min/mean on text)}."""
		f = quote_string(field)
		count, low, high, total, numeric = 0, None, None, 0.0, True
		first = last = None
		for policy in self.sources():
			source = self._from(measurement, policy)
			where = self._where(tag_key, tag_value, start_s, end_s)
			for r in self._rows(f"SELECT count({f}) FROM {source}{where}"):
				count += r.get('count') or 0
			for r in self._rows(f"SELECT first({f}) FROM {source}{where}"):
				if r.get('first') is not None and (first is None or int(r['time']) < first[0]):
					first = (int(r['time']), r['first'])
			for r in self._rows(f"SELECT last({f}) FROM {source}{where}"):
				if r.get('last') is not None and (last is None or int(r['time']) > last[0]):
					last = (int(r['time']), r['last'])
			if not numeric or not (first and _number(first[1])):
				numeric = False
				continue
			try:
				rows = self._rows(f"SELECT count({f}), min({f}), max({f}), mean({f}) FROM {source}{where}")
			except InfluxError as e:
				if isinstance(e, InfluxConnectionError) or (isinstance(e, InfluxHTTPError) and e.is_auth_error):
					raise
				numeric = False
				continue
			for r in rows:
				if not r.get('count'):
					continue
				total += r['mean'] * r['count']
				low = r['min'] if low is None else min(low, r['min'])
				high = r['max'] if high is None else max(high, r['max'])
		if not count:
			return None
		numbers = {"min": low, "max": high, "mean": total / count} if numeric and low is not None else None
		return {"count": count, "first": first, "last": last, "numbers": numbers}


################################################################################
# The tool
################################################################################

def _int_arg(value, name, low, high, default):
	if value is None:
		return default
	if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
		raise ToolError("validation", f"{name} must be an integer from {low} to {high}")
	return value


def _ref_list(value, name, limit):
	if value is None:
		return []
	if not isinstance(value, list) or not value:
		raise ToolError("validation", f"{name}: give a non-empty list of ids or exact names")
	if len(value) > limit:
		raise ToolError("validation", f"{name}: at most {limit} per call (got {len(value)})")
	return value


class HistoryQuery:
	def __init__(self, tools):
		self.tools = tools
		self.plugin = tools.plugin

	# ------------------------------------------------------------------
	# validation (on Indigo's callback thread: no network)

	def prepare(self, devices, variables, states, hours, days, start, end, bucket, max_changes):
		p = self.plugin
		if not p.configured:
			raise ToolError("conflict", "the plugin has not been configured yet; set the InfluxDB connection first")
		if p.adaptor is None:
			raise ToolError("conflict", "the plugin is still starting; try again in a moment")
		device_refs = _ref_list(devices, "devices", MAX_DEVICES)
		variable_refs = _ref_list(variables, "variables", MAX_VARIABLES)
		if not device_refs and not variable_refs:
			raise ToolError("validation", "give devices and/or variables (ids or exact names)")
		if states is not None:
			if (not isinstance(states, list) or not states
					or not all(isinstance(s, str) and s.strip() for s in states)):
				raise ToolError("validation", "states must be a non-empty list of state keys (see search_states)")
			if len(states) > MAX_STATES:
				raise ToolError("validation", f"states: at most {MAX_STATES} per call")
			if not device_refs:
				raise ToolError("validation", "states apply to devices; a variable's history is its value")
			states = [s.strip() for s in states]
		if bucket is not None and bucket not in ("auto",) + tuple(NAMED_BUCKETS):
			raise ToolError("validation", "bucket must be 'auto', '15m', 'hour' or 'day'")
		self.max_changes = _int_arg(max_changes, "max_changes", 1, MAX_CHANGES, DEFAULT_MAX_CHANGES)
		self.window = parse_window(hours, days, start, end)
		self.bucket = bucket

		self.targets = []  # dicts: kind, ref, measurement, tag key/value, fields [(key, note)], context
		for index, ref in enumerate(device_refs):
			dev = resolve_device(ref, f"devices[{index}]")
			if any(t['kind'] == 'device' and t['id'] == dev.id for t in self.targets):
				continue
			self.targets.append(self._device_target(dev, states))
		for index, ref in enumerate(variable_refs):
			var = resolve_variable(ref, f"variables[{index}]")
			if any(t['kind'] == 'variable' and t['id'] == var.id for t in self.targets):
				continue
			numeric = p.adaptor.smart_value(var.value, True) is not None
			self.targets.append({
				'kind': 'variable', 'id': var.id, 'ref': {"id": var.id, "name": var.name},
				'measurement': 'variable_changes', 'tag_key': 'varname', 'tag_value': var.name,
				'fields': [('value.num' if numeric else 'value', None)], 'notes': [],
			})
		series = sum(len(t['fields']) for t in self.targets)
		if series > MAX_SERIES:
			raise ToolError("validation", f"that is {series} device/state series; at most {MAX_SERIES} per call - "
										  f"name fewer states or devices")

	def _device_target(self, dev, states):
		tools = self.tools
		p = self.plugin
		values = p.adaptor.to_json(dev)
		measurement = values.pop('measurement', 'device_changes')
		keys = {k for k, v in values.items() if not isinstance(v, dict)}
		mode = tools._mode(dev.id)
		target = {'kind': 'device', 'id': dev.id, 'ref': device_ref(dev.id), 'dev': dev, 'mode': mode,
				  'measurement': measurement, 'tag_key': 'name', 'tag_value': dev.name, 'fields': [], 'notes': [],
				  'values': values}

		if states is not None:
			for key in states:
				if key in keys:
					target['fields'].append((key, None))
				elif 'state.' + key in keys:
					target['fields'].append(('state.' + key, f"read as state.{key}"))
				else:
					close = suggestions(key, sorted(keys))
					note = "not a current state of this device" + (f" (did you mean {', '.join(close)}?)" if close else "")
					target['fields'].append((key, note))
			return target

		if mode == 'excluded':
			target['notes'].append("the device is excluded from logging, so nothing is written for it now; name "
								   "states to read history from before it was excluded")
			return target
		chosen = self.default_states(mode, keys, values)
		target['fields'] = [(key, None) for key in chosen[:DEFAULT_STATE_COUNT]]
		if len(chosen) > DEFAULT_STATE_COUNT:
			target['notes'].append("more logged states (name them in `states`): "
								   + ", ".join(chosen[DEFAULT_STATE_COUNT:DEFAULT_STATE_COUNT + 20]))
		if not chosen:
			target['notes'].append("none of the device's states is logged (see explain_device)")
		return target

	def default_states(self, mode, keys, values):
		"""The states the plugin logs for the device that are worth a history: no
		always-sent or static description keys, and one key of each `x` / `x.num`
		/ `x.ui` family."""
		tools = self.tools
		always = tools.constants.ALWAYS_SENT_STATES
		sent = [k for k in keys if tools._send_decision(mode, k)[0] and k not in always]

		def twin(key):
			for suffix in ('.num', '.ui'):
				if key.endswith(suffix) and key[:-len(suffix)] in sent:
					return True
			return False

		def wanted(key):
			base = key[:-4] if key.endswith('.num') else key
			if base in METADATA_KEYS or base in always or base.startswith('supports') or twin(key):
				return False
			if key == 'state.onOffState' and 'onState' in sent:
				return False  # the same on/off value twice
			# top-level text attributes are descriptions (name, address, model...)
			return key.startswith('state.') or not isinstance(values.get(key), str)

		candidates = [k for k in sent if wanted(k)]
		include = self.plugin.StatesIncludeList
		order = {key: index for index, key in enumerate(list(include) + [k for k in PREFERRED_KEYS if k not in include])}
		return sorted(candidates, key=lambda k: (order.get(k, len(order)), not k.startswith('state.'), k))

	# ------------------------------------------------------------------
	# the network part (worker thread)

	def run(self):
		p = self.plugin
		try:
			settings = p.connectionSettings()
		except ValueError as e:
			raise ToolError("conflict", f"the InfluxDB connection settings are not valid: {e}") from e
		client = p.newClient(settings)
		client.timeout = HTTP_TIMEOUT
		self.reader = HistoryReader(client, settings['database'], settings['version'])
		self.deadline = time.monotonic() + TIME_BUDGET
		frequency = p.minimumUpdateFrequency
		self.heartbeat = frequency if isinstance(frequency, int) and frequency > 0 else None
		results = []
		try:
			for target in self.targets:
				results.append(self._target(target))
		except InfluxHTTPError as e:
			if e.is_auth_error:
				raise ToolError("conflict", (
					f"InfluxDB refused to read database '{settings['database']}' (HTTP {e.status_code}). The plugin's "
					f"credentials may only be allowed to write: query_history needs read access as well - use a "
					f"user or token with read and write on '{settings['database']}' (update_connection)."),
					{"status_code": e.status_code}) from e
			raise ToolError("internal", f"InfluxDB query failed: {e}", {"status_code": e.status_code}) from e
		except InfluxConnectionError as e:
			raise ToolError("internal", f"InfluxDB could not be reached: {e}") from e
		finally:
			client.close()

		reply = {
			"window": self.window.describe(),
			"minimum_update_frequency_minutes": self.heartbeat,
			"results": results,
		}
		notes = list(self.reader.notes)
		if self.heartbeat is None:
			notes.append("minimum-frequency updates (heartbeats) are off, so an unchanged value writes nothing; "
						 "gaps are not reported")
		if notes:
			reply["notes"] = notes
		return reply

	def _target(self, target):
		entry = {target['kind']: target['ref'], "measurement": target['measurement']}
		if target['kind'] == 'device':
			entry["mode"] = target['mode']
			lock = self.plugin.deviceLocks.get(target['id'])
			if lock:
				entry["locked"] = {"since": _iso_datetime(lock['since']), "filter": lock['filter'],
								   "state": lock['state']}
		if target['notes']:
			entry["notes"] = target['notes']
		entry["states" if target['kind'] == 'device' else "history"] = []
		for field, note in target['fields']:
			if time.monotonic() > self.deadline:
				result = {"state": field, "skipped": "the call ran out of time; ask for fewer states or a shorter window"}
			else:
				try:
					result = self._series(target, field)
				except InfluxHTTPError as e:
					if e.is_auth_error:
						raise
					result = {"state": field, "error": str(e)}
				except InfluxConnectionError:
					raise
				except InfluxError as e:
					result = {"state": field, "error": str(e)}
			if note:
				result["note"] = note
			entry["states" if target['kind'] == 'device' else "history"].append(result)
		if target['kind'] == 'variable':
			entry["history"] = entry["history"][0]
		if (self.heartbeat is not None and target['fields'] and target.get('mode') != 'excluded'
				and time.monotonic() <= self.deadline):
			try:
				entry["gaps"] = self._gaps(target)
			except InfluxHTTPError as e:
				if e.is_auth_error:
					raise
				entry["gaps"] = {"error": str(e)}
			except InfluxConnectionError:
				raise
			except InfluxError as e:
				entry["gaps"] = {"error": str(e)}
		return entry

	def _series(self, target, field):
		reader, window = self.reader, self.window
		args = (target['measurement'], target['tag_key'], target['tag_value'], field)
		points, truncated = reader.points(*args, window.start_s, window.end_s)
		result = {"state": field}
		if truncated:
			return self._large_series(target, field, result)

		before = reader.last_before(*args, window.start_s)
		if not points:
			result["points"] = 0
			result["no_data"] = self.explain_missing(target, field, before)
			return result

		values = [v for _, v in points]
		kind = classify(values)
		result["type"] = kind
		result["points"] = len(points)
		changes = change_points(points, before)

		if kind == 'numeric':
			result["summary"] = numeric_summary(points, window.end_s)
			if len(set(values)) == 1 and len(points) >= FLAT_MIN_POINTS:
				result["flat"] = self.flat_line(target, field, values[0])
			result["changes_total"] = len(changes)
			if len(changes) <= self.max_changes:
				result["changes"] = [{"time": iso_time(t), "value": v} for t, v in changes]
		else:
			if before is not None:
				result["value_at_start"] = before[1]
			result["current"] = points[-1][1]
			result["current_at"] = iso_time(points[-1][0])
			result["changes_total"] = len(changes)
			shown = changes[-self.max_changes:]
			result["changes"] = [{"time": iso_time(t), "value": v} for t, v in shown]
			if len(shown) < len(changes):
				result["changes_truncated"] = f"the newest {len(shown)} of {len(changes)} changes"
			held, unknown = time_in_state(points, before, window.start_s, window.end_s)
			result["time_in_state"] = [
				{"value": value, "duration": format_duration(seconds), "seconds": int(seconds),
				 "share": round(seconds / window.seconds, 3)}
				for value, seconds in sorted(held.items(), key=lambda item: -item[1])]
			if unknown:
				result["unknown_before_first_point"] = format_duration(unknown)

		if self.bucket:
			result["series"] = self._buckets(target, field, kind, points, before)
		return result

	def _large_series(self, target, field, result):
		"""More than RAW_POINT_CAP points: figures from InfluxDB aggregates."""
		reader, window = self.reader, self.window
		args = (target['measurement'], target['tag_key'], target['tag_value'], field)
		figures = reader.aggregate(*args, window.start_s, window.end_s)
		result["points"] = figures['count'] if figures else None
		result["truncated"] = (f"more than {RAW_POINT_CAP} points: too many to list changes or time in state "
							   f"(narrow the window for those); the figures come from InfluxDB")
		numbers = figures['numbers'] if figures else None
		if figures:
			first, last = figures['first'], figures['last']
			result["type"] = "numeric" if numbers else classify([v for _, v in (first, last) if v is not None])
			result["current"] = last[1] if last else None
			result["current_at"] = iso_time(last[0]) if last else None
		if numbers:
			change = last[1] - first[1]
			result.pop("current"), result.pop("current_at")
			result["summary"] = {
				"current": last[1], "current_at": iso_time(last[0]), "first": first[1], "first_at": iso_time(first[0]),
				"min": numbers['min'], "max": numbers['max'], "mean_of_points": _round(numbers['mean']),
				"change": _round(change),
				"trend": "steady" if abs(change) < TREND_THRESHOLD else "rising" if change > 0 else "falling",
			}
		if self.bucket and numbers:
			interval, note = bucket_interval(window.seconds, self.bucket)
			offset = bucket_offset(interval, window.end_s)
			rows = reader.buckets(*args, window.start_s, window.end_s, interval, offset)
			result["series"] = self._numeric_series(rows, interval, note)
		return result

	def _numeric_series(self, rows, interval, note):
		series = {"bucket": format_duration(interval), "columns": ["start", "min", "mean", "max", "points"],
				  "rows": [[iso_time(t), low, _round(mean), high, count] for t, low, mean, high, count in rows]}
		if note:
			series["note"] = note
		return series

	def _buckets(self, target, field, kind, points, before):
		window = self.window
		interval, note = bucket_interval(window.seconds, self.bucket)
		offset = bucket_offset(interval, window.end_s)
		if kind == 'numeric':
			rows = self.reader.buckets(target['measurement'], target['tag_key'], target['tag_value'], field,
									   window.start_s, window.end_s, interval, offset)
			return self._numeric_series(rows, interval, note)
		rows = bucketed_time_in_state(points, before, window.start_s, window.end_s, interval, offset)
		series = {"bucket": format_duration(interval), "columns": ["start", "seconds_by_value"],
				  "rows": [[iso_time(t), {str(v).lower() if isinstance(v, bool) else str(v): int(s)
										  for v, s in held.items()}] for t, held in rows]}
		if note:
			series["note"] = note
		return series

	def _gaps(self, target):
		"""Stretches in which the device (or variable) wrote nothing at all.  Read
		from the field every point carries - `id` on a device point, `value` on a
		variable's - and not per state: an unchanged state is re-sent only on the
		heartbeat, and any other state that changes postpones it, so one quiet
		state is normal while the device keeps writing."""
		window, reader = self.window, self.reader
		threshold = self.heartbeat * 120  # twice the heartbeat interval, in seconds
		field = 'value' if target['kind'] == 'variable' else 'id'
		args = (target['measurement'], target['tag_key'], target['tag_value'], field)
		points, truncated = reader.points(*args, window.start_s, window.end_s)
		if not truncated:
			gaps = find_gaps([t for t, _ in points], window.start_s, window.end_s, threshold)
		else:
			interval = threshold // 2
			offset = bucket_offset(interval, window.end_s)
			present = reader.present_buckets(*args, window.start_s, window.end_s, interval, offset)
			gaps = gaps_from_buckets(present, window.start_s, window.end_s, interval, offset)
		return describe_gaps(gaps, threshold)

	def flat_line(self, target, field, value):
		"""The value never moved in the window: when did it last differ?"""
		window = self.window
		different = self.reader.last_different(target['measurement'], target['tag_key'], target['tag_value'],
											   field, value, window.start_s)
		flat = {"warning": f"{field} did not change at all during the window"}
		if different is None:
			flat["last_different"] = None
			flat["hint"] = "no different value in the retained history; it may simply never change"
		else:
			days = (window.end_s - different[0]) / 86400
			flat["last_different"] = {"value": different[1], "time": iso_time(different[0]),
									  "ago": format_duration(window.end_s - different[0])}
			if days >= 1:
				flat["hint"] = ("unchanged for over a day: if this reading should vary, the sensor may be stuck "
								"or offline (see the device's secondsSinceLastSuccessfulComm)")
		return flat

	def explain_missing(self, target, field, before):
		"""Why a series has no points in the window."""
		reasons = []
		if before is not None:
			last = {"value": before[1], "time": iso_time(before[0]), "ago": format_duration(self.window.end_s - before[0])}
		else:
			last = None
		if target['kind'] == 'device':
			tools, p, dev = self.tools, self.plugin, target['dev']
			mode = target['mode']
			sent, reason = tools._send_decision(mode, field)
			if not sent:
				reasons.append(f"not logged now: {reason}")
			elif field in target['values']:
				value = target['values'][field]
				for position, f in enumerate(p.FilterList, start=1):
					if f.state != field or not f.appliesTo(dev.id):
						continue
					passed, _, _ = p.evaluateFilter(f, None, dev, field, value)
					if not passed:
						reasons.append(f"the current value {value!r} is blocked by filter {position} '{f.name}'")
						break
			lock = p.deviceLocks.get(dev.id)
			if lock:
				reasons.append(f"the device is locked out of updates by filter '{lock['filter']}' since "
							   f"{_iso_datetime(lock['since'])}")
			if p.FilterLogFileLoc:
				blocks, _ = read_records(p.FilterLogFileLoc, 200, device=dev.name, state=field)
				if blocks:
					reasons.append(f"filter.log holds {len(blocks)} blocked value(s) for it, newest "
								   f"{blocks[0].get('time')} ({blocks[0].get('value')}): see get_filter_blocks")
			if field not in target['values']:
				reasons.append("the device does not have this state now")
		if self.heartbeat is None and before is not None:
			reasons.append("heartbeats are off, so an unchanged value writes nothing")
		if not reasons:
			reasons.append("nothing was written in the window: the plugin or InfluxDB may have been down, or "
						   "the value only exists since later" if before is not None else
						   "nothing has ever been logged for it under this name (a renamed device's older history "
						   "is under its old name)")
		return {"reasons": reasons, "last_logged_before_window": last}


def query_history(tools, devices=None, variables=None, states=None, hours=None, days=None, start=None, end=None,
				  bucket=None, max_changes=None):
	query = HistoryQuery(tools)
	query.prepare(devices, variables, states, hours, days, start, end, bucket, max_changes)
	return AsyncResult(query.run)
