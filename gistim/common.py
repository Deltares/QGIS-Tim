"""
Common utilities used by conversions from GeoPackage (GPKG) layers to TimML and
TTim elements.

The relation between a GPKG layer and the elements is not perfect. A GPGK layer
consists of a table, with optionally an associated geometry for every row. This
matches one to one for elements such as HeadLineSinkStrings, Wells, etc: for
these elements, one row equals one element.

For elements such as PolygonImhomogenities, this is not the case. Every geometry
(a polygon) requires a table of its own. These tables are stored in associated
tables; their association is by name.

For transient (TTim) elements, the same is true: elements require an additional
table for their timeseries data, which should require repeating the geometry
for every time step. In this package, we assume that any ttim element is
accompanied by a timml element; the QGIS plugin always sets up the layer ih
that manner.

When processing a GPKG, we first parse the names, and group the different
tables together in the ElementSpecifications below. The ``timml_elements`` and
``ttim_elements`` then convert these grouped tables into ``timml`` and ``ttim``
models.
"""
import numbers
import pathlib
import re
from collections import defaultdict
from functools import partial
from typing import Any, Dict, NamedTuple, Tuple, Union

import fiona
import geopandas as gpd
import numpy as np
import pandas as pd

FloatArray = np.ndarray


def filter_scalar_nan(value: Any) -> Any:
    if isinstance(value, numbers.Real) and np.isnan(value):
        return None
    else:
        return value


def filter_nan(row: Union[Dict, pd.Series]):
    """
    Newer versions of geopandas return NaN rather than None for columns.
    TimML & TTim expect None for optional values.
    """
    return {k: filter_scalar_nan(v) for k, v in row.items()}


class ElementSpecification(NamedTuple):
    elementtype: str
    active: bool
    dataframe: gpd.GeoDataFrame
    associated_dataframe: gpd.GeoDataFrame


class TransientElementSpecification(NamedTuple):
    elementtype: str
    active: bool
    dataframe: gpd.GeoDataFrame
    steady_spec: ElementSpecification


class TimmlModelSpecification(NamedTuple):
    aquifer: gpd.GeoDataFrame
    elements: Dict[str, ElementSpecification]
    domain: gpd.GeoDataFrame


class TtimModelSpecification(NamedTuple):
    aquifer: gpd.GeoDataFrame
    temporal_settings: gpd.GeoDataFrame
    elements: Dict[str, ElementSpecification]
    domain: gpd.GeoDataFrame
    output_times: FloatArray


# Extract coordinates from geodataframe
# -------------------------------------
def point_coordinates(dataframe) -> Tuple[FloatArray, FloatArray]:
    return dataframe["geometry"].x, dataframe["geometry"].y


def remove_zero_length(coords: FloatArray):
    dx_dy = np.diff(coords, axis=0)
    notzero = (dx_dy != 0).any(axis=1)
    keep = np.full(len(coords), True)
    keep[1:] = notzero
    return coords[keep]


def linestring_coordinates(row) -> FloatArray:
    return remove_zero_length(np.array(row["geometry"].coords))


def polygon_coordinates(row) -> FloatArray:
    return remove_zero_length(np.array(row["geometry"].exterior.coords))


