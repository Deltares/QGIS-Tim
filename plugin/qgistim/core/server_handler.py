"""
This module contains the logic for starting, communicating with, and killing a
separate (conda) interpreter, which is running TimML and TTim.

For thread safety: DO NOT INCLUDE QGIS CALLS HERE.
"""
import json
import os
import platform
import signal
import subprocess
from pathlib import Path
from typing import Any, Dict, List


class ServerHandler:
    def __init__(self):
        self.process = None

    def alive(self):
        return self.process is not None and self.process.poll() is None

    @staticmethod
    def get_configdir() -> Path:
        """
        Get the location of the qgis-tim plugin settings.

        The location differs per OS.

        Returns
        -------
        configdir: pathlib.Path
        """
        if platform.system() == "Windows":
            configdir = Path(os.environ["APPDATA"]) / "qgis-tim"
        else:
            configdir = Path(os.environ["HOME"]) / ".qgis-tim"
        return configdir

    @staticmethod
    def interpreters() -> List[str]:
        with open(
            ServerHandler.get_configdir() / "environmental-variables.json", "r"
        ) as f:
            env_vars = json.loads(f.read())
        return list(env_vars.keys())

    @staticmethod
    def environmental_variables():
        with open(
            ServerHandler.get_configdir() / "environmental-variables.json", "r"
        ) as f:
            env_vars = json.loads(f.read())
        return env_vars

    @staticmethod
    def versions():
        with open(ServerHandler.get_configdir() / "tim-versions.json", "r") as f:
            versions = json.loads(f.read())
        return versions

    def start_server(self, interpreter: str) -> Dict[str, Any]:
        """
        Starts a new (conda) interpreter, based on the settings in the
        configuration directory.
        """
        env_vars = self.environmental_variables()
        self.process = subprocess.Popen(
            f"{interpreter} -u -m gistim serve",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            env=env_vars[interpreter],
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
            # Ask the process for its process_ID
            try:
                response = self.send({"operation": "process_ID"})
                process_ID = response["message"]
                # Now kill it
                os.kill(process_ID, signal.SIGTERM)
                self.process = None
            except ConnectionRefusedError:
                # it's already dead
                pass
