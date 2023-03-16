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
are supplied by the `.renderer` property.

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
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)
from qgis.core import (
    QgsDefaultValue,
    QgsFeature,
    QgsField,
    QgsFillSymbol,
    QgsGeometry,
    QgsLineSymbol,
    QgsPointXY,
    QgsSingleSymbolRenderer,
    QgsVectorLayer,
)
from qgistim.core import geopackage

# These columns are reused by Aquifer and Polygon Inhom, Building pit Aquitards
# are on top of the aquifer, so it comes first Nota bene: the order of these is
# important for hiding and showing the transient columns. QGIS has a bug which
# causes it to show the wrong column if hidden columns appear before shown
# ones. This only affects the attribute table when it has no features.
AQUIFER_ATTRIBUTES = [
    QgsField("layer", QVariant.Int),
    QgsField("aquifer_top", QVariant.Double),
    QgsField("aquifer_bottom", QVariant.Double),
    QgsField("aquitard_c", QVariant.Double),
    QgsField("aquifer_k", QVariant.Double),
    QgsField("semiconf_top", QVariant.Double),
    QgsField("semiconf_head", QVariant.Double),
    QgsField("aquitard_s", QVariant.Double),
    QgsField("aquifer_s", QVariant.Double),
    QgsField("aquitard_npor", QVariant.Double),
    QgsField("aquifer_npor", QVariant.Double),
]
INHOM_ATTRIBUTES = [
    QgsField("inhomogeneity_id", QVariant.Int),
] + AQUIFER_ATTRIBUTES


class NameDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
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


