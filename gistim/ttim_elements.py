"""
This model converts the geodataframe as read from the geopackage into keyword
arguments for TTim.

These keyword arguments are used to initialize a model, or used to generate a
Python script.

"""
from typing import Any, Dict, List, Tuple

import black
import geopandas as gpd
import numpy as np
import pandas as pd
import timml
import tqdm
import xarray as xr

try:
    import ttim
    from ttim.model import TimModel
except ImportError:
    ttim = None
    TimModel = None

from . import ugrid
from .common import (
    ElementSpecification,
    FloatArray,
    TransientElementSpecification,
    TtimModelSpecification,
    aquifer_data,
    dict_to_kwargs_code,
    headgrid_code,
    linestring_coordinates,
    point_coordinates,
    sanitized,
    trimesh,
)


# Dataframe to ttim element
# --------------------------
def transient_dataframe(spec):
    if spec.dataframe is not None:
        return spec.dataframe.set_index("geometry_id")
    else:
        return None


def transient_input(timeseries_df, row, field, tstart) -> List:
    geometry_id = row["geometry_id"]
    if timeseries_df is None or geometry_id not in timeseries_df.index:
        return [(tstart, 0.0)]
    else:
        timeseries = timeseries_df.loc[[geometry_id]]
        timeseries[field] -= row[field]
        timeseries = timeseries.sort_values(by="tstart")
        return list(timeseries[["tstart", field]].itertuples(index=False, name=None))


