from abc import ABC
from typing import Any
from PyQt5.QtWidgets import (
    QDialog,
    QPushButton,
    QLineEdit,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
)
from PyQt5.QtCore import QVariant
from qgis.core import QgsVectorLayer, QgsField, QgsSingleSymbolRenderer, QgsFillSymbol


class NameDialog(QDialog):
    def __init__(self, parent=None):
        super(NameDialog, self).__init__(parent)
        self.name_line_edit = QLineEdit()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        first_row = QHBoxLayout()
        first_row.addWidget(QLabel("Layer name"))
        first_row.addWidget(self.name_line_edit)
        second_row = QHBoxLayout()
        second_row.addStretch()
        second_row.addWidget(self.ok_button)
        second_row.addWidget(self.cancel_button)
        layout = QVBoxLayout()
        layout.addLayout(first_row)
        layout.addLayout(second_row)
        self.setLayout(layout)


class Element(ABC):
    element_type = None
    geometry_type = None
    timml_attributes = None
    ttim_attributes = None
    assoc_attributes = None

    def __init__(self, path: str, name: str):
        self.name = name
        self.timml_name = (f"timml {self.elementtype}:{name}",)
        self.path = path
        self.timml_layer = None
        self.item = None

    def layer(self, crs: Any, geometry_type: str, name: str, attributes: List):
        layer = QgsVectorLayer(geometry_type, name, "memory")
        provider = layer.dataProvider()
        provider.addAttributes(attributes)
        layer.updateFields()
        layer.setCrs(crs)

    def timml_layer(self, crs: Any):
        return self.layer(
            crs=crs,
            geometry_type=self.geometry_type,
            name=self.timml_name,
            attributes=self.timml_attributes,
        )

    def ttim_layer(self, crs: Any):
        return None

    def assoc_layer(self, crs: Any):
        return None

    def renderer(self):
        return None

    def timml_layer_from_geopackage(self, path: str) -> QgsVectorLayer:
        layer = QgsVectorLayer(
            f"{self.path}|layername={self.timml_name}", self.timml_name
        )
        return layer, self.renderer()

    def ttim_layer_from_geopackage(self):
        return None

    def assoc_layer_from_geopackage(self):
        return None

    def remove(self):
        geopackage.remove_layer(self.path, self.timml_name)


class TransientElement(ABC, Element):
    def __init__(self, path: str, name: str):
        self.name = name
        self.timml_name = (f"timml {self.elementtype}:{name}",)
        self.ttim_name = (f"ttim {self.elementtype}:{name}",)
        self.path = path
        self.timml_layer = None
        self.ttim_layer = None
        self.item = None

    def ttim_layer(self, crs: Any):
        return self.layer(crs=crs, geometry_type="No Geometry", name=self.ttim_name)

    def ttim_layer_from_geopackage(self):
        layer = QgsVectorLayer(
            f"{self.path}|layername={self.ttim_name}",
            self.ttim_name,
            self.ttim_attributes,
        )
        return layer

    def remove(self):
        geopackage.remove_layer(self.path, self.timml_name)
        geopackage.remove_layer(self.path, self.ttim_name)


class AssociatedElement(ABC, Element):
    def __init__(self, path: str, name: str):
        self.name = name
        self.timml_name = (f"timml {self.elementtype}:{name}",)
        self.assoc_name = f"timml {self.elementtype} Properties:{name}"
        self.path = path
        self.timml_layer = None
        self.assoc_name = None
        self.item = None

    def assoc_layer_from_geopackage(self):
        layer = QgsVectorLayer(
            f"{self.path}|layername={self.assoc_name}",
            self.assoc_name,
            self.assoc_attributes,
        )
        return layer

    def remove(self):
        geopackage.remove_layer(self.path, self.timml_name)
        geopackage.remove_layer(self.path, self.assoc_name)


class Domain(TransientElement):
    element_type = "Domain"
    geometry_type = "Polygon"

    def __init__(self, path: str, name: str):
        self.name = name
        self.timml_name = (f"timml {self.elementtype}",)
        self.ttim_name = (f"ttim Computation Times",)
        self.path = path
        self.timml_layer = None
        self.ttim_layer = None
        self.item = None

    def renderer() -> QgsSingleSymbolRenderer:
        """
        Results in transparent fill, with a medium thick black border line.
        """
        symbol = QgsFillSymbol.createSimple(
            {
                "color": "255,0,0,0",  # transparent
                "color_border": "#000000#",  # black
                "width_border": "0.5",
            }
        )
        return QgsSingleSymbolRenderer(symbol)

    def remove(self):
        pass


class Aquifer(TransientElement):
    element_type = "Aquifer"
    geometry_type = "No geometry"
    timml_attributes = [
        QgsField("layer", QVariant.Int),
        QgsField("resistance", QVariant.Double),
        QgsField("conductivity", QVariant.Double),
        QgsField("z_top", QVariant.Double),
        QgsField("z_bottom", QVariant.Double),
        QgsField("porosity_aquifer", QVariant.Double),
        QgsField("porosity_aquitard", QVariant.Double),
        QgsField("head_topboundary", QVariant.Double),
        QgsField("z_topboundary", QVariant.Double),
    ]
    ttim_attributes = [
        QgsField("tmin", QVariant.Double),
        QgsField("tmax", QVariant.Double),
        QgsField("tstart", QVariant.Double),
        QgsField("M", QVariant.Int),
        QgsField("starting_date", QVariant.DateTime),
    ]

    def __init__(self, path: str, name: str):
        self.name = name
        self.timml_name = (f"timml {self.elementtype}",)
        self.ttim_name = (f"ttim Temporal Properties",)
        self.path = path
        self.timml_layer = None
        self.ttim_layer = None
        self.item = None

    def remove():
        pass


