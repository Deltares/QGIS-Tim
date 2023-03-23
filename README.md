# QGIS-Tim

QGIS-Tim is an open source project for multi-layer groundwater flow
simulations. QGIS-Tim provides a link between QGIS and the open source analytic
element method software: [TimML (steady-state)](https://github.com/mbakker7/timml)
and [TTim (transient)](https://github.com/mbakker7/ttim).

The benefit of the analytic element method (AEM) is that no grid or
time-stepping is required. Geohydrological features are represented by points,
lines, and polygons. QGIS-Tim stores these features in a
[GeoPackage](https://www.geopackage.org/).

QGIS-Tim consists of a "front-end" and a "back-end". The front-end is a QGIS
plugin that provides a limited graphical interface to setup model input,
visualize, and analyze model input. The back-end is a Python package. It reads
the contents of the GeoPackage and transforms it into a TimML or TTim model,
computes a result, and writes it to a file that the QGIS plugin loads.

## Installation

Download and install a recent version of QGIS (>3.22):
<https://www.qgis.org/en/site/forusers/download.html>

Download and install a miniforge Python installation:
<https://github.com/conda-forge/miniforge>

Install the gistim Python package:

1.  Open the miniforge prompt (search in Windows Start for \"Miniforge
    Prompt\").
2.  Create a new conda environment, run: conda create \--name tim
    python=3.9
3.  Activate the environment: conda activate tim
4.  Run: conda install -c conda-forge gistim
6.  Configure the gistim installation, so that the QGIS plugin is able
    to find it. Run: ``python -m gistim configure``

Install the QGIS plugin now. The qgistim.zip should not be unzipped
manually, QGIS will do so.

1.  Open QGIS.
2.  At the top, find the Plugins menu (\~sixth object in the menubar).
3.  Find \"Manage and Install plugins\" (first object in drop-down).
4.  Find \"Install from ZIP\" (Sixth in list).
5.  Enter the path to the qgistim.zip file.
6.  Click \"Install Plugin\".

This will add an icon to the toolbar(s). By clicking the icon, the plugin is
started. The QGIS plugin will automatically start and external interpreter when
it is required.
