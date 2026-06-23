import abc
from typing import Any, Dict

from qgis.core import (
    QgsDefaultValue,
    QgsField,
    QgsSingleSymbolRenderer,
)
from qgis.PyQt.QtCore import QVariant

from qgistim.core.elements.colors import GREY, LIGHT_GREY
from qgistim.core.elements.default_values import DefaultValues
from qgistim.core.elements.element import TransientElement
from qgistim.core.elements.schemata import RowWiseSchema
from qgistim.core.schemata import (
    AllGreaterEqual,
    AllLesserEqual,
    AllOrNone,
    Optional,
    Positive,
    Required,
    StrictlyPositive,
)


class ParticleSchema(RowWiseSchema):
    steady_schemata = {
        "geometry": Required(),
        "z_start": Required(),
        "max_horizontal_step": Required(StrictlyPositive()),
        "max_vertical_step_fraction": Required(StrictlyPositive()),
        "nstep_max": Required(StrictlyPositive()),
    }
    transient_schemata = {
        "time_start": Optional(Positive()),
        "time_step": Optional(Positive()),
        "time_end": Optional(Positive()),
        "time_start_offset": Optional(Positive()),
    }
    steady_consistency_schemata = (
        AllGreaterEqual("z_start", "minimum_z_aquifer"),
        AllLesserEqual("z_start", "maximum_z_aquifer"),
    )
    transient_consistency_schemata = (
        AllOrNone(("time_start", "time_step", "time_end", "time_start_offset")),
    )


class Particle(TransientElement, abc.ABC):
    element_type = None
    geometry_type = "Point"
    steady_attributes = (
        QgsField("label", QVariant.String),
        QgsField("z_start", QVariant.Double),
        QgsField("max_horizontal_step", QVariant.Double),
        QgsField("max_vertical_step_fraction", QVariant.Double),
        QgsField("nstep_max", QVariant.Int),
        QgsField("time_start", QVariant.Double),
        QgsField("time_step", QVariant.Double),
        QgsField("time_end", QVariant.Double),
        QgsField("time_start_offset", QVariant.Double),
    )
    steady_defaults = {
        "nstep_max": QgsDefaultValue("100"),
        "time_start_offset": QgsDefaultValue(DefaultValues.tmin),
    }
    transient_columns = (
        "time_start",
        "time_step",
        "time_end",
        "time_start_offset",
    )
    schema = ParticleSchema()

    def process_steady_row(self, row, other=None) -> Dict[str, Any]:
        x, y = self.point_xy(row)
        return {
            "xstart": x,
            "ystart": y,
            "zstart": row["z_start"],
            "hstepmax": row["max_horizontal_step"],
            "vstepfrac": row["max_vertical_step_fraction"],
            "nstepmax": row["nstep_max"],
            "label": row["label"],
        }

    def process_transient_row(self, row, grouped) -> tuple[Dict[str, Any], set[float]]:
        x, y = self.point_xy(row)
        times = {row["time_end"]}
        return {
            "xstart": x,
            "ystart": y,
            "zstart": row["z_start"],
            "tstartend": [row["time_start"], row["time_end"]],
            "tstartoffset": row["time_start_offset"],
            "hstepmax": row["max_horizontal_step"],
            "tstep": row["time_step"],
            "nstepmax": row["nstep_max"],
            "label": row["label"],
        }, times


class Particle_Forward(Particle):
    element_type = "Particle Forward"

    @classmethod
    def renderer(cls) -> QgsSingleSymbolRenderer:
        return cls.marker_renderer(color=GREY, size="3")

    @classmethod
    def renderer_output(cls) -> QgsSingleSymbolRenderer:
        return cls.line_renderer(color=GREY, width="1.0")


class Particle_Backward(Particle):
    element_type = "Particle Backward"

    def process_steady_row(self, row, other=None) -> Dict[str, Any]:
        data = super().process_steady_row(row, other)
        data["hstepmax"] = -data[
            "hstepmax"
        ]  # Reverse horizontal step reverses direction
        return data

    def process_transient_row(self, row, grouped) -> tuple[Dict[str, Any], set[float]]:
        data, times = super().process_transient_row(row, grouped)
        data["hstepmax"] = -data[
            "hstepmax"
        ]  # Reverse horizontal step reverses direction
        return data, times

    @classmethod
    def renderer(cls) -> QgsSingleSymbolRenderer:
        return cls.marker_renderer(color=LIGHT_GREY, size="3")

    @classmethod
    def renderer_output(cls) -> QgsSingleSymbolRenderer:
        return cls.line_renderer(color=LIGHT_GREY, width="1.0")
