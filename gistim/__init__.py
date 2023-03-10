import pathlib
from typing import Dict, Union

import pkg_resources

from gistim import timml_elements, ttim_elements

from .common import gridspec, model_specification
from .compute import compute_steady, compute_transient
from .data_extraction import as_aquifer_aquitard, layer_statistics
from .ugrid import to_ugrid2d

# version
try:
    __version__ = pkg_resources.get_distribution(__name__).version
except pkg_resources.DistributionNotFound:
    # package is not installed
    pass


def convert_to_script(inpath: str, outpath: str) -> None:
    timml_spec, ttim_spec = model_specification(inpath, {})
    timml_script = timml_elements.convert_to_script(timml_spec)
    try:
        ttim_script = ttim_elements.convert_to_script(ttim_spec)
    except Exception:
        ttim_script = ""

    with open(outpath, "w") as f:
        f.write(timml_script)
        f.write("\n")
        f.write(ttim_script)


def compute(
    inpath: Union[pathlib.Path, str],
    outpath: Union[pathlib.Path, str],
    mode: str,
    cellsize: float,
    active_elements: Dict[str, bool],
) -> None:
    """
    Compute the results of TimML model.

    The model is fully specified by the GeoPacakge dataset in the path.

    The extent of the head grids is read from a vector layer in the
    GeoPackage file.

    Parameters
    ----------
    path: Union[pathlib.Path, str]
        Path to the GeoPackage file containing the full model input.
    cellsize: float
        Grid cell size of the computed output

    Returns
    -------
    None
        The result is written to a netCDF file. Its name is generated from
        the geopackage name, and the requested grid cell size.
    """
    if mode == "steady-state":
        compute_steady(inpath, outpath, cellsize, active_elements)
    elif mode == "transient":
        compute_transient(inpath, outpath, cellsize, active_elements)
    else:
        raise ValueError(f'Invalid mode: {mode}: should be "steady" or "transient".')
    return
