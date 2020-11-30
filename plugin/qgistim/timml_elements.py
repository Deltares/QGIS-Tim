"""
Specification of TimML data requirements
"""
from qgis.core import QgsFeature, QgsField, QgsGeometry, QgsPointXY, QgsVectorLayer
from qgis.PyQt.QtCore import QVariant

ELEMENT_SPEC = {
    "Aquifer": (
        "No geometry",
        [
            QgsField("conductivity", QVariant.Double),
            QgsField("resistance", QVariant.Double),
            QgsField("top", QVariant.Double),
            QgsField("bottom", QVariant.Double),
            QgsField("porosity", QVariant.Double),
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
            QgsField("conductivity", QVariant.Double),
            QgsField("resistance", QVariant.Double),
            QgsField("top", QVariant.Double),
            QgsField("bottom", QVariant.Double),
            QgsField("topconfined", QVariant.Bool),
            QgsField("tophead", QVariant.Double),
            QgsField("order", QVariant.Int),
            QgsField("ndegrees", QVariant.Int),
        ],
    ),
}


def create_timml_layer(elementtype: str, layername: str, crs) -> QgsVectorLayer:
    geometry_type, attributes = ELEMENT_SPEC[elementtype]
    layer = QgsVectorLayer(geometry_type, f"timml{elementtype}:{layername}", "memory")
    provider = layer.dataProvider()
    provider.addAttributes(attributes)
    layer.updateFields()
    layer.setCrs(crs)
    return layer
