from PyQt5.QtCore import QVariant
from qgis.core import QgsDefaultValue, QgsField, QgsSingleSymbolRenderer
from qgistim.core.elements.colors import RED
from qgistim.core.elements.element import Element, ElementSchema
from qgistim.core.schemata import Membership, Positive, Required


class ImpermeableLineDoubletSchema(ElementSchema):
    timml_schemata = {
        "order": Required(Positive()),
        "layer": Required(Membership("aquifer layers")),
    }


class ImpermeableLineDoublet(Element):
    element_type = "Impermeable Line Doublet"
    geometry_type = "Linestring"
    timml_attributes = (
        QgsField("order", QVariant.Int),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
    )
    timml_defaults = {
        "order": QgsDefaultValue("4"),
    }
    schema = ImpermeableLineDoubletSchema()

    @property
    def renderer(self) -> QgsSingleSymbolRenderer:
        return self.line_renderer(color=RED, width="0.75")

    def process_timml_row(self, row):
        return {
            "xy": self.linestring_xy(row),
            "layers": row["layer"],
            "order": row["order"],
            "label": row["label"],
        }

    def to_ttim(self, other):
        # TTim doesn't have an ImpermeableLineDoublet, we need to add "imp" as
        # the resistance entry.
        data = self.to_timml(other)
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
        return out
