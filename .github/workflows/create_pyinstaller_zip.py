import json
import hashlib
import os
import platform
import shutil


def write_versions(path):
    import timml
    import gistim
    import ttim

    versions = {
        "timml": timml.__version__,
        "ttim": ttim.__version__,
        "gistim": gistim.__version__,
    }
    with open(path, "w") as f:
        json.dump(versions, f)
    return


# Write versions into PyInstaller directory
write_versions("./dist/gistim/versions.json")

# Create archive
# Use the RUNNER_OS variable on the Github Runner. Use platform system locally.
system = os.environ.get("RUNNER_OS", platform.system())
zippath = shutil.make_archive(f"./dist/gistim-{system}", "zip", "./dist/gistim")

# Create a checksum
with open(zippath, "rb", buffering=0) as f:
    sha256_hash = hashlib.file_digest(f, "sha256").hexdigest()

txt_path = f"./dist/sha256-checksum-{system}.txt"
with open(txt_path, "w") as f:
    f.write(sha256_hash)
