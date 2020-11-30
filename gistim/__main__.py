"""
Turns a geopackage into a TimML model result
"""
import argparse
import socket
import socketserver

import rioxarray

import gistim


def run(input_path, output_path, cellsize):
    spec = gistim.model_specification(input_path)
    model = gistim.initialize_model(input_path, spec)
    model.solve()

    extent, crs = gistim.gridspec(input_path, cellsize)
    head = gistim.headgrid(model, extent, cellsize)
    head = head.rio.write_crs(crs)
    head.to_netcdf(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "port",
        type=int,
        nargs=1,
        help="localhost PORT number",
    )
    args = parser.parse_args()

    HOST = "localhost"
    PORT = args.port[0]
    print(f"Starting TimServer on localhost, port: {PORT}")
    # Create the server, binding to localhost on port 9999
    with gistim.StatefulTimServer((HOST, PORT), gistim.TimHandler) as server:
        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl-C
        server.serve_forever()
