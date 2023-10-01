from typing import Any, Dict

from PyQt5.QtCore import QVariant
from qgis.core import QgsDefaultValue, QgsField, QgsSingleSymbolRenderer
from qgistim.core.elements.colors import BLUE
from qgistim.core.elements.element import ElementSchema, TransientElement
from qgistim.core.schemata import (
    AllOrNone,
    AllRequired,
    Membership,
    NotBoth,
    Positive,
    Required,
)


class HeadWellSchema(ElementSchema):
    timml_schemata = {
        "head": Required(),
        "radius": Required(Positive()),
        "resistance": Required(Positive()),
        "layer": Required(Membership("aquifer layers")),
    }
    ttim_consistency_schemata = (
        AllOrNone(("time_start", "time_end", "head_transient")),
        NotBoth("time_start", "timeseries_id"),
    )
    timeseries_schemata = {
        "timeseries_id": AllRequired(),
        "time_start": AllRequired(Positive()),
        "head": AllRequired(),
    }


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
    timml_defaults = {
        "radius": QgsDefaultValue("0.1"),
        "resistance": QgsDefaultValue("0.0"),
    }
    transient_columns = (
        "time_start",
        "time_end",
        "head_transient",
        "timeseries_id",
    )
    schema = HeadWellSchema()

    @classmethod
    def renderer(cls) -> QgsSingleSymbolRenderer:
        return cls.marker_renderer(color=BLUE, size="3")

    def process_timml_row(self, row, other=None) -> Dict[str, Any]:
        x, y = self.point_xy(row)
        return {
            "xw": x,
            "yw": y,
            "hw": row["head"],
            "rw": row["radius"],
            "res": row["resistance"],
            "layers": row["layer"],
            "label": row["label"],
        }
