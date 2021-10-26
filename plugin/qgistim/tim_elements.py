"""
This module contains the classes to represent the TimML and TTim input layers.

The classes specify:
    
* The (unabbreviated) name
* The type of geometry (No geometry, point, linestring, polygon)
* The required attributes of the attribute table

They contain logic for setting up:

* Simple input, requiring a single table, e.g. Uniform Flow or Constant 
* Transient input, requiring two tables, one with geometry and steady-state
  properties, and one containing optional time series input e.g. Well, Head Line
  Sink.
* Associated input, requiring two tables, one with geometry and one with input
  for layers, e.g. Polygon Inhomogeneity or Building Pit.
  
Each element is (optionally) represented in multiple places:

* It always lives in a GeoPackage.
* While a geopackage is active within plugin, it is always represented in a
  Dataset Tree: the Dataset Tree provides a direct look at the state of the
  GeoPackage. In this tree, steady and transient input are on the same row.
  Associated input is, to potentially enable transient associated data later
  on (like a building pit with changing head top boundary).
* It can be added to the Layers Panel in QGIS. This enables a user to visualize
  and edit its data.

Some elements require specific rendering in QGIS (e.g. no fill polygons), which
are supplied by the `.renderer()` method.

The coupling of separate tables (geometry table and time series table) is only
explicit in the Dataset Tree. The only way of knowing that tables are
associated with each other is by comparing names. Names must therefore be
unique within a group of the same type of elements.
"""

import re
from collections import defaultdict
from functools import partial
from typing import Any, List, Tuple

from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsFillSymbol,
    QgsGeometry,
    QgsLineSymbol,
    QgsPointXY,
    QgsSingleSymbolRenderer,
    QgsVectorLayer,
)
from qgistim import geopackage

# These columns are reused by Aquifer and Polygon Inhom, Building pit
# Aquitards are on top of the aquifer, so it comes first
AQUIFER_ATTRIBUTES = [
    QgsField("layer", QVariant.Int),
    QgsField("aquitard_c", QVariant.Double),
    QgsField("aquitard_npor", QVariant.Double),
    QgsField("aquitard_s", QVariant.Double),
    QgsField("aquifer_k", QVariant.Double),
    QgsField("aquifer_npor", QVariant.Double),
    QgsField("aquifer_s", QVariant.Double),
    QgsField("aquifer_top", QVariant.Double),
    QgsField("aquifer_bottom", QVariant.Double),
    QgsField("semiconf_top", QVariant.Double),
    QgsField("semiconf_head", QVariant.Double),
]
INHOM_ATTRIBUTES = [
    QgsField("geometry_id", QVariant.Int),
] + AQUIFER_ATTRIBUTES


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


class RadiusDialog(QDialog):
    def __init__(self, parent=None):
        super(RadiusDialog, self).__init__(parent)
        self.name_line_edit = QLineEdit()
        self.radius_line_edit = QLineEdit()
        self.radius_line_edit.setValidator(QDoubleValidator())
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        first_row = QHBoxLayout()
        first_row.addWidget(QLabel("Layer name"))
        first_row.addWidget(self.name_line_edit)
        second_row = QHBoxLayout()
        second_row.addWidget(QLabel("Radius"))
        second_row.addWidget(self.radius_line_edit)
        third_row = QHBoxLayout()
        third_row.addStretch()
        third_row.addWidget(self.ok_button)
        third_row.addWidget(self.cancel_button)
        layout = QVBoxLayout()
        layout.addLayout(first_row)
        layout.addLayout(second_row)
        layout.addLayout(third_row)
        self.setLayout(layout)


