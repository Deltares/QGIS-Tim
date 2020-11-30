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

1. Start QGIS.
2. Define the TimML model with the plugin.
3. The model input is written to a geopackage.
4. Start the TimServer.
5. Compute is called, the server reads the geopackage, sets up the model,
   solves, produces a grid of heads, and stores the heads in a netCDF file.
6. The netCDF file is loaded into QGIS.

In comparison, a scripting workflow:

1. Start QGIS.
2. Define the TimML model with the plugin.
3. The model input is written to a geopackage.
4. Close QGIS.
5. Start an interactive Python (conda) session.
6. Use ``gistim`` to load the GeoPackage data into a number of dataframes.
7. Initialize the model with the dataframes.
8. Solve the model and compute heads, store some results.
9. Change the values in a dataframe (e.g. in the context of a sensitivity
   analysis).
10. Initialize the model for the second time.
12. Solve, compute heads, store some results.
13. ... and so forth.
