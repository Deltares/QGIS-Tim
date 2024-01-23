"""
This module contains the logic for starting, communicating with, and killing a
separate (conda) interpreter, which is running TimML and TTim.

For thread safety: DO NOT INCLUDE QGIS CALLS HERE.
"""
import json
import os
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict


class ServerHandler:
    def __init__(self):
        self.process = None

    def alive(self):
        return self.process is not None and self.process.poll() is None

    @staticmethod
    def get_gistim_dir() -> Path:
        """
        Get the location of the qgis-tim PyInstaller executable.

        The location differs per OS.

        Returns
        -------
        gistim_dir: pathlib.Path
        """
        if platform.system() == "Windows":
            gistim_dir = Path(os.environ["APPDATA"]) / "qgis-tim"
        else:
            gistim_dir = Path(os.environ["HOME"]) / ".qgis-tim"
        return gistim_dir
    
    @staticmethod
    def get_interpreter() -> Path:
        if platform.system() == "Windows":
            return ServerHandler.get_gistim_dir() / "gistim.exe"
        else:
            return ServerHandler.get_gistim_dir() / "gistim"
        
    @staticmethod
    def versions():
        path = ServerHandler.get_gistim_dir() / "versions.json"
        if path.exists():
            with open(path, "r") as f:
                versions = json.loads(f.read())
        else:
            versions = {}
        return versions

    def start_server(self) -> Dict[str, Any]:
        """
        Starts a new PyInstaller interpreter.
        """
        interpreter = self.get_interpreter()
        self.process = subprocess.Popen(
            [interpreter, "serve"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        response = json.loads(self.process.stdout.readline())
        return response

    def send(self, data) -> Dict[str, Any]:
        """
        Send a data package (should be a JSON string) to the external
        interpreter, running gistim.

        Parameters
        ----------
        data: str
            A JSON string describing the operation and parameters

        Returns
        -------
        received: str
            Value depends on the requested operation
        """
        self.process.stdin.write(json.dumps(data))
        self.process.stdin.write("\n")
        self.process.stdin.flush()
        response = json.loads(self.process.stdout.readline())
        return response

    def kill(self) -> None:
        """
        Kills the external interpreter.

        This enables shutting down the external window when the plugin is
        closed.
        """
        if self.alive():
            try:
                self.process.kill()
                self.process = None
            except ConnectionRefusedError:
                # it's already dead
                pass
