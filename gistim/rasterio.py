"""
Functions that make use of `rasterio
<https://rasterio.readthedocs.io/en/stable/>`_ and
https://corteva.github.io/rioxarray/stable/index.html for input and output to
raster formats, and contouring/polygonization of raster data.

Maybe copy over a utility to read multiple files (e.g. layers) into a single
DataArrray: https://gitlab.com/deltares/imod/imod-python/-/tree/master/imod/array_io
"""
import geopandas as gpd
import numpy as np
import shapely.geometry as sg
import xarray as xr


# since rasterio is a big dependency that is sometimes hard to install
# and not always required, this is an optional dependency
try:
    import rasterio
    import rioxarray
except ImportError:
    pass


def contours(da):
    """
    Contour a 2D-DataArray into a GeoDataFrame.

    Parameters
    ----------
    da : xr.DataArray with dimensions ("y", "x")

    Returns
    -------
    polygonized : geopandas.GeoDataFrame
    """
    if da.dims != ("y", "x"):
        raise ValueError('Dimensions must be ("y", "x")')

    values = da.values
    if values.dtype == np.float64:
        values = values.astype(np.float32)

    transform = da.rio.transform()
    shapes = rasterio.features.shapes(values, transform=transform)

    geometries = []
    colvalues = []
    for (geom, colval) in shapes:
        geometries.append(sg.Polygon(geom["coordinates"][0]))
        colvalues.append(colval)

    gdf = gpd.GeoDataFrame({"value": colvalues, "geometry": geometries})
    gdf.crs = da.attrs.get("crs")
    return gdf
