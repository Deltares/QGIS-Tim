from PyQt5.QtCore import QVariant
from qgis.core import QgsField, QgsSingleSymbolRenderer
from qgistim.core.elements.colors import RED
from qgistim.core.elements.element import Element, ElementSchema
from qgistim.core.schemata import Membership, Required, SingleRow


class ConstantSchema(ElementSchema):
    timml_consistency_schemata = (SingleRow(),)
    timml_schemata = {
        "geometry": Required(),
        "head": Required(),
        "layer": Required(Membership("aquifer layers")),
    }


class Constant(Element):
    element_type = "Constant"
    geometry_type = "Point"
    timml_attributes = (
        QgsField("head", QVariant.Double),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
    )
    schema = ConstantSchema()

    @property
    def renderer(self) -> QgsSingleSymbolRenderer:
        return self.marker_renderer(color=RED, name="star", size="5")

    def process_timml_row(self, row):
        x, y = self.point_xy(row)
        return {
            "xr": x,
            "yr": y,
            "hr": row["head"],
            "layer": row["layer"],
            "label": row["label"],
        }
