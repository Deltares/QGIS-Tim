import pathlib
from typing import List, Union

import affine
import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import shapely.wkt
import xarray as xr


def coord_reference(da_coord):
    """
    Extracts dx, xmin, xmax for a coordinate DataArray, where x is any coordinate.

    If the DataArray coordinates are nonequidistant, dx will be returned as
    1D ndarray instead of float.

    Parameters
    ----------
    a : xarray.DataArray of a coordinate

    Returns
    --------------
    tuple
        (dx, xmin, xmax) for a coordinate x
    """
    x = da_coord.values

    # Possibly non-equidistant
    dx_string = f"d{da_coord.name}"
    if dx_string in da_coord.coords:
        dx = da_coord.coords[dx_string]
        if (dx.shape == x.shape) and (dx.size != 1):
            # choose correctly for decreasing coordinate
            if dx[0] < 0.0:
                end = 0
                start = -1
            else:
                start = 0
                end = -1
            dx = dx.values.astype(np.float64)
            xmin = float(x.min()) - 0.5 * abs(dx[start])
            xmax = float(x.max()) + 0.5 * abs(dx[end])
            # As a single value if equidistant
            if np.allclose(dx, dx[0]):
                dx = dx[0]
        else:
            dx = float(dx)
            xmin = float(x.min()) - 0.5 * abs(dx)
            xmax = float(x.max()) + 0.5 * abs(dx)
    elif x.size == 1:
        raise ValueError(
            f"DataArray has size 1 along {da_coord.name}, so cellsize must be provided"
            f" as a coordinate named d{da_coord.name}."
        )
    else:  # Equidistant
        # TODO: decide on decent criterium for what equidistant means
        # make use of floating point epsilon? E.g:
        # https://github.com/ioam/holoviews/issues/1869#issuecomment-353115449
        dxs = np.diff(x.astype(np.float64))
        dx = dxs[0]
        atolx = abs(1.0e-4 * dx)
        if not np.allclose(dxs, dx, atolx):
            raise ValueError(
                f"DataArray has to be equidistant along {da_coord.name}, or cellsizes"
                f" must be provided as a coordinate named d{da_coord.name}."
            )

        # as xarray uses midpoint coordinates
        xmin = float(x.min()) - 0.5 * abs(dx)
        xmax = float(x.max()) + 0.5 * abs(dx)

    return dx, xmin, xmax


def spatial_reference(a):
    """
    Extracts spatial reference from DataArray.

    If the DataArray coordinates are nonequidistant, dx and dy will be returned
    as 1D ndarray instead of float.

    Parameters
    ----------
    a : xarray.DataArray

    Returns
    --------------
    tuple
        (dx, xmin, xmax, dy, ymin, ymax)

    """
    dx, xmin, xmax = coord_reference(a["x"])
    dy, ymin, ymax = coord_reference(a["y"])
    return dx, xmin, xmax, dy, ymin, ymax


def transform(a):
    """
    Extract the spatial reference information from the DataArray coordinates,
    into an affine.Affine object for writing to e.g. rasterio supported formats.

    Parameters
    ----------
    a : xarray.DataArray

    Returns
    -------
    affine.Affine

    """
    dx, xmin, _, dy, _, ymax = spatial_reference(a)

    def equidistant(dx, name):
        if isinstance(dx, np.ndarray):
            if np.unique(dx).size == 1:
                return dx[0]
            else:
                raise ValueError(f"DataArray is not equidistant along {name}")
        else:
            return dx

    dx = equidistant(dx, "x")
    dy = equidistant(dy, "y")

    if dx < 0.0:
        raise ValueError("dx must be positive")
    if dy > 0.0:
        raise ValueError("dy must be negative")
    return affine.Affine(dx, 0.0, xmin, 0.0, dy, ymax)


