from PyQt5.QtCore import QVariant
from qgis.core import QgsField
from qgistim.core.elements.element import Element, ElementSchema
from qgistim.core.schemata import Required


class UniformFlowSchema(ElementSchema):
    timml_schemata = {
        "slope": Required(),
        "angle": Required(),
    }


class UniformFlow(Element):
    element_type = "Uniform Flow"
    geometry_type = "No geometry"
    timml_attributes = (
        QgsField("slope", QVariant.Double),
        QgsField("angle", QVariant.Double),
        QgsField("label", QVariant.String),
    )
    schema = UniformFlowSchema()

    def process_timml_row(self, row, other=None):
        # No renaming or changes required
        return row
