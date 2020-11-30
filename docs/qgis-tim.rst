********
Qgis-Tim
********

Qgis-Tim is a QGIS plugin to facilitate creating input for TimML analytic
element models.

This section briefly discusses the plugin functionality.

Dataset
=======

Analytic element input is typically a collection of points, lines, and polygons.
Qgis-Tim represent a single model with a single GeoPackage. To quote wikipedia:

    A GeoPackage (GPKG) is an open, non-proprietary, platform-independent and
    standards-based data format for geographic information system implemented as
    a SQLite database container.

The primary benefit of a format like GeoPackage over e.g. ESRI Shapefiles is
that it is possible to store multiple vector layers in a single file. This means
that a single geopackage file is sufficient to describe all input of a TimML
analytic element model.

Within the context of Qgis-Tim, every analytic element must be stored in a
GeoPackage. Changes are immediately written to the geopackage file, which is
thereby always kept up to date.

Styling layers
==============

The different elements are represented as layers in the GeoPackage, and also as
ordinary vector layers in QGIS. Consequently, all the standard QGIS
functionality works on them, and layers can be styled via the Layers Panel, by
right-clicking on a layer.

Deleting element layers
=======================

Deleting layers from the Layers panel will not actually delete a layer from the
geopackage. The Layers panel is purely a representation of the layers that are
on display in the map window.

To delete a layer from a GeoPackage, use the Browser Panel, and find the GeoPackage
icon. Right-click on the GeoPackage icon, and choose "New Connection". Now, find
the geopackage of interest. 

It will be added under the GeoPackage icon (check the triangle dropdown menu if
it's not visible). Right-click the layer to delete, and choose "Delete
Layer...".

Elements
========

By clicking on the button of one the elements, an empty layer will be added to
the geopackage. The layer will also be added to the Layers Panel.

Individual elements can be added to this layer by toggling Editing, and adding
Geometries. Per element, a menu will pop up where parameter values can be
entered.

UniformFlow
-----------

CircularAreaSink
----------------

Well
----

Headwell
--------

PolygonInhom
------------

HeadLineSink
------------

LineSinkDitch
-------------

LeakyLineDoublet
----------------

ImpLineDoublet
--------------


Start TimServer
===============

For a number of technical reasons, TimML does not run in the QGIS interpreter.
Instead, a server-client approach is used, where the client (the plugin) asks
the server process (running locally in a conda interpreter) to compute a result.

Since the geopackage is a full specification of the analytic element model, a
call from the plugin only needs to specify the location of the geopackage and
the desired cellsize of the output suffice to run the analytic element model.
Of course, this does mean a server has to running, listening for the calls!

This "Start TimServer" button starts the server. It'll open a new command line
window, which shows some information about the current status of the server.

Domain
======

The domain button creates a rectangular polygon, with its corners on the current
viewing extent of the QGIS map view. This polygon determines the area in which
head values of the analytic element model are computed (recall that the analytic
elements give results for an infinite plane).

To change the domain, either zoom in or out and click the domain button again.
Alternatively, toggle Editing, and click vertex editing to change the location
of the rectangle corners. Note that only the extent (xmin, xmax, ymin, ymax) of
the domain polygon is used; the exact shape of the polygon does not matter.

Cellsize
========

Defines the cellsize of the computed result.

Note that the units of the cellsize are defined by the coordinate reference
system. If your coordinate reference system is a projected system (like RD New,
EPSG:28992) cellsize units are generally in meters; if your coordinate reference
system is set to WGS84 (latitudes and longitudes), cellsize is interpreted in
degrees

Compute
=======

Makes the call to the TimServer to compute heads.

The active GeoPackage (visible in the Dataset "window") at the top of the
Qgis-Tim panel is converted into a TimML model. The heads are computed
within the most recently created Domain polygon, at a cellsize provided
by the cellsize spinbox.