def rasterize(geodataframe, like, fill, **kwargs):
    """
    Rasterize a geopandas GeoDataFrame onto the given
    xarray coordinates.

    Parameters
    ----------
    geodataframe : geopandas.GeoDataFrame
    column : str, int, float
        column name of geodataframe to burn into raster
    like : xarray.DataArray
        Example DataArray. The rasterized result will match the shape and
        coordinates of this DataArray.
    fill : float, int
        Fill value for nodata areas. Optional, default value is np.nan.
    kwargs : additional keyword arguments for rasterio.features.rasterize.
        See: https://rasterio.readthedocs.io/en/stable/api/rasterio.features.html#rasterio.features.rasterize

    Returns
    -------
    rasterized : xarray.DataArray
        Vector data rasterized. Matches shape and coordinates of ``like``.
    """
    shapes = [geom for geom in geodataframe.geometry]
    # shapes must be an iterable
    try:
        iter(shapes)
    except TypeError:
        shapes = (shapes,)

    raster = rasterio.features.rasterize(
        shapes,
        out_shape=like.shape,
        fill=fill,
        transform=transform(like),
        **kwargs,
    )
    return xr.DataArray(raster, like.coords, like.dims)


def layer_statistics(path: Union[pathlib.Path, str], gdf: gpd.GeoDataFrame):
    """
    Extract summary statistics of all variables present in a Dataset.

    Variables must contain dimensions ``("layer", "y","x")``.

    Parameters
    ----------
    path: Union[pathlib.Path, str]
        Path to the netCDF dataset containing geohydrologic subsoil properties.
    geodataframe: gpd.GeoDataFrame
        Defines area of interest

    Returns
    -------
    statistics: pandas.DataFrame
        The layers are stored as rows, the variables as columns.
    """
    xmin, ymin, xmax, ymax = gdf.total_bounds
    ds = xr.open_dataset(path).sel(x=slice(xmin, xmax), y=slice(ymax, ymin))
    first_var = next(iter(ds.data_vars.keys()))
    like = ds[first_var].isel(layer=0).drop("layer")
    area_of_interest = rasterize(gdf, like, fill=0) != 0

    stats = pd.DataFrame()
    for variable in ds.data_vars:
        da = ds[variable].where(area_of_interest)
        stats[f"{variable}-min"] = da.min(["y", "x"])  # .to_dataframe(),
        stats[f"{variable}-max"] = da.max(["y", "x"])  # .to_dataframe(),
        stats[f"{variable}-mean"] = da.mean(["y", "x"])  # .to_dataframe(),
        stats[f"{variable}-median"] = da.median(["y", "x"])  # .to_dataframe(),
        stats[f"{variable}-std"] = da.std(["y", "x"])  # .to_dataframe(),
    return stats


def as_aquifer_aquitard(dataframe: pd.DataFrame, statistic: str = "mean"):
    """
    Convert a layer statistics dataframe into a table that can be directly
    copy-pasted into the QGIS plugin Aquifer properties layer.

    Primarily, this means interleaving conductivities and resistances
    in separate rows.

    Parameters
    ----------
    dataframe: pandas.DataFrame
        A dataframe containing layer statistics.
    statistic: str, optional
        Which statistic to use. Default value: ``"mean"``

    Returns
    -------
    aquifer_aquitard_table: pandas.DataFrame
        Reshuffled rows, containing only the data required for the plugin
        Aquifer properties.
    """
    n_layer = len(dataframe)
    out = pd.DataFrame()
    out["fid"] = np.arange(n_layer)
    out["layer"] = np.arange(n_layer)
    out["aquitard_resistance"] = np.nan
    out["aquitard_resistance"].values[1:] = dataframe[f"c-{statistic}"].values[:-1]
    out["aquitard_porosity"] = np.nan
    out["aquitard_storage"] = np.nan
    out["aquifer_conductivity"] = dataframe[f"kh-{statistic}"].values
    out["aquifer_porosity"] = np.nan
    out["aquifer_storage"] = np.nan
    out["aquifer_top"] = dataframe[f"top-{statistic}"]
    out["aquifer_bottom"] = dataframe[f"bottom-{statistic}"]
    out["topboundary_top"] = np.nan
    out["topboundary_head"] = np.nan
    return out


def netcdf_to_table(inpath: str, outpath: str, wkt_geometry: List[str]) -> None:
    geometries = [shapely.wkt.loads(geom) for geom in wkt_geometry]
    outpath = pathlib.Path(outpath)
    gdf = gpd.GeoDataFrame(geometry=geometries)
    stats = layer_statistics(inpath, gdf)
    stats.to_csv(outpath.parent / f"{outpath.stem}-statistics.csv")
    table = as_aquifer_aquitard(stats)
    table.to_csv(outpath)
