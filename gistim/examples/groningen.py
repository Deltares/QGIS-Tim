"""
This example shows how to:

* load a GeoPackage dataset, which has been made by the QGIS plugin and contains
  the TimML input, into Python
* access the aquifer properties and make some changes to them 
* access the properties of a sheetpile, and change its resistance
* run the model, and observe some head results

"""
import gistim

path = r"data/groningen.gpkg"

# We'll define a number of parameters we'd like to change from defaults:
fictitious_c = 10.0
peelo_conductivity = 2.5
peelo_resistance = 125.0
sheetpile_resistance = 500.0

# Load the GeoPackage data into Python.
# This returns a ModelSpecification named tuple with two fields:
#
# * aquifer: the aquifer specification
# * elements: a dictionary containing the specification of the individual
#   elements
#
# The specifiction is stored in another named tuple, ElementSpecification,
# which has two fields:
#
# * elementtype: a string describing which TimML element type the data
#   represents
# * dataframe: a geopandas GeoDataFrame containing the data
model_spec = gistim.model_specification(path)

# Grab the aquifer data, stored in the dataframe:
aquifer_data = model_spec.aquifer.dataframe
# Now, change the default values in the DataFrame.
# We'll access the individual values by column name, and row number.
aquifer_data["resistance"].iloc[3] = fictitious_c
aquifer_data["conductivity"].iloc[2] = peelo_conductivity
aquifer_data["conductivity"].iloc[4] = peelo_conductivity
aquifer_data["resistance"].iloc[5] = peelo_resistance

# Similarly, we can grab the sheet pile data, and make a change.
sheetpile_data = model_spec.elements["timmlLeakyLineDoublet:damwand"].dataframe
sheetpile_data["resistance"].iloc[0] = sheetpile_resistance

# The model specification can be turned into a TimML model as follows:
model = gistim.initialize_model(model_spec)
# This will initially both the model, as well as add all elements to it. In this
# case, a Constant, two Wells, UniformFlow, and a LeakyLineDoublet (the sheet
# piles).

# Solve and check the head at an observation point:
model.solve()
x_obs = 234_560.0
y_obs = 580_735.0
control_head = model.head(x_obs, y_obs, layers=1)
print(control_head)

# To extract an extent in which to compute heads, the extent is
# extracted from the "timmlDomain" layer in the GeoPackage:
cellsize = 1.0
extent, crs = gistim.gridspec(path, cellsize)
# The headgrid function returns an xarray DataArray object
# which has the necessary coordinates (layer, y, x)
head = gistim.headgrid(model, extent, cellsize)
# We can select a layer and plot it:
head.sel(layer=2).plot.imshow()