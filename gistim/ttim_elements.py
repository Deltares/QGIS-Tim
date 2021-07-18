import pathlib
import re
from typing import Any, Callable, Dict, NamedTuple, Tuple, Union

import fiona
import geopandas as gpd
import numpy as np
import pandas as pd
from ttim.model import TimModel
import ttim
import timml
import xarray as xr

from .common import (
    FloatArray,
    ElementSpecification,
    TransientElementSpecification,
    TtimModelSpecification,
    point_coordinates,
    linestring_coordinates,
    aquifer_data,
)


# Dataframe to ttim element
# --------------------------
def transient_dataframe(spec):
    if spec.dataframe is not None:
        return spec.dataframe.set_index("geometry_id")
    else:
        return None


def transient_input(timeseries_df, row, field, tstart):
    print(timeseries_df)
    print(row)
    if timeseries_df is None:
        return [(tstart, 0.0)]
    else:
        timeseries = timeseries_df.loc[[row["geometry_id"]]]
        timeseries[field] -= row[field]
        timeseries = timeseries.sort_values(by="tstart")
        return list(timeseries[["tstart", field]].itertuples(index=False, name=None))


def aquifer(
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
    return ttim.ModelMaq(**data)


def well(
    spec: TransientElementSpecification, model: TimModel, name: str, elements: Dict
):
    df = transient_dataframe(spec)
    dataframe = spec.steady_spec.dataframe
    X, Y = point_coordinates(dataframe)
    for ((i, row), x, y) in zip(dataframe.iterrows(), X, Y):
        elements[f"{name}_{i}"] = ttim.Well(
            model=model,
            xw=x,
            yw=y,
            tsandQ=transient_input(df, row, "discharge", model.tstart),
            rw=row["radius"],
            res=row["resistance"],
            layers=row["layer"],
            label=row["label"],
            rc=row["caisson_radius"],
            wbstype="slug" if row["slug"] else "pumping",
        )


def headwell(
    spec: TransientElementSpecification, model: TimModel, name: str, elements: Dict
):
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    df = transient_dataframe(spec)
    dataframe = spec.steady_spec.dataframe
    X, Y = point_coordinates(dataframe)
    for ((i, row), x, y) in zip(dataframe.iterrows(), X, Y):
        elements[f"{name}_{i}"] = ttim.HeadWell(
            xw=x,
            yw=y,
            tsandh=transient_input(df, row, "head", model.tstart),
            rw=row["radius"],
            res=row["resistance"],
            layers=row["layer"],
            label=row["label"],
            model=model,
        )


def headlinesink(
    spec: TransientElementSpecification, model: TimModel, name: str, elements: Dict
) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    df = transient_dataframe(spec)
    for i, row in spec.steady_spec.dataframe.iterrows():
        elements[f"{name}_{i}"] = ttim.HeadLineSinkString(
            model=model,
            xy=linestring_coordinates(row),
            tsandh=transient_input(df, row, "head", model.tstart),
            res=row["resistance"],
            wh=row["width"],
            order=row["order"],
            layers=row["layer"],
            label=row["label"],
        )


def linesinkditch(
    spec: ElementSpecification, model: TimModel, name: str, elements: Dict
) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    df = transient_dataframe(spec)
    for i, row in spec.steady_spec.dataframe.iterrows():
        elements[f"{name}_{i}"] = ttim.LineSinkDitchString(
            model=model,
            xy=linestring_coordinates(row),
            tsandQ=transient_input(df, row, "discharge", model.tstart),
            res=row["resistance"],
            wh=row["width"],
            order=row["order"],
            layers=row["layer"],
            label=row["label"],
        )


def leakylinedoublet(
    spec: ElementSpecification, model: TimModel, name: str, elements: Dict
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
        elements[f"{name}_{i}"] = ttim.LeakyLineDoubletString(
            model=model,
            xy=linestring_coordinates(row),
            res=row["resistance"],
            layers=row["layer"],
            order=row["order"],
            label=row["label"],
        )


def implinedoublet(
    spec: ElementSpecification, model: TimModel, name: str, elements: Dict
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
        elements[f"{name}_{i}"] = ttim.LeakyLineDoubletString(
            model=model,
            xy=linestring_coordinates(row),
            res="imp",
            layers=row["layer"],
            order=row["order"],
            label=row["label"],
        )


def circareasink(
    spec: TransientElementSpecification, model: TimModel, name: str, elements: Dict
) -> None:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    None
    """
    df = transient_dataframe(spec)
    for i, row in spec.steady_spec.dataframe.iterrows():
        x, y = row.geometry.centroid.xy
        coords = np.array(row.geometry.exterior.coords)
        x0, y0 = coords[0]
        radius = np.sqrt((x0 - x) ** 2 + (y0 - y) ** 2)
        elements[f"{name}_{i}"] = ttim.CircAreaSink(
            model=model,
            xc=x,
            yc=y,
            R=radius,
            tsandN=transient_input(df, row, "rate", model.tstart),
        )


# Map the names of the elements to their constructors
MAPPING = {
    "Circular Area Sink": circareasink,
    "Well": well,
    "Head Well": headwell,
    "Head Line Sink": headlinesink,
    "Line Sink Ditch": linesinkditch,
    "Leaky Line Doublet": leakylinedoublet,
    "Impermeable Line Doublet": implinedoublet,
}


def initialize_model(spec: TtimModelSpecification, timml_model=None) -> TimModel:
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
    model = aquifer(spec.aquifer, spec.temporal_settings, timml_model)
    elements = {}

    for name, element_spec in spec.elements.items():
        elementtype = element_spec.elementtype

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
    head = model.headgrid(x, y, times)
    nlayer = head.shape[0]
    time = pd.to_datetime(reference_date) + pd.to_timedelta(times, "D")
    out = xr.DataArray(
        data=head,
        name="head",
        coords={"time": time, "layer": range(nlayer), "y": y, "x": x},
        dims=("layer", "time", "y", "x"),
    ).transpose("time", "layer", "y", "x")
    return out
