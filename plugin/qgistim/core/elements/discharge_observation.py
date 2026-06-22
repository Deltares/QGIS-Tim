from qgis.core import QgsDefaultValue, QgsField, QgsSingleSymbolRenderer
from qgis.PyQt.QtCore import QVariant

from qgistim.core.elements.colors import LIGHT_BLUE
from qgistim.core.elements.element import Element
from qgistim.core.elements.schemata import RowWiseSchema
from qgistim.core.schemata import (
    Positive,
    Required,
)


class DischargeObservationSchema(RowWiseSchema):
    steady_schemata = {
        "geometry": Required(),
        "legendre_method": Required(),
        "ndegrees": Required(Positive()),
    }


class DischargeObservation(Element):
    element_type = "Discharge Observation"
    geometry_type = "Linestring"
    steady_attributes = (
        QgsField("legendre_method", QVariant.Bool),
        QgsField("ndegrees", QVariant.Int),
        QgsField("label", QVariant.String),
    )
    steady_defaults = {
        "legendre_method": QgsDefaultValue("True"),
        "ndegrees": QgsDefaultValue("10"),
    }
    schema = DischargeObservationSchema()

    @classmethod
    def renderer(cls) -> QgsSingleSymbolRenderer:
        return cls.line_renderer(color=LIGHT_BLUE, width="0.75", outline_style="dash")

    def process_steady_row(self, row, other=None):
        return {
            "xy": self.linestring_xy(row),
            "method": "legendre" if row["legendre_method"] else "quad",
            "ndeg": row["ndegrees"],
            "label": row["label"],
        }
