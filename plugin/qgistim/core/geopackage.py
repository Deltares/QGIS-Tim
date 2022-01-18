"""
Geopackage management utilities.

This module lightly wraps a few QGIS built in functions to:

    * List the layers of a geopackage
    * Write a layer to a geopackage
    * Remove a layer from a geopackage

"""
from typing import List

from qgis import processing
from qgis.core import QgsVectorFileWriter, QgsVectorLayer


def layers(path: str) -> List[str]:
    """
    Return all layers that are present in the geopackage.

    Parameters
    ----------
    path: str
        Path to the geopackage

    Returns
    -------
    layernames: List[str]
    """
    # Adapted from PyQGIS cheatsheet:
    # https://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/cheat_sheet.html#layers
    layer = QgsVectorLayer(path, "", "ogr")
    return [name.split("!!::!!")[1] for name in layer.dataProvider().subLayers()]


def write_layer(
    path: str, layer: QgsVectorLayer, layername: str, newfile: bool = False
) -> QgsVectorLayer:
    """
    Writes a QgsVectorLayer to a GeoPackage file.

    Parameters
    ----------
    path: str
        Path to the GeoPackage file
    layer: QgsVectorLayer
        QGIS map layer (in-memory)
    layername: str
        Layer name to write in the GeoPackage
    newfile: bool, optional
        Whether to write a new GPGK file. Defaults to false.

    Returns
    -------
    layer: QgsVectorLayer
        The layer, now associated with the both GeoPackage and its QGIS
        representation.
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
            f" with error: {error_message}"
        )
    layer = QgsVectorLayer(f"{path}|layername={layername}", layername, "ogr")
    return layer


def remove_layer(path: str, layer: str) -> None:
    query = {"DATABASE": f"{path}|layername={layer}", "SQL": f"drop table {layer}"}
    print(query)
    try:
        processing.run("native:spatialiteexecutesql", query)
    except Exception:
        raise RuntimeError(f"Failed to remove layer with {query}")
