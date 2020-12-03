A QGIS Primer
=============

There are a number of QGIS functionalities and settings to be aware of before
you can effectively setup an analytic element model. I highly recommend
reading through the steps below and to configure QGIS accordingly.

Setting the "Browser" and "Layers" panel
----------------------------------------

In the default view, the "Browser" and/or "Layers" panel may not be active.

.. image:: _static/qgis-start.png
  :target: _static/qgis-start.png

The Browser panel provides a simple file Browser. It will be necessary to
delete elements. A checkbox can be found at ``View > Panels > Browser``.

.. image:: _static/qgis-views-browser.png
  :target: _static/qgis-views-browser.png

The Layers panel provides an overview of layers active in the map view.
A checkbox can be found at ``View > Panels > Layers``.

.. image:: _static/qgis-views-layers.png
  :target: _static/qgis-views-layers.png

Setting an appropriate projection
---------------------------------

Be aware:

* A PC monitor is generally a flat surface;
* The earth is not a flat surface.

Consequently, there are many ways of approximately representing a sphere /
ellipsoid / geoid on a flat surface. These ways are encoded in different
coordinate reference systems. QGIS will automatically reproject datasets to its
"Project Coordinate Reference System" if the dataset has a coordinate
reference system defined.

The act of reprojecting may result in "squeezed", or "warped" looking geometry:
a locally optimal cartesian representation of a sphere is not a globally optimal
representation, after all. To avoid a warped representation, set the Project
Coordinate Reference System appropriately.

You can find it the menu at ``Project > Properties > CRS``.

.. image:: _static/qgis-project-properties.png
  :target: _static/qgis-project-properties.png
 
For the Netherlands, Amersfoort / RD New (ESPG: 28992) is the appropriate
coordinate reference system.

.. image:: _static/qgis-project-crs.png
  :target: _static/qgis-project-crs.png

Setting a basemap background
----------------------------

By default, QGIS provides OpenStreetMap as a basemap. It can be found in the
Browser window, under XYZ tiles.

.. image:: _static/qgis-openstreetmap.png
  :target: _static/qgis-openstreetmap.png

Useful plugins
--------------

QGIS has a flexible plugin structure, allowing you to add existing functionality
to QGIS (such as an analytic element modeling plugin!). Plugins can be installed
via ``Plugins > Manage and Install Plugins ...``.

.. image:: _static/qgis-plugins.png
  :target: _static/qgis-plugins.png

Click on `All`, and use the search bar at the top of the window to find a
plugin.

.. image:: _static/qgis-plugin-menu.png
  :target: _static/qgis-plugin-menu.png

The following plugins are highly useful and should (in my opinion) be installed 
with every QGIS installation:

* The `Value Tool <https://plugins.qgis.org/plugins/valuetool/>`_ allows you
  to interactively inspect rasters or meshes as it displays the value at the
  current location of the mouse pointer.
* The `Profile Tool <https://plugins.qgis.org/plugins/profiletool/>`_ allows
  you to draw cross-sections through raster data.

For Dutch users:

* The `PDOK Services Plugin <https://plugins.qgis.org/plugins/pdokservicesplugin/>`_
  allows you to easily load the excellent basemaps provided by PDOK into QGIS.

Advanced Digitizing Toolbar
---------------------------

The toolbars that are displayed by default do not provide easy ways of moving
geometries. To enable these options, right click on a toolbar, and find the
``Advanced Digitizing Toolbar`` checkbox.

.. image:: _static/qgis-advanced-digitizing-toolbar.png
  :target: _static/qgis-advanced-digitizing-toolbar.png

Editing Vector Layers
---------------------

Before changes can be made to vector layers, editing has to be toggled.

.. image:: _static/qgis-toggle-editing.png
  :target: _static/qgis-toggle-editing.png

Changes have to be saved explicitly, which can be done both while editing is
toggled on, or off.

Often, the easiest way of entering values is via the Attribute Table. Find it by
right-clicking on a layer in the Layers Panel, and left-clicking on Attribute
Table.

.. image:: _static/qgis-attribute-table.png
  :target: _static/qgis-attribute-table.png
