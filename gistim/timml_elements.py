from typing import Dict, List, Tuple
import textwrap

import black
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
    round_extent,
    linestring_coordinates,
    point_coordinates,
    polygon_coordinates,
    trimesh,
)


def dict_to_kwargs_code(data: dict) -> str:
    strings = []
    for key, value in data.items():
        if isinstance(value, np.ndarray):
            value = value.tolist()
        elif isinstance(value, str):
            value = f'"{value}"'
        if key == "model":
            value = "model"
        strings.append(f"{key}={value}")
    return ",".join(strings)


def sanitize(name: str):
    return name.split(":")[-1].replace(" ", "_")


def headgrid_code(domain: gpd.GeoDataFrame) -> str:
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
    return f"head = model.headgrid(xg={xg}, yg={yg})"


# Dataframe to TimML element
# --------------------------
def aquifer(dataframe: gpd.GeoDataFrame, code: bool) -> timml.Model:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    timml.Model
    """
    kwargs = aquifer_data(dataframe)
    if code:
        kwargs = dict_to_kwargs_code(aquifer_data(dataframe))
        return f"model = timml.ModelMaq({kwargs})"
    else:
        return timml.ModelMaq()


def constant(
    spec: ElementSpecification,
    model: timml.Model,
    name: str,
    elements: Dict,
    code: bool,
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
    kwargs = {"model": model, "xr": x, "yr": y}
    if code:
        kwargs = dict_to_kwargs_code(kwargs)
        return f"constant = timml.Constant({kwargs})"
    else:
        elements[name] = timml.Constant(**kwargs)


def uflow(
    spec: ElementSpecification,
    model: timml.Model,
    name: str,
    elements: Dict,
    code: bool,
) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    row = spec.dataframe.iloc[0]
    kwargs = {
        "model": model,
        "slope": row["slope"],
        "angle": row["angle"],
        "label": row["label"],
    }
    if code:
        kwargs = dict_to_kwargs_code(kwargs)
        return f"{name} = timml.Uflow({kwargs})"
    else:
        elements[f"{name}"] = timml.Uflow(**kwargs)


def well(
    spec: ElementSpecification,
    model: timml.Model,
    name: str,
    elements: Dict,
    code: bool,
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
    strings = []
    for ((i, row), x, y) in zip(dataframe.iterrows(), X, Y):
        kwargs = {
            "model": model,
            "xw": x,
            "yw": y,
            "Qw": row["discharge"],
            "rw": row["radius"],
            "res": row["resistance"],
            "layers": row["layer"],
            "label": row["label"],
        }
        if code:
            kwargs = dict_to_kwargs_code(kwargs)
            strings.append(f"{name}_{i} = timml.Well({kwargs})")
        else:
            elements[f"{name}_{i}"] = timml.Well(**kwargs)

    if code:
        return "\n".join(strings)


def headwell(
    spec: ElementSpecification,
    model: timml.Model,
    name: str,
    elements: Dict,
    code: bool,
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
    strings = []
    for ((i, row), x, y) in zip(dataframe.iterrows(), X, Y):
        kwargs = {
            "model": model,
            "xw": x,
            "yw": y,
            "hw": row["head"],
            "rw": row["radius"],
            "res": row["resistance"],
            "layers": row["layer"],
            "label": row["label"],
        }
        if code:
            kwargs = dict_to_kwargs_code(kwargs)
            strings.append(f"{name}_{i} = timml.HeadWell({kwargs})")
        else:
            elements[f"{name}_{i}"] = timml.HeadWell(**kwargs)

    if code:
        return "\n".join(strings)


def polygoninhom(
    spec: ElementSpecification,
    model: timml.Model,
    name: str,
    elements: Dict,
    code: bool,
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
    strings = []
    for i, row in geometry.iterrows():
        dataframe = properties.loc[[row["geometry_id"]]]
        kwargs = aquifer_data(dataframe)
        kwargs["model"] = model
        kwargs["xy"] = polygon_coordinates(row)
        kwargs["order"] = row["order"]
        kwargs["ndeg"] = row["ndegrees"]

        if code:
            kwargs = dict_to_kwargs_code(kwargs)
            strings.append(f"{name}_{i} = timml.PolygonInhomMaq({kwargs})")
        else:
            elements[f"{name}_{i}"] = timml.PolygonInhomMaq(**kwargs)

    if code:
        return "\n".join(strings)


def buildingpit(
    spec: ElementSpecification,
    model: timml.Model,
    name: str,
    elements: Dict,
    code: bool,
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
    strings = []
    for i, row in geometry.iterrows():
        dataframe = properties.loc[row["geometry_id"]]
        kwargs = aquifer_data(dataframe)
        kwargs["model"] = model
        kwargs["xy"] = polygon_coordinates(row)
        kwargs["order"] = row["order"]
        kwargs["ndeg"] = row["ndegrees"]
        kwargs["layers"] = np.atleast_1d(row["layer"])

        if code:
            kwargs = dict_to_kwargs_code(kwargs)
            strings.append(f"{name}_{i} = timml.BuildingPit({kwargs})")
        else:
            elements[f"{name}_{i}"] = timml.BuildingPit(**kwargs)

    if code:
        return "\n".join(strings)


def headlinesink(
    spec: ElementSpecification,
    model: timml.Model,
    name: str,
    elements: Dict,
    code: bool,
) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    strings = []
    for i, row in spec.dataframe.iterrows():
        kwargs = {
            "model": model,
            "xy": linestring_coordinates(row),
            "hls": row["head"],
            "res": row["resistance"],
            "wh": row["width"],
            "order": row["order"],
            "layers": row["layer"],
            "label": row["label"],
        }

        if code:
            kwargs = dict_to_kwargs_code(kwargs)
            strings.append(f"{name}_{i} = timml.HeadLineSinkString({kwargs})")
        else:
            elements[f"{name}_{i}"] = timml.HeadLineSinkString(**kwargs)

    if code:
        return "\n".join(strings)


def linesinkditch(
    spec: ElementSpecification,
    model: timml.Model,
    name: str,
    elements: Dict,
    code: bool,
) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    strings = []
    for i, row in spec.dataframe.iterrows():
        kwargs = {
            "model": model,
            "xy": linestring_coordinates(row),
            "Qls": row["discharge"],
            "res": row["resistance"],
            "wh": row["width"],
            "order": row["order"],
            "layers": row["layer"],
            "label": row["label"],
        }

        if code:
            kwargs = dict_to_kwargs_code(kwargs)
            strings.append(f"{name}_{i} = timml.LineSinkDitchString({kwargs})")
        else:
            elements[f"{name}_{i}"] = timml.LineSinkDitchString(**kwargs)

    if code:
        return "\n".join(strings)


def leakylinedoublet(
    spec: ElementSpecification,
    model: timml.Model,
    name: str,
    elements: Dict,
    code: bool,
) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    strings = []
    for i, row in spec.dataframe.iterrows():
        kwargs = {
            "model": model,
            "xy": linestring_coordinates(row),
            "res": row["resistance"],
            "layers": row["layer"],
            "order": row["order"],
            "label": row["label"],
        }

        if code:
            kwargs = dict_to_kwargs_code(kwargs)
            strings.append(f"{name}_{i} = timml.LeakyLineDoubletString({kwargs})")
        else:
            elements[f"{name}_{i}"] = timml.LeakyLineDoubletString(**kwargs)

    if code:
        return "\n".join(strings)


def implinedoublet(
    spec: ElementSpecification,
    model: timml.Model,
    name: str,
    elements: Dict,
    code: bool,
) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    strings = []
    for i, row in spec.dataframe.iterrows():
        kwargs = {
            "model": model,
            "xy": linestring_coordinates(row),
            "layers": row["layer"],
            "order": row["order"],
            "label": row["label"],
        }
        if code:
            kwargs = dict_to_kwargs_code(kwargs)
            strings.append(f"{name}_{i} = timml.ImpLineDoubletString({kwargs})")
        else:
            elements[f"{name}_{i}"] = timml.ImpLineDoubletString(**kwargs)

    if code:
        return "\n".join(strings)


def circareasink(
    spec: ElementSpecification,
    model: timml.Model,
    name: str,
    elements: Dict,
    code: bool,
) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    strings = []
    for i, row in spec.dataframe.iterrows():
        x, y = row.geometry.centroid.xy
        coords = np.array(row.geometry.exterior.coords)
        x0, y0 = coords[0]
        radius = np.sqrt((x0 - x) ** 2 + (y0 - y) ** 2)

        kwargs = {
            "model": model,
            "xc": x,
            "yc": y,
            "R": radius,
            "N": row["rate"],
        }

        if code:
            kwargs = dict_to_kwargs_code(kwargs)
            strings.append(f"{name}_{i} = timml.CircAreaSink({kwargs})")
        else:
            elements[f"{name}_{i}"] = timml.CircAreaSink(**kwargs)

    if code:
        return "\n".join(strings)


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


def initialize_model(spec: TimmlModelSpecification, code: bool = False) -> timml.Model:
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
    model = aquifer(spec.aquifer, code)
    elements = {}

    strings = ["from numpy import nan", "import numpy as np", "import timml", model]
    for name, element_spec in spec.elements.items():
        if not element_spec.active:
            continue
        elementtype = element_spec.elementtype
        print(f"adding {name} as {elementtype}")
        # Grab conversion function
        try:
            element = MAPPING[elementtype]
            if code:
                name = sanitize(name)
                result = element(element_spec, model, name, elements, code)
                strings.append(result)
            else:
                element(element_spec, model, name, elements, code)

        except KeyError as e:
            msg = (
                f'Invalid element specification "{elementtype}". '
                f'Available types are: {", ".join(MAPPING.keys())}.'
            )
            raise KeyError(msg) from e

    if code:
        strings.append("model.solve()")
        strings.append(headgrid_code(spec.domain))
        return black.format_str("\n".join(strings), mode=black.FileMode())
    else:
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
