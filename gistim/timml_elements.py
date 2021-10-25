from typing import Dict, List, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
import timml
import tqdm
import xarray as xr

from . import ugrid
from .common import (
    ElementSpecification,
    TimmlModelSpecification,
    aquifer_data,
    linestring_coordinates,
    point_coordinates,
    polygon_coordinates,
    trimesh,
)


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
    return timml.ModelMaq(**aquifer_data(dataframe))


def constant(
    spec: ElementSpecification, model: timml.Model, name: str, elements: Dict
) -> None:
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
    elements[name] = timml.Constant(
        model=model,
        xr=x,
        yr=y,
        hr=firstrow["head"],
    )


def uflow(
    spec: ElementSpecification, model: timml.Model, name: str, elements: Dict
) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    for i, row in spec.dataframe.iterrows():
        elements[f"{name}_{i}"] = timml.Uflow(
            model=model,
            slope=row["slope"],
            angle=row["angle"],
            label=row["label"],
        )


def well(
    spec: ElementSpecification, model: timml.Model, name: str, elements: Dict
) -> None:
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
    for ((i, row), x, y) in zip(dataframe.iterrows(), X, Y):
        elements[f"{name}_{i}"] = timml.Well(
            model=model,
            xw=x,
            yw=y,
            Qw=row["discharge"],
            rw=row["radius"],
            res=row["resistance"],
            layers=row["layer"],
            label=row["label"],
        )


def headwell(
    spec: ElementSpecification, model: timml.Model, name: str, elements: Dict
) -> None:
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
    for ((i, row), x, y) in zip(dataframe.iterrows(), X, Y):
        elements[f"{name}_{i}"] = timml.HeadWell(
            xw=x,
            yw=y,
            hw=row["head"],
            rw=row["radius"],
            res=row["resistance"],
            layers=row["layer"],
            label=row["label"],
            model=model,
        )


def polygoninhom(
    spec: ElementSpecification, model: timml.Model, name: str, elements: Dict
) -> None:
    """
    Parameters
    ----------
    dataframe: tuple of geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    geometry = spec.dataframe
    properties = spec.associated_dataframe.set_index("geometry_id")
    # Iterate through the row containing the geometry
    # and iterate through the associated table containing k properties.
    for i, row in geometry.iterrows():
        dataframe = properties.loc[[row["geometry_id"]]]
        data = aquifer_data(dataframe)
        data["model"] = model
        data["xy"] = polygon_coordinates(row)
        data["order"] = row["order"]
        data["ndeg"] = row["ndegrees"]
        elements[f"{name}_{i}"] = timml.PolygonInhomMaq(**data)


def buildingpit(
    spec: ElementSpecification, model: timml.Model, name: str, elements: Dict
) -> None:
    """
    Parameters
    ----------
    dataframe: tuple of geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    geometry = spec.dataframe
    properties = spec.associated_dataframe.set_index("geometry_id")
    # Iterate through the row containing the geometry
    # and iterate through the associated table containing k properties.
    for i, row in geometry.iterrows():
        dataframe = properties.loc[row["geometry_id"]]
        data = aquifer_data(dataframe)
        data["model"] = model
        data["xy"] = polygon_coordinates(row)
        data["order"] = row["order"]
        data["ndeg"] = row["ndegrees"]
        data["layers"] = np.atleast_1d(row["layer"])
        elements[f"{name}_{i}"] = timml.BuildingPit(**data)


def headlinesink(
    spec: ElementSpecification, model: timml.Model, name: str, elements: Dict
) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    for i, row in spec.dataframe.iterrows():
        elements[f"{name}_{i}"] = timml.HeadLineSinkString(
            model=model,
            xy=linestring_coordinates(row),
            hls=row["head"],
            res=row["resistance"],
            wh=row["width"],
            order=row["order"],
            layers=row["layer"],
            label=row["label"],
        )


def linesinkditch(
    spec: ElementSpecification, model: timml.Model, name: str, elements: Dict
) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    for i, row in spec.dataframe.iterrows():
        elements[f"{name}_{i}"] = timml.LineSinkDitchString(
            model=model,
            xy=linestring_coordinates(row),
            Qls=row["discharge"],
            res=row["resistance"],
            wh=row["width"],
            order=row["order"],
            layers=row["layer"],
            label=row["label"],
        )


def leakylinedoublet(
    spec: ElementSpecification, model: timml.Model, name: str, elements: Dict
) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    for i, row in spec.dataframe.iterrows():
        elements[f"{name}_{i}"] = timml.LeakyLineDoubletString(
            model=model,
            xy=linestring_coordinates(row),
            res=row["resistance"],
            layers=row["layer"],
            order=row["order"],
            label=row["label"],
        )


