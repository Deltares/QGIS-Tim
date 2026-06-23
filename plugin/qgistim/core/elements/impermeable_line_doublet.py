from qgis.core import QgsDefaultValue, QgsField, QgsSingleSymbolRenderer
from qgis.PyQt.QtCore import QVariant

from qgistim.core.elements.colors import RED
from qgistim.core.elements.default_values import DefaultValues
from qgistim.core.elements.element import Element
from qgistim.core.elements.schemata import RowWiseSchema
from qgistim.core.schemata import Membership, Positive, Required


class ImpermeableWallSchema(RowWiseSchema):
    steady_schemata = {
        "geometry": Required(),
        "order": Required(Positive()),
        "layer": Required(Membership("aquifer layers")),
    }


class ImpermeableWall(Element):
    element_type = "Impermeable Wall"
    geometry_type = "Linestring"
    steady_attributes = (
        QgsField("order", QVariant.Int),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
    )
    steady_defaults = {
        "order": QgsDefaultValue(DefaultValues.order),
    }
    schema = ImpermeableWallSchema()

    @classmethod
    def renderer(cls) -> QgsSingleSymbolRenderer:
        return cls.line_renderer(color=RED, width="0.75")

    def process_steady_row(self, row, other=None):
        return {
            "xy": self.linestring_xy(row),
            "layers": row["layer"],
            "order": row["order"],
            "label": row["label"],
        }

    def extract_transient_data(self, other):
        # TTim doesn't have an ImpermeableWall, we need to add "imp" as
        # the resistance entry.
        _, data = self.extract_steady_data(other)
        out = []
        for row in data:
            out.append(
                {
                    "xy": row["xy"],
                    "res": "imp",
                    "order": row["order"],
                    "label": row["label"],
                }
            )
        return None, out
