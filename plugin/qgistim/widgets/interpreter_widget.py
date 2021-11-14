import json
from typing import Dict

from PyQt5.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QVBoxLayout, QWidget
from qgis.core import Qgis, QgsApplication

from ..core.server_handler import ServerHandler


class InterpreterWidget(QWidget):
    def __init__(self, parent):
        super(InterpreterWidget, self).__init__(parent)
        self.parent = parent

        self.server_handler = None  # ServerHandler()  # To connect with TimServer
        self.interpreter_combo_box = QComboBox()
        self.interpreter_combo_box.insertItems(0, ServerHandler.interpreters())
        self.interpreter_button = QPushButton("Start")
        self.interpreter_button.clicked.connect(self.start_server)
        self.config_button = QPushButton()
        self.config_button.clicked.connect(self.configure_server)
        self.config_button.setIcon(QgsApplication.getThemeIcon("/mActionOptions.svg"))

        interpreter_layout = QVBoxLayout()
        interpreter_row = QHBoxLayout()
        interpreter_row.addWidget(self.interpreter_combo_box)
        interpreter_row.addWidget(self.interpreter_button)
        interpreter_row.addWidget(self.config_button)
        interpreter_layout.addLayout(interpreter_row)
        self.setLayout(interpreter_layout)

    def configure_server(self) -> None:
        return

    def start_server(self) -> None:
        """Start an external interpreter running gistim"""
        self.server_handler = ServerHandler()
        interpreter = self.interpreter_combo_box.currentText()
        self.server_handler.start_server(interpreter)

    def shutdown_server(self) -> None:
        if self.server_handler is not None:
            self.server_handler.kill()
            self.server_handler = None

    def execute(self, data: Dict[str, str]) -> str:
        jsondata = json.dumps(data)
        received = self.server_handler.send(jsondata)
        if received != "0":
            self.parent.iface.messageBar().pushMessage(
                "Error",
                "Something seems to have gone wrong, "
                "try checking the TimServer window...",
                level=Qgis.Critical,
            )
        return received
