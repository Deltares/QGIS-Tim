QGIS-Tim
========

Documentation: https://deltares.gitlab.io/imod/qgis-tim

This repository contains two Python packages:

* A QGIS plugin to provide a limited graphical interface to setup a `GeoPackage` _
  containing the vector data required by a `TimML`_ and  analytic element model
  and read results.
* The ``gistim`` package which contains the functions required to transform a
  GeoPackage into a TimML model. It is fully independent of the plugin, relying
  on packages such as ``geopandas`` instead of QGIS functions. The utilities it
  provides can be used independently of QGIS, in a fully scripted workflow.

.. _TimML: https://github.com/mbakker7/timml
.. _TTim: https://github.com/mbakker7/ttim
.. _GeoPackage: https://www.geopackage.org

Installation
------------

In case no recent version of QGIS is available:
Download and install a recent version of QGIS: 3.18 or upwards:
https://www.qgis.org/en/site/forusers/download.html

Download and install a miniforge Python installation:
https://github.com/conda-forge/miniforge

Install the gistim Python package:

1. Open the miniforge prompt (search in Windows Start for "Miniforge Prompt").
2. Create a new conda environment, run: conda create --name tim python=3.9
3. Activate the environment: conda activate tim
4. Run: conda install -c conda-forge gistim
5. Install ttim: pip install ttim
6. Configure the gistim installation, so that the QGIS plugin is able to find it.
   Run: python -m gistim configure append

Install the QGIS plugin now. The qgistim.zip should not be inzipped manually, QGIS will do so.

1. Open QGIS.
2. At the top, find the Plugins menu (~sixth object in the menubar).
3. Find "Manage and Install plugins" (first object in drop-down).
4. Find "Install from ZIP" (Sixth in list).
5. Enter the path to the qgistim.zip file.
6. Click "Install Plugin".

This will add an icon to the toolbar(s). By clicking the icon, the plugin is started.
Most of the functionality of the plugin will only work if the external (conda) Python
interpreter is running. This can be started by clicking the "Start" button, which is
found above the tabs.

(In the drop-down menu there, all interpreters are listed that have been added
by the "python -m gistim configure append"  command.)
