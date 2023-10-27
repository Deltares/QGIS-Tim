from PyQt5.QtCore import QVariant
from qgis.core import QgsDefaultValue, QgsField, QgsSingleSymbolRenderer
from qgistim.core.elements.colors import LIGHT_BLUE
from qgistim.core.elements.element import TransientElement
from qgistim.core.elements.schemata import RowWiseSchema
from qgistim.core.schemata import AllRequired, Positive, Required


class HeadObservationSchema(RowWiseSchema):
    timml_schemata = {
        "geometry": Required(),
    }
    timeseries_schemata = {
        "timeseries_id": AllRequired(),
        "time": AllRequired(Positive()),
    }


class HeadObservation(TransientElement):
    element_type = "Head Observation"
    geometry_type = "Point"
    timml_attributes = (
        QgsField("label", QVariant.String),
        QgsField("timeseries_id", QVariant.Int),
    )
    ttim_attributes = (
        QgsField("timeseries_id", QVariant.Int),
        QgsField("time", QVariant.Double),
    )
    timml_defaults = {
        "timeseries_id": QgsDefaultValue("1"),
    }
    ttim_defaults = {
        "timeseries_id": QgsDefaultValue("1"),
    }
    transient_columns = ("timeseries_id",)
    schema = HeadObservationSchema()

    @classmethod
    def renderer(cls) -> QgsSingleSymbolRenderer:
        return cls.marker_renderer(color=LIGHT_BLUE, name="triangle", size="3")

    def process_timml_row(self, row, other=None):
        x, y = self.point_xy(row)
        return {
            "x": x,
            "y": y,
            "label": row["label"],
        }

    def process_ttim_row(self, row, grouped):
        x, y = self.point_xy(row)
        times = grouped[row["timeseries_id"]]["time"]
        return {
            "x": x,
            "y": y,
            "t": times,
            "label": row["label"],
        }, times