class Element:
    """
    Abstract base class for "ordinary" timml elements.
    """

    element_type = None
    geometry_type = None
    timml_attributes = ()
    ttim_attributes = ()
    assoc_attributes = ()
    transient_columns = ()
    timml_defaults = {}
    ttim_defaults = {}
    assoc_defaults = {}

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
        self._initialize_default(path, name)
        self.timml_name = f"timml {self.element_type}:{name}"

    @classmethod
    def dialog(cls, path: str, crs: Any, iface: Any, names: List[str]):
        dialog = NameDialog()
        dialog.show()
        ok = dialog.exec_()
        if not ok:
            return

        name = dialog.name_line_edit.text()
        if name in names:
            raise ValueError(f"Name already exists in geopackage: {name}")

        instance = cls(path, name)
        instance.create_layers(crs)
        return instance

    def create_layer(
        self, crs: Any, geometry_type: str, name: str, attributes: List
    ) -> QgsVectorLayer:
        layer = QgsVectorLayer(geometry_type, name, "memory")
        provider = layer.dataProvider()
        provider.addAttributes(attributes)
        layer.updateFields()
        layer.setCrs(crs)
        return layer

    def create_timml_layer(self, crs: Any):
        self.timml_layer = self.create_layer(
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

    def set_defaults(self):
        for layer, defaults in zip(
            (self.timml_layer, self.ttim_layer, self.assoc_layer),
            (self.timml_defaults, self.ttim_defaults, self.assoc_defaults),
        ):
            if layer is None:
                continue
            fields = layer.fields()
            for name, definition in defaults.items():
                index = fields.indexFromName(name)
                layer.setDefaultValueDefinition(index, definition)
        return

    @property
    def renderer(self):
        return None

    def timml_layer_from_geopackage(self) -> QgsVectorLayer:
        self.timml_layer = QgsVectorLayer(
            f"{self.path}|layername={self.timml_name}", self.timml_name
        )

    def ttim_layer_from_geopackage(self):
        return

    def assoc_layer_from_geopackage(self):
        return

    def load_layers_from_geopackage(self) -> None:
        self.timml_layer_from_geopackage()
        self.ttim_layer_from_geopackage()
        self.assoc_layer_from_geopackage()
        self.set_defaults()
        return

    def write(self):
        self.timml_layer = geopackage.write_layer(
            self.path, self.timml_layer, self.timml_name
        )
        self.set_defaults()

    def remove_from_geopackage(self):
        geopackage.remove_layer(self.path, self.timml_name)

    def on_transient_changed(self, transient: bool):
        if len(self.transient_columns) == 0:
            return

        config = self.timml_layer.attributeTableConfig()
        columns = config.columns()

        for i, column in enumerate(columns):
            if column.name in self.transient_columns:
                config.setColumnHidden(i, not transient)

        self.timml_layer.setAttributeTableConfig(config)
        return


class TransientElement(Element):
    """
    Abstract base class for transient (ttim) elements.
    """

    def __init__(self, path: str, name: str):
        self._initialize_default(path, name)
        self.timml_name = f"timml {self.element_type}:{name}"
        self.ttim_name = f"ttim {self.element_type}:{name}"

    def create_ttim_layer(self, crs: Any):
        self.ttim_layer = self.create_layer(
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
        self.set_defaults()

    def remove_from_geopackage(self):
        geopackage.remove_layer(self.path, self.timml_name)
        geopackage.remove_layer(self.path, self.ttim_name)


class AssociatedElement(Element):
    """
    Abstract class for elements that require associated tables such as
    Inhomogenities.
    """

    def __init__(self, path: str, name: str):
        self._initialize_default(path, name)
        self.timml_name = f"timml {self.element_type}:{name}"
        self.assoc_name = f"timml {self.element_type} Properties:{name}"

    def create_assoc_layer(self, crs: Any):
        self.assoc_layer = self.create_layer(
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
        self.set_defaults()

    def remove_from_geopackage(self):
        geopackage.remove_layer(self.path, self.timml_name)
        geopackage.remove_layer(self.path, self.assoc_name)


class Domain(TransientElement):
    element_type = "Domain"
    geometry_type = "Polygon"
    ttim_attributes = (QgsField("time", QVariant.Double),)

    def __init__(self, path: str, name: str):
        self._initialize_default(path, name)
        self.timml_name = f"timml {self.element_type}:Domain"
        self.ttim_name = "ttim Computation Times:Domain"

    @property
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
    element_type = "Aquifer"
    geometry_type = "No Geometry"
    timml_attributes = AQUIFER_ATTRIBUTES.copy()
    ttim_attributes = (
        QgsField("time_min", QVariant.Double),
        QgsField("time_max", QVariant.Double),
        QgsField("time_start", QVariant.Double),
        QgsField("stehfest_M", QVariant.Int),
        QgsField("reference_date", QVariant.DateTime),
    )
    ttim_defaults = {
        "time_min": QgsDefaultValue("0.01"),
        "time_max": QgsDefaultValue("10.0"),
        "time_start": QgsDefaultValue("0.0"),
        "stehfest_M": QgsDefaultValue("10"),
    }
    transient_columns = (
        "aquitard_s",
        "aquifer_s",
        "aquitard_npor",
        "aquifer_npor",
    )

    def __init__(self, path: str, name: str):
        self._initialize_default(path, name)
        self.timml_name = f"timml {self.element_type}:Aquifer"
        self.ttim_name = "ttim Temporal Settings:Aquifer"

    def write(self):
        self.timml_layer = geopackage.write_layer(
            self.path, self.timml_layer, self.timml_name, newfile=True
        )
        self.ttim_layer = geopackage.write_layer(
            self.path, self.ttim_layer, self.ttim_name
        )
        self.set_defaults()

    def remove_from_geopackage(self):
        """This element may not be removed."""
        return


class UniformFlow(Element):
    element_type = "Uniform Flow"
    geometry_type = "No geometry"
    timml_attributes = (
        QgsField("slope", QVariant.Double),
        QgsField("angle", QVariant.Double),
        QgsField("label", QVariant.String),
    )


class Constant(Element):
    element_type = "Constant"
    geometry_type = "Point"
    timml_attributes = (
        QgsField("head", QVariant.Double),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
    )


class Observation(TransientElement):
    element_type = "Observation"
    geometry_type = "Point"
    timml_attributes = (
        QgsField("label", QVariant.String),
        QgsField("timeseries_id", QVariant.Int),
    )
    ttim_attributes = (
        QgsField("timeseries_id", QVariant.Int),
        QgsField("time", QVariant.Double),
    )
    timml_defaults = {
        "timeseries_id": QgsDefaultValue("1"),
    }
    ttim_defaults = {
        "timeseries_id": QgsDefaultValue("1"),
    }
    transient_columns = ("timeseries_id",)


class Well(TransientElement):
    element_type = "Well"
    geometry_type = "Point"
    timml_attributes = (
        QgsField("discharge", QVariant.Double),
        QgsField("radius", QVariant.Double),
        QgsField("resistance", QVariant.Double),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
        QgsField("time_start", QVariant.Double),
        QgsField("time_end", QVariant.Double),
        QgsField("discharge_transient", QVariant.Double),
        QgsField("caisson_radius", QVariant.Double),
        QgsField("slug", QVariant.Bool),
        QgsField("timeseries_id", QVariant.Int),
    )
    ttim_attributes = (
        QgsField("timeseries_id", QVariant.Int),
        QgsField("time_start", QVariant.Double),
        QgsField("discharge", QVariant.Double),
    )
    transient_columns = (
        "time_start",
        "time_end",
        "discharge_transient",
        "caisson_radius",
        "slug",
        "timeseries_id",
    )


class HeadWell(TransientElement):
    element_type = "Head Well"
    geometry_type = "Point"
    timml_attributes = (
        QgsField("head", QVariant.Double),
        QgsField("radius", QVariant.Double),
        QgsField("resistance", QVariant.Double),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
        QgsField("time_start", QVariant.Double),
        QgsField("time_end", QVariant.Double),
        QgsField("head_transient", QVariant.Double),
        QgsField("timeseries_id", QVariant.Int),
    )
    ttim_attributes = (
        QgsField("timeseries_id", QVariant.Int),
        QgsField("time_start", QVariant.Double),
        QgsField("head", QVariant.Double),
    )
    transient_columns = (
        "time_start",
        "time_end",
        "head_transient",
        "timeseries_id",
    )


class HeadLineSink(TransientElement):
    element_type = "Head Line Sink"
    geometry_type = "Linestring"
    timml_attributes = (
        QgsField("head", QVariant.Double),
        QgsField("resistance", QVariant.Double),
        QgsField("width", QVariant.Double),
        QgsField("order", QVariant.Int),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
        QgsField("time_start", QVariant.Double),
        QgsField("time_end", QVariant.Double),
        QgsField("head_transient", QVariant.Double),
        QgsField("timeseries_id", QVariant.Int),
    )
    ttim_attributes = (
        QgsField("timeseries_id", QVariant.Int),
        QgsField("time_start", QVariant.Double),
        QgsField("head", QVariant.Double),
    )
    timml_defaults = {
        "order": QgsDefaultValue("4"),
    }
    transient_columns = (
        "time_start",
        "time_end",
        "head_transient",
        "timeseries_id",
    )

    @property
    def renderer(self) -> QgsSingleSymbolRenderer:
        symbol = QgsLineSymbol.createSimple(
            {
                "color": "#3690c0",  # lighter blue
                "width": "0.5",
            }
        )
        return QgsSingleSymbolRenderer(symbol)


class LineSinkDitch(TransientElement):
    element_type = "Line Sink Ditch"
    geometry_type = "Linestring"
    timml_attributes = (
        QgsField("discharge", QVariant.Double),
        QgsField("resistance", QVariant.Double),
        QgsField("width", QVariant.Double),
        QgsField("order", QVariant.Int),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
        QgsField("time_start", QVariant.Double),
        QgsField("time_end", QVariant.Double),
        QgsField("discharge_transient", QVariant.Double),
        QgsField("timeseries_id", QVariant.Int),
    )
    ttim_attributes = (
        QgsField("timeseries_id", QVariant.Int),
        QgsField("time_start", QVariant.Double),
        QgsField("discharge", QVariant.Double),
    )
    timml_defaults = {
        "order": QgsDefaultValue("4"),
    }
    transient_columns = (
        "time_start",
        "time_end",
        "discharge_transient",
        "timeseries_id",
    )

    @property
    def renderer(self) -> QgsSingleSymbolRenderer:
        symbol = QgsLineSymbol.createSimple(
            {
                "color": "#034e7b",  # blue
                "width": "0.5",
            }
        )
        return QgsSingleSymbolRenderer(symbol)


class ImpermeableLineDoublet(Element):
    element_type = "Impermeable Line Doublet"
    geometry_type = "Linestring"
    timml_attributes = (
        QgsField("order", QVariant.Int),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
    )
    timml_defaults = {
        "order": QgsDefaultValue("4"),
    }

    @property
    def renderer(self) -> QgsSingleSymbolRenderer:
        symbol = QgsLineSymbol.createSimple(
            {
                "color": "#993404",  # dark orange / brown
                "width": "0.5",
            }
        )
        return QgsSingleSymbolRenderer(symbol)


class LeakyLineDoublet(Element):
    element_type = "Leaky Line Doublet"
    geometry_type = "Linestring"
    timml_attributes = (
        QgsField("resistance", QVariant.Double),
        QgsField("order", QVariant.Int),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
    )
    timml_defaults = {
        "order": QgsDefaultValue("4"),
    }

    @property
    def renderer(self) -> QgsSingleSymbolRenderer:
        symbol = QgsLineSymbol.createSimple(
            {
                "color": "#ec7014",  # orange
                "width": "0.5",
            }
        )
        return QgsSingleSymbolRenderer(symbol)


class CircularAreaSink(TransientElement):
    element_type = "Circular Area Sink"
    geometry_type = "Polygon"
    timml_attributes = (
        QgsField("rate", QVariant.Double),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
        QgsField("time_start", QVariant.Double),
        QgsField("time_end", QVariant.Double),
        QgsField("rate_transient", QVariant.Double),
        QgsField("timeseries_id", QVariant.Int),
    )
    ttim_attributes = (
        QgsField("timeseries_id", QVariant.Int),
        QgsField("time_start", QVariant.Double),
        QgsField("rate", QVariant.Double),
    )
    transient_columns = (
        "time_start",
        "time_end",
        "rate_transient",
        "timeseries_id",
    )

    @property
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


class PolygonSemiConfinedTop(Element):
    element_type = "Polygon Semi-Confined Top"
    geometry_type = "Polygon"
    timml_attributes = (
        QgsField("aquitard_c", QVariant.Double),
        QgsField("semiconf_top", QVariant.Double),
        QgsField("semiconf_head", QVariant.Double),
        QgsField("order", QVariant.Int),
        QgsField("ndegrees", QVariant.Int),
    )
    assoc_attributes = INHOM_ATTRIBUTES.copy()
    timml_defaults = {
        "order": QgsDefaultValue("4"),
        "ndegrees": QgsDefaultValue("6"),
    }

    @property
    def renderer(self) -> QgsSingleSymbolRenderer:
        symbol = QgsFillSymbol.createSimple(
            {
                "color": "255,0,0,0",  # transparent
                "color_border": "#878787",  # grey
                "width_border": "0.75",
            }
        )
        return QgsSingleSymbolRenderer(symbol)


class PolygonAreaSink(Element):
    element_type = "Polygon Area Sink"
    geometry_type = "Polygon"
    timml_attributes = (
        QgsField("phreatic_top", QVariant.Int),
        QgsField("phreatic_head", QVariant.Int),
        QgsField("order", QVariant.Int),
        QgsField("ndegrees", QVariant.Int),
    )
    assoc_attributes = INHOM_ATTRIBUTES.copy()
    timml_defaults = {
        "order": QgsDefaultValue("4"),
        "ndegrees": QgsDefaultValue("6"),
    }

    @property
    def renderer(self) -> QgsSingleSymbolRenderer:
        symbol = QgsFillSymbol.createSimple(
            {
                "color": "255,0,0,0",  # transparent
                "color_border": "#034e7b",  # blue
                "width_border": "0.75",
            }
        )
        return QgsSingleSymbolRenderer(symbol)


class PolygonInhomogeneity(AssociatedElement):
    element_type = "Polygon Inhomogeneity"
    geometry_type = "Polygon"
    timml_attributes = (
        QgsField("inhomogeneity_id", QVariant.Int),
        QgsField("order", QVariant.Int),
        QgsField("ndegrees", QVariant.Int),
    )
    assoc_attributes = INHOM_ATTRIBUTES.copy()
    timml_defaults = {
        "order": QgsDefaultValue("4"),
        "ndegrees": QgsDefaultValue("6"),
    }

    @property
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
    element_type = "Building Pit"
    geometry_type = "Polygon"
    timml_attributes = (
        QgsField("timeseries_id", QVariant.Int),
        QgsField("order", QVariant.Int),
        QgsField("ndegrees", QVariant.Int),
        QgsField("layer", QVariant.Int),
    )
    assoc_attributes = INHOM_ATTRIBUTES.copy()

    @property
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
    element.element_type: element
    for element in (
        Aquifer,
        Domain,
        Constant,
        UniformFlow,
        Well,
        HeadWell,
        HeadLineSink,
        LineSinkDitch,
        CircularAreaSink,
        ImpermeableLineDoublet,
        LeakyLineDoublet,
        # PolygonAreaSink,  # not in pypi release yet
        PolygonSemiConfinedTop,
        PolygonInhomogeneity,
        BuildingPit,
        Observation,
    )
}


def parse_name(layername: str) -> Tuple[str, str, str]:
    """
    Based on the layer name find out:

    * whether it's a timml or ttim element;
    * which element type it is;
    * what the user provided name is.

    For example:
    parse_name("timml Headwell: drainage") -> ("timml", "Head Well", "drainage")

    This function can also be found in gistim.common
    """
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
    # List the names in the geopackage
    gpkg_names = geopackage.layers(path)

    # Group them on the basis of name
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
