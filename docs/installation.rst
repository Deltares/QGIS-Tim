Installation
============

This repository contains two Python packages:

* ``./plugin`` contains the source code for a QGIS plugin. This plugin provides a
  limited graphical interface to setup a
  `GeoPackage <https://www.geopackage.org/>`_ containing the vector data required
  by a `TimML <https://github.com/mbakker7/timml>`_ analytic element model and
  read results.
* ``./gistim`` contains the functions required to transform a GeoPackage into a
  TimML model. It is fully independent of the plugin, relying on packages such
  as `rasterio` and `geopandas` instead of QGIS functions. The utilities it
  provides can be used independently of QGIS, in a fully scripted workflow.

A modern (>=3.0) QGIS installation is required. A basic QGIS installation (as
can be gotten `here <https://qgis.org/en/site/>`_) suffices to run the plugin,
but will not suffice for full development capabilities, see the Developer
Documentation. When downloading, choose the Standalone installer, currently
version 3.16.

QGIS comes with its own Python installation and interpreter. This installation
does not provide a package manager such as
`conda <https://docs.conda.io/en/latest/>`_. This complicates the distribution of
complex binary dependencies. Hence, the ``gistim`` package (and TimML) should run
in a different interpreter. This requires:

* A modern Python version (>=3.6)
* `GeoPandas <https://geopandas.org/>`_
* `Xarray <https://xarray.pydata.org/en/stable/>`_, which in turn requires numpy
  and pandas
* `Rasterio <https://rasterio.readthedocs.io/en/latest/>`_
* `rioxarray <https://corteva.github.io/rioxarray/stable/index.html>`_
* `netCDF4 <https://unidata.github.io/netcdf4-python/netCDF4/index.html>`_

Rasterio, rioxarray, and netCDF4 are optional dependencies but output options
are severely limited without them. Both geopandas and rasterio requires GDAL,
which is a heavy and complex binary dependency. It is highly recommended to
install these packages via `conda` in a separate environment -- the
specification is included in the `environment.yml` of this repository.

Installing the Python package
-----------------------------

The recommended way of installing is using conda, in a separate conda
environment. This environment (called `tim`) can be setup by downloading the
`environment.yml` and running the following command in the anaconda prompt:

.. code-block:: console

    conda env create -f environment.yml

After creation, the conda environment can be activated by running the following
command in the anaconda prompt:

.. code-block:: console

    conda activate tim

See the installation instruction below.

Installing the plugin in QGIS
-----------------------------

There are a few ways to install this plugin:

* Copy the directory `./plugin/qgistim` to your local QGIS plugins directory.
  On Windows, this should be located at:

  ``c:\Users\{username}\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins``

  The location can be found in the QGIS GUI via: 

  ``QGIS menu > Settings > User Profiles > Open Active Profile Folder``

* Alternatively, zip the ``./plugin/qgistim`` directory. Then, in the Plugins
  menu, under "Manage and Install Plugins...", find "Install from ZIP", and
  enter the path to the zipfile -- this unzips the files and copies them to the
  directory mentioned above.

The plugin is good to go now. Find the Qgis-Tim entry in the Plugins menu, and
click it to open a docked menu on the right side of your QGIS screen.