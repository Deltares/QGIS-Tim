import pkg_resources

import gistim.compute
import gistim.data_extraction

# version
try:
    __version__ = pkg_resources.get_distribution(__name__).version
except pkg_resources.DistributionNotFound:
    # package is not installed
    pass
