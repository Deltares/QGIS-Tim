import socket
import subprocess


class ServerHandler:
    def __init__(self):
        self.interpreter = None
        self.HOST = "localhost"
        self.PORT = None
        self.socket = None 
        self.process_ID = None
    
    def find_free_port(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = 1024
        while port <= 65535:
            try:
                sock.bind(('', port))
                sock.close()
                break
            except OSError:
                port += 1
        else:
            raise IOError('no free ports')
        return port

    def start_server(self, prefix, name):
        self.PORT = self.find_free_port()
        process = subprocess.Popen(
            f"{prefix}/Scripts/activate.bat {name} & python -m gistim {self.PORT}",
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        self.process_ID = process.pid
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.HOST, self.PORT))
    
    def kill(self):
        try:
            subprocess.run(["Taskkill", "/PID", self.process_ID, "/F"], check=False)
        except:
            pass
