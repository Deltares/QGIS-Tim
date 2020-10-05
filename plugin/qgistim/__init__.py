"""
 This script initializes the plugin, making it known to QGIS.
"""
from . import geopackage
from . import timml_elements

# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load QgisTim class from file QgisTim.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .qgistim import QgisTim

    return QgisTim(iface)
