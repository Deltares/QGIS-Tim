import os
import socket
import subprocess
from pathlib import Path


class ServerHandler:
    def __init__(self):
        self.HOST = "localhost"
        self.PORT = None
        self.socket = None
        self.process_ID = None

    def find_free_port(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = 1024
        while port <= 65535:
            try:
                sock.bind(("", port))
                sock.close()
                break
            except OSError:
                port += 1
        else:
            raise IOError("no free ports")
        return port

    def start_server(self):
        self.PORT = self.find_free_port()

        configdir = Path(os.environ["APPDATA"]) / "qgis-tim"
        with open(configdir / "interpreter.txt") as f:
            interpreter = f.read().strip()

        script = configdir / "activate.py"
        env_vars = configdir / "environmental-variables.json"

        process = subprocess.Popen(
            f"python {script} {env_vars} {interpreter} {self.PORT}",
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        self.process_ID = process.pid

    def send(self, data):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.HOST, self.PORT))
        self.socket.sendall(bytes(data, "utf-8"))
        received = str(self.socket.recv(1024), "utf-8")
        return received

    def kill(self):
        try:
            subprocess.run(["Taskkill", "/PID", self.process_ID, "/F"], check=False)
        except:
            pass
