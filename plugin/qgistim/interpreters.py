from pathlib import Path
import os
import sys
import subprocess


def get_env_data(path):
    parts = path.parts
    n = len(parts)
    for i, part in enumerate(parts):
        if part == "envs":
            if i < n:
                return parts[i + 1], str(path), Path("/".join(parts[:i]))
    return "base", str(path), path


def valid(line):
    return line != "" and (not line.startswith("#"))


def get_conda_environments():
    # Next few lines all Windows specific
    if sys.platform != "win32":
        raise NotImplementedError()
    home = os.environ.get("HOME")
    # Try reading the .conda environment txt
    with open(Path(home) / ".conda" / "environments.txt") as f:
        paths = [Path(line.strip()) for line in f.readlines() if valid(line)]

    data = [get_env_data(env) for env in paths]
    return data
