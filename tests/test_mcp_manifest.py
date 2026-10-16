"""Drift guards between Contents/Resources/mcp-manifest.json, the dispatcher's
tool table, Actions.xml and Info.plist (the provider contract of the Indigo MCP
Server, docs/mcp-provider-manifest.md in indigo-mcp-server)."""

import json
import os
import plistlib
import re
import xml.etree.ElementTree as ET

import pytest

from mcp_api.config_tools import InfluxLogTools

CONTENTS = os.path.join(os.path.dirname(__file__), '..', 'Grafana Home Dashboard.indigoPlugin', 'Contents')

# name: (write, timeout)
EXPECTED = {
    'get_status': (False, 10),
    'get_config': (False, 15),
    'explain_device': (False, 15),
    'search_states': (False, 15),
    'get_filter_blocks': (False, 10),
    'query_history': (False, 60),
    'set_device_mode': (True, 30),
    'update_included_states': (True, 30),
    'update_settings': (True, 30),
    'update_connection': (True, 30),
    'reconnect': (True, 15),
    'list_snapshots': (False, 10),
    'restore_snapshot': (True, 30),
    'create_filter': (True, 30),
    'update_filter': (True, 30),
    'delete_filter': (True, 30),
}


@pytest.fixture(scope='module')
def manifest():
    with open(os.path.join(CONTENTS, 'Resources', 'mcp-manifest.json')) as f:
        return json.load(f)


def tool(manifest, name):
    return next(t for t in manifest['tools'] if t['name'] == name)


def test_manifest_basics(manifest):
    with open(os.path.join(CONTENTS, 'Info.plist'), 'rb') as f:
        info = plistlib.load(f)
    assert manifest['manifest_version'] == 1
    assert manifest['provider']['plugin_id'] == info['CFBundleIdentifier'] == 'com.vtmikel.grafana'
    assert manifest['tool_prefix'] == 'influxlog'
    assert re.match(r'^[a-z][a-z0-9_]{0,31}$', manifest['tool_prefix'])
    assert manifest['invoke_action_id'] == 'mcp_tool_invoke'


def test_manifest_lists_exactly_the_dispatched_tools(manifest):
    names = [t['name'] for t in manifest['tools']]
    assert len(names) == len(set(names))
    assert sorted(names) == sorted(InfluxLogTools.TOOLS) == sorted(EXPECTED)
    for name in names:
        assert re.match(r'^[a-z][a-z0-9_]{0,40}$', name)


def test_write_flags_and_timeouts(manifest):
    for name, (write, timeout) in EXPECTED.items():
        entry = tool(manifest, name)
        assert entry['write'] is write, name
        assert entry['timeout_seconds'] == timeout, name
        assert 5 <= entry['timeout_seconds'] <= 120


def test_every_schema_is_a_documented_object(manifest):
    for entry in manifest['tools']:
        assert len(entry['description']) > 80, entry['name']
        schema = entry['inputSchema']
        assert schema['type'] == 'object', entry['name']
        assert set(schema['required']) <= set(schema['properties']), entry['name']
        for prop_name, prop in schema['properties'].items():
            assert prop.get('description'), f"{entry['name']}.{prop_name}"
            assert prop.get('type'), f"{entry['name']}.{prop_name}"


def test_schema_properties_match_the_handler_signatures(manifest):
    import inspect
    for entry in manifest['tools']:
        params = inspect.signature(getattr(InfluxLogTools, entry['name'])).parameters
        accepted = [p for p in params if p != 'self']
        assert sorted(entry['inputSchema']['properties']) == sorted(accepted), entry['name']
        required = [p for p, spec in params.items() if p != 'self' and spec.default is inspect.Parameter.empty]
        assert sorted(entry['inputSchema']['required']) == sorted(required), entry['name']


def test_hidden_invoke_action_is_declared():
    root = ET.parse(os.path.join(CONTENTS, 'Server Plugin', 'Actions.xml')).getroot()
    action = root.find("Action[@id='mcp_tool_invoke']")
    assert action is not None
    assert action.get('uiPath') == 'hidden'
    assert action.findtext('CallbackMethod') == 'handle_mcp_tool_invoke'
