import pathlib
from typing import Union

import numpy as np
import pandas as pd
import xarray as xr


def layer_statistics(
    path: Union[pathlib.Path, str], xmin=None, xmax=None, ymin=None, ymax=None
):
    """
    Extract summary statistics of all variables present in a Dataset.

    Variables must contain dimensions ``("layer", "y","x")``.

    Parameters
    ----------
    path: Union[pathlib.Path, str]
        Path to the netCDF dataset containing geohydrologic subsoil properties.
    xmin: float
    xmax: float
    ymin: float
    ymax: float

    Returns
    -------
    statistics: pandas.DataFrame
        The layers are stored as rows, the variables as columns.
    """
    ds = xr.open_dataset(path).sel(x=slice(xmin, xmax), y=slice(ymax, ymin))
    stats = pd.DataFrame()
    for variable in ds.data_vars:
        da = ds[variable]
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
    n_aquifer = len(dataframe)
    n_layer = n_aquifer * 2 - 1
    out = pd.DataFrame()
    out["fid"] = np.arange(n_layer)
    out["index"] = np.arange(n_layer)
    out["conductivity"] = np.full(n_layer, np.nan)
    out["resistance"] = np.full(n_layer, np.nan)
    out["top"] = np.full(n_layer, np.nan)
    out["bottom"] = np.full(n_layer, np.nan)
    out["porosity"] = 0.30
    out["headtop"] = np.full(n_layer, np.nan)

    out.loc[out.index[::2], "conductivity"] = dataframe[f"kh-{statistic}"].values
    out.loc[out.index[1::2], "resistance"] = dataframe[f"c-{statistic}"].values[:-1]

    z = np.empty(n_aquifer * 2)
    z[::2] = dataframe[f"top-{statistic}"]
    z[1::2] = dataframe[f"bottom-{statistic}"]
    out.loc[:, "top"] = z[:-1]
    out.loc[out.index[-1], "bottom"] = z[-1]

    return out
