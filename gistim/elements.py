from collections import defaultdict
import pathlib
import re
from typing import Any, Callable, Dict, NamedTuple, Tuple, Union

import fiona
import geopandas as gpd
import numpy as np
import pandas as pd
import timml
import xarray as xr

FloatArray = np.ndarray


class ElementSpecification(NamedTuple):
    elementtype: str
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


# Dataframe to TimML element
# --------------------------
def aquifer(dataframe: gpd.GeoDataFrame) -> timml.Model:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    timml.Model
    """
    # Make sure the layers are in the right order.
    dataframe = dataframe.sort_values(by="index")
    # Deal with optional semi-confined top layer.
    hstar = dataframe["headtop"].values[0]
    semi = pd.notnull(hstar)
    k_offset = 1 if semi else 0
    c_offset = 0 if semi else 1
    kaq = dataframe["conductivity"].values[k_offset::2]
    c = dataframe["resistance"].values[c_offset:-1:2]

    model = timml.ModelMaq(
        kaq=kaq,
        z=np.append(dataframe["top"].values, dataframe["bottom"].values[-1]),
        c=c,
        npor=dataframe["porosity"],
        topboundary="semi" if semi else "conf",
        hstar=hstar,
    )
    return model


def constant(spec: ElementSpecification, model: timml.Model) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    firstrow = spec.dataframe.iloc[0]
    x, y = point_coordinates(firstrow)
    timml.Constant(
        model=model,
        xr=x,
        yr=y,
        hr=firstrow["head"],
    )


def uflow(spec: ElementSpecification, model: timml.Model) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    for _, row in spec.dataframe.iterrows():
        timml.Uflow(
            model=model,
            slope=row["slope"],
            angle=row["angle"],
            label=row["label"],
        )


def well(spec: ElementSpecification, model: timml.Model) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    dataframe = spec.dataframe
    X, Y = point_coordinates(dataframe)
    for ((_, row), x, y) in zip(dataframe.iterrows(), X, Y):
        timml.Well(
            model=model,
            xw=x,
            yw=y,
            Qw=row["discharge"],
            rw=row["radius"],
            res=row["resistance"],
            layers=row["layer"],
            label=row["label"],
        )


def headwell(spec: ElementSpecification, model: timml.Model) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    dataframe = spec.dataframe
    X, Y = point_coordinates(dataframe)
    for ((_, row), x, y) in zip(dataframe.iterrows(), X, Y):
        timml.HeadWell(
            xw=x,
            yw=y,
            hw=row["head"],
            rw=row["radius"],
            res=row["resistance"],
            layers=row["layer"],
            label=row["label"],
            model=model,
        )


def polygoninhom(spec: ElementSpecification, model: timml.Model) -> None:
    """
    Parameters
    ----------
    dataframe: tuple of geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    geometry = spec.dataframe
    properties = spec.associated_dataframe
    # Iterate through the row containing the geometry
    # and iterate through the associated table containing k properties.
    for (geom_fid, row), (assoc_fid, dataframe) in zip(
        geometry.iterrows(), properties.groupby("geometry_fid")
    ):
        if geom_fid != assoc_fid:
            raise ValueError(
                f"Feature IDs do not match up between geometry table and its associated table: "
                f"{geom_fid} versus {assoc_fid}"
            )
        # Make sure the layers are in the right order.
        dataframe = dataframe.sort_values(by="index")
        # Deal with optional semi-confined top layer.
        hstar = dataframe["headtop"].values[0]
        semi = pd.notnull(hstar)
        k_offset = 1 if semi else 0
        c_offset = 0 if semi else 1
        kaq = dataframe["conductivity"].values[k_offset::2]
        c = dataframe["resistance"].values[c_offset:-1:2]

        timml.PolygonInhomMaq(
            model=model,
            xy=polygon_coordinates(row),
            kaq=kaq,
            z=np.append(dataframe["top"].values, dataframe["bottom"].values[-1]),
            c=c,
            npor=dataframe["porosity"],
            topboundary="semi" if semi else "conf",
            hstar=hstar,
            order=row["order"],
            ndeg=row["ndegrees"],
        )


def headlinesink(spec: ElementSpecification, model: timml.Model) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    for _, row in spec.dataframe.iterrows():
        timml.HeadLineSinkString(
            model=model,
            xy=linestring_coordinates(row),
            hls=row["head"],
            res=row["resistance"],
            wh=row["width"],
            order=row["order"],
            layers=row["layer"],
            label=row["label"],
        )


def linesinkditch(spec: ElementSpecification, model: timml.Model) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    for _, row in spec.dataframe.iterrows():
        timml.LineSinkDitchString(
            model=model,
            xy=linestring_coordinates(row),
            Qls=row["discharge"],
            res=row["resistance"],
            wh=row["width"],
            order=row["order"],
            layers=row["layer"],
            label=row["label"],
        )


def leakylinedoublet(spec: ElementSpecification, model: timml.Model) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    for _, row in spec.dataframe.iterrows():
        timml.LeakyLineDoubletString(
            model=model,
            xy=linestring_coordinates(row),
            res=row["resistance"],
            layers=row["layer"],
            order=row["order"],
            label=row["label"],
        )


def implinedoublet(spec: ElementSpecification, model: timml.Model) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    for _, row in spec.dataframe.iterrows():
        timml.ImpLineDoubletString(
            model=model,
            xy=linestring_coordinates(row),
            layers=row["layer"],
            order=row["order"],
            label=row["label"],
        )


