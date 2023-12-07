import json
import pathlib
from collections import defaultdict
from functools import singledispatch
from typing import Any, Dict, List, Union

import numpy as np
import pandas as pd
import timml
import ttim
import xarray as xr

from gistim.geopackage import CoordinateReferenceSystem, write_geopackage
from gistim.netcdf import write_raster, write_ugrid

TIMML_MAPPING = {
    "Constant": timml.Constant,
    "Uflow": timml.Uflow,
    "CircAreaSink": timml.CircAreaSink,
    "Well": timml.Well,
    "HeadWell": timml.HeadWell,
    "PolygonInhomMaq": timml.PolygonInhomMaq,
    "HeadLineSinkString": timml.HeadLineSinkString,
    "LineSinkDitchString": timml.LineSinkDitchString,
    "LeakyLineDoubletString": timml.LeakyLineDoubletString,
    "ImpLineDoubletString": timml.ImpLineDoubletString,
    "BuildingPit": timml.BuildingPitMaq,
    "LeakyBuildingPit": timml.LeakyBuildingPitMaq,
}
TTIM_MAPPING = {
    "CircAreaSink": ttim.CircAreaSink,
    "Well": ttim.Well,
    "HeadWell": ttim.HeadWell,
    "HeadLineSinkString": ttim.HeadLineSinkString,
    "LineSinkDitchString": ttim.LineSinkDitchString,
    "LeakyLineDoubletString": ttim.LeakyLineDoubletString,
}


def initialize_elements(model, mapping, data):
    elements = defaultdict(list)
    for name, entry in data.items():
        klass = mapping[entry["type"]]
        for kwargs in entry["data"]:
            element = klass(model=model, **kwargs)
            elements[name].append(element)
    return elements


def initialize_timml(data):
    aquifer = data.pop("ModelMaq")
    timml_model = timml.ModelMaq(**aquifer)
    elements = initialize_elements(timml_model, TIMML_MAPPING, data)
    return timml_model, elements


def initialize_ttim(data, timml_model):
    aquifer = data.pop("ModelMaq")
    ttim_model = ttim.ModelMaq(**aquifer, timmlmodel=timml_model)
    elements = initialize_elements(ttim_model, TTIM_MAPPING, data)
    return ttim_model, elements


@singledispatch
def headgrid(model, **kwargs):
    raise TypeError("Expected timml or ttim model")


@headgrid.register
def _(
    model: timml.Model,
    xmin: float,
    xmax: float,
    ymin: float,
    ymax: float,
    spacing: float,
    **_,
) -> xr.DataArray:
    """
    Compute the headgrid of the TimML model, and store the results
    in an xarray DataArray with the appropriate dimensions.

    Parameters
    ----------
    model: timml.Model
        Solved model to get heads from
    data: Dict[str, Any]

    Returns
    -------
    head: xr.DataArray
        DataArray with dimensions ``("layer", "y", "x")``.
    """
    x = np.arange(xmin, xmax, spacing) + 0.5 * spacing
    # In geospatial rasters, y is DECREASING with row number
    y = np.arange(ymax, ymin, -spacing) - 0.5 * spacing
    head = model.headgrid(xg=x, yg=y)
    nlayer = model.aq.find_aquifer_data(x[0], y[0]).naq
    layer = [i for i in range(nlayer)]
    return xr.DataArray(
        data=head,
        name="head",
        coords={"layer": layer, "y": y, "x": x},
        dims=("layer", "y", "x"),
    )


@headgrid.register
def _(
    model: ttim.ModelMaq,
    xmin: float,
    xmax: float,
    ymin: float,
    ymax: float,
    spacing: float,
    start_date: str,
    time: List[float],
) -> Union[None, xr.DataArray]:
    if time is None:
        return None

    # Get coordinates ready
    x = np.arange(xmin, xmax, spacing) + 0.5 * spacing
    # In geospatial rasters, y is DECREASING with row number
    y = np.arange(ymax, ymin, -spacing) - 0.5 * spacing
    nlayer = model.aq.find_aquifer_data(x[0], y[0]).naq

    if 0.0 in time:
        steady_head = model.timmlmodel.headgrid(xg=x, yg=y)[:, np.newaxis, :, :]
        transient_head = model.headgrid(xg=x, yg=y, t=time[1:])
        head = np.hstack((steady_head, transient_head))
    else:
        head = model.headgrid(xg=x, yg=y, t=time)

    # Other coordinates
    layer = [i for i in range(nlayer)]
    time = pd.to_datetime(start_date) + pd.to_timedelta(time, "D")
    return xr.DataArray(
        data=head,
        name="head",
        coords={"layer": layer, "time": time, "y": y, "x": x},
        dims=("layer", "time", "y", "x"),
    )


@singledispatch
def compute_head_observations(model, observations):
    raise TypeError("Expected timml or ttim model")


@compute_head_observations.register
def _(
    model: timml.Model,
    observations: Dict,
    **_,
) -> Dict[str, pd.DataFrame]:
    d = {"geometry": [], "label": []}
    heads = []
    for kwargs in observations:
        x = kwargs["x"]
        y = kwargs["y"]
        heads.append(model.head(x=x, y=y))
        d["geometry"].append({"type": "Point", "coordinates": [x, y]})
        d["label"].append(kwargs["label"])
    for i, layerhead in enumerate(np.vstack(heads).T):
        d[f"head_layer{i}"] = layerhead
    return pd.DataFrame(d)


