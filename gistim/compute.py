import json
import pathlib
from collections import defaultdict
from typing import Any, Dict, Union

import numpy as np
import pandas as pd
import timml
import tqdm
import ttim
import xarray as xr

from gistim.geopackage import CoordinateReferenceSystem, write_geopackage
from gistim.ugrid import to_ugrid2d

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
    "BuildingPit": timml.BuildingPit,
    "LeakyBuildingPit": timml.LeakyBuildingPit,
}


def write_raster(
    head: xr.DataArray,
    crs: CoordinateReferenceSystem,
    outpath: Union[pathlib.Path, str],
) -> None:
    # Write GDAL required metadata.
    head["spatial_ref"] = xr.DataArray(
        np.int32(0), attrs={"crs_wkt": crs.wkt, "spatial_ref": crs.wkt}
    )
    head.attrs["grid_mapping"] = "spatial_ref"
    head["x"].attrs = {
        "axis": "X",
        "long_name": "x coordinate of projection",
        "standard_name": "projection_x_coordinate",
    }
    head["y"].attrs = {
        "axis": "Y",
        "long_name": "y coordinate of projection",
        "standard_name": "projection_y_coordinate",
    }
    head.to_netcdf(outpath.with_suffix(".nc"), format="NETCDF3_CLASSIC")
    return


def write_ugrid(
    head: xr.DataArray,
    crs: CoordinateReferenceSystem,
    outpath: Union[pathlib.Path, str],
) -> None:
    ugrid_head = to_ugrid2d(head)
    # Write MDAL required metadata.
    ugrid_head["projected_coordinate_system"] = xr.DataArray(
        data=np.int32(0),
        attrs={"epsg": np.int32(crs.srs_id)},
    )
    ugrid_head.to_netcdf(outpath.with_suffix(".ugrid.nc"), format="NETCDF3_CLASSIC")
    return


def write_vector(
    gdf_head,
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
    elements = defaultdict(list)
    for name, entry in data.items():
        klass = TIMML_MAPPING[entry["type"]]
        for kwargs in entry["data"]:
            element = klass(model=timml_model, **kwargs)
            elements[name].append(element)
    return timml_model, elements


def timml_head_observations(
    model: timml.Model, observations: Dict
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


def timml_discharges(elements: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
    discharges = {}
    for layername, content in elements.items():
        first_element = content[0]


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


def extract_discharges(elements, nlayers):
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
                # Workaround for: https://github.com/mbakker7/timml/issues/85
                discharges = np.zeros((linestring.nls, nlayers))
                Q = (
                    (linestring.parameters[:, 0] * linestring.dischargeinf())
                    .reshape((linestring.nls, linestring.nlayers, linestring.order + 1))
                    .sum(axis=2)
                )
                discharges[:, linestring.layers[0]] = Q

                xy = linestring.xy
                for q_layered, vertex0, vertex1 in zip(discharges, xy[:-1], xy[1:]):
                    row = {f"discharge_layer{i}": q for i, q in enumerate(q_layered)}
                    row["geometry"] = {
                        "type": "LineString",
                        "coordinates": [vertex0, vertex1],
                    }
                    table_rows.append(row)
            tables[f"discharge-{layername}"] = pd.DataFrame.from_records(table_rows)

    return tables


def compute_steady(
    path: Union[pathlib.Path, str],
) -> None:
    with open(path, "r") as f:
        data = json.load(f)

    output_options = data.pop("output_options")
    headgrid = data.pop("headgrid")
    crs = CoordinateReferenceSystem(**data.pop("crs"))
    observation_names = [
        key for key, value in data.items() if value.get("type") == "Head Observation"
    ]
    observations = {name: data.pop(name) for name in observation_names}
    timml_model, elements = initialize_timml(data)
    timml_model.solve()

    # Compute gridded head data and write to netCDF.
    if output_options["raster"] or output_options["mesh"]:
        head = timml_headgrid(timml_model, **headgrid)

    if output_options["raster"]:
        write_raster(head, crs, path)
    if output_options["mesh"]:
        write_ugrid(head, crs, path)

    # Compute observations and discharge, and write to geopackage.
    if output_options["discharge"]:
        tables = extract_discharges(elements, timml_model.aq.nlayers)
    else:
        tables = {}

    if output_options["head_observations"] and observations:
        for layername, content in observations.items():
            tables[layername] = timml_head_observations(timml_model, content["data"])

    if tables:
        write_geopackage(tables, crs, path)
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


def compute(path: str, transient: bool):
    path = pathlib.Path(path)
    if not path.exists():
        raise FileExistsError(path)
    if transient:
        compute_transient(path)
    else:
        compute_steady(path)
    return
