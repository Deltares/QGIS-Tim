import pkg_resources

from gistim.compute import compute_steady, compute_transient
from gistim.data_extraction import as_aquifer_aquitard, layer_statistics
from gistim.ugrid import to_ugrid2d

# version
try:
    __version__ = pkg_resources.get_distribution(__name__).version
except pkg_resources.DistributionNotFound:
    # package is not installed
    pass
