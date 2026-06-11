import abc
from typing import Any, Dict

from PyQt5.QtCore import QVariant
from qgis.core import (
    QgsDefaultValue,
    QgsField,
    QgsSingleSymbolRenderer,
)

from qgistim.core.elements.colors import GREY, LIGHT_GREY
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
    }
    steady_consistency_schemata = (
        AllGreaterEqual("z_start", "minimum_z_aquifer"),
        AllLesserEqual("z_start", "maximum_z_aquifer"),
    )
    transient_consistency_schemata = (
        AllOrNone(("time_start", "time_step", "time_end")),
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
    )
    steady_defaults = {
        "nstep_max": QgsDefaultValue("100"),
    }
    transient_columns = (
        "time_start",
        "time_step",
        "time_end",
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

    def process_transient_row(self, row, grouped) -> Dict[str, Any]:
        x, y = self.point_xy(row)
        return {
            "xstart": x,
            "ystart": y,
            "zstart": row["z_start"],
            "hstepmax": row["max_horizontal_step"],
            "tstart": row["time_start"],
            "delt": row["time_step"],
            "tmax": row["time_end"],
            "nstepmax": row["nstep_max"],
            "label": row["label"],
        }


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

    def process_transient_row(self, row, grouped) -> Dict[str, Any]:
        data = super().process_transient_row(row, grouped)
        data["hstepmax"] = -data[
            "hstepmax"
        ]  # Reverse horizontal step reverses direction
        return data

    @classmethod
    def renderer(cls) -> QgsSingleSymbolRenderer:
        return cls.marker_renderer(color=LIGHT_GREY, size="3")

    @classmethod
    def renderer_output(cls) -> QgsSingleSymbolRenderer:
        return cls.line_renderer(color=LIGHT_GREY, width="1.0")