# Parse GPKG content to Tim input
# -------------------------------
def aquifer_data(
    dataframe: gpd.GeoDataFrame, transient: bool = False
) -> Dict[str, Any]:
    """
    Convert a table created by the QGIS plugin to the layer configuration and
    keywords arguments as expected by TimML or TTim.
    """
    # Make sure the layers are in the right order.
    dataframe = dataframe.sort_values(by="layer").set_index("layer")
    nlayer = len(dataframe)
    # Deal with optional semi-confined top layer.
    hstar = dataframe.loc[0, "semiconf_head"]
    semi = pd.notnull(hstar)
    kaq = dataframe["aquifer_k"].values

    if semi:
        c = dataframe["aquitard_c"].values
        porosity = np.empty(nlayer * 2)
        z = np.empty(nlayer * 2 + 1)
        z[0] = dataframe.loc[0, "semiconf_top"]
        z[1::2] = dataframe["aquifer_top"].values
        z[2::2] = dataframe["aquifer_bottom"].values
        porosity[::2] = dataframe["aquitard_npor"].values
        porosity[1::2] = dataframe["aquifer_npor"].values
        topboundary = "semi"
        storage_aquifer = dataframe["aquifer_s"].values
        storage_aquitard = dataframe["aquitard_s"].values
    else:
        c = dataframe["aquitard_c"].values[1:]
        z = np.empty(nlayer * 2)
        z[::2] = dataframe["aquifer_top"].values
        z[1::2] = dataframe["aquifer_bottom"].values
        porosity = np.empty(nlayer * 2 - 1)
        porosity[::2] = dataframe["aquifer_npor"].values
        porosity[1::2] = dataframe["aquitard_npor"].values[1:]
        topboundary = "conf"
        storage_aquifer = dataframe["aquifer_s"].values
        storage_aquitard = dataframe["aquifer_s"].values[1:]

    d = {
        "kaq": kaq,
        "z": z,
        "c": c,
        "topboundary": topboundary,
    }
    if transient:
        d["Sll"] = storage_aquitard
        d["Saq"] = storage_aquifer
        # TODO: for now, assume there is always at least one specific yield
        # this is the aquifer if conf, the aquitard if semi
        d["phreatictop"] = True
    else:
        d["npor"] = porosity
        d["hstar"] = hstar

    # For inhomogeneities
    if "rate" in dataframe:
        d["N"] = dataframe.loc[0, "rate"]

    # For leaky building pit
    if "resistance" in dataframe:
        d["res"] = dataframe.loc[0, "resistance"]

    filtered = {}
    for k, value in d.items():
        if isinstance(value, np.ndarray):
            filtered[k] = [filter_scalar_nan(v) for v in value]
        else:
            filtered[k] = filter_scalar_nan(value)

    return filtered


