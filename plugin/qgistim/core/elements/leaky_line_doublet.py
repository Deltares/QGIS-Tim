from PyQt5.QtCore import QVariant
from qgis.core import QgsDefaultValue, QgsField, QgsSingleSymbolRenderer

from qgistim.core.elements.colors import RED
from qgistim.core.elements.default_values import DefaultValues
from qgistim.core.elements.element import Element
from qgistim.core.elements.schemata import RowWiseSchema
from qgistim.core.schemata import Membership, Positive, Required, StrictlyPositive


class LeakyWallSchema(RowWiseSchema):
    steady_schemata = {
        "geometry": Required(),
        "resistance": Required(StrictlyPositive()),
        "order": Required(Positive()),
        "layer": Required(Membership("aquifer layers")),
    }


class LeakyWall(Element):
    element_type = "Leaky Wall"
    geometry_type = "Linestring"
    steady_attributes = (
        QgsField("resistance", QVariant.Double),
        QgsField("order", QVariant.Int),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
    )
    steady_defaults = {
        "order": QgsDefaultValue(DefaultValues.order),
    }
    schema = LeakyWallSchema()

    @classmethod
    def renderer(cls) -> QgsSingleSymbolRenderer:
        return cls.line_renderer(color=RED, width="0.75", outline_style="dash")

    def process_steady_row(self, row, other=None):
        return {
            "xy": self.linestring_xy(row),
            "res": row["resistance"],
            "layers": row["layer"],
            "order": row["order"],
            "label": row["label"],
        }
