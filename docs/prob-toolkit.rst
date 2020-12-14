Using the Probabilistic Toolkit
===============================

 To quote the webpage of the `Probabilistic toolkit
 <https://www.deltares.nl/en/software/probabilistic-toolkit-ptk/>`_:

    The Probabilistic Toolkit analyzes the effects of uncertainty to any model.
    These models range from Python scripts to geotechnical and hydrodynamical
    Deltares applications and non-Deltares applications.

Since the input produced by QGIS plugin is processed by a Python package
(``gistim``), which then feeds it to the (also Python-based) TimML analytic
element model code, it is quite straightforward to:

* Define the analytic elements and their geometry using the QGIS plugin;
* Store the input in a GeoPackage;
* Write a script that loads the GeoPackage into Python;
* Once loaded, make some changes to some parameters;
* Provide this script to the Probabilistic Toolkit to run a sensitivity or
  uncertainty analysis.

Example
-------

This example uses the (abbreviated) ``groningen.py`` example. This examples
focuses on the configuration of the Probabilistic Toolkit (hereafter abbreviated
as "PTK").

After starting the PTK, start by choosing the appropriate model type, Internal,
with as language Python:

.. image:: _static/ptk-model-type.png
  :target: _static/ptk-model-type.png

In the ``Python file`` input, we need to set the path to the appropriate Python
interpreter. If you've followed the installation instructions in this documentation,
it should be located in a conda environment named ``tim``.

To get the path:

* Start a (anaconda) command prompt;
* Activate the ``tim`` environment;
* Get the path to the interpreter.

These commands will do the trick, on Windows:

.. code-block:: console

    conda activate tim
    where python

In Powershell, Unix, Linux, Mac:

.. code-block:: console

    conda activate tim
    which python

The path to the interpreter will be printed, and can be entered in the PTK.

Next, we can paste the source code. The example below suffices to get the groningen
example running in the PTK.

.. code-block:: python

    import gistim

    path = r"c:\projects\qgis-tim_toolbox\groningen.gpkg"

    # Parameters
    fictitious_c = fic_c
    peelo_conductivity = peelo_k
    peelo_resistance = peelo_c
    sheetpile_resistance = sheetpile_c

    # Grab aquifer data
    model_spec = gistim.model_specification(path)

    # Grab the aquifer data
    aquifer_data = model_spec.aquifer.dataframe
    # Set the values in the DataFrames
    aquifer_data["resistance"].iloc[3] = fictitious_c
    aquifer_data["conductivity"].iloc[2] = peelo_conductivity 
    aquifer_data["conductivity"].iloc[4] = peelo_conductivity
    aquifer_data["resistance"].iloc[5] = peelo_resistance

    # Grab sheetpile data
    sheetpile_data = model_spec.elements["timmlLeakyLineDoublet:damwand"].dataframe
    sheetpile_data["resistance"].iloc[0] = sheetpile_resistance

    # Solve and check the head for an observation point
    model = gistim.initialize_model(model_spec)
    model.solve()
    x_obs = 234_560.0
    y_obs = 580_735.0
    control_head1 = model.head(x_obs, y_obs, layers=1)
    control_head2 = model.head(x_obs + 50.0, y_obs, layers=1)

Within this example, we vary:

* The resistance of a fictitious resistance layer in the second aquifer;
* The horizontale conductance of the second aquifer;
* The resistance below the second aquifer;
* The resistance of the sheetpile walls.

And we check the results at two observation wells (control head 1 & 2).

Please note that the paths have to be set appropriately, in accordance with the
present working directory of the PTK; in this case an absolute path to the
GeoPackage is used.

Next, we define the inputs and output of the PTK. Their names correspond to the names
in the Python script. They are:

* ``fic_c``
* ``peelo_k``
* ``peelo_c``
* ``sheetpile_c``

Outputs:

* ``control_head1``
* ``control_head2``

.. image:: _static/ptk-input-output.png
  :target: _static/ptk-input-output.png

Next, go to the ``Variables`` tab to define the input ranges / distributions
from which to sample input values. Once defined, the PTK is ready to run. For
more background on the PTK, please refer to the PTK manual.
