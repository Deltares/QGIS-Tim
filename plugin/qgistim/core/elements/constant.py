from PyQt5.QtCore import QVariant
from qgis.core import QgsField, QgsSingleSymbolRenderer
from qgistim.core.elements.colors import RED
from qgistim.core.elements.element import Element
from qgistim.core.elements.schemata import SingleRowSchema
from qgistim.core.schemata import Membership, Required, RequiresConfinedAquifer


class ConstantSchema(SingleRowSchema):
    timml_schemata = {
        "geometry": Required(),
        "head": Required(),
        "layer": Required(Membership("aquifer layers")),
    }
    timml_consistency_schemata = (RequiresConfinedAquifer(),)


class Constant(Element):
    element_type = "Constant"
    geometry_type = "Point"
    timml_attributes = (
        QgsField("head", QVariant.Double),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
    )
    schema = ConstantSchema()

    @classmethod
    def renderer(cls) -> QgsSingleSymbolRenderer:
        return cls.marker_renderer(color=RED, name="star", size="5")

    def process_timml_row(self, row, other=None):
        x, y = self.point_xy(row)
        return {
            "xr": x,
            "yr": y,
            "hr": row["head"],
            "layer": row["layer"],
            "label": row["label"],
        }
