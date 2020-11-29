"""
Turns a geopackage into a TimML model result
"""
import argparse
import socket
import socketserver

import gistim
import rioxarray


def run(input_path, output_path, cellsize):
    spec = gistim.elements.model_specification(input_path)
    model = gistim.elements.initialize_model(input_path, spec)
    model.solve()

    extent, crs = gistim.elements.gridspec(input_path, cellsize)
    head = gistim.elements.headgrid(model, extent, cellsize)
    head = head.rio.write_crs(crs)
    head.to_netcdf(output_path)


# if __name__ == "__main__":
#    parser = argparse.ArgumentParser()
#
#    parser.add_argument(
#        "input_path",
#        type=str,
#        nargs=1,
#        help="Path to the geopackage containing the TimML vector input data.",
#    )
#    parser.add_argument(
#        "output_path",
#        type=str,
#        nargs=1,
#        help="Path to the output netCDF storing the layer heads.",
#    )
#    parser.add_argument(
#        "cellsize",
#        type=float,
#        nargs=1,
#        help="Float specifying the output grid cellsize.",
#    )
#    args = parser.parse_args()
#    run(args.input_path[0], args.output_path[0], args.cellsize[0])


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
#    with socketserver.TCPServer((HOST, PORT), gistim.TimHandler) as server:
    with gistim.StatefulTimServer((HOST, PORT), gistim.TimHandler) as server:
        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl-C
        server.serve_forever()
