from typing import Any, Dict

from PyQt5.QtCore import QVariant
from qgis.core import QgsDefaultValue, QgsField, QgsSingleSymbolRenderer
from qgistim.core.elements.colors import RED, TRANSPARENT_RED
from qgistim.core.elements.element import AssociatedElement, ElementSchema
from qgistim.core.schemata import (
    AllGreaterEqual,
    AllRequired,
    Membership,
    OffsetAllRequired,
    OptionalFirstOnly,
    Positive,
    Range,
    Required,
    SemiConfined,
    StrictlyDecreasing,
)


class BuildingPitSchema(ElementSchema):
    timml_schemata = {
        "inhomogeneity_id": Required(Membership("properties inhomogeneity_id")),
        "order": Required(Positive()),
        "ndegrees": Required(Positive()),
    }


class AssociatedBuildingPitSchema(ElementSchema):
    timml_schemata = {
        "inhomogeneity_id": AllRequired(),
        "layer": AllRequired(Range()),
        "aquifer_top": AllRequired(StrictlyDecreasing()),
        "aquifer_bottom": AllRequired(StrictlyDecreasing()),
        "aquitard_c": OffsetAllRequired(Positive()),
        "aquifer_k": AllRequired(Positive()),
        "semiconf_top": OptionalFirstOnly(),
        "semiconf_head": OptionalFirstOnly(),
    }
    timml_consistency_schemata = (
        SemiConfined(),
        AllGreaterEqual("aquifer_top", "aquifer_bottom"),
    )


class BuildingPit(AssociatedElement):
    element_type = "Building Pit"
    geometry_type = "Polygon"
    timml_attributes = (
        QgsField("inhomogeneity_id", QVariant.Int),
        QgsField("order", QVariant.Int),
        QgsField("ndegrees", QVariant.Int),
    )
    assoc_attributes = [
        QgsField("inhomogeneity_id", QVariant.Int),
        QgsField("layer", QVariant.Int),
        QgsField("aquifer_top", QVariant.Double),
        QgsField("aquifer_bottom", QVariant.Double),
        QgsField("aquitard_c", QVariant.Double),
        QgsField("aquifer_k", QVariant.Double),
        QgsField("semiconf_top", QVariant.Double),
        QgsField("semiconf_head", QVariant.Double),
        QgsField("wall_in_layer", QVariant.Bool),
        QgsField("aquitard_npor", QVariant.Double),
        QgsField("aquifer_npor", QVariant.Double),
    ]
    timml_defaults = {
        "order": QgsDefaultValue("4"),
        "ndegrees": QgsDefaultValue("6"),
        "inhomogeneity_id": QgsDefaultValue("1"),
    }
    assoc_defaults = {
        "inhomogeneity_id": QgsDefaultValue("1"),
        "wall_in_layer": QgsDefaultValue("false"),
    }
    schema = BuildingPitSchema()
    assoc_schema = AssociatedBuildingPitSchema()

    @property
    def renderer(self) -> QgsSingleSymbolRenderer:
        return self.polygon_renderer(
            color=TRANSPARENT_RED, color_border=RED, width_border="0.75"
        )

    def process_timml_row(self, row: Dict[str, Any], grouped: Dict[int, Any]):
        inhom_id = row["inhomogeneity_id"]
        raw_data = grouped[inhom_id]
        layers = [i for i, active in enumerate(raw_data["wall_in_layer"]) if active]
        aquifer_data = self.aquifer_data(raw_data, transient=False)
        return {
            "xy": self.polygon_xy(row),
            "order": row["order"],
            "ndeg": row["ndegrees"],
            "layers": layers,
            **aquifer_data,
        }
