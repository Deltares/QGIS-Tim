import hashlib
import json
import pathlib
import socketserver
import sys
from typing import NamedTuple

import gistim
import rioxarray


# This might be useful:
# If the geopackage has changed, reinitialize the model.
# If elements are added piecemeal, hashing per element (maybe via pickle?) could be nicer.
# Currently, the server is stateless.
def hash_file(path):
    md5 = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            # 64kb chunks
            chunk = f.read(65536)
            if not chunk:
                break
            md5.update(chunk)
    return md5.hexdigest()


class TimHandler(socketserver.BaseRequestHandler):
    def initialize(self, path):
        spec = gistim.elements.model_specification(path)
        self.model = gistim.elements.initialize_model(path, spec)

    def compute(self, path, cellsize):
        path = pathlib.Path(path)
        self.initialize(path)
        self.model.solve()
        self.solve = True
        name = path.name
        extent, crs = gistim.elements.gridspec(path, cellsize)
        head = gistim.elements.headgrid(self.model, extent, cellsize)
        head.rio.write_crs(crs)

        outpath = (path.parent / f"{name}-{cellsize}").with_suffix(".nc")
        print("Writing result to:", outpath)
        head.to_netcdf(outpath)

    def handle(self):
        # TODO: rfile stream? Seems more robust than these 1024 bytes
        # TODO: try-except, and return error in return message
        message = self.request.recv(1024).strip()
        print(message)
        data = json.loads(message)
        self.compute(
            path=data["path"],
            cellsize=data["cellsize"],
        )
        print("Computation succesful")
        # Send error code 0: all okay
        self.request.sendall(bytes("0", "utf-8"))
