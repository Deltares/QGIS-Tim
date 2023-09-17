from PyQt5.QtCore import QVariant
from qgis.core import QgsDefaultValue, QgsField, QgsSingleSymbolRenderer
from qgistim.core.elements.colors import GREEN, TRANSPARENT_GREEN
from qgistim.core.elements.element import Element, ElementSchema
from qgistim.core.schemata import (
    Positive,
    Required,
)


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
        return {
            "xy": self._polygon_xy(row),
            "rate": row["rate"],
            "order": row["order"],
            "ndeg": row["ndegrees"],
            **other["global_aquifer"],
        }
