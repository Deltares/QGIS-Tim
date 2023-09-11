from PyQt5.QtCore import QVariant
from qgis.core import QgsDefaultValue, QgsField, QgsSingleSymbolRenderer
from qgistim.core.elements.colors import GREEN
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


class WellSchema:
    schemata = {
        "discharge": Required(),
        "radius": Required(),
        "resistance": Required(),
        "layer": Required(Membership("layers")),
    }


class TransientWellSchema:
    schemata = {
        "caisson_radius": Required(Positive),
        "slug": Required(),
        "time_start": Optional(Time()),
        "time_end": Optional(Time()),
        "timeseries_id": Optional(Membership("timeseries_ids")),
    }
    consistency_schemata = (
        AllOrNone(("time_start", "time_end", "discharge_transient")),
        NotBoth("time_start", "timeseries_id"),
    )


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
        "caisson_radius": QgsDefaultValue("0.0"),
        "slug": QgsDefaultValue("True"),
    }
    transient_columns = (
        "time_start",
        "time_end",
        "discharge_transient",
        "caisson_radius",
        "slug",
        "timeseries_id",
    )

    @property
    def renderer(self) -> QgsSingleSymbolRenderer:
        return self.marker_renderer(color=GREEN, size="3")

    def to_timml(self):
        data = self.to_dict(self.timml_layer)
        wells = []
        for row in data:
            x, y = self.point_xy(row)
            wells.append(
                {
                    "xw": x,
                    "yw": y,
                    "Q": row["discharge"],
                    "rw": row["radius"],
                    "res": row["resistance"],
                    "layers": row["layer"],
                    "label": row["label"],
                }
            )
        return wells

    def to_ttim(self, time_start):
        data = self.to_dict(self.timml_layer)
        ttim_data = self.table_to_dict(self.ttim_layer)
        grouped = self.groupby(ttim_data, "timeseries_id")
        wells = []
        for row in data:
            x, y = self.point_xy(row)
            wells.append(
                {
                    "xw": x,
                    "yw": y,
                    "tsandQ": self._transient_input(
                        row, grouped, "discharge", time_start
                    ),
                    "hw": row["head"],
                    "rw": row["radius"],
                    "res": row["resistance"],
                    "layers": row["layer"],
                    "label": row["label"],
                    "rc": row["caisson_radius"],
                    "wbstype": "slug" if row["slug"] else "pumping",
                }
            )
        return wells
