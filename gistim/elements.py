import pathlib
import re
from typing import Callable, Dict, NamedTuple, Tuple, Union

import geopandas as gpd
import fiona
import numpy as np
import timml
import xarray as xr


FloatArray = np.ndarray


# Some geometry helpers
# ---------------------
def point_coordinates(dataframe) -> Tuple[FloatArray, FloatArray]:
    return dataframe["geometry"].x, dataframe["geometry"].y


def linestring_coordinates(row) -> Tuple[FloatArray, FloatArray]:
    xy = np.array(row["geometry"].coords).transpose()
    return (xy[0], xy[1])


polygon_coordinates = linestring_coordinates


# Dataframe to TimML element
# --------------------------
def aquifer(dataframe) -> timml.Model:
    model = timml.Model(
        kaq=dataframe["conductivity"].values,
        z=np.append(dataframe["top"].values, dataframe["bottom"].values[-1]),
        c=dataframe["resistance"],
        npor=dataframe["porosity"],
        ltype=["a" for _ in range(len(dataframe))],  # TODO
    )
    return model


def constant(dataframe, model) -> None:
    firstrow = dataframe.iloc[0]
    x, y = point_coordinates(firstrow)
    timml.Constant(
        model=model,
        xr=x,
        yr=y,
        hr=firstrow["head"],
    )


def well(dataframe, model) -> None:
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


def headwell(dataframe, model) -> None:
    raise NotImplementedError


def headlinesink(dataframe, model) -> None:
    raise NotImplementedError


# Map the names of the elements to their constructors
# (Basically equivalent to eval(key)...)
MAPPING = {
    "well": well,
    "headwell": headwell,
    "headlinesink": headlinesink,
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
    aquifer = None
    constant = None
    elements = {}
    for layername in fiona.listlayers(str(path)):
        key = extract_elementtype(layername)
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
def round_extent(extent, cellsize):
    """
    Increases the extent until all sides lie on a coordinate
    divisible by cellsize.
    """
    xmin, ymin, xmax, ymax = extent
    xmin = np.floor(xmin / cellsize) * cellsize
    ymin = np.floor(ymin / cellsize) * cellsize
    xmax = np.ceil(xmax / cellsize) * cellsize
    ymax = np.ceil(ymax / cellsize) * cellsize
    return xmin, ymin, xmax, ymax


def gridspec(path, cellsize):
    domain = gpd.read_file(path, layer="timmlDomain")
    xmin, ymin, xmax, ymax = domain.bounds.iloc[0]
    extent = (xmin, xmax, ymin, ymax)
    return round_extent(extent, cellsize), domain.crs


def headgrid(model, extent, cellsize) -> xr.DataArray:
    # TODO: check if model is already solved?
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
