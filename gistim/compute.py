import json
import os
import pathlib
from typing import Dict, Union

import geopandas as gpd
import xarray as xr

import gistim


def write_ugrid(
    ugrid_head: xr.DataArray,
    outpath: Union[pathlib.Path, str],
) -> None:
    ugrid_head.to_netcdf(outpath)


def write_observations(
    gdf_head: gpd.GeoDataFrame,
    outpath: Union[pathlib.Path, str],
) -> None:
    if len(gdf_head.index) > 0:
        outpath = pathlib.Path(outpath)
        vector_outpath = outpath.parent / f"{outpath.stem}-vector.gpkg"
        gdf_head.to_file(vector_outpath, driver="GPKG")


def compute_steady(
    inpath: Union[pathlib.Path, str],
    outpath: Union[pathlib.Path, str],
    cellsize: float,
    active_elements: Dict[str, bool],
    as_trimesh: bool = False,
) -> None:
    path = pathlib.Path(inpath)
    timml_spec, ttim_spec = gistim.model_specification(path, active_elements)
    timml_model, _, observations = gistim.timml_elements.initialize_model(timml_spec)
    timml_model.solve()

    gdf_head = gistim.timml_elements.head_observations(timml_model, observations)

    extent, crs = gistim.gridspec(path, cellsize)
    if as_trimesh:
        ugrid_head = gistim.timml_elements.headmesh(timml_model, timml_spec, cellsize)
    else:
        head = gistim.timml_elements.headgrid(timml_model, extent, cellsize)
        ugrid_head = gistim.to_ugrid2d(head)

    write_ugrid(ugrid_head, outpath)
    write_observations(gdf_head, outpath)
    return


def compute_transient(
    inpath: Union[pathlib.Path, str],
    outpath: Union[pathlib.Path, str],
    cellsize: float,
    active_elements: Dict[str, bool],
    as_trimesh: bool = False,
) -> None:
    path = pathlib.Path(inpath)
    timml_spec, ttim_spec = gistim.model_specification(path, active_elements)
    timml_model, _, observations = gistim.timml_elements.initialize_model(timml_spec)
    ttim_model, _ = gistim.ttim_elements.initialize_model(ttim_spec, timml_model)
    timml_model.solve()
    ttim_model.solve()

    gdf_head = gistim.ttim_elements.head_observations(timml_model, observations)

    extent, crs = gistim.gridspec(path, cellsize)
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
    write_observations(gdf_head, outpath)
    return
