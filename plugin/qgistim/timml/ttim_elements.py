"""
Specification of TTim data requirements
"""
from qgis.core import QgsField, QgsVectorLayer
from qgis.PyQt.QtCore import QVariant


TTIM_ELEMENT_SPEC = {
    "Temporal Settings": (
        "No geometry",
        [
            QgsField("tmin", QVariant.Double),
            QgsField("tmax", QVariant.Double),
            QgsField("tstart", QVariant.Double),
            QgsField("M", QVariant.Int),
            QgsField("starting_date", QVariant.DateTime),
        ],
    ),
    "Computation Times": (
        "No geometry",
        [
            QgsField("time", QVariant.Double),
        ],
    ),
    "Well": (
        "No geometry",
        [
            QgsField("geometry_id", QVariant.Int),
            QgsField("tstart", QVariant.Double),
            QgsField("discharge", QVariant.Double),
        ],
    ),
    "Head Well": (
        "No geometry",
        [
            QgsField("geometry_id", QVariant.Int),
            QgsField("tstart", QVariant.Double),
            QgsField("head", QVariant.Double),
        ],
    ),
    "Head Link Sink": (
        "No geometry",
        [
            QgsField("geometry_id", QVariant.Int),
            QgsField("tstart", QVariant.Double),
            QgsField("head", QVariant.Double),
        ],
    ),
    "Link Sink Ditch": (
        "No geometry",
        [
            QgsField("geometry_id", QVariant.Int),
            QgsField("tstart", QVariant.Double),
            QgsField("discharge", QVariant.Double),
        ],
    ),
    "Circular Area Sink": (
        "No geometry",
        [
            QgsField("geometry_id", QVariant.Int),
            QgsField("tstart", QVariant.Double),
            QgsField("rate", QVariant.Double),
        ],
    ),
}


def create_ttim_layer(elementtype: str, layername: str, crs) -> QgsVectorLayer:
    """
    Parameters
    ----------
    elementtype: str
        Used as a key in ELEMENT_SPEC, to find the geometry type (e.g. point,
        linestring), and the required attributes (columns in the attribute
        table).
    layername: str
    crs:
        Coordinate Reference System to assign to the new layer.

    Returns
    -------
    layer: QgsVectorLayer
        A new vector layer
    """
    geometry_type, attributes = TTIM_ELEMENT_SPEC[elementtype]
    layer = QgsVectorLayer(geometry_type, f"timml {elementtype}:{layername}", "memory")
    provider = layer.dataProvider()
    provider.addAttributes(attributes)
    layer.updateFields()
    layer.setCrs(crs)
    return layer
