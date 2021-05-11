import pathlib
import re
from typing import Any, Callable, Dict, NamedTuple, Tuple, Union

import fiona
import geopandas as gpd
import numpy as np
import pandas as pd
import ttim
import xarray as xr


# Dataframe to ttim element
# --------------------------
def aquifer(dataframe: gpd.GeoDataFrame) -> ttim.TimModel:
    """
    Parameters
    ----------
    dataframe: geopandas.GeoDataFrame

    Returns
    -------
    ttim.TimModel
    """
    pass 