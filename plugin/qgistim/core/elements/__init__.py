import re
from collections import defaultdict
from functools import partial
from typing import List, Tuple

from qgistim.core import geopackage
from qgistim.core.elements.aquifer import Aquifer
from qgistim.core.elements.building_pit import BuildingPit
from qgistim.core.elements.circular_area_sink import CircularAreaSink
from qgistim.core.elements.constant import Constant
from qgistim.core.elements.domain import Domain
from qgistim.core.elements.element import Element
from qgistim.core.elements.head_line_sink import HeadLineSink
from qgistim.core.elements.headwell import HeadWell, RemoteHeadWell
from qgistim.core.elements.impermeable_line_doublet import ImpermeableLineDoublet
from qgistim.core.elements.leaky_building_pit import LeakyBuildingPit
from qgistim.core.elements.leaky_line_doublet import LeakyLineDoublet
from qgistim.core.elements.line_sink_ditch import LineSinkDitch
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
        HeadLineSink,
        LineSinkDitch,
        CircularAreaSink,
        ImpermeableLineDoublet,
        LeakyLineDoublet,
        PolygonAreaSink,
        PolygonSemiConfinedTop,
        PolygonInhomogeneity,
        BuildingPit,
        LeakyBuildingPit,
        HeadObservation,
    )
}


def parse_name(layername: str) -> Tuple[str, str, str]:
    """
    Based on the layer name find out:

    * whether it's a timml or ttim element;
    * which element type it is;
    * what the user provided name is.

    For example:
    parse_name("timml Headwell:drainage") -> ("timml", "Head Well", "drainage")
    """
    prefix, name = layername.split(":")
    element_type = re.split("timml |ttim ", prefix)[1]
    mapping = {
        "Computation Times": "Domain",
        "Temporal Settings": "Aquifer",
        "Polygon Inhomogeneity Properties": "Polygon Inhomogeneity",
        "Building Pit Properties": "Building Pit",
        "Leaky Building Pit Properties": "Leaky Building Pit",
    }
    element_type = mapping.get(element_type, element_type)
    if "timml" in prefix:
        if "Properties" in prefix:
            tim_type = "timml_assoc"
        else:
            tim_type = "timml"
    elif "ttim" in prefix:
        tim_type = "ttim"
    else:
        raise ValueError("Neither timml nor ttim in layername")
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