def circareasink(spec: ElementSpecification, model: timml.Model) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    for _, row in spec.dataframe.iterrows():
        x, y = row.geometry.centroid.xy
        coords = np.array(row.geometry.exterior.coords)
        x0, y0 = coords[0]
        radius = np.sqrt((x0 - x) ** 2 + (y0 - y) ** 2)
        timml.CircAreaSink(
            model=model,
            xc=x,
            yc=y,
            R=radius,
            N=row["rate"],
        )


# Map the names of the elements to their constructors
# (Basically equivalent to eval(key)...)
MAPPING = {
    "constant": constant,
    "uniformflow": uflow,
    "circareasink": circareasink,
    "well": well,
    "headwell": headwell,
    "polygoninhom": polygoninhom,
    "headlinesink": headlinesink,
    "linesinkditch": linesinkditch,
    "leakylinedoublet": leakylinedoublet,
    "implinedoublet": implinedoublet,
}


# Infer model structure from geopackage layers
# --------------------------------------------
def extract_elementtype(s: str) -> str:
    """
    Extract the TimML element type from the geopackage layer name.
    """
    s = s.lower().split(":")[0]
    return s.split("timml")[-1]


def model_specification(path: Union[str, pathlib.Path]) -> ModelSpecification:
    """
    Parse the layer names of the geopackage to find which elements are present
    in the model.

    Special case the aquifer properties and the constant, since these are
    mandatory for every model, and singleton (there can only be one).

    Returns a named tuple with the layer name of the aquifer, the constant, and
    a dictionary of other element names to its construction function.

    Parameters
    ----------
    path: Union[str, pathlib.Path]
        path to the geopackage containing the model data

    Returns
    -------
    ModelSpecification
    """
    aquifer = None
    elements = {}
    layernames = fiona.listlayers(str(path))
    for layername in layernames:
        elementtype = extract_elementtype(layername)
        print("adding", layername, "as", elementtype)
        if "polygoninhom" in elementtype:
            if elementtype == "polygoninhom":
                # Find geometry table and associated table.
                name = layername.split(":")[-1]
                geometry_name = f"timmlPolygonInhom:{name}"
                properties_name = f"timmlPolygonInhomProperties:{name}"
                elements[layername] = ElementSpecification(
                    elementtype="polygoninhom",
                    dataframe=gpd.read_file(path, layer=geometry_name),
                    associated_dataframe=gpd.read_file(path, layer=properties_name),
                )
            elif elementtype == "polygoninhomproperties":
                # Skip if it's the associated table
                continue
        else:
            element_spec = ElementSpecification(
                elementtype=elementtype,
                dataframe=gpd.read_file(path, layer=layername),
                associated_dataframe=None,
            )
            # Special case aquifer, since only a single instance may occur
            if elementtype == "aquifer":
                aquifer = element_spec
            else:
                elements[layername] = element_spec

    return ModelSpecification(aquifer, elements)


def validate(spec: ModelSpecification) -> None:
    if spec.aquifer is None:
        raise ValueError("Aquifer entry is missing")
    # TODO: more checks


def initialize_model(spec: ModelSpecification) -> timml.Model:
    """
    Initialize a TimML analytic model based on the data in a geopackage.

    Parameters
    ----------
    path: Union[str, pathlib.Path]
        path to the geopackage containing the model data
    spec: ModelSpecification
        Named tuple with the layer name of the aquifer, the constant, and a
        dictionary of other element names to its construction function.

    Returns
    -------
    timml.Model

    Examples
    --------

    >>> import gistim
    >>> path = "my-model.gpkg"
    >>> spec = gistim.model_specification(path)
    >>> model = gistim.initialize_model(spec)
    >>> model.solve()

    """
    validate(spec)
    model = aquifer(spec.aquifer.dataframe)

    for element_spec in spec.elements.values():
        elementtype = element_spec.elementtype
        if elementtype == "domain":
            continue

        # Grab conversion function
        try:
            element = MAPPING[elementtype]
            element(element_spec, model)
        except KeyError as e:
            msg = (
                f'Invalid element specification "{elementtype}". '
                f'Available types are: {", ".join(MAPPING.keys())}.'
            )
            raise KeyError(msg) from e

    return model


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
    Infer the grid specifiction from the geopackage ``timmlDomain``  layer and
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
    domain = gpd.read_file(path, layer="timmlDomain")
    xmin, ymin, xmax, ymax = domain.bounds.iloc[0]
    extent = (xmin, xmax, ymin, ymax)
    return round_extent(extent, cellsize), domain.crs


def headgrid(model: timml.Model, extent: Tuple[float], cellsize: float) -> xr.DataArray:
    """
    Compute the headgrid of the TimML model, and store the results
    in an xarray DataArray with the appropriate dimensions.

    Parameters
    ----------
    model: timml.Model
        Solved model to get heads from
    extent: Tuple[float]
        xmin, xmax, ymin, ymax
    cellsize: float
        Desired cell size of the output head grids

    Returns
    -------
    head: xr.DataArray
        DataArray with dimensions ``("layer", "y", "x")``.
    """
    xmin, xmax, ymin, ymax = extent
    x = np.arange(xmin, xmax, cellsize) + 0.5 * cellsize
    # In geospatial rasters, y is DECREASING with row number
    y = np.arange(ymax, ymin, -cellsize) - 0.5 * cellsize
    head = model.headgrid(x, y)
    nlayer = head.shape[0]
    out = xr.DataArray(
        data=head,
        name="head",
        coords={"layer": range(nlayer), "y": y, "x": x},
        dims=("layer", "y", "x"),
    )
    return out
