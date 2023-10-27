from typing import Any, Dict

from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QColor
from qgis.core import (
    QgsArrowSymbolLayer,
    QgsDefaultValue,
    QgsField,
    QgsLineSymbol,
    QgsSingleSymbolRenderer,
)
from qgistim.core.elements.colors import BLUE
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
    StrictlyPositive,
)


class HeadWellSchema(RowWiseSchema):
    timml_schemata = {
        "geometry": Required(),
        "head": Required(),
        "radius": Required(StrictlyPositive()),
        "resistance": Required(Positive()),
        "layer": Required(Membership("aquifer layers")),
    }
    ttim_schemata = {
        "time_start": Optional(Positive()),
        "time_end": Optional(Positive()),
        "timeseries_id": Optional(Membership("ttim timeseries IDs")),
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

    def process_ttim_row(self, row, grouped):
        x, y = self.point_xy(row)
        tsandh, times = self.transient_input(row, grouped, "head")
        return {
            "xw": x,
            "yw": y,
            "tsandh": tsandh,
            "rw": row["radius"],
            "res": row["resistance"],
            "layers": row["layer"],
            "label": row["label"],
        }, times


class RemoteHeadWell(HeadWell):
    element_type = "Remote Head Well"
    geometry_type = "Linestring"

    @classmethod
    def renderer(cls) -> QgsSingleSymbolRenderer:
        arrow = QgsArrowSymbolLayer()
        red, green, blue, _ = [int(v) for v in BLUE.split(",")]
        arrow.setColor(QColor(red, green, blue))
        arrow.setHeadLength(2.5)
        symbol = QgsLineSymbol.createSimple({})
        symbol.changeSymbolLayer(0, arrow)
        return QgsSingleSymbolRenderer(symbol)

    def process_timml_row(self, row, other=None) -> Dict[str, Any]:
        xy = self.linestring_xy(row)
        xw, yw = xy[-1]
        xc, yc = xy[0]
        return {
            "xw": xw,
            "yw": yw,
            "hw": row["head"],
            "rw": row["radius"],
            "res": row["resistance"],
            "layers": row["layer"],
            "label": row["label"],
            "xc": xc,
            "yc": yc,
        }
