
from PyQt5.QtCore import QVariant
from qgis.core import QgsDefaultValue, QgsField, QgsSingleSymbolRenderer
from qgistim.core.elements.colors import LIGHT_BLUE
from qgistim.core.elements.element import Element
from qgistim.core.elements.schemata import RowWiseSchema
from qgistim.core.schemata import (
    Positive,
    Required,
)


class DischargeObservationSchema(RowWiseSchema):
    timml_schemata = {
        "geometry": Required(),
        "legendre_method": Required(),
        "ndegrees": Required(Positive()),
    }


class DischargeObservation(Element):
    element_type = "Discharge Observation"
    geometry_type = "Linestring"
    timml_attributes = (
        QgsField("legendre_method", QVariant.Bool),
        QgsField("ndegrees", QVariant.Int),
        QgsField("label", QVariant.String)
    )
    timml_defaults = {
        "legendre_method": QgsDefaultValue("True"),
        "ndegrees": QgsDefaultValue("10"),
    }
    schema = DischargeObservationSchema()

    @classmethod
    def renderer(cls) -> QgsSingleSymbolRenderer:
        return cls.line_renderer(color=LIGHT_BLUE, width="0.75", outline_style="dash")

    def process_timml_row(self, row, other=None):
        return {
            "xy": self.linestring_xy(row),
            "method": "legendre" if row["legendre_method"] else "quad",
            "ndeg": row["ndegrees"],
            "label": row["label"],
        }
