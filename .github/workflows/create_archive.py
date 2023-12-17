import hashlib
import os
import platform
import shutil

# Create archive
# Use the RUNNER_OS variable on the Github Runner. Use platform system locally.
system = os.environ.get("RUNNER_OS", platform.system())
zippath = shutil.make_archive(f"dist/gistim-{system}", "zip", "dist/gistim")

# Create a checksum
with open(zippath, "rb", buffering=0) as f:
    sha256_hash = hashlib.file_digest(f, "sha256").hexdigest()

with open(f"dist/sha256-checksum-{system}.txt", "w") as f:
    f.write(sha256_hash)
