from typing import Any, cast

from qgis.utils import plugins


def test_plugin_is_loaded():
    """Test plugin is properly loaded and appears in QGIS plugins."""
    qgis_plugins = cast(dict[str, Any], plugins)
    plugin = qgis_plugins.get("qgistim")
    assert plugin, "QGIS Tim plugin not loaded"