def ttim_model(
    dataframe: gpd.GeoDataFrame,
    temporal_settings: pd.DataFrame,
    timml_model: timml.Model,
) -> TimModel:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    ttim.TimModel
    """
    data = aquifer_data(dataframe, transient=True)
    for arg in ("tstart", "tmin", "tmax", "M"):
        data[arg] = temporal_settings[arg].iloc[0]
    data["timmlmodel"] = timml_model
    return data


def observation(spec: TransientElementSpecification, _):
    df = transient_dataframe(spec)
    dataframe = spec.steady_spec.dataframe
    X, Y = point_coordinates(dataframe)
    kwargslist = []
    for (row, x, y) in zip(dataframe.to_dict("records"), X, Y):
        geometry_id = row["geometry_id"]
        kwargslist.append(
            {
                "x": x,
                "y": y,
                "t": df.loc[geometry_id, "time"].values,
                "label": row["label"],
            }
        )
    return kwargslist


def well(spec: TransientElementSpecification, tstart: float) -> List[Dict[str, Any]]:
    df = transient_dataframe(spec)
    dataframe = spec.steady_spec.dataframe
    X, Y = point_coordinates(dataframe)
    kwargslist = []
    for (row, x, y) in zip(dataframe.to_dict("records"), X, Y):
        kwargslist.append(
            {
                "xw": x,
                "yw": y,
                "tsandQ": transient_input(df, row, "discharge", tstart),
                "rw": row["radius"],
                "res": row["resistance"],
                "layers": row["layer"],
                "label": row["label"],
                "rc": row["caisson_radius"],
                "wbstype": "slug" if row["slug"] else "pumping",
            }
        )
    return kwargslist


def headwell(
    spec: TransientElementSpecification, tstart: float
) -> List[Dict[str, Any]]:
    df = transient_dataframe(spec)
    dataframe = spec.steady_spec.dataframe
    X, Y = point_coordinates(dataframe)
    kwargslist = []
    for (row, x, y) in zip(dataframe.to_dict("records"), X, Y):
        kwargslist.append(
            {
                "xw": x,
                "yw": y,
                "tsandh": transient_input(df, row, "head", tstart),
                "rw": row["radius"],
                "res": row["resistance"],
                "layers": row["layer"],
                "label": row["label"],
            }
        )
    return kwargslist


def headlinesink(
    spec: TransientElementSpecification, tstart: float
) -> List[Dict[str, Any]]:
    df = transient_dataframe(spec)
    kwargslist = []
    for row in spec.steady_spec.dataframe.to_dict("records"):
        kwargslist.append(
            {
                "xy": linestring_coordinates(row),
                "tsandh": transient_input(df, row, "head", tstart),
                "res": row["resistance"],
                "wh": row["width"],
                "layers": row["layer"],
                "label": row["label"],
            }
        )
    return kwargslist


def linesinkditch(spec: ElementSpecification, tstart: float) -> List[Dict[str, Any]]:
    df = transient_dataframe(spec)
    kwargslist = []
    for row in spec.steady_spec.dataframe.to_dict("records"):
        kwargslist.append(
            {
                "xy": linestring_coordinates(row),
                "tsandQ": transient_input(df, row, "discharge", tstart),
                "res": row["resistance"],
                "wh": row["width"],
                "layers": row["layer"],
                "label": row["label"],
            }
        )
    return kwargslist


def leakylinedoublet(spec: ElementSpecification, tstart: float) -> List[Dict[str, Any]]:
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


def implinedoublet(spec: ElementSpecification, tstart: float) -> List[Dict[str, Any]]:
    kwargslist = []
    for row in spec.dataframe.to_dict("records"):
        kwargslist.append(
            {
                "xy": linestring_coordinates(row),
                "res": "imp",
                "layers": row["layer"],
                "order": row["order"],
                "label": row["label"],
            }
        )
    return kwargslist


def circareasink(spec: TransientElementSpecification, tstart: float) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    df = transient_dataframe(spec)
    kwargslist = []
    for row in spec.steady_spec.dataframe.to_dict("records"):
        x, y = np.array(row["geometry"].centroid.coords)[0]
        coords = np.array(row["geometry"].exterior.coords)
        x0, y0 = coords[0]
        radius = np.sqrt((x0 - x) ** 2 + (y0 - y) ** 2)
        kwargslist.append(
            {
                "xc": x,
                "yc": y,
                "R": radius,
                "tsandN": transient_input(df, row, "rate", tstart),
            }
        )
    return kwargslist


def head_observations(
    model: TimModel,
    reference_date: pd.Timestamp,
    observations: Dict,
) -> gpd.GeoDataFrame:
    # We'll duplicate all values in time, except head which is unique per time.
    if len(observations) == 0:
        return gpd.GeoDataFrame()

    refdate = pd.to_datetime(reference_date)
    xx = []
    yy = []
    labels = []
    heads = []
    starts = []
    ends = []
    for kwargs in observations.values():
        x = kwargs["x"]
        y = kwargs["y"]
        t = kwargs["t"]
        end = refdate + pd.to_timedelta(t, "D")
        start = np.insert(end[:-1], 0, refdate)

        starts.append(start)
        ends.append(end)
        heads.append(model.head(x=x, y=y, t=t))
        xx.append(np.repeat(x, len(t)))
        yy.append(np.repeat(y, len(t)))
        labels.append(np.repeat(kwargs["label"], len(t)))

    d = {
        "geometry": gpd.points_from_xy(np.concatenate(xx), np.concatenate(yy)),
        "datetime_start": np.concatenate(starts),
        "datetime_end": np.concatenate(ends),
        "label": np.concatenate(labels),
    }
    for i, layerhead in enumerate(np.hstack(heads)):
        d[f"head_layer{i}"] = layerhead

    return gpd.GeoDataFrame(d)


def headgrid(
    model: TimModel,
    extent: Tuple[float],
    cellsize: float,
    times: FloatArray,
    reference_date: pd.Timestamp,
) -> xr.DataArray:
    xmin, xmax, ymin, ymax = extent
    x = np.arange(xmin, xmax, cellsize) + 0.5 * cellsize
    # In geospatial rasters, y is DECREASING with row number
    y = np.arange(ymax, ymin, -cellsize) - 0.5 * cellsize
    nlayer = model.aq.find_aquifer_data(x[0], y[0]).naq
    layer = [i for i in range(nlayer)]
    head = np.empty((nlayer, times.size, y.size, x.size), dtype=np.float64)
    for i in tqdm.tqdm(range(y.size)):
        for j in range(x.size):
            head[:, :, i, j] = model.head(x[j], y[i], times, layer)

    time = pd.to_datetime(reference_date) + pd.to_timedelta(times, "D")
    return xr.DataArray(
        data=head,
        name="head",
        coords={"layer": layer, "time": time, "y": y, "x": x},
        dims=("layer", "time", "y", "x"),
    )


def headmesh(
    model: TimModel,
    spec,
    cellsize: float,
    times: FloatArray,
    reference_date: pd.Timestamp,
) -> xr.Dataset:
    nodes, face_nodes, centroids = trimesh(spec, cellsize)
    nface = len(face_nodes)

    nlayer = model.aq.find_aquifer_data(nodes[0, 0], nodes[0, 0]).naq
    layer = [i for i in range(nlayer)]
    head = np.empty((nlayer, times.size, nface), dtype=np.float64)
    for i in tqdm.tqdm(range(nface)):
        x = centroids[i, 0]
        y = centroids[i, 1]
        head[:, :, i] = model.head(x, y, times, layer)
    uds = ugrid._ugrid2d_dataset(
        node_x=nodes[:, 0],
        node_y=nodes[:, 1],
        face_x=centroids[:, 0],
        face_y=centroids[:, 1],
        face_nodes=face_nodes,
    )
    time = pd.to_datetime(reference_date) + pd.to_timedelta(times, "D")
    uds = uds.assign_coords(time=time)
    uds["head"] = xr.DataArray(head, dims=("layer", "time", "face"))
    return ugrid._unstack_layers(uds)


# Map the names of the elements to their constructors
if ttim is not None:
    MAPPING = {
        "Circular Area Sink": (circareasink, ttim.CircAreaSink),
        "Well": (well, ttim.Well),
        "Head Well": (headwell, ttim.HeadWell),
        "Head Line Sink": (headlinesink, ttim.HeadLineSinkString),
        "Line Sink Ditch": (linesinkditch, ttim.LineSinkDitchString),
        "Leaky Line Doublet": (leakylinedoublet, ttim.LeakyLineDoubletString),
        "Impermeable Line Doublet": (implinedoublet, ttim.LeakyLineDoubletString),
        "Observation": (observation, None),
    }


def initialize_model(spec: TtimModelSpecification, timml_model) -> TimModel:
    """
    Initialize a Ttim analytic model based on the data in a geopackage.

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
    model = ttim.ModelMaq(
        **ttim_model(spec.aquifer, spec.temporal_settings, timml_model)
    )
    elements = {}
    observations = {}
    for name, element_spec in spec.elements.items():
        elementtype = element_spec.elementtype
        if (
            (not element_spec.active)
            or (elementtype not in MAPPING)
            or (len(element_spec.dataframe.index) == 0)
        ):
            continue

        # print(f"adding {name} as {elementtype}")
        f_to_kwargs, element = MAPPING[elementtype]
        for i, kwargs in enumerate(f_to_kwargs(element_spec, model.tstart)):
            if elementtype == "Observation":
                observations[f"{name}_{i}"] = kwargs
            else:
                kwargs["model"] = model
                elements[f"{name}_{i}"] = element(**kwargs)

    return model, elements, observations


