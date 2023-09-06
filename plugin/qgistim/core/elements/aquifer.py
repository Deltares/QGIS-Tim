from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List

from PyQt5.QtCore import QVariant
from qgis.core import QgsDefaultValue, QgsField
from qgistim.core import geopackage
from qgistim.core.elements.element import TransientElement
from qgistim.core.schemata import (
    AllGreaterEqual,
    AllOptional,
    AllRequired,
    FirstOnly,
    OffsetAllRequired,
    Positive,
    Range,
    SemiConfined,
    StrictlyDecreasing,
)


class Aquifer(TransientElement):
    element_type = "Aquifer"
    geometry_type = "No Geometry"
    timml_attributes = [
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

    timml_schemata = {
        "layer": AllRequired(Range()),
        "aquifer_top": AllRequired(StrictlyDecreasing()),
        "aquifer_bottom": AllRequired(StrictlyDecreasing()),
        "aquifer_k": AllRequired(Positive()),
        "aquitard_c": OffsetAllRequired(Positive()),
        "semiconf_top": AllOptional(FirstOnly()),
        "semiconf_head": AllOptional(FirstOnly()),
    }
    timml_global_schemata = (
        SemiConfined(),
        AllGreaterEqual("aquifer_top", "aquifer_bottom"),
    )
    ttim_schemata = {
        "aquitard_s": OffsetAllRequired(Positive()),
        "aquifer_s": AllRequired(Positive()),
    }

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

    def to_timml(self):
        data = self.table_to_dict(self.timml_layer)
        self.validate_timml(data)
        return self.aquifer_data(data, transient=False)

    def to_ttim(self):
        data = self.table_to_dict(self.timml_layer)
        return self.aquifer_data(data, transient=True)
