"""
This module contains the logic for starting, communicating with, and killing a
separate (conda) interpreter, which is running TimML and TTim.
"""
import json
import os
import platform
import signal
import socket
import subprocess
from contextlib import closing
from pathlib import Path
from typing import List


class ServerHandler:
    def __init__(self):
        self.HOST = "localhost"
        self.PORT = None
        self.socket = None

    def find_free_port(self) -> int:
        """
        Finds a free localhost port number.

        Returns
        -------
        portnumber: int
        """
        # from:
        # https://stackoverflow.com/questions/1365265/on-localhost-how-do-i-pick-a-free-port-number
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.bind(("localhost", 0))
            return sock.getsockname()[1]

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

    def start_server(self, interpreter: str) -> None:
        """
        Starts a new (conda) interpreter, based on the settings in the
        configuration directory.
        """
        self.PORT = self.find_free_port()
        env_vars = self.environmental_variables()

        subprocess.Popen(
            f"{interpreter} -m gistim serve {self.PORT}",
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            env=env_vars[interpreter],
        )

    def send(self, data) -> str:
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
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.HOST, self.PORT))
        self.socket.sendall(bytes(data, "utf-8"))
        received = str(self.socket.recv(1024), "utf-8")
        return received

    def kill(self) -> None:
        """
        Kills the external interpreter.

        This enables shutting down the external window when the plugin is
        closed.
        """
        if self.PORT is not None:
            # Ask the process for its process_ID
            try:
                data = json.dumps({"operation": "process_ID"})
                process_ID = int(self.send(data))
                # Now kill it
                os.kill(process_ID, signal.SIGTERM)
            except ConnectionRefusedError:
                # it's already dead
                pass
