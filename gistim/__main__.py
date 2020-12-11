"""
Turns a geopackage into a TimML model result
"""
import argparse
import os
import socket
import socketserver

import rioxarray

import gistim


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
    print(f"Process ID: {os.getpid()}")

    # Create the server, binding to localhost on port 9999
    with gistim.StatefulTimServer((HOST, PORT), gistim.TimHandler) as server:
        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl-C
        server.serve_forever()
