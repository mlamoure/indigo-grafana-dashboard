"""
startup(): pref migrations, filter.log location (issue #12 item 11), obsolete
v2.x prefs (low item), never-configured detection.
"""

import logging
import os

from conftest import FakeDevice


def test_obsolete_v2_prefs_are_removed(make_plugin, indigo, caplog):
    with caplog.at_level(logging.INFO, logger="Plugin"):
        plugin = make_plugin(GrafanaAdminPassword='plaintext!', GrafanaPort='3006', InfluxDataLocation='/x',
                             DisableGrafana=True, ExternalDB=True, InfluxPort='8088')
    for key in ('GrafanaAdminPassword', 'GrafanaPort', 'InfluxDataLocation', 'DisableGrafana', 'ExternalDB', 'InfluxPort'):
        assert key not in plugin.pluginPrefs
    assert indigo.server.saved_prefs >= 1
    message = next(r.getMessage() for r in caplog.records if 'obsolete settings' in r.getMessage())
    assert 'plaintext!' not in message  # names only, never values
    assert plugin.pluginPrefs['InfluxHost'] == 'influx.example.com'  # current settings untouched


def test_v3_checkbox_is_migrated_then_removed(make_plugin):
    prefs = {'InfluxV3Compat': True}
    plugin = make_plugin(prefs)
    # BASE_PREFS carries InfluxVersion='1'; a pre-2026.7.0 config has none
    plugin = make_plugin(start=False, **prefs)
    del plugin.pluginPrefs['InfluxVersion']
    plugin.startup()
    assert plugin.pluginPrefs['InfluxVersion'] == '3'
    assert plugin.InfluxV3Compat
    assert 'InfluxV3Compat' not in plugin.pluginPrefs


def test_filter_log_moves_from_the_hard_coded_location(make_plugin, indigo, tmp_path, monkeypatch):
    home = tmp_path / 'home'
    legacy_dir = home / 'Library' / 'Application Support' / 'Perceptive Automation' / 'Indigo 2025.1' / 'Logs' / 'com.vtmikel.grafana'
    legacy_dir.mkdir(parents=True)
    (legacy_dir / 'filter.log').write_text("2026-10-14 07:47: Filter block (x): old line\n")
    monkeypatch.setenv('HOME', str(home))

    plugin = make_plugin()

    expected = os.path.join(indigo.server.getLogsFolderPath('com.vtmikel.grafana'), 'filter.log')
    assert plugin.FilterLogFileLoc == expected
    with open(expected) as moved:
        assert 'old line' in moved.read()
    assert not (legacy_dir / 'filter.log').exists()


def test_never_configured_does_not_connect(make_plugin):
    plugin = make_plugin(start=False)
    for key in ('InfluxHost', 'listIncStates'):
        del plugin.pluginPrefs[key]
    plugin.startup()
    assert not plugin.configured
    assert plugin.StatesIncludeList[:2] == ['state.onOffState', 'onState']
    plugin.newClient = lambda settings: (_ for _ in ()).throw(AssertionError("must not connect"))
    plugin.connect()
    assert not plugin.connected


def test_string_device_ids_are_normalized(make_plugin, indigo):
    indigo.devices.add(FakeDevice("Twelve", dev_id=12))
    indigo.devices.add(FakeDevice("Seven", dev_id=7))
    plugin = make_plugin(listIncDevices=['12', 12, 'x', 99], listExclDevices=['7'])
    assert plugin.DeviceIncludeList == [12]  # 99 no longer exists
    assert plugin.DeviceExcludeList == [7]


def test_v1_filter_format_is_upgraded(make_plugin):
    plugin = make_plugin(preferencesFilterVersion='1.0.0',
                         listFilterList=[['sensorValue', 'minMax', 0, 100, 0, True, [], False]])
    assert plugin.pluginPrefs['preferencesFilterVersion'] == '2.0.0'
    assert plugin.FilterList[0].lockMinimumUpdates is True
