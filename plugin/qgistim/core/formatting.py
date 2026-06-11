"""
Format the content of a collection of dictionaries into a Python script or a
dictionary to be serialized to JSON.
"""

import pprint
import re
import textwrap
from typing import Any, Dict, Tuple, Union

import numpy as np

from qgistim.widgets.compute_widget import OutputOptions

STEADY_MAPPING = {
    "Constant": "Constant",
    "Uniform Flow": "Uflow",
    "Circular Area Sink": "CircAreaSink",
    "Well": "Well",
    "Head Well": "HeadWell",
    "Remote Head Well": "HeadWell",
    "Polygon Inhomogeneity": "PolygonInhomMaq",
    "Polygon Area Sink": "PolygonInhomMaq",
    "Polygon Semi-Confined Top": "PolygonInhomMaq",
    "River": "RiverString",
    "Ditch": "DitchString",
    "Leaky Wall": "LeakyWallString",
    "Impermeable Wall": "ImpermeableWallString",
    "Building Pit": "BuildingPit",
    "Leaky Building Pit": "LeakyBuildingPit",
    "Head Observation": "Head Observation",
    "Discharge Observation": "Discharge Observation",
}
# In TTim, a constant or uniform flow may be added, but they have no effect on
# the transient superposed result.
TRANSIENT_MAPPING = {
    "Constant": None,
    "Uniform Flow": None,
    "Circular Area Sink": "CircAreaSink",
    "Well": "Well",
    "Head Well": "HeadWell",
    "River": "RiverString",
    "Ditch": "DitchString",
    "Leaky Wall": "LeakyWallString",
    "Impermeable Wall": "LeakyWallString",
    "Head Observation": "Head Observation",
}
PREFIX = "    "


def sanitized(name: str) -> str:
    return name.split(":")[-1].replace(" ", "_")


def format_kwargs(data: Dict[str, Any]) -> str:
    return textwrap.indent(
        "\n".join(f"{k}={pprint.pformat(v)}," for k, v in data.items()), prefix=PREFIX
    )


def round_spacing(ymin: float, ymax: float) -> float:
    """
    Some reasonable defaults for grid spacing.

    We attempt to get around 50 rows in the computed grid, with grid sizes a
    multiple of 1.0, 5.0, 50.0, or 500.0.
    """
    dy = (ymax - ymin) / 50.0
    if dy > 500.0:
        dy = round(dy / 500.0) * 500.0
    elif dy > 50.0:
        dy = round(dy / 50.0) * 50.0
    elif dy > 5.0:  # round to five
        dy = round(dy / 5.0) * 5.0
    elif dy > 1.0:
        dy = round(dy)
    return dy


