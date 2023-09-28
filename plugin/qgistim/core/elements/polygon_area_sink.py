from copy import deepcopy

from PyQt5.QtCore import QVariant
from qgis.core import QgsDefaultValue, QgsField, QgsSingleSymbolRenderer
from qgistim.core.elements.colors import GREEN, TRANSPARENT_GREEN
from qgistim.core.elements.element import Element, ElementSchema
from qgistim.core.schemata import Positive, Required


class PolygonAreaSinkSchema(ElementSchema):
    timml_schemata = {
        "rate": Required(),
        "order": Required(Positive()),
        "ndegrees": Required(Positive()),
    }


class PolygonAreaSink(Element):
    element_type = "Polygon Area Sink"
    geometry_type = "Polygon"
    timml_attributes = (
        QgsField("rate", QVariant.Double),
        QgsField("order", QVariant.Int),
        QgsField("ndegrees", QVariant.Int),
    )
    timml_defaults = {
        "order": QgsDefaultValue("4"),
        "ndegrees": QgsDefaultValue("6"),
    }
    schema = PolygonAreaSinkSchema()

    @property
    def renderer(self) -> QgsSingleSymbolRenderer:
        return self.polygon_renderer(
            color=TRANSPARENT_GREEN, color_border=GREEN, width_border="0.75"
        )

    def process_timml_row(self, row, other):
        raw_data = deepcopy(other["global_aquifer"])
        raw_data["aquitard_c"][0] = None
        raw_data["semiconf_top"][0] = None
        raw_data["semiconf_head"][0] = None
        aquifer_data = self.aquifer_data(raw_data, transient=False)
        return {
            "xy": self.polygon_xy(row),
            "order": row["order"],
            "ndeg": row["ndegrees"],
            "N": row["rate"],
            **aquifer_data,
        }
