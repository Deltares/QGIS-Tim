import argparse
import json
import os
import sys
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from os import devnull

# Make sure we explicitly import besselaesnumba for pyinstaller.
# It's a dynamic import inside of timml.
from timml.besselaesnumba import besselaesnumba  # noqa: F401

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


def handle(line) -> str:
    data = json.loads(line)
    operation = data.pop("operation")
    if operation == "compute":
        gistim.compute.compute(
            path=data["path"],
            transient=data["transient"],
        )
        response = "Computation of {path}".format(**data)
    elif operation == "process_ID":
        response = str(os.getpid())
    else:
        response = 'Invalid operation. Valid options are: "compute", "process_ID".'

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


def compute(args) -> None:
    if args.transient is None:
        transient = False
    else:
        transient = args.transient[0]
    gistim.compute.compute(path=args.path[0], transient=transient)
    return


if __name__ == "__main__":
    # Setup argparsers
    parser = argparse.ArgumentParser(prog="gistim")
    subparsers = parser.add_subparsers(help="sub-command help")
    parser_serve = subparsers.add_parser("serve", help="serve help")
    parser_compute = subparsers.add_parser("compute", help="compute help")

    parser_serve.set_defaults(func=serve)

    parser_compute.set_defaults(func=compute)
    parser_compute.add_argument("path", type=str, nargs=1, help="path to JSON file")
    parser_compute.add_argument("--transient", action=argparse.BooleanOptionalAction)
    parser_compute.set_defaults(transient=False)

    # Parse and call the appropriate function
    args = parser.parse_args()
    args.func(args)
