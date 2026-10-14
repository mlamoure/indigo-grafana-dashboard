# Tests

The suite exercises the real plugin modules (`plugin.py`, `json_adaptor.py`,
`influx_client.py`, `influx_settings.py`) against a fake `indigo` module
(`conftest.py`). The fake is strict where Indigo is: `indigo.Dict` and
`indigo.List` refuse a Python `set`, `None` and arbitrary objects with the same
`TypeError` the real ones raise.

## Running

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/pytest tests/ -q
```

Python 3.13 is what Indigo 2025.2 runs plugins on. CI (`.gitea/workflows/test.yml`)
runs the same command on every pull request.

## Layout

| File | Covers |
|---|---|
| `conftest.py` | fake `indigo` module, `make_plugin` fixture, production-shaped prefs |
| `fake_influx.py` | scriptable stand-in for `InfluxClient` |
| `test_line_protocol.py` | encoder vs. `influxdb==5.3.2`'s `make_lines`, byte for byte |
| `test_influx_client.py` | HTTP calls and error decoding, using real InfluxDB 1.8 / 3 response bodies |
| `test_writer.py` | write-error classification, type-conflict recovery, buffering through an outage |
| `test_connect.py` | connect(), DDL and retention on 1.x, auth failures, invalid settings |
| `test_config_dialog.py` | Cancel, validation, background reconnect, the config lock |
| `test_filters.py` | filter edit/delete/insert, generated names, filter.log, device locks |
| `test_update_all.py` | heartbeats (incl. Disabled and legacy "smart"), inclusion rules |
| `test_startup.py` | pref migrations, obsolete prefs, filter.log location |
| `test_json_adaptor.py` | include semantics, change detection, cache |
| `test_percent_changed.py` | percent-change helpers |
| `live/` | live InfluxDB matrix (below) |

## Live InfluxDB matrix (required before every release)

```bash
tests/live/run_influx_matrix.sh
```

Starts throwaway `influxdb:1.8` (authentication on) and `influxdb:3-core`
containers, runs `tests/live/` against both, prints the server versions tested
and removes the containers. It checks ping, DDL and retention on 1.x, batched
writes through the writer thread, column types identical to what the old
`influxdb` client created, type-conflict recovery, and 401/403/404 handling.
Needs Docker. Without `INFLUX_LIVE=1` the live tests skip themselves, so a
plain `pytest tests/` stays offline.

InfluxDB 3 Core allows five databases per server, so the v3 tests share one
database and keep apart by measurement name.

`influxdb==5.3.2` (the archived client the plugin used until 2026.11.0) is a
test-only dependency for the encoder comparison. Once the comparison has passed
for one release, freeze its expected lines into fixtures and drop the package.
