import pathlib
from typing import Union

import numpy as np
import xarray as xr

from gistim.geopackage import CoordinateReferenceSystem
from gistim.ugrid import to_ugrid2d


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
