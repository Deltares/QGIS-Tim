import json
import os
import pathlib
import socketserver
from typing import Dict, Union

import geopandas as gpd
import xarray as xr

import gistim


def write_ugrid(
    ugrid_head: xr.DataArray,
    outpath: Union[pathlib.Path, str],
) -> None:
    print("Writing result to:", outpath)
    ugrid_head.to_netcdf(outpath)


def write_observations(
    gdf_head: gpd.GeoDataFrame,
    outpath: Union[pathlib.Path, str],
) -> None:
    if len(gdf_head.index) > 0:
        outpath = pathlib.Path(outpath)
        vector_outpath = outpath.parent / f"{outpath.stem}-vector.gpkg"
        print("Writing observations to:", vector_outpath)
        gdf_head.to_file(vector_outpath, driver="GPKG")


def compute_steady(
    inpath: Union[pathlib.Path, str],
    outpath: Union[pathlib.Path, str],
    cellsize: float,
    active_elements: Dict[str, bool],
    as_trimesh: bool = False,
) -> None:
    path = pathlib.Path(inpath)
    timml_spec, ttim_spec = gistim.model_specification(path, active_elements)
    timml_model, _, observations = gistim.timml_elements.initialize_model(timml_spec)
    timml_model.solve()

    gdf_head = gistim.timml_elements.head_observations(timml_model, observations)

    extent, crs = gistim.gridspec(path, cellsize)
    if as_trimesh:
        ugrid_head = gistim.timml_elements.headmesh(timml_model, timml_spec, cellsize)
    else:
        head = gistim.timml_elements.headgrid(timml_model, extent, cellsize)
        ugrid_head = gistim.to_ugrid2d(head)

    write_ugrid(ugrid_head, outpath)
    write_observations(gdf_head, outpath)


def compute_transient(
    inpath: Union[pathlib.Path, str],
    outpath: Union[pathlib.Path, str],
    cellsize: float,
    active_elements: Dict[str, bool],
    as_trimesh: bool = False,
) -> None:
    path = pathlib.Path(inpath)
    timml_spec, ttim_spec = gistim.model_specification(path, active_elements)
    timml_model, _, observations = gistim.timml_elements.initialize_model(timml_spec)
    ttim_model, _, ttim_observations = gistim.ttim_elements.initialize_model(ttim_spec, timml_model)
    timml_model.solve()
    ttim_model.solve()

    gdf_head = gistim.ttim_elements.head_observations(
        timml_model,
        ttim_spec.temporal_settings["reference_date"].iloc[0],
        observations,
    )

    extent, crs = gistim.gridspec(path, cellsize)
    if as_trimesh:
        ugrid_head = gistim.ttim_elements.headmesh(ttim_model, timml_spec, cellsize)
    else:
        head = gistim.ttim_elements.headgrid(
            ttim_model,
            extent,
            cellsize,
            ttim_spec.output_times,
            ttim_spec.temporal_settings["reference_date"].iloc[0],
        )
        ugrid_head = gistim.to_ugrid2d(head)
    write_ugrid(ugrid_head, outpath)
    write_observations(gdf_head, outpath)


class StatefulTimServer(socketserver.ThreadingTCPServer):
    """
    Stores the state of the analytic element model. If the geopackage content
    have not changed, there is no need to re-initialize the model, and solve it
    again.

    If e.g. only cellsize or domain change, values can be computed immediately
    with the headgrid function.
    """

    def __init__(self, *args, **kwargs):
        super(__class__, self).__init__(*args, **kwargs)
        self.geopackage_hash = None
        self.timml_model = None
        self.ttim_model = None
        self.solved = False


class TimHandler(socketserver.BaseRequestHandler):
    """
    The handler deals with the individual requests from the QGIS plugin.

    It will initialize the model, compute the results for a given domain
    and cellsize, and write the result to a 3D (layer, y, x) netCDF file.
    """

    def compute(
        self,
        inpath: Union[pathlib.Path, str],
        outpath: Union[pathlib.Path, str],
        mode: str,
        cellsize: float,
        active_elements: Dict[str, bool],
        as_trimesh: bool = False,
    ) -> None:
        """
        Compute the results of TimML model.

        The model is fully specified by the GeoPacakge dataset in the path.

        The extent of the head grids is read from a vector layer in the
        GeoPackage file.

        Parameters
        ----------
        path: Union[pathlib.Path, str]
            Path to the GeoPackage file containing the full model input.
        cellsize: float
            Grid cell size of the computed output

        Returns
        -------
        None
            The result is written to a netCDF file. Its name is generated from
            the geopackage name, and the requested grid cell size.
        """
        if mode == "steady-state":
            compute_steady(inpath, outpath, cellsize, active_elements, as_trimesh)
        elif mode == "transient":
            compute_transient(inpath, outpath, cellsize, active_elements, as_trimesh)
        else:
            raise ValueError(
                f'Invalid mode: {mode}: should be "steady" or "transient".'
            )

    def handle(self) -> None:
        """
        Handle a request. This function has to be overloaded for a request
        handler class.
        """
        # TODO: rfile stream? Seems more robust than these 1024 bytes
        # TODO: try-except, and return error in return message
        message = self.request.recv(1024 * 1024).strip()
        data = json.loads(message)

        print("JSON received:")
        print(json.dumps(data, indent=4))

        operation = data.pop("operation")

        if operation == "compute":
            self.compute(
                inpath=data["inpath"],
                outpath=data["outpath"],
                cellsize=data["cellsize"],
                mode=data["mode"],
                active_elements=data["active_elements"],
                as_trimesh=data["as_trimesh"],
            )
            print("Computation succesful\n\n")
            # Send error code 0: all okay
            self.request.sendall(bytes("0", "utf-8"))

        elif operation == "process_ID":
            self.request.sendall(bytes(str(os.getpid()), "utf-8"))

        elif operation == "convert":
            inpath = data["inpath"]
            outpath = data["outpath"]
            gistim.convert_to_script(inpath, outpath)
            self.request.sendall(bytes("0", "utf-8"))

        elif operation == "extract":
            inpath = data["inpath"]
            outpath = data["outpath"]
            wkt_geometry = data["wkt_geometry"].split(";")
            gistim.data_extraction.netcdf_to_table(
                inpath=inpath,
                outpath=outpath,
                wkt_geometry=wkt_geometry,
            )
            print(f"Extraction from {inpath} to {outpath} succesful\n\n")
            # Send error code 0: all okay
            self.request.sendall(bytes("0", "utf-8"))

        else:
            print('Invalid operation. Valid options are: "compute", "process_ID".')
