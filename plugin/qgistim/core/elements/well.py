from typing import Any, Dict

from PyQt5.QtCore import QVariant
from qgis.core import QgsDefaultValue, QgsField, QgsSingleSymbolRenderer
from qgistim.core.elements.colors import GREEN
from qgistim.core.elements.element import TransientElement
from qgistim.core.elements.schemata import RowWiseSchema
from qgistim.core.schemata import (
    AllOrNone,
    AllRequired,
    ConditionallyRequired,
    Membership,
    NotBoth,
    Optional,
    Positive,
    Required,
    StrictlyPositive,
)


class WellSchema(RowWiseSchema):
    timml_schemata = {
        "geometry": Required(),
        "discharge": Required(),
        "radius": Required(StrictlyPositive()),
        "resistance": Required(Positive()),
        "layer": Required(Membership("aquifer layers")),
    }
    timml_consistency_schemata = (ConditionallyRequired("slug", "caisson_radius"),)
    ttim_schemata = {
        "caisson_radius": Optional(StrictlyPositive()),
        "slug": Required(),
        "time_start": Optional(Positive()),
        "time_end": Optional(Positive()),
        "timeseries_id": Optional(Membership("ttim timeseries IDs")),
    }
    ttim_consistency_schemata = (
        AllOrNone(("time_start", "time_end", "discharge_transient")),
        NotBoth("time_start", "timeseries_id"),
    )
    timeseries_schemata = {
        "timeseries_id": AllRequired(),
        "time_start": AllRequired(Positive()),
        "discharge": AllRequired(),
    }


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
    timml_defaults = {
        "radius": QgsDefaultValue("0.1"),
        "resistance": QgsDefaultValue("0.0"),
        "slug": QgsDefaultValue("False"),
    }
    transient_columns = (
        "time_start",
        "time_end",
        "discharge_transient",
        "caisson_radius",
        "slug",
        "timeseries_id",
    )
    schema = WellSchema()

    @classmethod
    def renderer(cls) -> QgsSingleSymbolRenderer:
        return cls.marker_renderer(color=GREEN, size="3")

    def process_timml_row(self, row, other=None) -> Dict[str, Any]:
        x, y = self.point_xy(row)
        return {
            "xw": x,
            "yw": y,
            "Qw": row["discharge"],
            "rw": row["radius"],
            "res": row["resistance"],
            "layers": row["layer"],
            "label": row["label"],
        }

    def process_ttim_row(self, row, grouped):
        x, y = self.point_xy(row)
        tsandQ, times = self.transient_input(row, grouped, "discharge")
        return {
            "xw": x,
            "yw": y,
            "tsandQ": tsandQ,
            "rw": row["radius"],
            "res": row["resistance"],
            "layers": row["layer"],
            "label": row["label"],
            "rc": row["caisson_radius"],
            "wbstype": "slug" if row["slug"] else "pumping",
        }, times
