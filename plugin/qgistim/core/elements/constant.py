from PyQt5.QtCore import QVariant
from qgis.core import QgsField, QgsSingleSymbolRenderer
from qgistim.core.elements.colors import RED
from qgistim.core.elements.element import Element, ElementSchema
from qgistim.core.schemata import Membership, Required, SingleRow


class ConstantSchema(ElementSchema):
    consistency_schemata = (SingleRow(),)
    schemata = {
        "head": Required(),
        "layer": Membership("layers"),
    }


class Constant(Element):
    element_type = "Constant"
    geometry_type = "Point"
    timml_attributes = (
        QgsField("head", QVariant.Double),
        QgsField("layer", QVariant.Int),
        QgsField("label", QVariant.String),
    )

    @property
    def renderer(self) -> QgsSingleSymbolRenderer:
        return self.marker_renderer(color=RED, name="star", size="5")

    def to_timml(self):
        data = self.to_dict()
        # TODO: validate
        data = data[0]
        return {
            "xr": data["geometry"][0][0],
            "yr": data["geometry"][0][1],
            "hr": data["head"],
            "layer": data["layer"],
            "label": data["label"],
        }
