# QGIS-Tim

QGIS-Tim is an open source project for multi-layer groundwater flow
simulations. QGIS-Tim provides a link between QGIS and the open source analytic
element method software: [TimML (steady-state)](https://github.com/mbakker7/timml)
and [TTim (transient)](https://github.com/mbakker7/ttim).

The benefit of the analytic element method (AEM) is that no grid or
time-stepping is required. Geohydrological features are represented by points,
lines, and polygons. QGIS-Tim stores these features in a
[GeoPackage](https://www.geopackage.org/).

QGIS-Tim consists of a "front-end" (the QGIS plugin) and a "back-end" (the TimML and TTim server).
The front-end is a QGIS plugin that provides a limited graphical interface to setup model input,
visualize, and analyze model input. The back-end is a Python package. The plugin converts the
GeoPackage content to a JSON file or a Python script. The back-end reads the JSON file, does the
necessary computations and writes result files that are loaded back into QGIS by the plugin.

## Documentation
[Find the documentation here.](https://deltares.github.io/QGIS-Tim/)

## Installation

Download and install a recent version of QGIS (>=3.28):
<https://www.qgis.org/en/site/forusers/download.html>

### Method 1: From the QGIS plugin database 
**NB** Due to ongoing developments new features and bug fixes might not be part of this release. Consider installation method 2.

1.  Open QGIS.
3.  At the top, find the Plugins menu (\~sixth object in the menubar).
4.  Find \"Manage and Install plugins\" (\~first object in drop-down).
5.  Find \"All\" (\~first in left section).
6.  Search for \"Qgis-Tim\".
7.  Click \"Install Plugin\".

### Method 2: From ZIP file (recommended for now) 
1.  Download the \"QGIS-Tim-plugin.zip\" from the [GitHub Releases page](https://github.com/Deltares/QGIS-Tim/releases) (do not unzip!).
2.  Open QGIS.
3.  At the top, find the Plugins menu (\~sixth object in the menubar).
4.  Find \"Manage and Install plugins\" (\~first object in drop-down).
5.  Find \"Install from ZIP\" (\~fourth in left section).
6.  Enter the path to the file \"QGIS-TIM-plugin.zip\".
7.  Click \"Install Plugin\".

This will add an icon to the toolbar(s). By clicking the icon, the plugin is started.

### 3. Install the TimML and TTim server
With the plugin installed, we can already define model input and convert it to Python scripts or JSON files.
To run TimML and TTim computations directly from QGIS, we need to install a server program which contains TimML and TTim.

1.  Start the QGIS-Tim plugin by clicking the QGIS-Tim icon in the toolbar.
2.  Find and click the "Install TimML and TTim server" button at the bottom of the plugin window.
3.  Click the "Install latest release from GitHub" button to download and install the server program.

Specific releases can also be manually downloaded from the [GitHub Releases page](https://github.com/Deltares/QGIS-Tim/releases):

1.  Download the gistim ZIP file for your platform: Windows, macOS, or Linux.
2.  Find and click the "Install TimML and TTim server" button at the bottom of the plugin window.
3.  Set the path to the downloaded ZIP file in the "Install from ZIP file" section.
4.  Click the "Install" button.
