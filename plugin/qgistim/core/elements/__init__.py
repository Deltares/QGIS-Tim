import re
from collections import defaultdict
from functools import partial
from typing import List, Tuple

from qgistim.core import geopackage
from qgistim.core.elements.aquifer import Aquifer
from qgistim.core.elements.building_pit import BuildingPit
from qgistim.core.elements.circular_area_sink import CircularAreaSink
from qgistim.core.elements.constant import Constant
from qgistim.core.elements.discharge_observation import DischargeObservation
from qgistim.core.elements.domain import Domain
from qgistim.core.elements.element import Element
from qgistim.core.elements.head_line_sink import River
from qgistim.core.elements.headwell import HeadWell, RemoteHeadWell
from qgistim.core.elements.impermeable_line_doublet import ImpermeableWall
from qgistim.core.elements.leaky_building_pit import LeakyBuildingPit
from qgistim.core.elements.leaky_line_doublet import LeakyWall
from qgistim.core.elements.line_sink_ditch import Ditch
from qgistim.core.elements.observation import HeadObservation
from qgistim.core.elements.polygon_area_sink import PolygonAreaSink
from qgistim.core.elements.polygon_inhomogeneity import PolygonInhomogeneity
from qgistim.core.elements.polygon_semi_confined_top import PolygonSemiConfinedTop
from qgistim.core.elements.uniform_flow import UniformFlow
from qgistim.core.elements.well import Well

ELEMENTS = {
    element.element_type: element
    for element in (
        Aquifer,
        Domain,
        Constant,
        UniformFlow,
        Well,
        HeadWell,
        RemoteHeadWell,
        River,
        Ditch,
        CircularAreaSink,
        ImpermeableWall,
        LeakyWall,
        PolygonAreaSink,
        PolygonSemiConfinedTop,
        PolygonInhomogeneity,
        BuildingPit,
        LeakyBuildingPit,
        HeadObservation,
        DischargeObservation,
    )
}


def parse_name(layername: str) -> Tuple[str, str, str]:
    """
    Based on the layer name find out:

    * whether it's a steady-state or transient element;
    * which element type it is;
    * what the user provided name is.

    For example:
    parse_name("steady-state Headwell:drainage") -> ("steady-state", "Head Well", "drainage")
    """
    prefix, name = layername.split(":")
    element_type = re.split("steady-state |transient ", prefix)[1]
    mapping = {
        "Computation Times": "Domain",
        "Temporal Settings": "Aquifer",
        "Polygon Inhomogeneity Properties": "Polygon Inhomogeneity",
        "Building Pit Properties": "Building Pit",
        "Leaky Building Pit Properties": "Leaky Building Pit",
    }
    element_type = mapping.get(element_type, element_type)
    if "steady-state" in prefix:
        if "Properties" in prefix:
            tim_type = "steady-state_assoc"
        else:
            tim_type = "steady-state"
    elif "transient" in prefix:
        tim_type = "transient"
    else:
        raise ValueError("Neither steady-state nor transient in layername")
    return tim_type, element_type, name


def load_elements_from_geopackage(path: str) -> List[Element]:
    # List the names in the geopackage
    gpkg_names = geopackage.layers(path)

    # Group them on the basis of name
    dd = defaultdict
    grouped_names = dd(partial(dd, partial(dd, list)))
    for layername in gpkg_names:
        tim_type, element_type, name = parse_name(layername)
        grouped_names[element_type][name][tim_type] = layername

    elements = []
    for element_type, group in grouped_names.items():
        for name in group:
            elements.append(ELEMENTS[element_type](path, name))

    return elements
