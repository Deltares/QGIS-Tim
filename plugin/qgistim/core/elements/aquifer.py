from PyQt5.QtCore import QVariant
from qgis.core import QgsDefaultValue, QgsField
from qgistim.core import geopackage
from qgistim.core.elements.element import ElementSchema, TransientElement
from qgistim.core.schemata import (
    AllGreaterEqual,
    AllRequired,
    OffsetAllRequired,
    OptionalFirstOnly,
    Positive,
    Range,
    SemiConfined,
    SingleRow,
    StrictlyDecreasing,
)


class AquiferSchema(ElementSchema):
    timml_schemata = {
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
    ttim_schemata = {
        "aquitard_s": OffsetAllRequired(Positive()),
        "aquifer_s": AllRequired(Positive()),
    }
    ttim_consistency_schemata = (SingleRow(),)


class Aquifer(TransientElement):
    element_type = "Aquifer"
    geometry_type = "No Geometry"
    timml_attributes = [
        QgsField("layer", QVariant.Int),
        QgsField("aquifer_top", QVariant.Double),
        QgsField("aquifer_bottom", QVariant.Double),
        QgsField("aquitard_c", QVariant.Double),
        QgsField("aquifer_k", QVariant.Double),
        QgsField("semiconf_top", QVariant.Double),
        QgsField("semiconf_head", QVariant.Double),
        QgsField("aquitard_s", QVariant.Double),
        QgsField("aquifer_s", QVariant.Double),
        QgsField("aquitard_npor", QVariant.Double),
        QgsField("aquifer_npor", QVariant.Double),
    ]
    ttim_attributes = (
        QgsField("time_min", QVariant.Double),
        QgsField("laplace_inversion_M", QVariant.Int),
        QgsField("reference_date", QVariant.DateTime),
    )
    ttim_defaults = {
        "time_min": QgsDefaultValue("0.01"),
        "laplace_inversion_M": QgsDefaultValue("10"),
    }
    transient_columns = (
        "aquitard_s",
        "aquifer_s",
        "aquitard_npor",
        "aquifer_npor",
    )
    schema = AquiferSchema()

    def __init__(self, path: str, name: str):
        self._initialize_default(path, name)
        self.timml_name = f"timml {self.element_type}:Aquifer"
        self.ttim_name = "ttim Temporal Settings:Aquifer"

    def write(self):
        self.timml_layer = geopackage.write_layer(
            self.path, self.timml_layer, self.timml_name, newfile=True
        )
        self.ttim_layer = geopackage.write_layer(
            self.path, self.ttim_layer, self.ttim_name
        )
        self.set_defaults()

    def remove_from_geopackage(self):
        """This element may not be removed."""
        return

    def to_timml(self):
        data = self.table_to_dict(self.timml_layer)
        errors = self.schema.validate_timml(data)
        return errors, data

    def to_ttim(self):
        data = self.table_to_dict(self.timml_layer)
        errors = self.schema.validate_ttim(data)
        return errors, data
