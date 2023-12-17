import hashlib
import os
import platform
import shutil

# Create archive
# Use the RUNNER_OS variable on the Github Runner. Use platform system locally.
system = os.environ.get("RUNNER_OS", platform.system())
zippath = shutil.make_archive(f"dist/gistim-{system}", "zip", "dist/gistim")
print(f"Created: {zippath}")

# Create a checksum
with open(zippath, "rb", buffering=0) as f:
    sha256_hash = hashlib.file_digest(f, "sha256").hexdigest()

txt_path = f"dist/sha256-checksum-{system}.txt"
print(f"Writing checksum to: {txt_path}")
with open(txt_path, "w") as f:
    f.write(sha256_hash)
