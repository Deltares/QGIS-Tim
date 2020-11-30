"""
Geopackage management utilities
"""
from typing import List

from qgis.core import QgsVectorFileWriter, QgsVectorLayer


def layers(path: str) -> List[str]:
    """
    Return all layers that are present in the geopackage.
    """
    # Adapted from PyQGIS cheatsheet:
    # https://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/cheat_sheet.html#layers
    layer = QgsVectorLayer(path, "", "ogr")
    return [name.split("!!::!!")[1] for name in layer.dataProvider().subLayers()]


def write_layer(path: str, layer: str, layername: str, newfile: bool = False) -> None:
    """
    Writes a QgsVectorLayer to a GeoPackage.
    """
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "gpkg"
    options.layerName = layername
    if not newfile:
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
    write_result, error_message = QgsVectorFileWriter.writeAsVectorFormat(
        layer, path, options
    )
    if write_result != QgsVectorFileWriter.NoError:
        raise RuntimeError(
            f"Layer {layername} could not be written to geopackage: {path}"
            f"with error: {error_message}"
        )
    layer = QgsVectorLayer(f"{path}|layername={layername}", layername, "ogr")
    return layer
