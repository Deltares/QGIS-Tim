from functools import singledispatch
import pathlib
from typing import Dict, NamedTuple, Union

import geopandas as gpd
import fiona
import numpy as np
import timml
import xarray as xr


FloatArray = np.ndarray


# Map the names of the elements to their TimML types
MAPPING = {
    "well": timml.Well,
    "headwell": timml.HeadWell,
    "aquifer3d": timml.Model3D,
    "headlinesink": timml.HeadLineSink,
}


class ModelSpecification(NamedTuple):
    aquifer: str
    reference: str
    elements: Dict[str, timml.Element]


def model_specification(path: Union[str, pathlib.Path]) -> ModelSpecification:
    aquifer = None
    reference = None
    elements = {}
    for layername in fiona.listlayers(path):
        key = s.split(":")[0].lower()
        # Special case aquifer and reference points, since only a single instance
        # may occur in a model (singleton)
        if key == "aquifer":
            aquifer = layername
        elif key == "reference":
            reference = reference
        else:
            try:
                elements[layername] = MAPPING[key]
            except KeyError as e:
                msg = (
                    f'Invalid element specification "{key}" in {path_geopackage}. '
                    f'Available types are: {", ".join(MAPPING.keys())}.'
                )
                raise KeyError(msg) from e
    return ModelSpecification(aquifer, reference, elements, domain)


def validate(spec: ModelSpecification) -> None:
    if spec.aquifer is None:
        raise ValueError("Aquifer entry is missing")
    if spec.reference is None:
        raise ValueError("Reference entry is missing")


# Add a method that dispatches on the first argument, the timml element
# thereby calling the appropriate logic required for the element
@singledispatch
def add_elements(element, dataframe, model):
    pass


def point_coordinates(dataframe) -> Tuple[FloatArray, FloatArray]:
    x, y = dataframe.geometry.coords.transpose()
    return x, y


@add_elements.register
def _(element: timml.Well, dataframe, model) -> None:
    X, Y = point_coordinates(dataframe)
    for ((rownumber, dataframe), x, y) in zip(dataframe.iterrows(), X, Y):
        element(
            model=model,
            x=x,
            y=y,
            Qw=row["discharge"],
            rw=row["radius"],
            res=row["resistance"],
            layers=row["layers"],
            label=row["label"],
        )


@add_elements.register
def _(element: timml.HeadLineSinkString, dataframe, model) -> None:
    for (rownumber, row) in dataframe.itterrows():
        coordinates = row.geometry.exterior
        element(
            model=model,
            xy=coordinates,
            hls=row["head"],
            res=row["resistance"],
            wh=row["width"],
            order=row["order"],
            layers=row["layer"],
            label=row["label"],
        )


def add_reference(dataframe, model) -> None:
    firstrow = dataframe.iloc[0]
    x, y = point_coordinates(first_row)
    timml.Reference(
        x=x,
        y=y,
        head=firstrow["head"],
    )


def interleave(top: FloatArray, bottom: FloatArray):
    # TODO
    return z


def initialize_aquifer(dataframe) -> timml.Model:
    z = interleave(dataframe["top"], dataframe["bottom"])
    model = timml.Model3D(
        kaq=dataframe["kaq"].values,
    )
    return model


def initialize_model(
    path: Union[str, pathlib.Path], spec: ModelSpecification
) -> timml.Model:
    dataframe = gpd.read_file(path, layer=spec.aquifer)
    model = initialize_aquifer(dataframe)

    dataframe = gpd.read_file(path, layer=spec.reference)
    add_reference(dataframe, model)

    for layername, element in spec.elements:
        dataframe = gpd.read_file(path, layer=layername)
        add_elements(element, dataframe, model)

    return model


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


def head(model, extent, cellsize) -> xr.DataArray:
    # TODO: check if model is already solved?

    extent = round_extent(extent, cellsize)
    xmin, xmax, ymin, ymax = extent
    x = np.arange(xmin, xmax, cellsize) + 0.5 * cellsize
    # In geospatial rasters, y is DECREASING with row number
    y = np.arange(ymax, ymin, -cellsize) - 0.5 * cellsize

    out = xr.DataArray(
        data=model.headgrid(x, y),
        coords={"y": y, "x": x},
        dims=("y", "x"),
    )
    return out
