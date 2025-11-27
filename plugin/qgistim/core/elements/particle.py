import abc
from typing import Any, Dict

from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QColor
from qgis.core import (
    QgsArrowSymbolLayer,
    QgsDefaultValue,
    QgsField,
    QgsLineSymbol,
    QgsSingleSymbolRenderer,
)
from qgistim.core.elements.colors import GREY
from qgistim.core.elements.element import TransientElement
from qgistim.core.elements.schemata import RowWiseSchema
from qgistim.core.schemata import (
    AllOrNone,
    AllRequired,
    Membership,
    NotBoth,
    Optional,
    Positive,
    Required,
    StrictlyIncreasing,
    StrictlyPositive,
)


class ParticleSchema(RowWiseSchema):
    timml_schemata = {
        "geometry": Required(),
        "z_start": Required(),
        "time_end": Required(Positive()),
        "hstep_max": Required(StrictlyPositive()),
        "vstep_fraction": Required(StrictlyPositive()),
        "nstep_max": Required(StrictlyPositive()),
    }
    ttim_schemata = {
        "time_start": Optional(Positive()),
        "delt": Optional(Positive()),
        "time_end": Optional(Positive()),
    }
    ttim_consistency_schemata = (
        AllOrNone(("time_start", "delt", "time_end")),
    )


class Particle(TransientElement, abc.ABC):
    element_type = None
    geometry_type = "Point"
    timml_attributes = (
        QgsField("label", QVariant.String),
        QgsField("z_start", QVariant.Double),
        QgsField("time_end", QVariant.Double),
        QgsField("hstep_max", QVariant.Double),
        QgsField("vstep_fraction", QVariant.Double),
        QgsField("nstep_max", QVariant.Int),
    )
    ttim_attributes = (
        QgsField("time_start", QVariant.Double),
        QgsField("time_end", QVariant.Double),
    )
    timml_defaults = {
        "nstep_max": QgsDefaultValue("100"),
    }
    transient_columns = (
        "time_start",
        "time_end",
    )
    schema = ParticleSchema()

    @classmethod
    def renderer(cls) -> QgsSingleSymbolRenderer:
        return cls.marker_renderer(color=GREY, size="3")

    def process_timml_row(self, row, other=None) -> Dict[str, Any]:
        x, y = self.point_xy(row)
        return {
            "xstart": x,
            "ystart": y,
            "zstart": row["z_start"],
            "hstepmax": row["hstep_max"],
            "vstepfrac": row["vstep_fraction"],
            "tmax": row["time_end"],
            "nstepmax": row["nstep_max"],
            "label": row["label"],
        }

    def process_ttim_row(self, row, grouped) -> Dict[str, Any]:
        x, y = self.point_xy(row)
        return {
            "xstart": x,
            "ystart": y,
            "zstart": row["z_start"],
            "hstepmax": row["hstep_max"],
            "tstart": row["time_start"],
            "delt": row["delt"],
            "tmax": row["time_end"],
            "nstepmax": row["nstep_max"],
            "label": row["label"],
        }

class Particle_Forward(Particle):
    element_type = "Particle Forward"

class Particle_Backward(Particle):
    element_type = "Particle Backward"

    def process_timml_row(self, row, other=None) -> Dict[str, Any]:
        data = super().process_timml_row(row, other)
        data["hstepmax"] = -data["hstepmax"] # Reverse horizontal step reverses direction
        return data

    def process_ttim_row(self, row, grouped) -> Dict[str, Any]:
        data = super().process_ttim_row(row, grouped)
        data["hstepmax"] = -data["hstepmax"] # Reverse horizontal step reverses direction
        return data