@compute_head_observations.register
def _(
    model: ttim.ModelMaq, observations: Dict, start_date: pd.Timestamp
) -> Dict[str, pd.DataFrame]:
    d = {
        "geometry": [],
        "datetime_start": [],
        "datetime_end": [],
        "label": [],
        "observation_id": [],
    }
    heads = []
    start_date = pd.to_datetime(start_date, utc=False)
    for observation_id, kwargs in enumerate(observations):
        x = kwargs["x"]
        y = kwargs["y"]
        t = kwargs["t"]
        n_time = len(t)
        datetime = start_date + pd.to_timedelta([0] + t, "day")
        d["geometry"].extend([{"type": "Point", "coordinates": [x, y]}] * n_time)
        d["datetime_start"].extend(datetime[:-1])
        d["datetime_end"].extend(datetime[1:] - pd.to_timedelta(1, "minute"))
        d["label"].extend([kwargs["label"]] * n_time)
        d["observation_id"].extend([observation_id] * n_time)
        heads.append(model.head(x=x, y=y, t=t))

    for i, layerhead in enumerate(np.hstack(heads)):
        d[f"head_layer{i}"] = layerhead

    df = pd.DataFrame(d)
    return df


def extract_discharges(elements, nlayers, **_):
    tables = {}
    for layername, content in elements.items():
        sample = content[0]

        if isinstance(sample, timml.WellBase):
            table_rows = []
            for well in content:
                row = {f"discharge_layer{i}": q for i, q in enumerate(well.discharge())}
                row["geometry"] = {
                    "type": "Point",
                    "coordinates": [well.xc[0], well.yc[0]],
                }
                table_rows.append(row)
            tables[f"discharge-{layername}"] = pd.DataFrame.from_records(table_rows)

        elif isinstance(sample, (timml.LineSinkDitchString, timml.HeadLineSinkString)):
            table_rows = []
            for linestring in content:
                discharges = linestring.discharge_per_linesink()
                xy = linestring.xy
                for q_layered, vertex0, vertex1 in zip(discharges.T, xy[:-1], xy[1:]):
                    row = {f"discharge_layer{i}": q for i, q in enumerate(q_layered)}
                    row["geometry"] = {
                        "type": "LineString",
                        "coordinates": [vertex0, vertex1],
                    }
                    table_rows.append(row)
            tables[f"discharge-{layername}"] = pd.DataFrame.from_records(table_rows)

    return tables


@singledispatch
def compute_discharge_observations(model, observations):
    raise TypeError("Expected timml or ttim model")


@compute_discharge_observations.register
def _(model: timml.Model, observations: Dict):
    table_rows = []
    for kwargs in observations:
        xy = kwargs["xy"]
        method = kwargs["method"]
        ndeg = kwargs["ndeg"]
        discharges = model.intnormflux(xy=xy, method=method, ndeg=ndeg)

        # Store the output per line segment. 
        for q_layered, vertex0, vertex1 in zip(discharges.T, xy[:-1], xy[1:]):
            row = {f"discharge_layer{i}": q for i, q in enumerate(q_layered)}
            row["geometry"] = {
                "type": "LineString",
                "coordinates": [vertex0, vertex1],
                "label": kwargs["label"]
            }
            table_rows.append(row)

    return pd.DataFrame(pd.DataFrame.from_records(table_rows))


@compute_discharge_observations.register
def _(model: ttim.ModelMaq, observations: Dict):
    # intnormflux is not supported by ttim (yet).
    return None


def write_output(
    model: Union[timml.Model, ttim.ModelMaq],
    elements: Dict[str, Any],
    data: Dict[str, Any],
    path: Union[pathlib.Path, str],
):
    crs = CoordinateReferenceSystem(**data["crs"])
    output_options = data["output_options"]
    observations = data["observations"]
    discharge_observations = data["discharge_observations"]
    start_date = pd.to_datetime(data.get("start_date"))

    # Compute gridded head data and write to netCDF.
    head = None
    if output_options["raster"] or output_options["mesh"]:
        head = headgrid(model, **data["headgrid"], start_date=start_date)

    if head is not None:
        if output_options["raster"]:
            write_raster(head, crs, path)
        if output_options["mesh"]:
            write_ugrid(head, crs, path)

    # Compute observations and discharge, and write to geopackage.
    if output_options["discharge"]:
        tables = extract_discharges(elements, model.aq.nlayers, start_date=start_date)
    else:
        tables = {}

    if output_options["head_observations"] and observations:
        for layername, content in observations.items():
            tables[layername] = compute_head_observations(
                model, content["data"], start_date=start_date
            )

    if output_options["discharge_observations"] and discharge_observations:
        for layername, content in discharge_observations.items():
            observations = compute_discharge_observations(model, content["data"])
            if observations is not None:
                tables[layername] = observations

    write_geopackage(tables, crs, path)
    return


def compute_steady(
    path: Union[pathlib.Path, str],
) -> None:
    with open(path, "r") as f:
        data = json.load(f)

    timml_model, elements = initialize_timml(data["timml"])
    timml_model.solve()

    write_output(
        timml_model,
        elements,
        data,
        path,
    )
    return


def compute_transient(
    path: Union[pathlib.Path, str],
) -> None:
    with open(path, "r") as f:
        data = json.load(f)

    timml_model, _ = initialize_timml(data["timml"])
    ttim_model, ttim_elements = initialize_ttim(data["ttim"], timml_model)
    timml_model.solve()
    ttim_model.solve()

    write_output(
        ttim_model,
        ttim_elements,
        data,
        path,
    )
    return


def compute(path: str, transient: bool):
    path = pathlib.Path(path)
    if not path.exists():
        raise FileExistsError(path)
    if transient:
        compute_transient(path)
    else:
        compute_steady(path)
    return