def round_extent(domain: Dict[str, float], spacing: float) -> Tuple[float]:
    """
    Increases the extent until all sides lie on a coordinate
    divisible by spacing.

    Parameters
    ----------
    extent: Tuple[float]
        xmin, xmax, ymin, ymax
    spacing: float
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
    xmin = np.floor(xmin / spacing) * spacing
    ymin = np.floor(ymin / spacing) * spacing
    xmax = np.ceil(xmax / spacing) * spacing
    ymax = np.ceil(ymax / spacing) * spacing
    xmin += 0.5 * spacing
    xmax += 0.5 * spacing
    ymax -= 0.5 * spacing
    xmin -= 0.5 * spacing
    return xmin, xmax, ymin, ymax


def headgrid_entry(domain: Dict[str, float], spacing: float) -> Dict[str, float]:
    (xmin, xmax, ymin, ymax) = round_extent(domain, spacing)
    return {
        "xmin": xmin,
        "xmax": xmax,
        "ymin": ymin,
        "ymax": ymax,
        "spacing": spacing,
        "time": domain.get("time"),
    }


def headgrid_code(domain) -> Tuple[str, str]:
    ymin = domain["ymin"]
    ymax = domain["ymax"]
    dy = round_spacing(ymin, ymax)
    (xmin, xmax, ymin, ymax) = round_extent(domain, dy)
    xg = textwrap.indent(f"xg=np.arange({xmin}, {xmax}, {dy})", prefix=PREFIX)
    yg = textwrap.indent(f"yg=np.arange({ymax}, {ymin}, -{dy})", prefix=PREFIX)
    time = domain.get("time")
    t = textwrap.indent(f"t={time}", prefix=PREFIX)
    return xg, yg, t


def elements_and_observations(data, mapping: Dict[str, str], temporal_string: str):
    strings = []
    observations = []
    if temporal_string == "steady-state":
        temporal_mode = "steady"
    else:
        temporal_mode = "transient"

    model_string = textwrap.indent(f"model={temporal_mode}_model,", prefix=PREFIX)

    for layername, element_data in data.items():
        prefix, name = layername.split(":")
        plugin_name = re.split("steady-state |transient ", prefix)[1]
        tim_name = mapping[plugin_name]
        if tim_name is None:
            continue

        for i, kwargs in enumerate(element_data):
            if plugin_name == "Head Observation":
                # Should not be added to the model.
                # Would result in e.g.:
                # observation_piezometer_0 = timflow.steady.head(
                #     x=10.0,
                #     y=20.0,
                # )
                kwargs.pop("label")
                observations.append(
                    f"observation_{sanitized(name)}_{i}={temporal_mode}_model.head(\n{format_kwargs(kwargs)}\n)"
                )
            elif plugin_name == "Discharge Observation":
                kwargs.pop("label")
                observations.append(
                    f"discharge_observation_{sanitized(name)}_{i}={temporal_mode}_model.intnormflux(\n{format_kwargs(kwargs)}\n)"
                )
            else:
                # Has to be added to the model.
                # Would result in e.g.:
                # steady-state_extraction_0 = timflow.steady.Well(
                #     model=steady-state_model,
                #     ...
                # )
                kwargs = format_kwargs(kwargs)
                strings.append(
                    f"{temporal_mode}_{sanitized(name)}_{i} = timflow.{temporal_mode}.{tim_name}(\n{model_string}\n{kwargs}\n)"
                )

    return strings, observations


def steady_script_content(data: Dict[str, Any]):
    data = data.copy()  # avoid side-effects
    aquifer_data = data.pop("steady-state Aquifer:Aquifer")
    data.pop("steady-state Domain:Domain")

    strings = [
        "import numpy as np",
        "import timflow",
        "",
        f"steady_model = timflow.steady.ModelMaq(\n{format_kwargs(aquifer_data)}\n)",
    ]

    element_strings, observations = elements_and_observations(
        data, STEADY_MAPPING, temporal_mode="steady-state"
    )
    strings = strings + element_strings
    return strings, observations


def steady_script(data: Dict[str, Any]) -> str:
    strings, observations = steady_script_content(data)
    strings.append("\nsteady_model.solve()\n")
    xg, yg, _ = headgrid_code(data["steady-state Domain:Domain"])
    strings.append(f"head = steady_model.headgrid(\n{xg},\n{yg}\n)")
    strings.append("\n")
    strings.extend(observations)
    return "\n".join(strings)


def transient_script(
    steady_data: Dict[str, Any], transient_data: Dict[str, Any]
) -> str:
    strings, _ = steady_script_content(steady_data)

    data = transient_data.copy()  # avoid side-effects
    aquifer_data = data.pop("steady-state Aquifer:Aquifer")
    domain_data = data.pop("steady-state Domain:Domain")
    data.pop("start_date")

    strings.append(
        f"\ntransient_model = timflow.transient.ModelMaq(\n{format_kwargs(aquifer_data)}\n{PREFIX}steady=steady_model,\n)"
    )

    element_strings, observations = elements_and_observations(
        data, TRANSIENT_MAPPING, temporal_mode="transient"
    )
    strings = strings + element_strings
    strings.append("\nsteady_model.solve()\ntransient_model.solve()\n")

    if domain_data.get("time"):
        xg, yg, t = headgrid_code(domain_data)
        strings.append(f"head = transient_model.headgrid(\n{xg},\n{yg},\n{t}\n)")
        strings.append("\n")

    strings.extend(observations)
    return "\n".join(strings)


def data_to_script(
    steady_data: Dict[str, Any],
    transient_data: Union[Dict[str, Any], None],
) -> str:
    if transient_data is None:
        return steady_script(steady_data)
    else:
        return transient_script(steady_data, transient_data)


def json_elements_and_observations(data, mapping: Dict[str, str]):
    aquifer_data = data.pop("steady-state Aquifer:Aquifer")

    observations = {}
    discharge_observations = {}
    tim_data = {"ModelMaq": aquifer_data}
    for layername, element_data in data.items():
        prefix, name = layername.split(":")
        plugin_name = re.split("steady-state |transient ", prefix)[1]
        tim_name = mapping[plugin_name]
        if tim_name is None:
            continue

        entry = {"type": tim_name, "name": name, "data": element_data}
        if tim_name == "Head Observation":
            observations[layername] = entry
        elif tim_name == "Discharge Observation":
            discharge_observations[layername] = entry
        else:
            tim_data[layername] = entry

    return tim_data, observations, discharge_observations


def steady_json(
    steady_data: Dict[str, Any],
    output_options: OutputOptions,
) -> Dict[str, Any]:
    """
    Take the data and add:

    * the timflow type
    * the layer name

    Parameters
    ----------
    data: Dict[str, Any]
    output_options: OutputOptions

    Returns
    -------
    json_data: Dict[str, Any]
        Data ready to dump to JSON.
    """
    # Process TimML elements
    data = steady_data.copy()  # avoid side-effects
    domain_data = data.pop("steady-state Domain:Domain")
    elements, observations, discharge_observations = json_elements_and_observations(
        data, mapping=STEADY_MAPPING
    )
    json_data = {
        "steady-state": elements,
        "observations": observations,
        "discharge_observations": discharge_observations,
        "window": domain_data,
        "output_options": output_options._asdict(),
    }
    if output_options.mesh or output_options.raster:
        json_data["headgrid"] = headgrid_entry(domain_data, output_options.spacing)
    return json_data


def transient_json(
    steady_data: Dict[str, Any],
    transient_data: Dict[str, Any],
    output_options: OutputOptions,
) -> Dict[str, Any]:
    json_data = steady_json(steady_data, output_options)

    data = transient_data.copy()
    domain_data = data.pop("steady-state Domain:Domain")
    start_date = data.pop("start_date")
    elements, observations, _ = json_elements_and_observations(
        data, mapping=TRANSIENT_MAPPING
    )

    json_data["transient"] = elements
    json_data["start_date"] = start_date
    json_data["observations"] = observations
    if output_options.mesh or output_options.raster:
        json_data["headgrid"] = headgrid_entry(domain_data, output_options.spacing)
    return json_data


def data_to_json(
    steady_data: Dict[str, Any],
    transient_data: Union[Dict[str, Any], None],
    output_options: OutputOptions,
) -> Dict[str, Any]:
    if transient_data is None:
        return steady_json(steady_data, output_options)
    else:
        return transient_json(steady_data, transient_data, output_options)
