import gistim

dataframe = gistim.layer_statistics(
    path="MIPWA-subsoil-data.nc",
    xmin=180_000.0,
    xmax=180_250.0,
    ymin=550_000.0,
    ymax=550_250.0,
)
out = gistim.as_aquifer_aquitard(dataframe)
out.to_csv("LHM-layer-statistics.csv")
