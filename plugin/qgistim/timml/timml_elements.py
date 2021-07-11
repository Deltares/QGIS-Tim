"""
Specification of TimML data requirements
"""
from qgis.core import QgsFeature, QgsField, QgsGeometry, QgsPointXY, QgsVectorLayer
from qgis.PyQt.QtCore import QVariant


ELEMENT_SPEC = {
    "Aquifer": (
        "No geometry",
        [
            QgsField("layer", QVariant.Int),
            QgsField("resistance", QVariant.Double),
            QgsField("conductivity", QVariant.Double),
            QgsField("z_top", QVariant.Double),
            QgsField("z_bottom", QVariant.Double),
            QgsField("porosity_aquifer", QVariant.Double),
            QgsField("porosity_aquitard", QVariant.Double),
            QgsField("head_topboundary", QVariant.Double),
            QgsField("z_topboundary", QVariant.Double),
        ],
    ),
    "Uniform Flow": (
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
            QgsField("caisson_radius", QVariant.Double),
            QgsField("slug", QVariant.Bool),
            QgsField("geometry_id", QVariant.Int),
        ],
    ),
    "Head Well": (
        "Point",
        [
            QgsField("head", QVariant.Double),
            QgsField("radius", QVariant.Double),
            QgsField("resistance", QVariant.Double),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
            QgsField("geometry_id", QVariant.Int),
        ],
    ),
    "Head Line Sink": (
        "Linestring",
        [
            QgsField("head", QVariant.Double),
            QgsField("resistance", QVariant.Double),
            QgsField("width", QVariant.Double),
            QgsField("order", QVariant.Int),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
            QgsField("geometry_id", QVariant.Int),
        ],
    ),
    "Line Sink Ditch": (
        "Linestring",
        [
            QgsField("discharge", QVariant.Double),
            QgsField("resistance", QVariant.Double),
            QgsField("width", QVariant.Double),
            QgsField("order", QVariant.Int),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
            QgsField("geometry_id", QVariant.Int),
        ],
    ),
    "Circular Area Sink": (
        "Polygon",
        [
            QgsField("rate", QVariant.Double),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
            QgsField("geometry_id", QVariant.Int),
        ],
    ),
    "Impermeable Line Doublet": (
        "Linestring",
        [
            QgsField("order", QVariant.Int),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
        ],
    ),
    "Leaky Line Doublet": (
        "Linestring",
        [
            QgsField("resistance", QVariant.Double),
            QgsField("order", QVariant.Int),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
        ],
    ),
    "Polygon Inhomogeneity": (
        "Polygon",
        [
            QgsField("geometry_id", QVariant.Int),
            QgsField("order", QVariant.Int),
            QgsField("ndegrees", QVariant.Int),
        ],
    ),
    "Polygon Inhomogeneity Properties": (
        "No geometry",
        [
            QgsField("geometry_id", QVariant.Int),
            QgsField("layer", QVariant.Int),
            QgsField("conductivity", QVariant.Double),
            QgsField("resistance", QVariant.Double),
            QgsField("z_top", QVariant.Double),
            QgsField("z_bottom", QVariant.Double),
            QgsField("porosity_aquifer", QVariant.Double),
            QgsField("porosity_aquitard", QVariant.Double),
            QgsField("head_topboundary", QVariant.Double),
            QgsField("z_topboundary", QVariant.Double),
        ],
    ),
    "Building Pit": (
        "Polygon",
        [
            QgsField("geometry_id", QVariant.Int),
            QgsField("order", QVariant.Int),
            QgsField("ndegrees", QVariant.Int),
            QgsField("layer", QVariant.Int),
        ],
    ),
    "Building Pit Properties": (
        "No geometry",
        [
            QgsField("geometry_id", QVariant.Int),
            QgsField("layer", QVariant.Int),
            QgsField("conductivity", QVariant.Double),
            QgsField("resistance", QVariant.Double),
            QgsField("z_top", QVariant.Double),
            QgsField("z_bottom", QVariant.Double),
            QgsField("porosity_aquifer", QVariant.Double),
            QgsField("porosity_aquitard", QVariant.Double),
            QgsField("head_topboundary", QVariant.Double),
            QgsField("z_topboundary", QVariant.Double),
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
    layer = QgsVectorLayer(geometry_type, f"timml {elementtype}:{layername}", "memory")
    provider = layer.dataProvider()
    provider.addAttributes(attributes)
    layer.updateFields()
    layer.setCrs(crs)
    return layer
