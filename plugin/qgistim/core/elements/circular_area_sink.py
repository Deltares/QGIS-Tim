from typing import Any, Dict

from PyQt5.QtCore import QVariant
from qgis.core import QgsField
from qgistim.core.elements.colors import GREEN, TRANSPARENT_GREEN
from qgistim.core.elements.element import TransientElement
from qgistim.core.elements.schemata import RowWiseSchema
from qgistim.core.schemata import (
    AllOrNone,
    AllRequired,
    CircularGeometry,
    Membership,
    NotBoth,
    Optional,
    Positive,
    Required,
    StrictlyIncreasing,
)


class CircularAreaSinkSchema(RowWiseSchema):
    timml_schemata = {
        "geometry": Required(CircularGeometry()),
        "rate": Required(),
        "layer": Required(Membership("aquifer layers")),
    }
    ttim_schemata = {
        "time_start": Optional(Positive()),
        "time_end": Optional(Positive()),
        "timeseries_id": Optional(Membership("ttim timeseries IDs")),
    }
    ttim_consistency_schemata = (
        AllOrNone("time_start", "time_end", "rate_transient"),
        NotBoth("time_start", "timeseries_id"),
    )
    timeseries_schemata = {
        "timeseries_id": AllRequired(),
        "time_start": AllRequired(Positive(), StrictlyIncreasing()),
        "rate": AllRequired(),
    }


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
    schema = CircularAreaSinkSchema()

    @classmethod
    def renderer(cls):
        return cls.polygon_renderer(
            color=TRANSPARENT_GREEN, color_border=GREEN, width_border="0.75"
        )

    def _centroid_and_radius(self, row):
        # Take the first vertex.
        x, y = self.point_xy(row)
        # Compare with the centroid to derive radius.
        xc, yc = row["centroid"]
        radius = ((x - xc) ** 2 + (y - yc) ** 2) ** 0.5
        return xc, yc, radius

    def process_timml_row(self, row, other=None) -> Dict[str, Any]:
        xc, yc, radius = self._centroid_and_radius(row)
        return {
            "xc": xc,
            "yc": yc,
            "R": radius,
            "N": row["rate"],
            "label": row["label"],
        }

    def process_ttim_row(self, row, grouped):
        xc, yc, radius = self._centroid_and_radius(row)
        tsandN, times = self.transient_input(row, grouped, "rate")
        return {
            "xc": xc,
            "yc": yc,
            "R": radius,
            "tsandN": tsandN,
            "label": row["label"],
        }, times
