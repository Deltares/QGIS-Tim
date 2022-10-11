import json
import os
import pathlib
from typing import Dict, Union

import geopandas as gpd
import numpy as np
import rioxarray as xr
import xarray as xr

import gistim


def write_gpkg_raster(
    head: xr.DataArray,
    crs: int,
    outpath: Union[pathlib.Path, str],
) -> None:
    out = head.rio.write_crs(crs).astype(np.float32)
    for layer, da in out.groupby("layer"):
        da.rio.to_raster(
            outpath,
            driver="GPKG",
            raster_table=f"head_layer{layer}",
            append_subdataset=True,
        )
    return


def write_ugrid(
    ugrid_head: xr.DataArray,
    outpath: Union[pathlib.Path, str],
) -> None:
    ugrid_head.to_netcdf(outpath)
    return


def write_observations(
    gdf_head: gpd.GeoDataFrame,
    outpath: Union[pathlib.Path, str],
) -> None:
    if len(gdf_head.index) > 0:
        outpath = pathlib.Path(outpath)
        gdf_head.to_file(outpath, driver="GPKG")
    return


def compute_steady(
    inpath: Union[pathlib.Path, str],
    outpath: Union[pathlib.Path, str],
    cellsize: float,
    active_elements: Dict[str, bool],
    as_trimesh: bool = False,
) -> None:
    inpath = pathlib.Path(inpath)
    outpath = pathlib.Path(outpath)
    timml_spec, ttim_spec = gistim.model_specification(inpath, active_elements)
    timml_model, _, observations = gistim.timml_elements.initialize_model(timml_spec)
    timml_model.solve()

    gdf_head = gistim.timml_elements.head_observations(timml_model, observations)

    extent, crs = gistim.gridspec(inpath, cellsize)
    if as_trimesh:
        ugrid_head = gistim.timml_elements.headmesh(timml_model, timml_spec, cellsize)
    else:
        head = gistim.timml_elements.headgrid(timml_model, extent, cellsize)
        ugrid_head = gistim.to_ugrid2d(head)

    write_ugrid(ugrid_head, outpath)

    gpkg_outpath = outpath.parent / f"{outpath.stem}-results.gpkg"
    write_observations(gdf_head, gpkg_outpath)
    write_gpkg_raster(head, crs, gpkg_outpath)
    return


def compute_transient(
    inpath: Union[pathlib.Path, str],
    outpath: Union[pathlib.Path, str],
    cellsize: float,
    active_elements: Dict[str, bool],
    as_trimesh: bool = False,
) -> None:
    inpath = pathlib.Path(inpath)
    outpath = pathlib.Path(outpath)
    timml_spec, ttim_spec = gistim.model_specification(inpath, active_elements)
    timml_model, _, observations = gistim.timml_elements.initialize_model(timml_spec)
    ttim_model, _ = gistim.ttim_elements.initialize_model(ttim_spec, timml_model)
    timml_model.solve()
    ttim_model.solve()

    gdf_head = gistim.ttim_elements.head_observations(timml_model, observations)

    extent, crs = gistim.gridspec(inpath, cellsize)
    if as_trimesh:
        ugrid_head = gistim.ttim_elements.headmesh(ttim_model, timml_spec, cellsize)
    else:
        head = gistim.ttim_elements.headgrid(
            ttim_model,
            extent,
            cellsize,
            ttim_spec.output_times,
            ttim_spec.temporal_settings["reference_date"].iloc[0],
        )
        ugrid_head = gistim.to_ugrid2d(head)

    write_ugrid(ugrid_head, outpath)
    gpkg_outpath = outpath.parent / f"{outpath.stem}-results.gpkg"
    write_observations(gdf_head, gpkg_outpath)
    return
