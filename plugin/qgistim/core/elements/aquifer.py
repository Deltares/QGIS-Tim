from PyQt5.QtCore import QVariant
from qgis.core import QgsDefaultValue, QgsField, QgsVectorLayerUtils

from qgistim.core import geopackage
from qgistim.core.elements.element import ElementExtraction, TransientElement
from qgistim.core.elements.schemata import SingleRowSchema, TableSchema
from qgistim.core.schemata import (
    AllGreaterEqual,
    AllOptional,
    AllRequired,
    OffsetAllRequired,
    OptionalFirstOnly,
    Positive,
    Range,
    Required,
    SemiConfined,
    StrictlyDecreasing,
    StrictlyPositive,
)


class AquiferSchema(TableSchema):
    steady_schemata = {
        "layer": AllRequired(Range()),
        "aquifer_top": AllRequired(StrictlyDecreasing()),
        "aquifer_bottom": AllRequired(StrictlyDecreasing()),
        "aquitard_c": OffsetAllRequired(StrictlyPositive()),
        "aquifer_k": AllRequired(StrictlyPositive()),
        "semiconf_top": OptionalFirstOnly(),
        "semiconf_head": OptionalFirstOnly(),
        "aquifer_npor": AllOptional(Positive()),
        "aquitard_npor": AllOptional(Positive()),
    }
    steady_consistency_schemata = (
        SemiConfined(),
        AllGreaterEqual("aquifer_top", "aquifer_bottom"),
    )
    transient_schemata = {
        "aquitard_s": OffsetAllRequired(Positive()),
        "aquifer_s": AllRequired(Positive()),
    }


class TemporalSettingsSchema(SingleRowSchema):
    transient_schemata = {
        "time_min": Required(StrictlyPositive()),
        "laplace_inversion_M": Required(StrictlyPositive()),
        "start_date": Required(),
    }


class Aquifer(TransientElement):
    element_type = "Aquifer"
    geometry_type = "No Geometry"
    steady_attributes = [
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
    transient_attributes = (
        QgsField("time_min", QVariant.Double),
        QgsField("laplace_inversion_M", QVariant.Int),
        QgsField("start_date", QVariant.DateTime),
    )
    steady_defaults = {
        "aquifer_npor": QgsDefaultValue("0.3"),
        "aquitard_npor": QgsDefaultValue("0.3"),
    }
    transient_defaults = {
        "time_min": QgsDefaultValue("0.01"),
        "laplace_inversion_M": QgsDefaultValue("10"),
        "start_date": QgsDefaultValue(
            "make_datetime(year(now()), month(now()), day(now()), 0, 0, 0)"
        ),
    }
    transient_columns = (
        "aquitard_s",
        "aquifer_s",
    )
    schema = AquiferSchema()
    assoc_schema = TemporalSettingsSchema()

    def __init__(self, path: str, name: str):
        self._initialize_default(path, name)
        self.steady_name = f"steady-state {self.element_type}:Aquifer"
        self.transient_name = "transient Temporal Settings:Aquifer"

    def write(self):
        self.steady_layer = geopackage.write_layer(
            self.path, self.steady_layer, self.steady_name, newfile=True
        )
        self.transient_layer = geopackage.write_layer(
            self.path, self.transient_layer, self.transient_name
        )
        self.set_defaults()

    def remove_from_geopackage(self):
        """This element may not be removed."""
        pass

    def extract_steady_data(self) -> ElementExtraction:
        missing = self.check_steady_columns()
        if missing:
            return ElementExtraction(errors=missing)

        data = self.table_to_dict(layer=self.steady_layer)
        errors = self.schema.validate_steady(name=self.steady_layer.name(), data=data)
        return ElementExtraction(errors=errors, data=data)

    def extract_transient_data(self) -> ElementExtraction:
        missing = self.check_transient_columns()
        if missing:
            return ElementExtraction(errors=missing)

        data = self.table_to_dict(layer=self.steady_layer)
        time_data = self.table_to_records(layer=self.transient_layer)
        errors = {
            **self.schema.validate_transient(name=self.steady_layer.name(), data=data),
            **self.assoc_schema.validate_transient(
                name=self.transient_layer.name(), data=time_data
            ),
        }
        if errors:
            return ElementExtraction(errors=errors)
        return ElementExtraction(data={**data, **time_data[0]})

    def get_start_date(self):
        """
        Returns the start date for the aquifer, which is used in transient
        simulations as well as particle tracking (also for steady-state models).
        This is a special-cased method as the alternative is using
        extract_data(transient=True) to get a start_date, which fails in
        validation for steady-state models.
        """
        time_data = self.table_to_records(layer=self.transient_layer)
        return time_data[0]["start_date"]

    def create_transient_layer(self, crs):
        # Initiate the self.transient_layer and add the default values to it, so that
        # the user doesn't have to do it manually. This to get a start_date
        # somewhere, which is used in transient simulations as well as particle
        # tracking.
        super().create_transient_layer(crs)
        # Set defaults before row is added, so that default values are applied
        # to the row.
        self.set_defaults()

        if self.transient_layer.featureCount() > 0:
            # Return if the layer already contains features, to avoid
            # overwriting user input.
            return

        # Add a single row to the layer, containing default values.
        self.transient_layer.startEditing()
        feature = QgsVectorLayerUtils.createFeature(self.transient_layer)
        self.transient_layer.addFeature(feature)
        self.transient_layer.commitChanges()
        self.transient_layer.updateExtents()

    def extract_data(self, transient: bool) -> ElementExtraction:
        if transient:
            return self.extract_transient_data()
        else:
            return self.extract_steady_data()
