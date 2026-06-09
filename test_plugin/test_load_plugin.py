from pathlib import Path

import pytest
from qgis.core import QgsApplication, QgsSettings
from qgis.utils import findPlugins


@pytest.fixture
def restore_qgistim_enabled_setting(request: pytest.FixtureRequest) -> None:
    """Restore qgistim enabled setting after a test mutates it."""
    settings = QgsSettings()
    key = "PythonPlugins/qgistim"
    had_value = settings.contains(key)
    old_value = settings.value(key, False, type=bool) if had_value else None

    def _restore() -> None:
        if had_value:
            settings.setValue(key, old_value)
        else:
            settings.remove(key)

    request.addfinalizer(_restore)


def test_plugin_is_installed_and_enabled() -> None:
    """Test the started QGIS app sees qgistim as installed and enabled."""
    settings_dir = Path(QgsApplication.qgisSettingsDirPath())
    plugin_root = settings_dir / "python" / "plugins"
    plugin_path = plugin_root / "qgistim"

    assert plugin_path.exists(), (
        "QGIS Tim plugin was not installed into the active QGIS profile"
    )

    discovered_plugins = {
        plugin_name for plugin_name, _ in findPlugins(str(plugin_root))
    }
    assert "qgistim" in discovered_plugins

    settings = QgsSettings()
    assert settings.value("PythonPlugins/qgistim", False, type=bool)


def test_plugin_is_installed_not_enabled(restore_qgistim_enabled_setting) -> None:
    """Test the started QGIS app does not see qgistim as enabled."""
    settings_dir = Path(QgsApplication.qgisSettingsDirPath())
    plugin_root = settings_dir / "python" / "plugins"
    plugin_path = plugin_root / "qgistim"

    assert plugin_path.exists(), (
        "QGIS Tim plugin was not installed into the active QGIS profile"
    )

    # Disable the plugin by changing QGIS3 settings before finding the plugins.
    settings = QgsSettings()
    settings.setValue("PythonPlugins/qgistim", False)

    discovered_plugins = {
        plugin_name for plugin_name, _ in findPlugins(str(plugin_root))
    }
    assert "qgistim" in discovered_plugins

    settings = QgsSettings()
    assert not settings.value("PythonPlugins/qgistim", False, type=bool)
