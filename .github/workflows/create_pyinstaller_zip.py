import hashlib
import os
import platform
import shutil
import stat
from pathlib import Path

# Find gistim executable in dist folder irregardless of platform and suffix.
dist_folder = Path("./dist/gistim")
gistim_executable = dist_folder.glob("gistim*").__next__()
# Set execution mode for the executable in the dist folder
# Irrelevant for Windows, but needed for Linux and MacOS.
gistim_executable.chmod(gistim_executable.stat().st_mode | stat.S_IEXEC)

# Create archive
# Use the RUNNER_OS variable on the Github Runner. Use platform system locally.
system = os.environ.get("RUNNER_OS", platform.system())
zippath = shutil.make_archive(f"./dist/gistim-{system}", "zip", str(dist_folder))

# Create a checksum
with open(zippath, "rb", buffering=0) as f:
    sha256_hash = hashlib.file_digest(f, "sha256").hexdigest()

txt_path = f"./dist/sha256-checksum-{system}.txt"
with open(txt_path, "w") as f:
    f.write(sha256_hash)
