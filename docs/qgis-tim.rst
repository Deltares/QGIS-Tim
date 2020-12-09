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


.. image:: https://www.geopackage.org/img/geopkg.png
  :target: https://www.geopackage.org//

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

.. image:: _static/qgis-geopackage-connection.png
  :target: _static/qgis-geopackage-connection.png

It will be added under the GeoPackage icon (check the triangle dropdown menu if
it's not visible). Right-click the layer to delete, and choose "Delete
Layer...".

.. image:: _static/qgis-geopackage-delete-layer.png
  :target: _static/qgis-geopackage-delete-layer.png

Elements
========

By clicking on the button of one the elements, an empty layer will be added to
the geopackage. The layer will also be added to the Layers Panel.

Individual elements can be added to this layer by toggling Editing, and adding
Geometries. Per element, a menu will pop up where parameter values can be
entered.

If you're entering a great deal of values -- e.g. dozens of wells with the same
discharge, it's probably inconvenient to enter a feature one by one. The pop-up
form can be disabled via the QGIS settings as follows:

``Settings > Options > Digitizing > Feature Creation > Suppress attribute form pop-up after feature creation``

Aquifer
-------

The aquifer and aquitard properties are stored in this layer. Note that TimML
has multiple Model constructors: ``ModelMaq``, ``Model3D``, and ``Model``. They
vary subtly in input requirements. The table of this plugin is meant for the
``ModelMaq`` class. For the input it means:

* Aquifers and leaky layers always interleave each other;
* Therefore, a row should either contain a resistance value or a conductivity value;
* Every row with with a conductivity (an aquifer) **must** be followed by a row
  with a resistance (the leaky layer);
* Only the final row bottom value is used, all top values are used to define
  the vertical position of the layers;
* Note that leaky layers can have a thickness of 0 in TimML;
* The final row is always an aquifer, with a closed geohydrological base below.

For a leaky top layer:

* A leaky layer on top can be set by entering a value for ``tophead``, in the
  first row;
* In that case, the first row must contain a resistance value.

Find two examples below. The attribute table without a leaky layer on top:

+-----+-----+-------+--------------+------------+-------+---------+----------+---------+
| row | fid | index | conductivity | resistance | top   |  bottom | porosity | headtop |
+-----+-----+-------+--------------+------------+-------+---------+----------+---------+
|   0 |   0 |     0 |          5.0 |            |   5.0 |         |      0.3 |         |
|   1 |   1 |     1 |              |      100.0 |   0.0 |         |      0.3 |         |
|   2 |   2 |     2 |          5.0 |            |  -5.0 |   -10.0 |      0.3 |         |
+-----+-----+-------+--------------+------------+-------+---------+----------+---------+

The same input, now with a semi-confined leaky layer on top:

+-----+-----+-------+--------------+------------+-------+---------+----------+---------+
| row | fid | index | conductivity | resistance | top   |  bottom | porosity | headtop |
+-----+-----+-------+--------------+------------+-------+---------+----------+---------+
|   0 |   0 |     0 |              |      100.0 |  10.0 |         |      0.3 |     3.0 |
|   1 |   1 |     1 |          5.0 |            |   5.0 |         |      0.3 |         |
|   2 |   2 |     2 |              |      100.0 |   0.0 |         |      0.3 |         |
|   3 |   3 |     3 |          5.0 |            |  -5.0 |   -10.0 |      0.3 |         |
+-----+-----+-------+--------------+------------+-------+---------+----------+---------+

The inclusion of a semi-confined leaky top exludes the use of
a Constant element, unless explicitly placed within an inhomogeneity.

**Note bene**: the index column specifies the relative order of this table, and
thereby which layers are on top, and which are bottom. Within TimML, only
aquifers have layer numbers, and leaky layers do not. Furthermore, heads are
only computed for the aquifers.

The Aquifer has the following columns:

* fid: int, QGIS feature ID
* index: int, determines table order for TimML
* conductivity: float, ``kaq``
* resistance: float, ``c``
* top: float, ``z``
* bottom: float, ``z``
* porosity: float, ``npor``
* headtop: float, ``hstar`` and ``topboundary``

Constant
--------

The following columns which correspond with the following TimML
keyword arguments:

* fid: int, QGIS feature ID
* head: float, ``hr``
* layer: int, ``layer``
* label: str, ``label``

UniformFlow
-----------

The following columns which correspond with the following TimML
keyword arguments:

* fid: int, QGIS feature ID
* slope: float, ``slope``
* angle: float, ``angle``
* label: str, ``label``

CircularAreaSink
----------------

The following columns which correspond with the following TimML
keyword arguments:

* fid: int, QGIS feature ID
* rate: float, ``N``

``xc``, ``yc``, and ``R`` (radius) are inferred from the geometry.

Well
----

The following columns which correspond with the following TimML
keyword arguments:

* fid: int, QGIS feature ID
* discharge: float, ``Qw``
* radius: float, ``rw``
* resistance: float, ``res``
* layer: float, ``layers``
* label: str, ``label``

``xw`` and ``yw`` are inferred from the geometry.

Headwell
--------

The following columns which correspond with the following TimML
keyword arguments:

* fid: int, QGIS feature ID
* head: float, ``hw``
* radius: float, ``rw``
* resistance: float, ``res``
* layer: float, ``layers``
* label: str, ``label``

``xw`` and ``yw`` are inferred from the geometry.

PolygonInhom
------------

Not implemented yet.

HeadLineSink
------------

The following columns which correspond with the following TimML
HeadLineSinkString keyword arguments:

* fid: int, QGIS feature ID
* head: float, ``hls``
* resistance: float, ``res``
* width: float, ``wh`` 
* order: int, ``order`` 
* layer: int, ``layers`` 
* label: str, ``label``

``xy`` is inferred from the geometry (row by row).

LineSinkDitch
-------------

The following columns which correspond with the following TimML
keyword arguments:

* fid: int, QGIS feature ID
* discharge: float, ``Qls``
* resistance: float, ``res``
* width: float, ``wh`` 
* order: int, ``order`` 
* layer: int, ``layers`` 
* label: str, ``label``

``xy`` is inferred from the geometry (row by row).

LeakyLineDoublet
----------------

The following columns which correspond with the following TimML
keyword arguments:

* fid: int, QGIS feature ID
* resistance: float, ``res``
* order: int, ``order`` 
* layer: int, ``layers`` 
* label: str, ``label``

``xy`` is inferred from the geometry (row by row).

ImpLineDoublet
--------------

The following columns which correspond with the following TimML
keyword arguments:

* fid: int, QGIS feature ID
* order: int, ``order`` 
* layer: int, ``layers`` 
* label: str, ``label``

``xy`` is inferred from the geometry (row by row).

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

.. code-block:: console

    Starting TimServer on localhost, port: 1024
    b'{"path": "C:\\\\tmp\\\\test-model.gpkg", "cellsize": 500.0}'
    Current server hash: None
    md5 hash: ea70382beb61a2240fed4b47baaed499
    adding timmlConstant as constant
    adding timmlHeadLineSink:kanalen as headlinesink
    adding timmlWell:onttrekking as well
    adding timmlDomain as domain
    adding timmlAquifer as aquifer
    Number of elements, Number of equations: 5 , 5
    .....
    solution complete
    Writing result to: C:\tmp\test-model.gpkg-500.nc
    Computation succesful
    b'{"path": "C:\\\\tmp\\\\test-model.gpkg", "cellsize": 100.0}'
    Current server hash: ea70382beb61a2240fed4b47baaed499
    md5 hash: ea70382beb61a2240fed4b47baaed499
    adding timmlConstant as constant
    adding timmlHeadLineSink:kanalen as headlinesink
    adding timmlWell:onttrekking as well
    adding timmlDomain as domain
    adding timmlAquifer as aquifer
    Number of elements, Number of equations: 5 , 5
    .....
    solution complete
    Writing result to: C:\tmp\test-model.gpkg-100.nc
    Computation succesful

Domain
======

The domain button creates a rectangular polygon, with its corners on the current
viewing extent of the QGIS map view. This polygon determines the area in which
head values of the analytic element model are computed (since the analytic
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
degrees.

Compute
=======

Makes the call to the TimServer to compute heads.

The active GeoPackage (visible in the Dataset "window") at the top of the
Qgis-Tim panel is converted into a TimML model. The heads are computed
within the most recently created Domain polygon, at a cellsize provided
by the cellsize spinbox.

The computation result will be written to a netCDF file, in the same location
as the model geopackage. The cellsize is included in the filename. Every layer
of the result is automatically added to the QGIS Map View.
