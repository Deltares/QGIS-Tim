"""
This model converts the geodataframe as read from the geopackage into keyword
arguments for TimML.

These keyword arguments are used to initialize a model, or used to generate a
Python script.
"""
from typing import Any, Dict, List, Tuple

import black
import numpy as np
import timml
import tqdm
import xarray as xr

from . import ugrid
from .common import (
    ElementSpecification,
    TimmlModelSpecification,
    aquifer_data,
    dict_to_kwargs_code,
    headgrid_code,
    linestring_coordinates,
    point_coordinates,
    polygon_coordinates,
    sanitized,
    trimesh,
)


def constant(spec: ElementSpecification) -> List[Dict[str, Any]]:
    firstrow = spec.dataframe.iloc[0]
    x, y = point_coordinates(firstrow)
    return [
        {
            "xr": x,
            "yr": y,
            "hr": firstrow["head"],
            "layer": firstrow["layer"],
            "label": firstrow["label"],
        }
    ]


def uflow(spec: ElementSpecification) -> List[Dict[str, Any]]:
    row = spec.dataframe.iloc[0]
    return [
        {
            "slope": row["slope"],
            "angle": row["angle"],
            "label": row["label"],
        }
    ]


def well(spec: ElementSpecification) -> List[Dict[str, Any]]:
    dataframe = spec.dataframe
    X, Y = point_coordinates(dataframe)
    kwargslist = []
    for (row, x, y) in zip(dataframe.to_dict("records"), X, Y):
        kwargslist.append(
            {
                "xw": x,
                "yw": y,
                "Qw": row["discharge"],
                "rw": row["radius"],
                "res": row["resistance"],
                "layers": row["layer"],
                "label": row["label"],
            }
        )
    return kwargslist


def headwell(spec: ElementSpecification) -> List[Dict[str, Any]]:
    dataframe = spec.dataframe
    X, Y = point_coordinates(dataframe)
    kwargslist = []
    for (row, x, y) in zip(dataframe.to_dict("records"), X, Y):
        kwargslist.append(
            {
                "xw": x,
                "yw": y,
                "hw": row["head"],
                "rw": row["radius"],
                "res": row["resistance"],
                "layers": row["layer"],
                "label": row["label"],
            }
        )
    return kwargslist


def polygoninhom(spec: ElementSpecification) -> List[Dict[str, Any]]:
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
    kwarglist = []
    for row in geometry.to_dict("records"):
        dataframe = properties.loc[[row["geometry_id"]]]
        kwargs = aquifer_data(dataframe)
        kwargs["xy"] = polygon_coordinates(row)
        kwargs["order"] = row["order"]
        kwargs["ndeg"] = row["ndegrees"]
        kwarglist.append(kwargs)
    return kwarglist


def buildingpit(spec: ElementSpecification) -> List[Dict[str, Any]]:
    geometry = spec.dataframe
    properties = spec.associated_dataframe.set_index("geometry_id")
    # Iterate through the row containing the geometry
    # and iterate through the associated table containing k properties.
    kwarglist = []
    for row in geometry.to_dict("records"):
        dataframe = properties.loc[row["geometry_id"]]
        kwargs = aquifer_data(dataframe)
        kwargs["xy"] = polygon_coordinates(row)
        kwargs["order"] = row["order"]
        kwargs["ndeg"] = row["ndegrees"]
        kwargs["layers"] = np.atleast_1d(row["layer"])
        kwarglist.append(kwargs)
    return kwarglist


def headlinesink(spec: ElementSpecification) -> List[Dict[str, Any]]:
    kwargslist = []
    for row in spec.dataframe.to_dict("records"):
        kwargslist.append(
            {
                "xy": linestring_coordinates(row),
                "hls": row["head"],
                "res": row["resistance"],
                "wh": row["width"],
                "order": row["order"],
                "layers": row["layer"],
                "label": row["label"],
            }
        )
    return kwargslist


def linesinkditch(spec: ElementSpecification) -> List[Dict[str, Any]]:
    kwargslist = []
    for row in spec.dataframe.to_dict("records"):
        kwargslist.append(
            {
                "xy": linestring_coordinates(row),
                "Qls": row["discharge"],
                "res": row["resistance"],
                "wh": row["width"],
                "order": row["order"],
                "layers": row["layer"],
                "label": row["label"],
            }
        )
    return kwargslist


