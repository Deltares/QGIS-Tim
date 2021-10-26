"""
Common utilities 
"""
import pathlib
import re
from collections import defaultdict
from functools import partial
from typing import Any, Callable, Dict, NamedTuple, Tuple, Union

import fiona
import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr

gpd.options.use_pygeos = False
FloatArray = np.ndarray


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


# Some geometry helpers
# ---------------------
def point_coordinates(dataframe) -> Tuple[FloatArray, FloatArray]:
    """
    Get the x and y coordinates from a GeoDataFrame of points.

    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    x: np.array
    y: np.array
    """
    return dataframe["geometry"].x, dataframe["geometry"].y


def linestring_coordinates(row) -> Tuple[FloatArray, FloatArray]:
    """
    Get the x and y coordinates from a single LineString feature,
    which is one row in a GeoDataFrame.

    Parameters
    ----------
    row: geopandas.GeoSeries

    Returns
    -------
    x: np.array
    y: np.array
    """
    return np.array(row["geometry"].coords)


def polygon_coordinates(row) -> Tuple[FloatArray, FloatArray]:
    """
    Get the x and y coordinates from a single Polygon feature,
    which is one row in a GeoDataFrame.

    Parameters
    ----------
    row: geopandas.GeoSeries

    Returns
    -------
    x: np.array
    y: np.array
    """
    return np.array(row["geometry"].exterior.coords)


def aquifer_data(
    dataframe: gpd.GeoDataFrame, transient: bool = False
) -> Dict[str, Any]:
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
    return d


def parse_name(layername: str) -> Tuple[str, str]:
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
        raise ValueError("Neither timml nor ttim in layername")
    return tim_type, element_type, name


def model_specification(path, active_elements):
    gpkg_names = fiona.listlayers(path)
    dd = defaultdict
    grouped_names = dd(partial(dd, partial(dd, list)))
    for layername in gpkg_names:
        tim_type, element_type, name = parse_name(layername)
        grouped_names[element_type][name][tim_type] = layername

    aquifer_entry = grouped_names.pop("Aquifer")["Aquifer"]
    aquifer = gpd.read_file(path, layer=aquifer_entry["timml"])
    temporal_settings = gpd.read_file(path, layer=aquifer_entry["ttim"])
    domain_entry = grouped_names.pop("Domain")["Domain"]
    domain = gpd.read_file(path, layer=domain_entry["timml"])
    output_times = gpd.read_file(path, layer=domain_entry["ttim"])

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


def trimesh(spec: TimmlModelSpecification, cellsize: float):
    # Only import it if needed
    import geomesh

    domain = spec.domain

    geometry = []
    for spec in spec.elements.values():
        df = spec.dataframe
        if spec.elementtype in ["Well", "HeadWell"]:
            df.geometry = df.buffer(cellsize, resolution=2)
        if spec.elementtype in ["PolygonInhomogeneity", "Building Pit"]:
            pass
        elif spec.elementtype in ["Impermeable Line Doublet", "Leaky Line Doublet"]:
            df.geometry = df.buffer(cellsize * 0.01, cap_style=2, join_style=2)
        geometry.append(
            gpd.overlay(df, domain, how="intersection").loc[:, ["geometry"]]
        )

    gdf = pd.concat([domain.loc[:, ["geometry"]], *geometry])
    gdf["cellsize"] = cellsize
    # intersect bounding box with elements
    mesher = geomesh.TriangleMesher(gdf)
    mesher.minimum_angle = 0.01
    mesher.conforming_delaunay = False
    nodes, face_nodes = mesher.generate()
    centroids = nodes[face_nodes].mean(axis=1)
    return nodes, face_nodes, centroids
