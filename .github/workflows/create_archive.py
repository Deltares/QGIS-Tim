from pathlib import Path
import hashlib
import platform
import shutil

# Create archive
shutil.make_archive("dist/gistim", "zip", "dist/gistim")

# Create a checksum
path = Path("dist/gistim.zip")
with open(path, "rb", buffering=0) as f:
    sha256_hash = hashlib.file_digest(f, "sha256").hexdigest()

# Include it in the filename.
filename = f"dist/gistim-{platform.system()}-{sha256_hash}.zip"
path.rename(filename)