def convert_to_script(spec: TtimModelSpecification) -> str:
    """
    Convert model specification to an equivalent Python script.
    """
    modelkwargs = ttim_model(spec.aquifer, spec.temporal_settings, "model")
    strkwargs = dict_to_kwargs_code(modelkwargs)

    observations = {}
    strings = ["import ttim", f"ttim_model = ttim.ModelMaq({strkwargs})"]
    for name, element_spec in spec.elements.items():
        elementtype = element_spec.elementtype
        if elementtype not in MAPPING:
            continue
        # print(f"adding {name} as {elementtype}")

        f_to_kwargs, element = MAPPING[elementtype]
        for i, kwargs in enumerate(f_to_kwargs(element_spec, modelkwargs["tstart"])):
            if elementtype == "Observation":
                kwargs.pop("label")
                kwargs = dict_to_kwargs_code(kwargs)
                observations[f"ttim_observation_{sanitized(name)}_{i}"] = kwargs
            else:
                kwargs["model"] = "ttim_model"
                kwargs = dict_to_kwargs_code(kwargs)
                strings.append(
                    f"ttim_{sanitized(name)}_{i} = ttim.{element.__name__}({kwargs})"
                )

    strings.append("ttim_model.solve()")

    xg, yg = headgrid_code(spec.domain)
    times = spec.output_times.tolist()
    strings.append(f"ttim_head = ttim_model.headgrid(xg={xg}, yg={yg}, t={times})")

    # Add all the individual observation points
    for name, kwargs in observations.items():
        strings.append(f"{name} = ttim_model.head({kwargs})")

    return black.format_str("\n".join(strings), mode=black.FileMode())