class Element:
    element_type = None
    geometry_type = None
    timml_attributes = []
    ttim_attributes = []
    assoc_attributes = []

    def _initialize_default(self, path, name):
        self.name = name
        self.path = path
        self.timml_name = None
        self.ttim_name = None
        self.assoc_name = None
        self.timml_layer = None
        self.ttim_layer = None
        self.assoc_layer = None
        self.item = None

    def __init__(self, path: str, name: str):
        self._initialize(path, name)
        self.timml_name = f"timml {self.element_type}:{name}"

    @staticmethod
    def dialog(
        path: str, crs: Any, iface: Any, klass: type, names: List[str]
    ) -> Tuple[Any]:
        dialog = NameDialog()
        dialog.show()
        ok = dialog.exec_()
        if not ok:
            return

        name = dialog.name_line_edit.text()
        if name in names:
            raise ValueError(f"Name already exists in geopackage: {name}")

        instance = klass(path, name)
        instance.create_layers(crs)
        return instance

    def layer(self, crs: Any, geometry_type: str, name: str, attributes: List):
        layer = QgsVectorLayer(geometry_type, name, "memory")
        provider = layer.dataProvider()
        provider.addAttributes(attributes)
        layer.updateFields()
        layer.setCrs(crs)
        return layer

    def create_timml_layer(self, crs: Any):
        self.timml_layer = self.layer(
            crs=crs,
            geometry_type=self.geometry_type,
            name=self.timml_name,
            attributes=self.timml_attributes,
        )

    def create_ttim_layer(self, crs: Any):
        pass

    def create_assoc_layer(self, crs: Any):
        pass

    def create_layers(self, crs: Any):
        self.create_timml_layer(crs)
        self.create_ttim_layer(crs)
        self.create_assoc_layer(crs)

    def renderer(self):
        return None

    def timml_layer_from_geopackage(self) -> QgsVectorLayer:
        self.timml_layer = QgsVectorLayer(
            f"{self.path}|layername={self.timml_name}", self.timml_name
        )

    def ttim_layer_from_geopackage(self):
        pass

    def assoc_layer_from_geopackage(self):
        pass

    def from_geopackage(self):
        self.timml_layer_from_geopackage()
        self.ttim_layer_from_geopackage()
        self.assoc_layer_from_geopackage()
        return [
            (self.timml_layer, self.renderer()),
            (self.ttim_layer, None),
            (self.assoc_layer, None),
        ]

    def write(self):
        self.timml_layer = geopackage.write_layer(
            self.path, self.timml_layer, self.timml_name
        )

    def remove_from_geopackage(self):
        geopackage.remove_layer(self.path, self.timml_name)


class TransientElement(Element):
    def __init__(self, path: str, name: str):
        self._initialize(path, name)
        self.timml_name = f"timml {self.element_type}:{name}"
        self.ttim_name = f"ttim {self.element_type}:{name}"

    def create_ttim_layer(self, crs: Any):
        self.ttim_layer = self.layer(
            crs=crs,
            geometry_type="No Geometry",
            name=self.ttim_name,
            attributes=self.ttim_attributes,
        )

    def ttim_layer_from_geopackage(self):
        self.ttim_layer = QgsVectorLayer(
            f"{self.path}|layername={self.ttim_name}",
            self.ttim_name,
        )

    def write(self):
        self.timml_layer = geopackage.write_layer(
            self.path, self.timml_layer, self.timml_name
        )
        self.ttim_layer = geopackage.write_layer(
            self.path, self.ttim_layer, self.ttim_name
        )

    def remove_from_geopackage(self):
        geopackage.remove_layer(self.path, self.timml_name)
        geopackage.remove_layer(self.path, self.ttim_name)


class AssociatedElement(Element):
    def __init__(self, path: str, name: str):
        self._initialize(path, name)
        self.timml_name = f"timml {self.element_type}:{name}"
        self.assoc_name = f"timml {self.element_type} Properties:{name}"

    def create_assoc_layer(self, crs: Any):
        self.assoc_layer = self.layer(
            crs=crs,
            geometry_type="No Geometry",
            name=self.assoc_name,
            attributes=self.assoc_attributes,
        )

    def assoc_layer_from_geopackage(self):
        self.assoc_layer = QgsVectorLayer(
            f"{self.path}|layername={self.assoc_name}",
            self.assoc_name,
        )

    def write(self):
        self.timml_layer = geopackage.write_layer(
            self.path, self.timml_layer, self.timml_name
        )
        self.assoc_layer = geopackage.write_layer(
            self.path, self.assoc_layer, self.assoc_name
        )

    def remove_from_geopackage(self):
        geopackage.remove_layer(self.path, self.timml_name)
        geopackage.remove_layer(self.path, self.assoc_name)


