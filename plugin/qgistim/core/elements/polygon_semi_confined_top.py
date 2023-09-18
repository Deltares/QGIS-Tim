from copy import deepcopy

from PyQt5.QtCore import QVariant
from qgis.core import QgsDefaultValue, QgsField, QgsSingleSymbolRenderer
from qgistim.core.elements.colors import BLUE, TRANSPARENT_BLUE
from qgistim.core.elements.element import Element, ElementSchema
from qgistim.core.schemata import Positive, Required


class PolygonSemiConfinedTopSchema(ElementSchema):
    timml_schemata = {
        "aquitard_c": Required(Positive()),
        "semiconf_top": Required(),
        "semiconf_head": Required(),
        "order": Required(Positive()),
        "ndegrees": Required(Positive()),
    }


class PolygonSemiConfinedTop(Element):
    element_type = "Polygon Semi-Confined Top"
    geometry_type = "Polygon"
    timml_attributes = (
        QgsField("aquitard_c", QVariant.Double),
        QgsField("semiconf_top", QVariant.Double),
        QgsField("semiconf_head", QVariant.Double),
        QgsField("order", QVariant.Int),
        QgsField("ndegrees", QVariant.Int),
    )
    timml_defaults = {
        "order": QgsDefaultValue("4"),
        "ndegrees": QgsDefaultValue("6"),
    }
    schema = PolygonSemiConfinedTopSchema()

    @property
    def renderer(self) -> QgsSingleSymbolRenderer:
        return self.polygon_renderer(
            color=TRANSPARENT_BLUE, color_border=BLUE, width_border="0.75"
        )

    def process_timml_row(self, row, other):
        raw_data = deepcopy(other["global_aquifer"])
        raw_data["aquitard_c"][0] = row["aquitard_c"]
        raw_data["semiconf_top"][0] = row["semiconf_top"]
        raw_data["semiconf_head"][0] = row["semiconf_head"]
        aquifer_data = self.aquifer_data(raw_data, transient=False)
        return {
            "xy": self.polygon_xy(row),
            "order": row["order"],
            "ndeg": row["ndegrees"],
            **aquifer_data,
        }