def parse_name(layername: str) -> Tuple[str, str, str]:
    """
    Based on the layer name find out:

    * whether it's a timml or ttim element;
    * which element type it is;
    * what the user provided name is.

    For example:
    parse_name("timml Headwell: drainage") -> ("timml", "Head Well", "drainage")

    Some grouping of tables occurs here.
    """
    prefix, name = layername.split(":")
    element_type = re.split("timml |ttim ", prefix)[1]
    mapping = {
        "Computation Times": "Domain",
        "Temporal Settings": "Aquifer",
        "Polygon Inhomogeneity Properties": "Polygon Inhomogeneity",
        "Building Pit Properties": "Building Pit",
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
        raise ValueError(f"Neither timml nor ttim in layername: {layername}")
    return tim_type, element_type, name


def model_specification(
    path: Union[str, pathlib.Path], active_elements: Dict[str, bool]
) -> Tuple[TimmlModelSpecification, TtimModelSpecification]:
    """
    Group the different layers of a GPKG into model specifications for timml
    and ttim. The grouping occurs solely on the basis of layer names.
    """
    # Start by listing all layers
    gpkg_names = fiona.listlayers(path)
    # Group all these names together (using a defaultdict)
    dd = defaultdict
    grouped_names = dd(partial(dd, partial(dd, list)))
    for layername in gpkg_names:
        tim_type, element_type, name = parse_name(layername)
        grouped_names[element_type][name][tim_type] = layername

    # Grab the names of the required elements and load the data into
    # geodataframes.
    aquifer_entry = grouped_names.pop("Aquifer")["Aquifer"]
    aquifer = gpd.read_file(path, layer=aquifer_entry["timml"])
    temporal_settings = gpd.read_file(path, layer=aquifer_entry["ttim"])
    domain_entry = grouped_names.pop("Domain")["Domain"]
    domain = gpd.read_file(path, layer=domain_entry["timml"])

    if len(domain.index) == 0:
        raise ValueError("Domain not defined")

    output_times = gpd.read_file(path, layer=domain_entry["ttim"])

    # Load the data all other elements into geodataframes.
    ttim_elements = {}
    timml_elements = {}
    for element_type, element_group in grouped_names.items():
        for name, group in element_group.items():
            timml_name = group["timml"]
            timml_assoc_name = group.get("timml_assoc", None)
            ttim_name = group.get("ttim", timml_name)

            timml_df = gpd.read_file(path, layer=timml_name)
            timml_assoc_df = (
                gpd.read_file(path, layer=timml_assoc_name)
                if timml_assoc_name is not None
                else None
            )
            ttim_df = (
                gpd.read_file(path, layer=ttim_name) if ttim_name is not None else None
            )

            # Use the background aquifer for a semi-confined top
            if element_type in ("Polygon Area Sink", "Polygon Semi-Confined Top"):
                timml_assoc_df = aquifer

            timml_spec = ElementSpecification(
                elementtype=element_type,
                active=active_elements.get(timml_name, False),
                dataframe=timml_df,
                associated_dataframe=timml_assoc_df,
            )

            ttim_spec = TransientElementSpecification(
                elementtype=element_type,
                active=active_elements.get(ttim_name, False),
                dataframe=ttim_df,
                steady_spec=timml_spec,
            )
            timml_elements[timml_name] = timml_spec
            ttim_elements[ttim_name] = ttim_spec

    return (
        TimmlModelSpecification(aquifer, timml_elements, domain),
        TtimModelSpecification(
            aquifer,
            temporal_settings,
            ttim_elements,
            domain,
            np.sort(output_times["time"].values),
        ),
    )


# Three helpers for conversion to Python scripts
# ----------------------------------------------
def dict_to_kwargs_code(data: dict) -> str:
    strings = []
    for key, value in data.items():
        if isinstance(value, np.ndarray):
            value = value.tolist()
        elif isinstance(value, str) and key not in ("model", "timmlmodel"):
            value = f'"{value}"'
        strings.append(f"{key}={value}")
    return ",".join(strings)


def sanitized(name: str) -> str:
    return name.split(":")[-1].replace(" ", "_")


def headgrid_code(domain: gpd.GeoDataFrame) -> Tuple[str, str]:
    xmin, ymin, xmax, ymax = domain.bounds.iloc[0]
    dy = (ymax - ymin) / 50.0
    if dy > 500.0:
        dy = round(dy / 500.0) * 500.0
    elif dy > 50.0:
        dy = round(dy / 50.0) * 50.0
    elif dy > 5.0:  # round to five
        dy = round(dy / 5.0) * 5.0
    elif dy > 1.0:
        dy = round(dy)
    (xmin, xmax, ymin, ymax) = round_extent((xmin, xmax, ymin, ymax), dy)
    xmin += 0.5 * dy
    xmax += 0.5 * dy
    ymax -= 0.5 * dy
    xmin -= 0.5 * dy
    xg = f"np.arange({xmin}, {xmax}, {dy})"
    yg = f"np.arange({ymax}, {ymin}, -{dy})"
    return xg, yg


# Output methods
# --------------
def round_extent(extent: Tuple[float], cellsize: float) -> Tuple[float]:
    """
    Increases the extent until all sides lie on a coordinate
    divisible by cellsize.

    Parameters
    ----------
    extent: Tuple[float]
        xmin, xmax, ymin, ymax
    cellsize: float
        Desired cell size of the output head grids

    Returns
    -------
    extent: Tuple[float]
        xmin, xmax, ymin, ymax
    """
    xmin, xmax, ymin, ymax = extent
    xmin = np.floor(xmin / cellsize) * cellsize
    ymin = np.floor(ymin / cellsize) * cellsize
    xmax = np.ceil(xmax / cellsize) * cellsize
    ymax = np.ceil(ymax / cellsize) * cellsize
    return xmin, xmax, ymin, ymax


def gridspec(
    path: Union[pathlib.Path, str], cellsize: float
) -> Tuple[Tuple[float], Any]:
    """
    Infer the grid specification from the geopackage ``timmlDomain`` layer and
    the provided cellsize.

    Parameters
    ----------
    path: Union[pathlib.Path, str]
        Path to the GeoPackage file.
    cellsize: float
        Desired cell size of the output head grids

    Returns
    -------
    extent: tuple[float]
        xmin, xmax, ymin, ymax
    crs: Any
        Coordinate Reference System
    """
    domain = gpd.read_file(path, layer="timml Domain:Domain")
    xmin, ymin, xmax, ymax = domain.bounds.iloc[0]
    extent = (xmin, xmax, ymin, ymax)
    return round_extent(extent, cellsize), domain.crs
