import subprocess

import pytest
import gistim
import geopandas as gpd
import rioxarray
import shapely.geometry as sg
import xarray as xr


@pytest.fixture
def basicmodel(scope="function"):
    aquifer_df = gpd.GeoDataFrame(
        dict(
            geometry=[None],
            conductivity=[10.0],
            resistance=[100.0],
            top=[5.0],
            bottom=[-5.0],
            porosity=[0.35],
            label=["my-testing-label"],
        )
    )
    constant_df = gpd.GeoDataFrame(
        dict(
            geometry=[sg.Point([0.0, 0.0])],
            head=[2.0],
            layer=[0],
            label=["my-testing-label"],
        )
    )
    well_df = gpd.GeoDataFrame(
        dict(
            geometry=[sg.Point(10.0, 10.0)],
            discharge=[10.0],
            radius=[0.5],
            resistance=[1.0],
            layer=[0],
            label=["my-testing-label"],
        )
    )
    domain_df = gpd.GeoDataFrame(
        dict(
            geometry=[sg.Polygon([(0.0, 0.0), (20.0, 0.0), (20.0, 20.0), (0.0, 20.0)])]
        )
    )
    domain_df.crs = "epsg:28992"
    return aquifer_df, constant_df, well_df, domain_df


@pytest.mark.integration
def test_geopackage_run(tmp_path, basicmodel):
    # Uses the tmp_path fixture which pytest provides
    path = tmp_path / "basic-test.gpkg"
    aquifer_df, constant_df, well_df, domain_df = basicmodel
    aquifer_df.to_file(path, layer="timmlAquifer", driver="GPKG")
    constant_df.to_file(path, layer="timmlConstant", driver="GPKG")
    well_df.to_file(path, layer="timmlWell:my-well", driver="GPKG")
    domain_df.to_file(path, layer="timmlDomain", driver="GPKG")

    output_path = tmp_path / "basic-test-output.nc"
    subprocess.run(args=["python", "-m", "gistim", str(path), str(output_path), "1.0"])

    da = xr.open_dataarray(output_path)
    assert da.shape == (1, 20, 20)
    assert da.name == "head"
    assert da.rio.crs is not None
