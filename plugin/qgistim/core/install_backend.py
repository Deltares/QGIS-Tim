"""Downloads and installs from GitHub or installs from zipfile."""
from typing import Dict
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
import json
import requests
import hashlib
import platform
import shutil
import os


def get_gistim_dir() -> Path:
    if platform.system() == "Windows":
        gistim_dir = Path(os.environ["APPDATA"]) / "qgis-tim"
    else:
        gistim_dir = Path(os.environ["HOME"]) / ".qgis-tim"
    return gistim_dir


def get_release_assets() -> Dict[str, str]:
    GITHUB_URL = "https://api.github.com/repos/deltares/qgis-tim/releases"
    response = requests.get(GITHUB_URL)
    json_content = json.loads(response.content)
    last_release = json_content[0]
    assets = last_release["assets"]
    named_assets = {asset["name"]: asset["browser_download_url"] for asset in assets}
    return named_assets


def download_assets(assets: Dict[str, str]) -> ZipFile:
    SYSTEMS = {
        "Windows": "Windows",
        "Darwin": "macOS",
        "Linux": "Linux",
    }
    user_system = platform.system()
    github_system = SYSTEMS.get(user_system)
    if github_system is None:
        raise ValueError(
            f"Unsupported OS: {user_system}. "
            f"Only {', '.join(SYSTEMS.keys())} are supported."
        )
    # Get checksum
    checksum_url = assets[f"sha256-checksum-{github_system}.txt"]
    checksum_github = requests.get(checksum_url).content.decode("utf-8")
    # Get zipfile content
    zip_url = assets[f"gistim-{github_system}.zip"]
    zipfile_content = requests.get(zip_url).content
    # Compare checksums
    sha = hashlib.sha256()
    sha.update(zipfile_content)
    checksum = sha.hexdigest()
    if checksum != checksum_github:
        raise ValueError("SHA-256 checksums do not match. Please try re-downloading.")
    return ZipFile(BytesIO(zipfile_content))


def create_destination() -> Path:
    gistim_dir = get_gistim_dir()
    if gistim_dir.exists():
        shutil.rmtree(gistim_dir)
    gistim_dir.mkdir()
    return gistim_dir


def install_from_github() -> None:
    assets = get_release_assets()
    zipfile = download_assets(assets)
    destination = create_destination()
    zipfile.extractall(destination)
    return


def install_from_zip(path: str) -> None:
    if not Path(path).exists:
        raise FileNotFoundError(path)
    zipfile = ZipFile(path)
    destination = create_destination()
    zipfile.extractall(destination)
    return
