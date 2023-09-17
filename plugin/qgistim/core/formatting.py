"""
Format the content of a collection of dictionaries into a Python script.
"""

import pprint
import re
import textwrap
from typing import Any, Dict, Tuple

import numpy as np

MAPPING = {
    "Constant": "Constant",
    "Uniform Flow": "Uflow",
    "Circular Area Sink": "CircAreaSink",
    "Well": "Well",
    "Head Well": "HeadWell",
    "Polygon Inhomogeneity": "PolygonInhomMaq",
    "Polygon Area Sink": "PolygonInhomMaq",
    "Polygon Semi-Confined Top": "PolygonInhomMaq",
    "Head Line Sink": "HeadLineSinkString",
    "Line Sink Ditch": "LineSinkDitchString",
    "Leaky Line Doublet": "LeakyLineDoubletString",
    "Impermeable Line Doublet": "ImpLineDoubletString",
    "Building Pit": "BuildingPit",
    "Leaky Building Pit": "LeakyBuildingPit",
    "Observation": "Observation",
}
PREFIX = "    "


def sanitized(name: str) -> str:
    return name.split(":")[-1].replace(" ", "_")


def format_kwargs(data: Dict[str, Any]) -> str:
    return textwrap.indent(
        "\n".join(f"{k}={pprint.pformat(v)}," for k, v in data.items()), prefix=PREFIX
    )


def round_extent(domain: Dict[str, float], cellsize: float) -> Tuple[float]:
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
    xmin = domain["xmin"]
    ymin = domain["ymin"]
    xmax = domain["xmax"]
    ymax = domain["ymax"]
    xmin = np.floor(xmin / cellsize) * cellsize
    ymin = np.floor(ymin / cellsize) * cellsize
    xmax = np.ceil(xmax / cellsize) * cellsize
    ymax = np.ceil(ymax / cellsize) * cellsize
    xmin += 0.5 * cellsize
    xmax += 0.5 * cellsize
    ymax -= 0.5 * cellsize
    xmin -= 0.5 * cellsize
    return xmin, xmax, ymin, ymax


def headgrid_entry(domain: Dict[str, float], cellsize: float) -> Dict[str, float]:
    (xmin, xmax, ymin, ymax) = round_extent(domain, cellsize)
    return {
        "xmin": xmin,
        "xmax": xmax,
        "ymin": ymin,
        "ymax": ymax,
        "spacing": cellsize,
    }


def headgrid_code(domain) -> Tuple[str, str]:
    ymin = domain["ymin"]
    ymax = domain["ymax"]
    dy = (ymax - ymin) / 50.0
    # Some reasonable defaults for grid spacing:
    if dy > 500.0:
        dy = round(dy / 500.0) * 500.0
    elif dy > 50.0:
        dy = round(dy / 50.0) * 50.0
    elif dy > 5.0:  # round to five
        dy = round(dy / 5.0) * 5.0
    elif dy > 1.0:
        dy = round(dy)
    (xmin, xmax, ymin, ymax) = round_extent(domain, dy)
    xg = textwrap.indent(f"xg=np.arange({xmin}, {xmax}, {dy})", prefix=PREFIX)
    yg = textwrap.indent(f"yg=np.arange({ymax}, {ymin}, -{dy})", prefix=PREFIX)
    return xg, yg


def to_script_string(data: Dict[str, Any]) -> str:
    """
    Convert the data into a runnable Python script.

    Returns
    -------
    data: Dict[str, Any]
        All the data for the TimML model.
    script: str
        A runnable Python script.
    """
    data = data.copy()  # avoid side-effects
    aquifer_data = data.pop("timml Aquifer:Aquifer")
    domain_data = data.pop("timml Domain:Domain")

    strings = [
        "import numpy as np",
        "import timml",
        "",
        f"model = timml.ModelMaq(\n{format_kwargs(aquifer_data)}\n)",
    ]

    model_string = textwrap.indent("model=model,", prefix=PREFIX)
    observations = []
    for layername, element_data in data.items():
        prefix, name = layername.split(":")
        plugin_name = re.split("timml |ttim ", prefix)[1]
        timml_name = MAPPING[plugin_name]

        for i, kwargs in enumerate(element_data):
            if plugin_name == "Observation":
                # Should not be added to the model.
                kwargs.pop("label")
                observations.append(
                    f"observation_{sanitized(name)}_{i}=model.head(\n{format_kwargs(kwargs)}\n)"
                )
            else:
                # Has to be added to the model.
                kwargs = format_kwargs(kwargs)
                strings.append(
                    f"{sanitized(name)}_{i} = timml.{timml_name}(\n{model_string}\n{kwargs}\n)"
                )

    strings.append("\nmodel.solve()\n")

    xg, yg = headgrid_code(domain_data)
    strings.append(f"head = model.headgrid(\n{xg},\n{yg}\n)")
    strings.append("\n")
    strings.extend(observations)

    return "\n".join(strings)


def to_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Take the data and add:

    * the TimML type
    * the layer name

    Parameters
    ----------
    data: Dict[str, Any]

    Returns
    -------
    json_data: Dict[str, Any]
        Data ready to dump to JSON.
    """
    data = data.copy()  # avoid side-effects
    aquifer_data = data.pop("timml Aquifer:Aquifer")
    domain_data = data.pop("timml Domain:Domain")

    json_data = {
        "ModelMaq": aquifer_data,
        "headgrid": headgrid_entry(domain_data, domain_data["cellsize"]),
    }

    for layername, element_data in data.items():
        prefix, name = layername.split(":")
        plugin_name = re.split("timml |ttim ", prefix)[1]
        timml_name = MAPPING[plugin_name]
        json_data[layername] = {"type": timml_name, "name": name, "data": element_data}

    return json_data
