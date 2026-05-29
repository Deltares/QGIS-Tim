from pathlib import Path

from qgis.core import QgsApplication, QgsSettings
from qgis.utils import findPlugins


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


def test_plugin_is_installed_not_enabled() -> None:
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
