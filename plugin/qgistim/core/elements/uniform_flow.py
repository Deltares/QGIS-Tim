from PyQt5.QtCore import QVariant
from qgis.core import QgsField
from qgistim.core.elements.element import Element
from qgistim.core.elements.schemata import SingleRowSchema
from qgistim.core.schemata import Required, RequiresConfinedAquifer


class UniformFlowSchema(SingleRowSchema):
    timml_schemata = {
        "slope": Required(),
        "angle": Required(),
    }
    timml_consistency_schemata = (RequiresConfinedAquifer(),)


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
        return {
            "slope": row["slope"],
            "angle": row["angle"],
            "label": row["label"],
        }
