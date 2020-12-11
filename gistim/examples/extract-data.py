"""
Extracting data from a regional dataset
=======================================

This examples demonstrates how to compute some summary statistics per layer,
from some data from a regional groundwater model.

The median or mean values can be used to parametrize aquifer and aquitard
properties, and the extrema or standard deviations could be used in 
sensitivity or uncertainty analyses.
"""
import gistim

dataframe = gistim.layer_statistics(
    path="data/regional-data-groningen.nc",
    xmin=230_000.0,
    xmax=233_000.0,
    ymin=580_000.0,
    ymax=583_000.0,
)
dataframe

###############################################################################
# This table is not immediately usable as Qgis-Tim input. With the aid of the
# following function, it is:

out = gistim.as_aquifer_aquitard(dataframe, statistic="mean")
out

###############################################################################
# Let's write it to a CSV for further use:

out.to_csv("groningen-layer-statistics.csv")
