import json
import os
import pathlib
import socketserver
from typing import Dict, Union

import gistim


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
        path = pathlib.Path(inpath)
        timml_spec, ttim_spec = gistim.model_specification(path, active_elements)
        self.server.timml_model, _ = gistim.timml_elements.initialize_model(timml_spec)
        self.server.timml_model.solve()

        if mode == "transient":
            self.server.ttim_model, _ = gistim.ttim_elements.initialize_model(
                ttim_spec, self.server.timml_model
            )

        extent, crs = gistim.gridspec(path, cellsize)

        if mode == "steady-state":
            if as_trimesh:
                ugrid_head = gistim.timml_elements.headmesh(
                    self.server.timml_model, timml_spec, cellsize
                )
            else:
                head = gistim.timml_elements.headgrid(
                    self.server.timml_model, extent, cellsize
                )
                ugrid_head = gistim.to_ugrid2d(head)

        elif mode == "transient":
            print("Solving transient model")
            self.server.ttim_model.solve()
            if as_trimesh:
                ugrid_head = gistim.ttim_elements.headmesh(
                    self.server.ttim_model, timml_spec, cellsize
                )
            else:
                head = gistim.ttim_elements.headgrid(
                    self.server.ttim_model,
                    extent,
                    cellsize,
                    ttim_spec.output_times,
                    ttim_spec.temporal_settings["reference_date"].iloc[0],
                )
                ugrid_head = gistim.to_ugrid2d(head)

        else:
            raise ValueError(
                f'Mode should be "steady-state" or "transient". Received: {mode}'
            )

        print("Writing result to:", outpath)
        ugrid_head.to_netcdf(outpath)

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
