"""
Common utilities 
"""
import pathlib
import re
from typing import Any, Callable, Dict, NamedTuple, Tuple, Union

import fiona
import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr


FloatArray = np.ndarray


class ElementSpecification(NamedTuple):
    elementtype: str
    active: bool
    dataframe: gpd.GeoDataFrame
    associated_dataframe: gpd.GeoDataFrame


class ModelSpecification(NamedTuple):
    aquifer: ElementSpecification
    elements: Dict[str, ElementSpecification]


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


def aquifer_data(dataframe):
    # Make sure the layers are in the right order.
    dataframe = dataframe.sort_values(by="layer").set_index("layer")
    nlayer = len(dataframe)
    # Deal with optional semi-confined top layer.
    hstar = dataframe.loc[0, "head_topboundary"]
    semi = pd.notnull(hstar)
    kaq = dataframe["conductivity"].values

    if semi:
        c = dataframe["resistance"].values
        porosity = np.empty(nlayer * 2)
        z = np.empty(nlayer * 2 + 1)
        z[0] = dataframe.loc[0, "z_topboundary"]
        z[1::2] = dataframe["z_top"].values
        z[2::2] = dataframe["z_bottom"].values
        porosity[::2] = dataframe["porosity_aquitard"].values
        porosity[1::2] = dataframe["porosity_aquifer"].values
        topboundary = "semi"
    else:
        c = dataframe["resistance"].values[1:]
        z = np.empty(nlayer * 2)
        z[::2] = dataframe["z_top"].values
        z[1::2] = dataframe["z_bottom"].values
        porosity = np.empty(nlayer * 2 - 1)
        porosity[::2] = dataframe["porosity_aquifer"].values
        porosity[1::2] = dataframe["porosity_aquitard"].values[1:]
        topboundary = "conf"

    return {
        "kaq": kaq,
        "z": z,
        "c": c,
        "npor": porosity,
        "topboundary": topboundary,
        "hstar": hstar,
    }


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
    Infer the grid specification from the geopackage ``timmlDomain``  layer and
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
    domain = gpd.read_file(path, layer="timml Domain")
    xmin, ymin, xmax, ymax = domain.bounds.iloc[0]
    extent = (xmin, xmax, ymin, ymax)
    return round_extent(extent, cellsize), domain.crs
