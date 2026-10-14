"""Parse filter.log lines (written by Plugin.DeviceToInflux) into records."""

import re

_PREFIX = r"^(?P<time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}): Filter block \((?P<filter>.*?)\): "
_LOCKED = r"(?P<locked>\.  The device has also been locked out of minimum-frequency updates until it reports a change\.)?$"

RANGE = re.compile(
	_PREFIX + r"a value \((?P<value>.*)\) for state/property '(?P<state>.*?)' on device '(?P<device>.*)' "
	r"was not in the configured range \((?P<min>[^,]*), (?P<max>[^)]*)\) and will not be sent to InfluxDB" + _LOCKED)
PERCENT = re.compile(
	_PREFIX + r"a value \(previous value: (?P<previous>.*), new value: (?P<value>.*)\) for state/property "
	r"'(?P<state>.*?)' on device '(?P<device>.*)' exceeded percent changed \(percent changed: (?P<change>[^%]*)%, "
	r"threshhold: (?P<threshold>[^%]*)%\) and will not be sent to InfluxDB" + _LOCKED)


def parse_line(line):
	"""A record {time, filter, device, state, value, reason, locked}, or
	{'raw': line} for a line in another format."""
	line = line.rstrip("\n")
	match = RANGE.match(line)
	if match:
		return {
			"time": match["time"], "filter": match["filter"], "device": match["device"], "state": match["state"],
			"value": match["value"], "reason": f"outside the range {match['min']} .. {match['max']}",
			"locked": bool(match["locked"]),
		}
	match = PERCENT.match(line)
	if match:
		return {
			"time": match["time"], "filter": match["filter"], "device": match["device"], "state": match["state"],
			"value": match["value"], "previous_value": match["previous"],
			"reason": f"changed {match['change']}% (more than {match['threshold']}%)",
			"locked": bool(match["locked"]),
		}
	return {"raw": line}


def read_records(path, limit, device=None, state=None, scan_lines=5000):
	"""The newest `limit` records matching device / state, newest first."""
	try:
		with open(path, "r", encoding="utf-8", errors="replace") as f:
			lines = f.readlines()[-scan_lines:]
	except FileNotFoundError:
		return [], 0

	records = []
	for line in reversed(lines):
		if not line.strip():
			continue
		record = parse_line(line)
		if device is not None and record.get("device") != device:
			continue
		if state is not None and record.get("state") != state:
			continue
		records.append(record)
		if len(records) >= limit:
			break
	return records, len(lines)
