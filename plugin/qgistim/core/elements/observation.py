from PyQt5.QtCore import QVariant
from qgis.core import QgsDefaultValue, QgsField, QgsSingleSymbolRenderer
from qgistim.core.elements.colors import LIGHT_BLUE
from qgistim.core.elements.element import TransientElement


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

    @property
    def renderer(self) -> QgsSingleSymbolRenderer:
        return self.marker_renderer(color=LIGHT_BLUE, name="triangle", size="3")

    def to_timml(self):
        data = self.to_dict(self.timml_layer)

        observations = []
        for row in data:
            observations.append(
                {
                    "x": row["geometry"][0][0],
                    "y": row["geometry"][0][1],
                    "label": row["label"],
                }
            )
        return observations
