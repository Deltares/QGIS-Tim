from PyQt5.QtCore import QVariant
from qgis.core import QgsDefaultValue, QgsField, QgsSingleSymbolRenderer
from qgistim.core.elements.colors import RED
from qgistim.core.elements.element import Element
from qgistim.core.elements.schemata import RowWiseSchema
from qgistim.core.schemata import Membership, Positive, Required, StrictlyPositive


class LeakyLineDoubletSchema(RowWiseSchema):
    timml_schemata = {
        "geometry": Required(),
        "resistance": Required(StrictlyPositive()),
        "order": Required(Positive()),
        "layer": Required(Membership("aquifer layers")),
    }


class LeakyLineDoublet(Element):
    element_type = "Leaky Line Doublet"
    geometry_type = "Linestring"
    timml_attributes = (
        QgsField("resistance", QVariant.Double),
        QgsField("order", QVariant.Int),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
    )
    timml_defaults = {
        "order": QgsDefaultValue("4"),
    }
    schema = LeakyLineDoubletSchema()

    @classmethod
    def renderer(cls) -> QgsSingleSymbolRenderer:
        return cls.line_renderer(color=RED, width="0.75", outline_style="dash")

    def process_timml_row(self, row, other=None):
        return {
            "xy": self.linestring_xy(row),
            "res": row["resistance"],
            "layers": row["layer"],
            "order": row["order"],
            "label": row["label"],
        }
