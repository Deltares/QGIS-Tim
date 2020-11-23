import hashlib
import json
import pathlib
import socketserver
import sys
from typing import NamedTuple

import gistim
import rioxarray


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


class TimServer(socketserver.BaseRequestHandler):
    def setup(self):
        # Set initial values of the state
        self.geopackage_hash = "NONE"
        self.solved = False
        self.model = None

    def initialize(self, path):
        spec = gistim.elements.model_specification(path)
        self.model = gistim.elements.initialize_model(path, spec)

    def compute(self, path, cellsize):
        hashed = hash_file(path)
        # If the geopackage has changed, reinitialize the model.
        # If elements are added piecemeal, hashing per element (maybe via pickle?) could be nicer. 
        if self.geopackage_hash != hashed:
            self.initialize(path)
            self.geopackage_hash = hashed
            self.solved = False
        if not self.solved:
            self.model.solve()
            self.solve = True
        name = pathlib.Path(path).name
        extent, crs = gistim.elements.gridspec(path, cellsize)
        head = gistim.elements.headgrid(self.model, extent, cellsize)
        head.rio.write_crs(crs)
        head.to_netcdf(pathlib.Path(f"{name}-{cellsize}").with_suffix(".nc"))

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
        # Send error code 0: all okay
        self.request.sendall(bytes("0", "utf-8"))


if __name__ == "__main__":
    PORT = find_free_port()
    HOST = "localhost"
    # Create the server, binding to localhost on port 9999
    with socketserver.TCPServer((HOST, PORT), TimServer) as server:
        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl-C
        server.serve_forever()
