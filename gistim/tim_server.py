import hashlib
import json
import os
import pathlib
import socketserver
import sys
from typing import NamedTuple, Union

import rioxarray

import gistim


# If the geopackage has changed, reinitialize the model.
#  If elements are added piecemeal, hashing per element (maybe via pickle?) could be nicer.
def hash_file(path: Union[pathlib.Path, str]) -> int:
    """Compute an MD5 hash of a file to check if it has changed"""
    md5 = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            # 64kb chunks
            chunk = f.read(65536)
            if not chunk:
                break
            md5.update(chunk)
    return md5.hexdigest()


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
        self.model = None
        self.solved = False


class TimHandler(socketserver.BaseRequestHandler):
    """
    The handler deals with the individual requests from the QGIS plugin.

    It will initialize the model, compute the results for a given domain
    and cellsize, and write the result to a 3D (layer, y, x) netCDF file.
    """

    def initialize(self, path: Union[pathlib.Path, str]) -> None:
        """
        Convert the contents of the GeoPackage into a TimML model.

        Parameters
        ----------
        path: Union[pathlib.Path, str]
            Path to the GeoPackage file containing the full model input.
        """
        spec = gistim.model_specification(path)
        self.server.model = gistim.initialize_model(spec)

    def compute(self, path: Union[pathlib.Path, str], cellsize: float) -> None:
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
        path = pathlib.Path(path)
        gpkg_hash = hash_file(path)
        print("Current server hash:", self.server.geopackage_hash)
        print("md5 hash:", gpkg_hash)
        # TODO: this currently gives issues, where md5 hashes are the same
        # even after changes?
        # Probably due to Write-Ahead-Logging (WAL) from the geopackage?
        # if gpkg_hash != self.server.geopackage_hash:
        #    self.initialize(path)
        #    self.server.geopackage_hash = gpkg_hash
        #    self.server.solved = False
        self.initialize(path)
        self.server.geopackage_hash = gpkg_hash
        self.server.solved = False
        if not self.server.solved:
            self.server.model.solve()
            self.server.solved = True
        name = path.stem
        extent, crs = gistim.gridspec(path, cellsize)
        head = gistim.headgrid(self.server.model, extent, cellsize)
        head = head.rio.write_crs(crs)

        outpath = (path.parent / f"{name}-{cellsize}".replace(".", "_")).with_suffix(
            ".nc"
        )
        print("Writing result to:", outpath)
        head.to_netcdf(outpath)

    def handle(self) -> None:
        """
        Handle a request. This function has to be overloaded for a request
        handler class.
        """
        # TODO: rfile stream? Seems more robust than these 1024 bytes
        # TODO: try-except, and return error in return message
        message = self.request.recv(1024).strip()
        print(message)
        data = json.loads(message)
        operation = data.pop("operation")
        if operation == "compute":
            self.compute(
                path=data["path"],
                cellsize=data["cellsize"],
            )
            print("Computation succesful")
            # Send error code 0: all okay
            self.request.sendall(bytes("0", "utf-8"))
        elif operation == "process_ID":
            self.request.sendall(bytes(str(os.getpid()), "utf-8"))
        else:
            print('Invalid operation. Valid options are: "compute", "process_ID".')
