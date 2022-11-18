import pathlib
from typing import Dict, Union

import geopandas as gpd
import numpy as np
import rioxarray  # noqa # pylint: disable=unused-import
import xarray as xr

import gistim


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
    ugrid_head = gistim.to_ugrid2d(head)
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
) -> None:
    if len(gdf_head.index) > 0:
        gdf_head = gdf_head.set_crs(crs)
        gdf_head.to_file(
            outpath.with_suffix(".output.gpkg"),
            driver="GPKG",
        )
    return


def compute_steady(
    inpath: Union[pathlib.Path, str],
    outpath: Union[pathlib.Path, str],
    cellsize: float,
    active_elements: Dict[str, bool],
) -> None:
    inpath = pathlib.Path(inpath)
    outpath = pathlib.Path(outpath)

    timml_spec, _ = gistim.model_specification(inpath, active_elements)
    timml_model, _, observations = gistim.timml_elements.initialize_model(timml_spec)
    timml_model.solve()

    extent, crs = gistim.gridspec(inpath, cellsize)
    gdf_head = gistim.timml_elements.head_observations(timml_model, observations)
    head = gistim.timml_elements.headgrid(timml_model, extent, cellsize)

    write_vector(gdf_head, crs, outpath)
    write_raster(head, crs, outpath)
    write_ugrid(head, crs, outpath)
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
    gdf_head = gistim.ttim_elements.head_observations(
        timml_model, refdate, observations
    )
    head = gistim.ttim_elements.headgrid(
        ttim_model,
        extent,
        cellsize,
        ttim_spec.output_times,
        refdate,
    )

    write_vector(gdf_head, crs, outpath)
    write_raster(head, crs, outpath)
    write_ugrid(head, crs, outpath)
    return
