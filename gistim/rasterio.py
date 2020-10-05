"""
Functions that make use of `rasterio
<https://rasterio.readthedocs.io/en/stable/>`_ and
https://corteva.github.io/rioxarray/stable/index.html for input and output to
raster formats, and contouring/polygonization of raster data.
"""
import pathlib

import geopandas as gpd
import numpy as np
import rasterio.features
import rioxarray
import shapely.geometry as sg
import xarray as xr


def contours(da, levels):
    """
    Contour a 2D-DataArray into a GeoDataFrame.

    Parameters
    ----------
    da : xr.DataArray with dimensions ("y", "x")
    levels : np.ndarray of floats

    Returns
    -------
    polygonized : geopandas.GeoDataFrame
    """
    if da.dims != ("y", "x"):
        raise ValueError('Dimensions must be ("y", "x")')

    transform = da.rio.transform()
    # rasterio.features.shapes does not accept 64-bit dtypes
    index = np.digitize(da.values, levels).astype(np.int32)

    geometries = []
    values = []
    shapes = rasterio.features.shapes(index, transform=transform)
    for (geometry_collection, value) in shapes:
        # Skip if value >= largest level
        if value < levels.size:
            # geometry_collection["coordinates"] is a list of linearrings
            # the first one is the exterior. For contours, we only need this one
            # or we end up with duplicated geometries.
            geometry = geometry_collection["coordinates"][0]
            geometries.append(sg.LineString(geometry))
            values.append(int(value))

    gdf = gpd.GeoDataFrame({"head": levels[values], "geometry": geometries})
    gdf.crs = da.rio.crs
    return gdf