class Domain(TransientElement):
    def _initialize(self, path, name):
        self._initialize_default(path, name)
        self.element_type = "Domain"
        self.geometry_type = "Polygon"
        self.ttim_attributes = [
            QgsField("time", QVariant.Double),
        ]

    def __init__(self, path: str, name: str):
        self._initialize(path, name)
        self.timml_name = f"timml {self.element_type}:Domain"
        self.ttim_name = f"ttim Computation Times:Domain"

    def renderer(self) -> QgsSingleSymbolRenderer:
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

    def remove_from_geopackage(self):
        pass

    def update_extent(self, iface: Any) -> Tuple[float, float]:
        provider = self.timml_layer.dataProvider()
        provider.truncate()  # removes all features
        canvas = iface.mapCanvas()
        extent = canvas.extent()
        xmin = extent.xMinimum()
        ymin = extent.yMinimum()
        xmax = extent.xMaximum()
        ymax = extent.yMaximum()
        points = [
            QgsPointXY(xmin, ymax),
            QgsPointXY(xmax, ymax),
            QgsPointXY(xmax, ymin),
            QgsPointXY(xmin, ymin),
        ]
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPolygonXY([points]))
        provider.addFeatures([feature])
        canvas.refresh()
        return ymax, ymin


class Aquifer(TransientElement):
    def _initialize(self, path, name):
        self._initialize_default(path, name)
        self.name = "Aquifer"
        self.element_type = "Aquifer"
        self.geometry_type = "No geometry"
        self.timml_attributes = AQUIFER_ATTRIBUTES.copy()
        self.ttim_attributes = [
            QgsField("tmin", QVariant.Double),
            QgsField("tmax", QVariant.Double),
            QgsField("tstart", QVariant.Double),
            QgsField("M", QVariant.Int),
            QgsField("reference_date", QVariant.DateTime),
        ]

    def __init__(self, path: str, name: str):
        self._initialize(path, name)
        self.timml_name = f"timml {self.element_type}:Aquifer"
        self.ttim_name = f"ttim Temporal Settings:Aquifer"

    def write(self):
        self.timml_layer = geopackage.write_layer(
            self.path, self.timml_layer, self.timml_name, newfile=True
        )
        self.ttim_layer = geopackage.write_layer(
            self.path, self.ttim_layer, self.ttim_name
        )

    def remove_from_geopackage(self):
        pass


class UniformFlow(Element):
    def _initialize(self, path, name):
        self._initialize_default(path, name)
        self.element_type = "Uniform Flow"
        self.geometry_type = "No geometry"
        self.timml_attributes = [
            QgsField("slope", QVariant.Double),
            QgsField("angle", QVariant.Double),
            QgsField("label", QVariant.String),
        ]


class Constant(Element):
    def _initialize(self, path, name):
        self._initialize_default(path, name)
        self.element_type = "Constant"
        self.geometry_type = "Point"
        self.timml_attributes = [
            QgsField("head", QVariant.Double),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
        ]


class Well(TransientElement):
    def _initialize(self, path, name):
        self._initialize_default(path, name)
        self.element_type = "Well"
        self.geometry_type = "Point"
        self.timml_attributes = [
            QgsField("discharge", QVariant.Double),
            QgsField("radius", QVariant.Double),
            QgsField("resistance", QVariant.Double),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
            QgsField("caisson_radius", QVariant.Double),
            QgsField("slug", QVariant.Bool),
            QgsField("geometry_id", QVariant.Int),
        ]
        self.ttim_attributes = [
            QgsField("geometry_id", QVariant.Int),
            QgsField("tstart", QVariant.Double),
            QgsField("discharge", QVariant.Double),
        ]


