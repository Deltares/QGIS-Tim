gistim
======

``gistim`` is a Python package. It translates GIS data to ``TimML`` objects. Specifically:

1. It infers the model definition from a GeoPackage.
2. It loads every layer of the GeoPackage into a ``geopandas.GeoDataFrame``.
3. It translates the GeoDataFrames into the corresponding TimML analytic elements.
4. It translates ``headgrid`` output of a TimML model to an ``xarray.DataArray``.

The result can be processed, plotted, or stored in many file formats with the aid of the
DataArray data structure.

When called by the plugin, the result is automatically written to a netCDF file
and loaded into QGIS. However, the module can also be used fully separately from
QGIS (albeit to process a GeoPackage that was likely earlier written with the 
Qgis-Tim plugin).

To illustrate, a typical interactive workflow consists of the following steps:

* Start QGIS.
* Define the TimML model with the plugin.
* The model input is written to a geopackage.
* Start the TimServer.
* Compute is called, the server reads the geopackage, sets up the model,
* solves, produces a grid of heads, and stores the heads in a netCDF file.
* The netCDF file is loaded into QGIS.

In comparison, a scripting workflow:

* Start QGIS.
* Define the TimML model with the plugin.
* The model input is written to a geopackage.
* Close QGIS.
* Start an interactive Python (conda) session.
* Use ``gistim`` to load the GeoPackage data into a number of dataframes.
* Initialize the model with the dataframes.
* Solve the model and compute heads, store some results.
* Change the values in a dataframe.
* Initialize the model for the second time.
* Solve, compute heads, store some results.
* ... and so forth.
