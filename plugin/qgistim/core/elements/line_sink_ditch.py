from PyQt5.QtCore import QMetaType
from qgis.core import QgsDefaultValue, QgsField, QgsSingleSymbolRenderer

from qgistim.core.elements.colors import GREEN
from qgistim.core.elements.element import TransientElement
from qgistim.core.elements.schemata import RowWiseSchema
from qgistim.core.schemata import (
    AllOrNone,
    AllRequired,
    Membership,
    NotBoth,
    Optional,
    Positive,
    Required,
    StrictlyIncreasing,
    StrictlyPositive,
)


class LineSinkDitchSchema(RowWiseSchema):
    timml_schemata = {
        "geometry": Required(),
        "discharge": Required(),
        "resistance": Required(Positive()),
        "width": Required(StrictlyPositive()),
        "order": Required(Positive()),
        "layer": Required(Membership("aquifer layers")),
    }
    ttim_consistency_schemata = (
        AllOrNone("time_start", "time_end", "discharge_transient"),
        NotBoth("time_start", "timeseries_id"),
    )
    ttim_schemata = {
        "time_start": Optional(Positive()),
        "time_end": Optional(Positive()),
        "timeseries_id": Optional(Membership("ttim timeseries IDs")),
    }
    timeseries_schemata = {
        "timeseries_id": AllRequired(),
        "time_start": AllRequired(Positive(), StrictlyIncreasing()),
        "discharge": AllRequired(),
    }


class LineSinkDitch(TransientElement):
    element_type = "Line Sink Ditch"
    geometry_type = "Linestring"
    timml_attributes = (
        QgsField("discharge", QMetaType.Type.Double),
        QgsField("resistance", QMetaType.Type.Double),
        QgsField("width", QMetaType.Type.Double),
        QgsField("order", QMetaType.Type.Int),
        QgsField("layer", QMetaType.Type.Int),
        QgsField("label", QMetaType.Type.QString),
        QgsField("time_start", QMetaType.Type.Double),
        QgsField("time_end", QMetaType.Type.Double),
        QgsField("discharge_transient", QMetaType.Type.Double),
        QgsField("timeseries_id", QMetaType.Type.Int),
    )
    ttim_attributes = (
        QgsField("timeseries_id", QMetaType.Type.Int),
        QgsField("time_start", QMetaType.Type.Double),
        QgsField("discharge", QMetaType.Type.Double),
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
    schema = LineSinkDitchSchema()

    @classmethod
    def renderer(cls) -> QgsSingleSymbolRenderer:
        return cls.line_renderer(color=GREEN, width="0.75")

    def process_timml_row(self, row, other=None):
        return {
            "xy": self.linestring_xy(row),
            "Qls": row["discharge"],
            "res": row["resistance"],
            "wh": row["width"],
            "order": row["order"],
            "layers": row["layer"],
            "label": row["label"],
        }

    def process_ttim_row(self, row, grouped):
        tsandQ, times = self.transient_input(row, grouped, "discharge")
        return {
            "xy": self.linestring_xy(row),
            "tsandQ": tsandQ,
            "res": row["resistance"],
            "wh": row["width"],
            "layers": row["layer"],
            "label": row["label"],
        }, times
