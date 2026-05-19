import sys
from pathlib import Path

from enable_plugin import enable_plugin

if __name__ == "__main__":
    this_path = Path(__file__).parent.absolute()
    target_path = this_path.parent / "plugin/qgistim"
    plugins_path = Path(sys.argv[1]) / "python/plugins"
    qgis_path = plugins_path / "qgistim"

    plugins_path.mkdir(parents=True, exist_ok=True)
    qgis_path.unlink(missing_ok=True)
    qgis_path.symlink_to(target_path, target_is_directory=True)
    enable_plugin("qgistim", sys.argv[1])
