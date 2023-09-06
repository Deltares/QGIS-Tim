from PyQt5.QtCore import QVariant
from qgis.core import QgsField
from qgistim.core.elements.element import Element


class UniformFlow(Element):
    element_type = "Uniform Flow"
    geometry_type = "No geometry"
    timml_attributes = (
        QgsField("slope", QVariant.Double),
        QgsField("angle", QVariant.Double),
        QgsField("label", QVariant.String),
    )

    def to_timml(self):
        data = self.to_dict(self.timml_layer)
        return {
            "slope": data["slope"],
            "angle": data["angle"],
            "label": data["label"],
        }