class UniformFlow(Element):
    element_type = "Uniform Flow"
    geometry_type = "No geometry"
    timml_attributes = [
        QgsField("slope", QVariant.Double),
        QgsField("angle", QVariant.Double),
        QgsField("label", QVariant.String),
    ]


class Constant(Element):
    element_type = "Constant"
    geometry_type = "Point"
    timml_attributes = [
        QgsField("head", QVariant.Double),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
    ]


class Well(TransientElement):
    element_type = "Well"
    geometry_type = "Point"
    timml_attributes = [
        QgsField("discharge", QVariant.Double),
        QgsField("radius", QVariant.Double),
        QgsField("resistance", QVariant.Double),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
        QgsField("caisson_radius", QVariant.Double),
        QgsField("slug", QVariant.Bool),
        QgsField("geometry_id", QVariant.Int),
    ]
    ttim_attributes = [
        QgsField("geometry_id", QVariant.Int),
        QgsField("tstart", QVariant.Double),
        QgsField("discharge", QVariant.Double),
    ]


class HeadWell(TransientElement):
    element_type = "Head Well"
    geometry_type = "Point"
    timml_attributes = [
        QgsField("head", QVariant.Double),
        QgsField("radius", QVariant.Double),
        QgsField("resistance", QVariant.Double),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
        QgsField("geometry_id", QVariant.Int),
    ]
    ttim_attributes = [
        QgsField("geometry_id", QVariant.Int),
        QgsField("tstart", QVariant.Double),
        QgsField("head", QVariant.Double),
    ]


class HeadLineSink(TransientElement):
    element_type = "Head Line Sink"
    geometry_type = "Linestring"
    timml_attributes = [
        QgsField("head", QVariant.Double),
        QgsField("resistance", QVariant.Double),
        QgsField("width", QVariant.Double),
        QgsField("order", QVariant.Int),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
        QgsField("geometry_id", QVariant.Int),
    ]
    ttim_attributes = [
        QgsField("geometry_id", QVariant.Int),
        QgsField("tstart", QVariant.Double),
        QgsField("head", QVariant.Double),
    ]


class LineSinkDitch(TransientElement):
    element_type = "Line Sink Ditch"
    geometry_type = "Linestring"
    timml_attributes = [
        QgsField("discharge ", QVariant.Double),
        QgsField("resistance", QVariant.Double),
        QgsField("width", QVariant.Double),
        QgsField("order", QVariant.Int),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
        QgsField("geometry_id", QVariant.Int),
    ]
    ttim_attributes = [
        QgsField("geometry_id", QVariant.Int),
        QgsField("tstart", QVariant.Double),
        QgsField("discharge", QVariant.Double),
    ]


class ImpermeableLineDoublet(TransientElement):
    element_type = "Impermeable Line Doublet"
    geometry_type = "Linestring"
    timml_attributes = [
        QgsField("order", QVariant.Int),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
    ]


class LeakyLineDoublet(Element):
    element_type = "Leaky Line Doublet"
    geometry_type = "Linestring"
    timml_attributes = [
        QgsField("resistance", QVariant.Double),
        QgsField("order", QVariant.Int),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
    ]


class CircularAreaSink(TransientElement):
    element_type = "Circular Area Sink"
    geometry_type = "Polygon"
    timml_attributes = [
        QgsField("rate", QVariant.Double),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
        QgsField("geometry_id", QVariant.Int),
    ]
    ttim_attributes = [
        QgsField("geometry_id", QVariant.Int),
        QgsField("tstart", QVariant.Double),
        QgsField("rate", QVariant.Double),
    ]

    def renderer(self):
        """
        Results in transparent fill, with a thick blue border line.
        """
        symbol = QgsFillSymbol.createSimple(
            {
                "color": "255,0,0,0",  # transparent
                "color_border": "#3182bd",  # blue
                "width_border": "0.75",
            }
        )
        return QgsSingleSymbolRenderer(symbol)


class PolygonInhomogeneity(AssociatedElement):
    element_type = "Polygon Inhomogeneity"
    geometry_type = "Polygon"
    timml_attributes = [
        QgsField("geometry_id", QVariant.Int),
        QgsField("order", QVariant.Int),
        QgsField("ndegrees", QVariant.Int),
    ]
    assoc_attributes = [
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
    ]


class BuildingPit(AssociatedElement):
    element_type = "Building Pit"
    geometry_type = "Polygon"
    timml_attributes = [
        QgsField("geometry_id", QVariant.Int),
        QgsField("order", QVariant.Int),
        QgsField("ndegrees", QVariant.Int),
        QgsField("layer", QVariant.Int),
    ]
    assoc_attributes = [
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
    ]
