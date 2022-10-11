import argparse
import json
import os
import platform
import sys
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from os import devnull
from pathlib import Path

import gistim


@contextmanager
def suppress_stdout_stderr():
    """A context manager that redirects stdout and stderr to devnull"""
    with open(devnull, "w") as fnull:
        with redirect_stderr(fnull) as err, redirect_stdout(fnull) as out:
            yield (err, out)


def write_json_stdout(data):
    sys.stdout.write(json.dumps(data))
    sys.stdout.write("\n")
    sys.stdout.flush()


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


def handle(line) -> None:
    data = json.loads(line)
    # print("JSON received:")
    # print(json.dumps(data, indent=4))

    operation = data.pop("operation")

    if operation == "compute":
        gistim.compute(
            inpath=data["inpath"],
            outpath=data["outpath"],
            cellsize=data["cellsize"],
            mode=data["mode"],
            active_elements=data["active_elements"],
            as_trimesh=data["as_trimesh"],
        )
        response = "Computation of {inpath} to {outpath}".format(**data)
    elif operation == "convert":
        inpath = data["inpath"]
        outpath = data["outpath"]
        gistim.convert_to_script(inpath, outpath)
        response = "Conversion of {inpath} to {outpath}".format(**data)
    elif operation == "extract":
        inpath = data["inpath"]
        outpath = data["outpath"]
        wkt_geometry = data["wkt_geometry"].split(";")
        gistim.data_extraction.netcdf_to_table(
            inpath=inpath,
            outpath=outpath,
            wkt_geometry=wkt_geometry,
        )
        response = "Extraction of {inpath} to {outpath}".format(**data)
    elif operation == "process_ID":
        response = os.getpid()
    else:
        response = (
            'Invalid operation. Valid options are: "compute", "convert", "process_ID".'
        )

    return response


def serve(_) -> None:
    """
    Spin up a process listening for calls messages from the QGIS plugin.
    """
    try:
        write_json_stdout({"success": True, "message": "Initialized Tim server"})
        for line in sys.stdin:
            try:
                with suppress_stdout_stderr():
                    message = handle(line)
                response = {"success": True, "message": message}

            except Exception as error:
                response = {"success": False, "message": str(error)}

            write_json_stdout(response)

    except Exception as error:
        write_json_stdout({"success": False, "message": str(error)})


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
    gistim.convert_to_script(inpath, outpath)


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
