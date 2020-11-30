import pathlib
import re
from typing import Any, Callable, Dict, NamedTuple, Tuple, Union

import fiona
import geopandas as gpd
import numpy as np
import timml
import xarray as xr

FloatArray = np.ndarray


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
    return dataframe["geometry"].x.values, dataframe["geometry"].y.values


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
    xy = np.array(row["geometry"].coords).transpose()
    return (xy[0], xy[1])


polygon_coordinates = linestring_coordinates


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
    model = timml.Model(
        kaq=dataframe["conductivity"].values,
        z=np.append(dataframe["top"].values, dataframe["bottom"].values[-1]),
        c=dataframe["resistance"],
        npor=dataframe["porosity"],
        ltype=["a" for _ in range(len(dataframe))],  # TODO
    )
    return model


def constant(dataframe: gpd.GeoDataFrame, model: timml.Model) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    firstrow = dataframe.iloc[0]
    x, y = point_coordinates(firstrow)
    timml.Constant(
        model=model,
        xr=x,
        yr=y,
        hr=firstrow["head"],
    )


def uflow(dataframe: gpd.GeoDataFrame, model: timml.Model) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    for _, row in dataframe.iterrows():
        timml.Uflow(
            model=model,
            slope=row["slope"],
            angle=row["angle"],
            label=row["label"],
        )


def well(dataframe: gpd.GeoDataFrame, model: timml.Model) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
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


def headwell(dataframe: gpd.GeoDataFrame, model: timml.Model) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
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


def polygoninhom(dataframe: gpd.GeoDataFrame, model: timml.Model) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    raise NotImplementedError


def headlinesink(dataframe: gpd.GeoDataFrame, model: timml.Model) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    for _, row in dataframe.iterrows():
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


def linesinkditch(dataframe: gpd.GeoDataFrame, model: timml.Model) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    for _, row in dataframe.iterrows():
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


def leakylinedoublet(dataframe: gpd.GeoDataFrame, model: timml.Model) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    for _, row in dataframe.iterrows():
        timml.LeakyLineDoubletString(
            model=model,
            xy=linestring_coordinates(row),
            res=row["resistance"],
            layers=row["layer"],
            order=row["order"],
            label=row["label"],
        )


def implinedoublet(dataframe: gpd.GeoDataFrame, model: timml.Model) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    for _, row in dataframe.iterrows():
        timml.ImpLineDoubletString(
            model=model,
            xy=linestring_coordinates(row),
            layers=row["layer"],
            order=row["order"],
            label=row["label"],
        )


def circareasink(dataframe: gpd.GeoDataFrame, model: timml.Model) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    for _, row in dataframe.iterrows():
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
    "uflow": uflow,
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
class ModelSpecification(NamedTuple):
    aquifer: str
    constant: str
    elements: Dict[str, Callable]


def extract_elementtype(s: str) -> str:
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
    constant = None
    elements = {}
    for layername in fiona.listlayers(str(path)):
        key = extract_elementtype(layername)
        print("adding", layername, "as", key)
        # Special case aquifer and reference point, since only a single instance
        # may occur in a model (singleton)
        if key == "aquifer":
            aquifer = layername
        elif key == "constant":
            constant = layername
        elif key == "domain":
            pass
        else:
            try:
                elements[layername] = MAPPING[key]
            except KeyError as e:
                msg = (
                    f'Invalid element specification "{key}" in {path}. '
                    f'Available types are: {", ".join(MAPPING.keys())}.'
                )
                raise KeyError(msg) from e
    return ModelSpecification(aquifer, constant, elements)


def validate(spec: ModelSpecification) -> None:
    if spec.aquifer is None:
        raise ValueError("Aquifer entry is missing")
    if spec.constant is None:
        raise ValueError("Constant entry is missing")
    # TODO: more checks


def initialize_model(
    path: Union[str, pathlib.Path], spec: ModelSpecification
) -> timml.Model:
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
    >>> model = gistim.initialize_model(path, spec)
    >>> model.solve()

    """
    validate(spec)
    dataframe = gpd.read_file(path, layer=spec.aquifer)
    model = aquifer(dataframe)

    dataframe = gpd.read_file(path, layer=spec.constant)
    constant(dataframe, model)

    for layername, element in spec.elements.items():
        dataframe = gpd.read_file(path, layer=layername)
        element(dataframe, model)

    return model


# Output methods
# --------------
def round_extent(extent: Tuple[float], cellsize: float) -> Tuple[float]:
    """
    Increases the extent until all sides lie on a coordinate
    divisible by cellsize.
    """
    xmin, xmax, ymin, ymax = extent
    xmin = np.floor(xmin / cellsize) * cellsize
    ymin = np.floor(ymin / cellsize) * cellsize
    xmax = np.ceil(xmax / cellsize) * cellsize
    ymax = np.ceil(ymax / cellsize) * cellsize
    return xmin, xmax, ymin, ymax


def gridspec(path: Union[pathlib.Path, str], cellsize: float) -> Tuple[float, Any]:
    """
    Infer the grid specifiction from the geopackage Domain layer and the
    provided cellsize.
    """
    domain = gpd.read_file(path, layer="timmlDomain")
    xmin, ymin, xmax, ymax = domain.bounds.iloc[0]
    extent = (xmin, xmax, ymin, ymax)
    return round_extent(extent, cellsize), domain.crs


def headgrid(model: timml.Model, extent: Tuple[float], cellsize: float) -> xr.DataArray:
    """
    Compute the headgrid of the TimML model, and store the results
    in an xarray DataArray with the appropriate dimensions.
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