def implinedoublet(
    spec: ElementSpecification, model: timml.Model, name: str, elements: Dict
) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    for i, row in spec.dataframe.iterrows():
        elements[f"{name}_{i}"] = timml.ImpLineDoubletString(
            model=model,
            xy=linestring_coordinates(row),
            layers=row["layer"],
            order=row["order"],
            label=row["label"],
        )


def circareasink(
    spec: ElementSpecification, model: timml.Model, name: str, elements: Dict
) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    for i, row in spec.dataframe.iterrows():
        x, y = row.geometry.centroid.xy
        coords = np.array(row.geometry.exterior.coords)
        x0, y0 = coords[0]
        radius = np.sqrt((x0 - x) ** 2 + (y0 - y) ** 2)
        elements[f"{name}_{i}"] = timml.CircAreaSink(
            model=model,
            xc=x,
            yc=y,
            R=radius,
            N=row["rate"],
        )


# Map the names of the elements to their constructors
MAPPING = {
    "Constant": constant,
    "Uniform Flow": uflow,
    "Circular Area Sink": circareasink,
    "Well": well,
    "Head Well": headwell,
    "Polygon Inhomogeneity": polygoninhom,
    "Head Line Sink": headlinesink,
    "Line Sink Ditch": linesinkditch,
    "Leaky Line Doublet": leakylinedoublet,
    "Impermeable Line Doublet": implinedoublet,
    "Building Pit": buildingpit,
}


def validate(spec: TimmlModelSpecification) -> None:
    if spec.aquifer is None:
        raise ValueError("Aquifer entry is missing")
    # TODO: more checks


def initialize_model(spec: TimmlModelSpecification) -> timml.Model:
    """
    Initialize a TimML analytic model based on the data in a geopackage.

    Parameters
    ----------
    spec: ModelSpecification
        Named tuple with the layer name of the aquifer and a dictionary of
        other element names to its construction function.

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
    model = aquifer(spec.aquifer)
    elements = {}

    for name, element_spec in spec.elements.items():
        if not element_spec.active:
            continue
        elementtype = element_spec.elementtype
        print(f"adding {name} as {elementtype}")
        # Grab conversion function
        try:
            element = MAPPING[elementtype]
            element(element_spec, model, name, elements)
        except KeyError as e:
            msg = (
                f'Invalid element specification "{elementtype}". '
                f'Available types are: {", ".join(MAPPING.keys())}.'
            )
            raise KeyError(msg) from e

    return model, elements


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
    nlayer = model.aq.find_aquifer_data(x[0], y[0]).naq
    layer = [i for i in range(nlayer)]
    head = np.empty((nlayer, y.size, x.size), dtype=np.float64)
    for i in tqdm.tqdm(range(y.size)):
        for j in range(x.size):
            head[:, i, j] = model.head(x[j], y[i], layer)

    return xr.DataArray(
        data=head,
        name="head",
        coords={"layer": layer, "y": y, "x": x},
        dims=("layer", "y", "x"),
    )


def headmesh(
    model: timml.Model, spec: TimmlModelSpecification, cellsize: float
) -> xr.Dataset:
    nodes, face_nodes, centroids = trimesh(spec, cellsize)
    nlayer = model.aq.find_aquifer_data(nodes[0, 0], nodes[0, 0]).naq
    layer = [i for i in range(nlayer)]
    head = np.empty((nlayer, len(nodes)), dtype=np.float64)
    # for i in tqdm.tqdm(range(nface)):
    #    x = centroids[i, 0]
    #    y = centroids[i, 1]
    for i, (x, y) in enumerate(tqdm.tqdm(nodes)):
        head[:, i] = model.head(x, y, layer)
        head[:, i] = model.head(x, y, layer)
    uds = ugrid._ugrid2d_dataset(
        node_x=nodes[:, 0],
        node_y=nodes[:, 1],
        face_nodes=face_nodes,
        face_x=centroids[:, 0],
        face_y=centroids[:, 1],
    )
    uds["head"] = xr.DataArray(head, dims=("layer", "node"))
    return ugrid._unstack_layers(uds)


def discharge(model: timml.Model, elements: Dict) -> Tuple[List[gpd.GeoDataFrame]]:
    """
    Extract the discharge for elements that have a discharge.

    Do this twice: once for the integral elements, and once for the individual
    line sections. Return this as two lists of geodataframes, which can be
    written to geopackages.

    Parameters
    ---------
    model: timml.Model
    elements: dict
    """