class HeadWell(TransientElement):
    def _initialize(self, path, name):
        self._initialize_default(path, name)
        self.element_type = "Head Well"
        self.geometry_type = "Point"
        self.timml_attributes = [
            QgsField("head", QVariant.Double),
            QgsField("radius", QVariant.Double),
            QgsField("resistance", QVariant.Double),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
            QgsField("geometry_id", QVariant.Int),
        ]
        self.ttim_attributes = [
            QgsField("geometry_id", QVariant.Int),
            QgsField("tstart", QVariant.Double),
            QgsField("head", QVariant.Double),
        ]


class HeadLineSink(TransientElement):
    def _initialize(self, path, name):
        self._initialize_default(path, name)
        self.element_type = "Head Line Sink"
        self.geometry_type = "Linestring"
        self.timml_attributes = [
            QgsField("head", QVariant.Double),
            QgsField("resistance", QVariant.Double),
            QgsField("width", QVariant.Double),
            QgsField("order", QVariant.Int),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
            QgsField("geometry_id", QVariant.Int),
        ]
        self.ttim_attributes = [
            QgsField("geometry_id", QVariant.Int),
            QgsField("tstart", QVariant.Double),
            QgsField("head", QVariant.Double),
        ]

    def renderer(self) -> QgsSingleSymbolRenderer:
        symbol = QgsLineSymbol.createSimple(
            {
                "color": "#3690c0",  # lighter blue
                "width": "0.5",
            }
        )
        return QgsSingleSymbolRenderer(symbol)


class LineSinkDitch(TransientElement):
    def _initialize(self, path, name):
        self._initialize_default(path, name)
        self.element_type = "Line Sink Ditch"
        self.geometry_type = "Linestring"
        self.timml_attributes = [
            QgsField("discharge ", QVariant.Double),
            QgsField("resistance", QVariant.Double),
            QgsField("width", QVariant.Double),
            QgsField("order", QVariant.Int),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
            QgsField("geometry_id", QVariant.Int),
        ]
        self.ttim_attributes = [
            QgsField("geometry_id", QVariant.Int),
            QgsField("tstart", QVariant.Double),
            QgsField("discharge", QVariant.Double),
        ]

    def renderer(self) -> QgsSingleSymbolRenderer:
        symbol = QgsLineSymbol.createSimple(
            {
                "color": "#034e7b",  # blue
                "width": "0.5",
            }
        )
        return QgsSingleSymbolRenderer(symbol)


class ImpermeableLineDoublet(Element):
    def _initialize(self, path, name):
        self._initialize_default(path, name)
        self.element_type = "Impermeable Line Doublet"
        self.geometry_type = "Linestring"
        self.timml_attributes = [
            QgsField("order", QVariant.Int),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
        ]

    def renderer(self) -> QgsSingleSymbolRenderer:
        symbol = QgsLineSymbol.createSimple(
            {
                "color": "#993404",  # dark orange / brown
                "width": "0.5",
            }
        )
        return QgsSingleSymbolRenderer(symbol)


class LeakyLineDoublet(Element):
    def _initialize(self, path, name):
        self._initialize_default(path, name)
        self.element_type = "Leaky Line Doublet"
        self.geometry_type = "Linestring"
        self.timml_attributes = [
            QgsField("resistance", QVariant.Double),
            QgsField("order", QVariant.Int),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
        ]

    def renderer(self) -> QgsSingleSymbolRenderer:
        symbol = QgsLineSymbol.createSimple(
            {
                "color": "#ec7014",  # orange
                "width": "0.5",
            }
        )
        return QgsSingleSymbolRenderer(symbol)


