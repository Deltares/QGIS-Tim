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

Rendering:

* Fixed discharge (area sink, well, ditch): green
* Fixed head (head well, semi-confined top, head line): blue
* Inhomogeneity: grey
* Constant: star
* Observations: triangle
* Line Doublets: red
* Polygons: Line and Fill same color, Fill color 15% opacity.

Nota bene: the order of the columns is important for hiding and showing the
transient columns. QGIS has a bug which causes it to show the wrong column if
hidden columns appear before shown ones. This only affects the attribute table
when it has no features.
"""

import abc
from collections import defaultdict
from copy import deepcopy
from typing import Any, Dict, List, Tuple, Union

from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)
from qgis.core import (
    QgsFillSymbol,
    QgsLineSymbol,
    QgsMarkerSymbol,
    QgsSingleSymbolRenderer,
    QgsVectorLayer,
)
from qgistim.core import geopackage
from qgistim.core.extractor import ExtractorMixin
from qgistim.core.schemata import (
    ConsistencySchema,
    IterableSchemaContainer,
    SchemaContainer,
)


class ElementSchema(abc.ABC):
    # TODO: check for presence of columns
    timml_schemata: Dict[str, Union[SchemaContainer, IterableSchemaContainer]] = {}
    timml_consistency_schemata: Tuple[ConsistencySchema] = ()
    ttim_schemata: Dict[str, Union[SchemaContainer, IterableSchemaContainer]] = {}
    ttim_consistency_schemata: Tuple[ConsistencySchema] = ()
    timeseries_schemata: Dict[str, Union[SchemaContainer, IterableSchemaContainer]] = {}

    @staticmethod
    def _validate_rows(schemata, consistency_schemata, data, other=None):
        errors = defaultdict(list)

        for schema in consistency_schemata:
            _error = schema.validate(data, other)
            if _error:
                errors["Table:"].append(_error)

        for i, row in enumerate(data):
            row_errors = defaultdict(list)
            for variable, schema in schemata.items():
                _errors = schema.validate(row[variable], other)
                if _errors:
                    row_errors[variable].extend(_errors)

            if row_errors:
                errors[f"Row {i + 1}:"] = row_errors

        return errors

    @staticmethod
    def _validate_table(schemata, consistency_schemata, data, other=None):
        if len(data) == 0:
            return {"Table:": ["Table is empty."]}

        errors = defaultdict(list)
        for variable, schema in schemata.items():
            _errors = schema.validate(data[variable], other)
            if _errors:
                errors[variable].extend(_errors)

        # The consistency schema rely on the row input being valid.
        # Hence, they are tested second.
        if not errors:
            for schema in consistency_schemata:
                _error = schema.validate(data, other)
                if _error:
                    errors["Table:"].append(_error)

        return errors

    @classmethod
    def _validate(
        cls, schemata, consistency_schemata, data, other=None
    ) -> Dict[str, Any]:
        if isinstance(data, list):
            return cls._validate_rows(schemata, consistency_schemata, data, other)
        elif isinstance(data, dict):
            return cls._validate_table(schemata, consistency_schemata, data, other)
        else:
            raise TypeError(
                f"Data should be list or dict, received: {type(data).__name__}"
            )

    @classmethod
    def validate_timml(cls, data, other=None):
        return cls._validate(
            cls.timml_schemata, cls.timml_consistency_schemata, data, other
        )

    @classmethod
    def validate_ttim(cls, data, other=None):
        return cls._validate(
            cls.ttim_schemata, cls.ttim_consistency_schemata, data, other
        )

    @classmethod
    def validate_timeseries(cls, data, other=None):
        return cls._validate_table(cls.timeseries_schemata, (), data, other)


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


class Element(ExtractorMixin, abc.ABC):
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

    @staticmethod
    def marker_renderer(**kwargs):
        symbol = QgsMarkerSymbol.createSimple(kwargs)
        return QgsSingleSymbolRenderer(symbol)

    @staticmethod
    def line_renderer(**kwargs):
        symbol = QgsLineSymbol.createSimple(kwargs)
        return QgsSingleSymbolRenderer(symbol)

    @staticmethod
    def polygon_renderer(**kwargs):
        symbol = QgsFillSymbol.createSimple(kwargs)
        return QgsSingleSymbolRenderer(symbol)

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

    def on_transient_changed(self, _):
        return

    @staticmethod
    def groupby(data: Dict[str, Any], key: str):
        # TODO: sort by layer or time?
        data = deepcopy(data)
        grouper = data.pop(key)
        grouped = {k: defaultdict(list) for k in grouper}
        for key, values in data.items():
            for groupkey, value in zip(grouper, values):
                grouped[groupkey][key].append(value)
        return grouped

    def to_timml(self, other=None):
        data = self.to_dict(self.timml_layer)
        errors = self.schema.validate_timml(data, other)
        if errors:
            return errors, data
        else:
            elements = [self.process_timml_row(row=row, other=other) for row in data]
            return [], elements

    def to_ttim(self, other=None):
        return self.to_timml(other)

    @staticmethod
    def aquifer_data(data, transient: bool):
        def interleave(a, b):
            return [value for pair in zip(a, b) for value in pair]

        data = deepcopy(data)  # Avoid side-effects
        hstar = data["semiconf_head"][0]
        semiconfined = (
            data["aquitard_c"][0] is not None
            and data["semiconf_top"][0] is not None
            and hstar is not None
        )

        kaq = data["aquifer_k"]
        c = data["aquitard_c"]
        z = [data["semiconf_top"][0]] + interleave(
            data["aquifer_top"], data["aquifer_bottom"]
        )
        porosity = interleave(data["aquitard_npor"], data["aquifer_npor"])
        s_aquifer = data["aquifer_s"]
        s_aquitard = data["aquitard_s"]

        if semiconfined:
            topboundary = "semi"
        else:
            topboundary = "conf"
            z.pop(0)
            c.pop(0)
            porosity.pop(0)
            if transient:
                s_aquitard.pop(0)

        aquifer = {
            "kaq": kaq,
            "z": z,
            "c": c,
            "npor": porosity,
        }

        if transient:
            aquifer["Saq"] = s_aquifer
            aquifer["Sll"] = s_aquitard
            aquifer["phreatictop"] = True
        else:
            aquifer["topboundary"] = topboundary
            aquifer["hstar"] = hstar

        if "resistance" in data:
            aquifer["res"] = data["resistance"][0]

        return aquifer


class TransientElement(Element, abc.ABC):
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

    @staticmethod
    def transient_input(row, all_timeseries, variable: str, time_start):
        timeseries_id = row["timeseries_id"]
        row_start = row["time_start"]
        row_end = row["time_end"]
        steady_value = row[variable]
        transient_value = row[f"{variable}_transient"]

        start_and_stop = (
            row_start is not None
            and row_end is not None
            and transient_value is not None
        )

        if timeseries_id is not None:
            timeseries = all_timeseries[timeseries_id]
            return [
                (time, value - steady_value)
                for time, value in zip(timeseries["time_start"], timeseries[variable])
            ]
        elif start_and_stop:
            return [(row_start, transient_value - steady_value), (row_end, 0.0)]
        else:
            return [(time_start), 0.0]

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

    def to_ttim(self, other=None):
        # Check timml input and timeseries input first.
        timml_errors, data = self.to_timml(other)
        timeseries = self.table_to_dict(self.ttim_layer)
        timeseries_errors = self.schema.validate_timeseries(timeseries)
        errors = {**timml_errors, **timeseries_errors}
        if errors:
            return errors, None

        other = other.copy()
        other["timeseries_ids"] = set([row["timeseries_id"] for row in timeseries])
        errors = self.schema.validate_ttim(data, other)
        if errors:
            return errors, None

        grouped = self.groupby(timeseries, "timeseries_id")
        elements = [self.process_ttim_row(row, grouped) for row in data]
        return None, elements


class AssociatedElement(Element, abc.ABC):
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

    def to_timml(self, other):
        properties = self.table_to_dict(self.assoc_layer)
        errors = self.assoc_schema.validate_timml(properties)
        if errors:
            return errors, None

        other = other.copy()  # Avoid side-effects
        other["properties inhomogeneity_id"] = list(set(properties["inhomogeneity_id"]))
        data = self.to_dict(self.timml_layer)
        errors = self.schema.validate_timml(data, other)
        if errors:
            return errors, None

        grouped = self.groupby(properties, "inhomogeneity_id")
        elements = [self.process_timml_row(row=row, grouped=grouped) for row in data]
        return None, elements

    def to_ttim(self, _):
        raise NotImplementedError(f"{type(self).__name__} is not supported in TTim.")
