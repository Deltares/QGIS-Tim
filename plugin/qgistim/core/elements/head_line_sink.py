from PyQt5.QtCore import QVariant
from qgis.core import QgsDefaultValue, QgsField, QgsSingleSymbolRenderer
from qgistim.core.elements.colors import BLUE
from qgistim.core.elements.element import TransientElement
from qgistim.core.schemata import (
    AllOrNone,
    Membership,
    NotBoth,
    Optional,
    Positive,
    Required,
    Time,
)


class HeadLineSinkSchema:
    schemata = {
        "head": Required(),
        "resistance": Required(Positive()),
        "width": Required(Positive()),
        "order": Required(Positive()),
        "layer": Required(Membership("layers")),
    }


class TransientHeadLineSinkSchema:
    global_schemata = (
        AllOrNone("time_start", "time_end", "head_transient"),
        NotBoth("time_start", "timeseries_id"),
        Time(),
    )
    schemata = {
        "time_start": Optional(Time()),
        "time_end": Optional(Time()),
    }


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
        return self.line_renderer(color=BLUE, width="0.75")

    def to_timml(self):
        data = self.to_dict(self.timml_layer)
        sinks = []
        for row in data:
            sinks.append(
                {
                    "xy": self.linestring_xy(row),
                    "hls": row["head"],
                    "res": row["resistance"],
                    "wh": row["width"],
                    "order": row["order"],
                    "layers": row["layer"],
                    "label": row["label"],
                }
            )
        return sinks

    def to_ttim(self, time_start):
        data = self.to_dict(self.timml_layer)
        ttim_data = self.table_to_dict(self.ttim_layer)
        grouped = self.groupby(ttim_data, "timeseries_id")
        sinks = []
        for row in data:
            sinks.append(
                {
                    "xy": self.linestring_xy(row),
                    "tsandh": self._transient_input(row, grouped, "head", time_start),
                    "res": row["resistance"],
                    "wh": row["width"],
                    "order": row["order"],
                    "layers": row["layer"],
                    "label": row["label"],
                }
            )
        return sinks