def leakylinedoublet(spec: ElementSpecification) -> List[Dict[str, Any]]:
    kwargslist = []
    for row in spec.dataframe.to_dict("records"):
        kwargslist.append(
            {
                "xy": linestring_coordinates(row),
                "res": row["resistance"],
                "layers": row["layer"],
                "order": row["order"],
                "label": row["label"],
            }
        )
    return kwargslist


def implinedoublet(spec: ElementSpecification) -> List[Dict[str, Any]]:
    kwargslist = []
    for row in spec.dataframe.to_dict("records"):
        kwargslist.append(
            {
                "xy": linestring_coordinates(row),
                "layers": row["layer"],
                "order": row["order"],
                "label": row["label"],
            }
        )
    return kwargslist


def circareasink(spec: ElementSpecification) -> List[Dict[str, Any]]:
    kwargslist = []
    for row in spec.dataframe.to_dict("records"):
        x, y = np.array(row["geometry"].centroid.coords)[0]
        coords = np.array(row["geometry"].exterior.coords)
        x0, y0 = coords[0]
        radius = np.sqrt((x0 - x) ** 2 + (y0 - y) ** 2)
        kwargslist.append(
            {
                "xc": x,
                "yc": y,
                "R": radius,
                "N": row["rate"],
            }
        )
    return kwargslist


def validate(spec: TimmlModelSpecification) -> None:
    if spec.aquifer is None:
        raise ValueError("Aquifer entry is missing")
    # TODO: more checks


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


# Map the names of the elements to their constructors
MAPPING = {
    "Constant": (constant, timml.Constant),
    "Uniform Flow": (uflow, timml.Uflow),
    "Circular Area Sink": (circareasink, timml.CircAreaSink),
    "Well": (well, timml.Well),
    "Head Well": (headwell, timml.HeadWell),
    "Polygon Inhomogeneity": (polygoninhom, timml.PolygonInhomMaq),
    "Head Line Sink": (headlinesink, timml.HeadLineSinkString),
    "Line Sink Ditch": (linesinkditch, timml.LineSinkDitchString),
    "Leaky Line Doublet": (leakylinedoublet, timml.LeakyLineDoubletString),
    "Impermeable Line Doublet": (implinedoublet, timml.ImpLineDoubletString),
    "Building Pit": (buildingpit, timml.BuildingPit),
}


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
    model = timml.ModelMaq(**aquifer_data(spec.aquifer))
    elements = {}
    for name, element_spec in spec.elements.items():
        if not element_spec.active:
            continue

        elementtype = element_spec.elementtype
        print(f"adding {name} as {elementtype}")

        try:
            f_to_kwargs, element = MAPPING[elementtype]
            for i, kwargs in enumerate(f_to_kwargs(element_spec)):
                kwargs["model"] = model
                elements[f"{name}_{i}"] = element(**kwargs)
        except KeyError as e:
            msg = (
                f'Invalid element specification "{elementtype}". '
                f'Available types are: {", ".join(MAPPING.keys())}.'
            )
            raise KeyError(msg) from e

    return model, elements


def convert_to_script(spec: TimmlModelSpecification) -> str:
    """
    Convert model specification to an equivalent Python script.
    """
    modelkwargs = dict_to_kwargs_code(aquifer_data(spec.aquifer))
    strings = [
        "from numpy import nan",
        "import numpy as np",
        "import timml",
        f"model = timml.ModelMaq({modelkwargs})",
    ]
    for name, element_spec in spec.elements.items():
        elementtype = element_spec.elementtype
        print(f"adding {name} as {elementtype}")

        try:
            f_to_kwargs, element = MAPPING[elementtype]
            for i, kwargs in enumerate(f_to_kwargs(element_spec)):
                kwargs["model"] = "model"
                kwargs = dict_to_kwargs_code(kwargs)
                strings.append(
                    f"{sanitized(name)}_{i} = timml.{element.__name__}({kwargs})"
                )
        except KeyError as e:
            msg = (
                f'Invalid element specification "{elementtype}". '
                f'Available types are: {", ".join(MAPPING.keys())}.'
            )
            raise KeyError(msg) from e

    strings.append("model.solve()")

    xg, yg = headgrid_code(spec.domain)
    strings.append(f"head = model.headgrid(xg={xg}, yg={yg})")

    return black.format_str("\n".join(strings), mode=black.FileMode())
