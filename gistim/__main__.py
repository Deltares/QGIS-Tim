"""
Turns a geopackage into a TimML model result
"""
import argparse
import json
import os
import platform
import sys
from pathlib import Path

import gistim


def configure(args) -> None:
    """
    Write all the environmental variables so the QGIS interpreter
    can (re)set them properly.
    """
    if platform.system() == "Windows":
        configdir = Path(os.environ["APPDATA"]) / "qgis-tim"
    else:
        configdir = Path(os.environ["HOME"]) / ".qgis-tim"
    configdir.mkdir(exist_ok=True)

    env = {key: value for key, value in os.environ.items()}
    path = configdir / "environmental-variables.json"
    if path.exists():
        with open(path, "r") as f:
            content = json.loads(f.read())
        content[sys.executable] = env
    else:
        content = {sys.executable: env}

    with open(configdir / "environmental-variables.json", "w") as f:
        f.write(json.dumps(content))


def serve(args) -> None:
    """
    Spin up a process listening for calls messages from the QGIS plugin.
    """
    HOST = "localhost"
    PORT = args.port[0]
    print(f"Starting TimServer on localhost, port: {PORT}")
    print(f"Process ID: {os.getpid()}")
    # Create the server, binding to localhost on port 9999
    with gistim.StatefulTimServer((HOST, PORT), gistim.TimHandler) as server:
        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl-C
        server.serve_forever()


def extract(args) -> None:
    """
    Extract layer input from a netcdf dataset
    """
    inpath = args.inpath[0]
    outpath = args.outpath[0]
    wkt_geometry = args.wkt[0].split(";")
    gistim.data_extraction.netcdf_to_table(inpath, outpath, wkt_geometry)


def convert(args) -> None:
    """
    Convert a Geopackage into a Python script.
    """
    inpath = args.inpath[0]
    outpath = args.outpath[0]

    timml_spec, ttim_spec = gistim.model_specification(inpath, {})
    timml_script = gistim.timml_elements.convert_to_script(timml_spec)
    ttim_script = gistim.ttim_elements.convert_to_script(ttim_spec)

    with open(outpath, "w") as f:
        f.write(timml_script)
        f.write("\n")
        f.write(ttim_script)


if __name__ == "__main__":
    # Setup argparsers
    parser = argparse.ArgumentParser(prog="GisTim")
    subparsers = parser.add_subparsers(help="sub-command help")
    parser_configure = subparsers.add_parser("configure", help="configure help")
    parser_serve = subparsers.add_parser("serve", help="serve help")
    parser_extract = subparsers.add_parser("extract", help="extract help")
    parser_convert = subparsers.add_parser("convert", help="convert help")

    parser_configure.set_defaults(func=configure)
    parser_configure.add_argument("append", type=bool, nargs=1, help="append")

    # Serve has a single argument: the port number
    parser_serve.set_defaults(func=serve)
    parser_serve.add_argument(
        "port",
        type=int,
        nargs=1,
        help="localhost PORT number",
    )

    parser_extract.set_defaults(func=extract)
    parser_extract.add_argument("inpath", type=str, nargs=1, help="inpath")
    parser_extract.add_argument("outpath", type=str, nargs=1, help="outpath")
    parser_extract.add_argument("wkt", type=str, nargs=1, help="wkt")

    parser_convert.set_defaults(func=convert)
    parser_convert.add_argument("inpath", type=str, nargs=1, help="inpath")
    parser_convert.add_argument("outpath", type=str, nargs=1, help="outpath")

    # Parse and call the appropriate function
    args = parser.parse_args()
    args.func(args)
