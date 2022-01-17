Developing the plugin
=====================

Development installation
------------------------

A modern (>=3.0) QGIS installation, within the context of
`OSGeo4W <https://trac.osgeo.org/osgeo4w/>`_. A basic QGIS installation (as can be
gotten `here <https://qgis.org/en/site/>`_) suffices to run the plugin, but will
not suffice for full development capabilities.

Compiling Qt resources
----------------------

pyrcc5 takes a Qt Resource File (. qrc) and converts it into a Python module
which can be imported into a PyQt5 application.

It is available in the OSGeo4W shell, after running the following commands:

.. code-block:: console

    qt5_env.bat
    py3_env.bat

Then, within the `./plugin/qgistim/` directory, run:

.. code-block:: console

    pyrcc5 -o resources.py resources.qrc
