from PyQt5.QtCore import QVariant
from qgis.core import QgsDefaultValue, QgsField, QgsSingleSymbolRenderer
from qgistim.core.elements.colors import LIGHT_BLUE
from qgistim.core.elements.element import ElementSchema, TransientElement
from qgistim.core.schemata import AllRequired, Positive, Required


class ObservationSchema(ElementSchema):
    timml_schemata = {
        "geometry": Required(),
    }
    timeseries_schemata = {
        "timeseries_id": AllRequired(),
        "time": AllRequired(Positive()),
    }


class Observation(TransientElement):
    element_type = "Observation"
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
    schema = ObservationSchema()

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
