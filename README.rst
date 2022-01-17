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
