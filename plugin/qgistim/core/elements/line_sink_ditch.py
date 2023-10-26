from PyQt5.QtCore import QVariant
from qgis.core import QgsDefaultValue, QgsField, QgsSingleSymbolRenderer
from qgistim.core.elements.colors import GREEN
from qgistim.core.elements.element import ElementSchema, TransientElement
from qgistim.core.schemata import (
    AllOrNone,
    AllRequired,
    Membership,
    NotBoth,
    Optional,
    Positive,
    Required,
)


class LineSinkDitchSchema(ElementSchema):
    timml_schemata = {
        "discharge": Required(),
        "resistance": Required(Positive()),
        "width": Required(Positive()),
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
    }
    timeseries_schemata = {
        "timeseries_id": AllRequired(),
        "time_start": AllRequired(Positive()),
        "discharge": AllRequired(),
    }


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
        return {
            "xy": self.linestring_xy(row),
            "tsandQ": self.transient_input(row, grouped, "discharge"),
            "res": row["resistance"],
            "wh": row["width"],
            "layers": row["layer"],
            "label": row["label"],
        }
