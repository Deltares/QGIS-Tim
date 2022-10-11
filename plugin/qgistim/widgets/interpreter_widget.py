import json
from typing import Any, Dict, Union

from PyQt5.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QVBoxLayout, QWidget
from qgis.core import QgsApplication

from ..core.server_handler import ServerHandler
from ..core.task import BaseServerTask


class StartTask(BaseServerTask):
    @property
    def task_description(self):
        return "starting server"

    def run(self):
        try:
            self.response = self.parent.server_handler.start_server(
                self.data["interpreter"]
            )
            if not self.response["success"]:
                return False
            return True
        except Exception as exception:
            self.exception = exception
            return False


class InterpreterWidget(QWidget):
    def __init__(self, parent):
        super(InterpreterWidget, self).__init__(parent)
        self.parent = parent
        self.start_task = None

        self.server_handler = ServerHandler()
        self.interpreter_combo_box = QComboBox()
        self.interpreter_combo_box.insertItems(0, ServerHandler.interpreters())
        self.interpreter_button = QPushButton("Start")
        self.interpreter_button.clicked.connect(self.start_server)
        self.config_button = QPushButton("Options")
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

    def start_interpreter_task(self) -> Union[StartTask, None]:
        if not self.server_handler.alive():
            interpreter = self.interpreter_combo_box.currentText()
            self.start_task = StartTask(self, {"interpreter": interpreter})
            return self.start_task
        else:
            return None

    def start_server(self):
        self.start_task = self.start_interpreter_task()
        QgsApplication.taskManager().addTask(self.start_task)

    def shutdown_server(self) -> None:
        if self.server_handler.process is not None:
            self.server_handler.kill()
        return

    def execute(self, data: Dict[str, str]) -> Dict[str, Any]:
        """
        Execute a command, and check whether it executed succesfully.
        """
        response = self.server_handler.send(data)
        return response
