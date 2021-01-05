"""
Specification of TimML data requirements
"""
from qgis.core import QgsFeature, QgsField, QgsGeometry, QgsPointXY, QgsVectorLayer
from qgis.PyQt.QtCore import QVariant

ELEMENT_SPEC = {
    "Aquifer": (
        "No geometry",
        [
            QgsField("index", QVariant.Int),
            QgsField("conductivity", QVariant.Double),
            QgsField("resistance", QVariant.Double),
            QgsField("top", QVariant.Double),
            QgsField("bottom", QVariant.Double),
            QgsField("porosity", QVariant.Double),
            QgsField("headtop", QVariant.Double),
        ],
    ),
    "UniformFlow": (
        "No geometry",
        [
            QgsField("slope", QVariant.Double),
            QgsField("angle", QVariant.Double),
            QgsField("label", QVariant.String),
        ],
    ),
    "Constant": (
        "Point",
        [
            QgsField("head", QVariant.Double),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
        ],
    ),
    "Well": (
        "Point",
        [
            QgsField("discharge", QVariant.Double),
            QgsField("radius", QVariant.Double),
            QgsField("resistance", QVariant.Double),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
        ],
    ),
    "HeadWell": (
        "Point",
        [
            QgsField("head", QVariant.Double),
            QgsField("radius", QVariant.Double),
            QgsField("resistance", QVariant.Double),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
        ],
    ),
    "HeadLineSink": (
        "Linestring",
        [
            QgsField("head", QVariant.Double),
            QgsField("resistance", QVariant.Double),
            QgsField("width", QVariant.Double),
            QgsField("order", QVariant.Int),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
        ],
    ),
    "LineSinkDitch": (
        "Linestring",
        [
            QgsField("discharge", QVariant.Double),
            QgsField("resistance", QVariant.Double),
            QgsField("width", QVariant.Double),
            QgsField("order", QVariant.Int),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
        ],
    ),
    "CircAreaSink": (
        "Polygon",
        [
            QgsField("rate", QVariant.Double),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
        ],
    ),
    "ImpLineDoublet": (
        "Linestring",
        [
            QgsField("order", QVariant.Int),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
        ],
    ),
    "LeakyLineDoublet": (
        "Linestring",
        [
            QgsField("resistance", QVariant.Double),
            QgsField("order", QVariant.Int),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
        ],
    ),
    "PolygonInhom": (
        "Polygon",
        [
            QgsField("order", QVariant.Int),
            QgsField("ndegrees", QVariant.Int),
        ],
    ),
    "PolygonInhomProperties": (
        "No geometry",
        [
            QgsField("index", QVariant.Int),
            QgsField("conductivity", QVariant.Double),
            QgsField("resistance", QVariant.Double),
            QgsField("top", QVariant.Double),
            QgsField("bottom", QVariant.Double),
            QgsField("porosity", QVariant.Double),
            QgsField("headtop", QVariant.Double),
            QgsField("geometry_fid", QVariant.Int),
        ],
    ),
}


def create_timml_layer(elementtype: str, layername: str, crs) -> QgsVectorLayer:
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
    geometry_type, attributes = ELEMENT_SPEC[elementtype]
    layer = QgsVectorLayer(geometry_type, f"timml{elementtype}:{layername}", "memory")
    provider = layer.dataProvider()
    provider.addAttributes(attributes)
    layer.updateFields()
    layer.setCrs(crs)
    return layer
