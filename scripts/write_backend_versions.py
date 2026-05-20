import json
import os


def write_versions(path):
    import timflow

    import gistim

    versions = {
        "timflow": timflow.__version__,
        "gistim": gistim.__version__,
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(versions, f)


# Write versions into PyInstaller directory
write_versions("./dist/gistim/versions.json")
