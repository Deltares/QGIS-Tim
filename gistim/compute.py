import json
import pathlib
from typing import Dict, Union

import geopandas as gpd
import numpy as np
import rioxarray  # noqa # pylint: disable=unused-import
import timml
import tqdm
import ttim
import xarray as xr

from gistim.ugrid import to_ugrid2d

TIMML_MAPPING = {
    "Constant": timml.Constant,
    "Uflow": timml.Uflow,
    "CircAreaSink": timml.CircAreaSink,
    "Well": timml.Well,
    "HeadWell": timml.HeadWell,
    "PolygonInhom": timml.PolygonInhomMaq,
    "HeadLineSinkString": timml.HeadLineSinkString,
    "LineSinkDitchString": timml.LineSinkDitchString,
    "LeakyLineDoubletString": timml.LeakyLineDoubletString,
    "ImpLineDoubletString": timml.ImpLineDoubletString,
    "BuildingPit": timml.BuildingPit,
    "LeakyBuildingPit": timml.LeakyBuildingPit,
}


def write_raster(
    head: xr.DataArray,
    crs: int,
    outpath: Union[pathlib.Path, str],
) -> None:
    out = head.rio.write_crs(crs).rio.write_coordinate_system()
    out.to_netcdf(outpath.with_suffix(".nc"))
    return


def write_ugrid(
    head: xr.DataArray,
    crs: int,
    outpath: Union[pathlib.Path, str],
) -> None:
    ugrid_head = to_ugrid2d(head)
    ugrid_head["projected_coordinate_system"] = xr.DataArray(
        data=np.int32(0),
        attrs={"epsg": np.int32(crs.to_epsg())},
    )
    ugrid_head.to_netcdf(outpath.with_suffix(".ugrid.nc"))
    return


def write_vector(
    gdf_head: gpd.GeoDataFrame,
    crs: int,
    outpath: Union[pathlib.Path, str],
    layername: str,
) -> None:
    if len(gdf_head.index) > 0:
        gdf_head = gdf_head.set_crs(crs)
        gdf_head.to_file(
            outpath.with_suffix(".output.gpkg"),
            driver="GPKG",
            layer=layername,
        )
    return


def initialize_timml(data):
    aquifer = data.pop("ModelMaq")
    timml_model = timml.ModelMaq(**aquifer)
    for elementtype, entry in data.items():
        klass = TIMML_MAPPING[elementtype]
        for kwargs in entry["data"]:
            element = klass(model=timml_model, **kwargs)
    return timml_model


def timml_head_observations(model: timml.Model, observations: Dict) -> gpd.GeoDataFrame:
    geodataframes = {}
    for name, kwargs_collection in observations.items():
        heads = []
        xx = []
        yy = []
        labels = []
        for kwargs in kwargs_collection:
            x = kwargs["x"]
            y = kwargs["y"]
            heads.append(model.head(x=x, y=y))
            xx.append(x)
            yy.append(y)
            labels.append(kwargs["label"])

        d = {"geometry": gpd.points_from_xy(xx, yy), "label": labels}
        for i, layerhead in enumerate(np.vstack(heads).T):
            d[f"head_layer{i}"] = layerhead

        geodataframes[name] = gpd.GeoDataFrame(d)

    return geodataframes


def timml_headgrid(model: timml.Model, xmin, xmax, ymin, ymax, spacing) -> xr.DataArray:
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


def compute_steady(
    inpath: Union[pathlib.Path, str],
    outpath: Union[pathlib.Path, str],
) -> None:
    inpath = pathlib.Path(inpath)
    outpath = pathlib.Path(outpath)

    with open(inpath, "r") as f:
        data = json.load(f)

    crs = data.pop("crs")
    observations = data.pop("Observations", None)
    headgrid = data.pop("headgrid")
    timml_model = initialize_timml(data)
    timml_model.solve()

    gdfs_obs = timml_head_observations(timml_model, observations)
    head = timml_headgrid(timml_model, **headgrid)

    write_raster(head, crs, outpath)
    write_ugrid(head, crs, outpath)

    for name, gdf in gdfs_obs.items():
        write_vector(gdf, crs, outpath, layername=name)

    return


def compute_transient(
    inpath: Union[pathlib.Path, str],
    outpath: Union[pathlib.Path, str],
    cellsize: float,
    active_elements: Dict[str, bool],
) -> None:
    inpath = pathlib.Path(inpath)
    outpath = pathlib.Path(outpath)

    timml_spec, ttim_spec = gistim.model_specification(inpath, active_elements)
    timml_model, _, observations = gistim.timml_elements.initialize_model(timml_spec)
    ttim_model, _, observations = gistim.ttim_elements.initialize_model(
        ttim_spec, timml_model
    )
    timml_model.solve()
    ttim_model.solve()

    extent, crs = gistim.gridspec(inpath, cellsize)
    refdate = ttim_spec.temporal_settings["reference_date"].iloc[0]
    gdfs_obs = gistim.ttim_elements.head_observations(ttim_model, refdate, observations)

    # If no output times are specified, just compute the TimML steady-state
    # heads.
    if len(ttim_spec.output_times) > 0:
        head = gistim.ttim_elements.headgrid(
            ttim_model,
            extent,
            cellsize,
            ttim_spec.output_times,
            refdate,
        )
        write_raster(head, crs, outpath)
        write_ugrid(head, crs, outpath)
    else:
        head = gistim.timml_elements.headgrid(timml_model, extent, cellsize)

    write_raster(head, crs, outpath)
    write_ugrid(head, crs, outpath)

    for name, gdf in gdfs_obs.items():
        write_vector(gdf, crs, outpath, layername=name)

    return