class CircularAreaSink(TransientElement):
    def _initialize(self, path, name):
        self._initialize_default(path, name)
        self.element_type = "Circular Area Sink"
        self.geometry_type = "Polygon"
        self.timml_attributes = [
            QgsField("rate", QVariant.Double),
            QgsField("layer", QVariant.Int),
            QgsField("label", QVariant.String),
            QgsField("geometry_id", QVariant.Int),
        ]
        self.ttim_attributes = [
            QgsField("geometry_id", QVariant.Int),
            QgsField("tstart", QVariant.Double),
            QgsField("rate", QVariant.Double),
        ]

    @staticmethod
    def dialog(
        path: str, crs: Any, iface: Any, klass: type, names: List[str]
    ) -> Tuple[Any]:
        dialog = RadiusDialog()
        dialog.show()
        ok = dialog.exec_()
        if not ok:
            return

        name = dialog.name_line_edit.text()
        if name in names:
            raise ValueError(f"Name already exists in geopackage: {name}")

        radius = float(dialog.radius_line_edit.text())
        instance = klass(path, name)
        instance.create_layers(crs)
        provider = instance.timml_layer.dataProvider()
        feature = QgsFeature()
        center = iface.mapCanvas().center()
        feature.setGeometry(QgsGeometry.fromPointXY(center).buffer(radius, 5))
        provider.addFeatures([feature])
        instance.timml_layer.updateFields()

        return instance

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
    def _initialize(self, path, name):
        self._initialize_default(path, name)
        self.element_type = "Polygon Inhomogeneity"
        self.geometry_type = "Polygon"
        self.timml_attributes = [
            QgsField("geometry_id", QVariant.Int),
            QgsField("order", QVariant.Int),
            QgsField("ndegrees", QVariant.Int),
        ]
        self.assoc_attributes = INHOM_ATTRIBUTES.copy()

    def renderer(self) -> QgsSingleSymbolRenderer:
        symbol = QgsFillSymbol.createSimple(
            {
                "color": "255,0,0,0",  # transparent
                "color_border": "#878787",  # grey
                "width_border": "0.75",
            }
        )
        return QgsSingleSymbolRenderer(symbol)


class BuildingPit(AssociatedElement):
    def _initialize(self, path, name):
        self._initialize_default(path, name)
        self.element_type = "Building Pit"
        self.geometry_type = "Polygon"
        self.timml_attributes = [
            QgsField("geometry_id", QVariant.Int),
            QgsField("order", QVariant.Int),
            QgsField("ndegrees", QVariant.Int),
            QgsField("layer", QVariant.Int),
        ]
        self.assoc_attributes = INHOM_ATTRIBUTES.copy()

    def renderer(self) -> QgsSingleSymbolRenderer:
        symbol = QgsFillSymbol.createSimple(
            {
                "color": "255,0,0,0",  # transparent
                "color_border": "#d73027",  # red
                "width_border": "0.5",
            }
        )
        return QgsSingleSymbolRenderer(symbol)


ELEMENTS = {
    "Aquifer": Aquifer,
    "Domain": Domain,
    "Constant": Constant,
    "Uniform Flow": UniformFlow,
    "Well": Well,
    "Head Well": HeadWell,
    "Head Line Sink": HeadLineSink,
    "Line Sink Ditch": LineSinkDitch,
    "Circular Area Sink": CircularAreaSink,
    "Impermeable Line Doublet": ImpermeableLineDoublet,
    "Leaky Line Doublet": LeakyLineDoublet,
    "Polygon Inhomogeneity": PolygonInhomogeneity,
    "Building Pit": BuildingPit,
}


def parse_name(layername: str) -> Tuple[str, str]:
    prefix, name = layername.split(":")
    element_type = re.split("timml |ttim ", prefix)[1]
    mapping = {
        "Computation Times": "Domain",
        "Temporal Settings": "Aquifer",
        "Polygon Inhomogeneity Properties": "Polygon Inhomogeneity",
        "Building Pit Properties": "Building Pit",
    }
    element_type = mapping.get(element_type, element_type)
    if "timml" in prefix:
        if "Properties" in prefix:
            tim_type = "timml_assoc"
        else:
            tim_type = "timml"
    elif "ttim" in prefix:
        tim_type = "ttim"
    else:
        raise ValueError("Neither timml nor ttim in layername")
    return tim_type, element_type, name


def load_elements_from_geopackage(path: str) -> List[Element]:
    gpkg_names = geopackage.layers(path)
    dd = defaultdict
    grouped_names = dd(partial(dd, partial(dd, list)))
    for layername in gpkg_names:
        tim_type, element_type, name = parse_name(layername)
        grouped_names[element_type][name][tim_type] = layername
    elements = []
    for element_type, group in grouped_names.items():
        for name in group:
            elements.append(ELEMENTS[element_type](path, name))
    return elements
