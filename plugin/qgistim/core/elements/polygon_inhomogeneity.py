from PyQt5.QtCore import QVariant
from qgis.core import QgsDefaultValue, QgsField, QgsSingleSymbolRenderer
from qgistim.core.elements.colors import GREY, TRANSPARENT_GREY
from qgistim.core.elements.element import AssociatedElement, ElementSchema
from qgistim.core.schemata import (
    AllGreaterEqual,
    AllOptional,
    AllRequired,
    FirstOnly,
    Membership,
    OffsetAllRequired,
    Positive,
    Range,
    Required,
    SemiConfined,
    StrictlyDecreasing,
)


class PolygonInhomgeneitySchema(ElementSchema):
    timml_schemata = {
        "inhomogeneity_id": Required(Membership("inhomogeneity_id")),
        "order": Required(Positive()),
        "ndegrees": Required(Positive()),
    }


class AssociatedPolygonInhomogeneitySchema(ElementSchema):
    timml_schemata = {
        "inhomogeneity_id": AllRequired(),
        "layer": AllRequired(Range()),
        "aquifer_top": AllRequired(StrictlyDecreasing()),
        "aquifer_bottom": AllRequired(StrictlyDecreasing()),
        "aquitard_c": OffsetAllRequired(Positive()),
        "aquifer_k": AllRequired(Positive()),
        "semiconf_top": AllOptional(FirstOnly()),
        "semiconf_head": AllOptional(FirstOnly()),
    }
    timml_consistency_schemata = (
        SemiConfined(),
        AllGreaterEqual("aquifer_top", "aquifer_bottom"),
    )


# TODO: each group should have equal length


class PolygonInhomogeneity(AssociatedElement):
    element_type = "Polygon Inhomogeneity"
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
        QgsField("rate", QVariant.Double),
        QgsField("aquitard_s", QVariant.Double),
        QgsField("aquifer_s", QVariant.Double),
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
    }
    transient_columns = (
        "aquitard_s",
        "aquifer_s",
        "aquitard_npor",
        "aquifer_npor",
    )
    schema = PolygonInhomgeneitySchema()
    assoc_schema = AssociatedPolygonInhomogeneitySchema()

    @property
    def renderer(self) -> QgsSingleSymbolRenderer:
        return self.polygon_renderer(
            color=TRANSPARENT_GREY, color_border=GREY, width_border="0.75"
        )

    def on_transient_changed(self, transient: bool):
        config = self.assoc_layer.attributeTableConfig()
        columns = config.columns()

        for i, column in enumerate(columns):
            if column.name in self.transient_columns:
                config.setColumnHidden(i, not transient)

        self.assoc_layer.setAttributeTableConfig(config)
        return

    def to_timml(self):
        data = self.to_dict(self.timml_layer)
        assoc_data = self.table_to_dict(self.assoc_layer)
        timml_errors = self.schema.validate_timml(data)
        assoc_errors = self.assoc_schema.validate_timml(assoc_data)
        errors = {**timml_errors, **assoc_errors}
        if errors:
            return errors, None
        else:
            grouped = self.groupby(assoc_data, "inhomogeneity_id")
            inhoms = []
            for row in data:
                inhom_id = row["inhomogeneity_id"]
                kwargs = self._aquifer_data(grouped[inhom_id])
                kwargs["xy"] = self._polygon_xy(row)
                kwargs["order"] = row["order"]
                kwargs["ndeg"] = row["ndegrees"]
                inhoms.append(kwargs)
            return inhoms
