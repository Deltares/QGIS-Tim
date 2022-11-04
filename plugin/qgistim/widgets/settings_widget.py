import subprocess
from functools import partial

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)
from qgis.core import QgsApplication

from ..core.server_handler import ServerHandler
from ..core.task import BaseServerTask

INSTALL_COMMANDS = {
    "Git": "{interpreter} -m pip install git+{repo_url} {package}",
    "conda-forge": "mamba install -c conda-forge {package}",
}
INSTALL_VERSION_COMMANDS = {
    "Git": INSTALL_COMMANDS["Git"] + "@{version}",
    "conda-forge": INSTALL_COMMANDS["conda-forge"] + "={version}",
}


class InstallTask(BaseServerTask):
    @property
    def task_description(self):
        return "Updating package"

    def run(self):
        try:
            self.response = subprocess.run(
                self.data["command"],
                check=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                env=self.data["env_vars"],
            )
            return True
        except Exception as exception:
            self.exception = exception
            return False


class OptionsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        QDialog.__init__(self, parent)
        self.setWindowTitle("QGIS-Tim Options")

        self.install_task = None
        self.close_button = QPushButton("Close")
        self.interpreter_combo_box = QComboBox()
        self.interpreter_combo_box.insertItems(0, ServerHandler.interpreters())
        self.interpreter_combo_box.currentIndexChanged.connect(
            self.on_interpreter_changed
        )

        layout = QVBoxLayout()
        version_layout = QGridLayout()
        self.version_widgets = {}

        for i, package in enumerate(["timml", "ttim", "gistim"]):
            version_line_edit = QLineEdit()
            version_line_edit.setText("Latest"),
            version_view = QLineEdit()
            version_view.setEnabled(False)
            origin_combo_box = QComboBox()
            install_button = QPushButton("Install")
            install_button.clicked.connect(partial(self.install, package=package))
            origin_combo_box.insertItems(0, ["conda-forge", "Git"])
            widgets = (
                QLabel(package),
                version_view,
                origin_combo_box,
                version_line_edit,
                install_button,
            )
            for j, widget in enumerate(widgets):
                version_layout.addWidget(widget, i, j)

            self.version_widgets[package] = widgets

        layout.addWidget(self.interpreter_combo_box)
        layout.addLayout(version_layout)
        layout.addWidget(self.close_button, stretch=0, alignment=Qt.AlignRight)
        layout.addStretch()
        self.setLayout(layout)
        self.on_interpreter_changed()

    def install(self, package: str):
        interpreter = self.interpreter_combo_box.currentText()
        _, origin_combo_box, version_line_edit, _ = self.version_widgets[package]
        origin = origin_combo_box.currentText()
        version = version_line_edit.text()

        lowered_version = version.lower().strip()
        if lowered_version in ("latest", ""):
            command = INSTALL_COMMANDS[origin].format(
                interpreter=interpreter, package=package
            )
        else:
            command = INSTALL_VERSION_COMMANDS[origin].format(
                interpreter=interpreter, package=package, version=version
            )

        env_vars = ServerHandler.environmental_variables[interpreter]
        self.install_task = InstallTask(
            self, data={"command": command, "env_vars": env_vars}
        )
        self.parent.set_interpreter_interaction(False)
        QgsApplication.taskManager().addTask(self.install_task)
        return

    def on_interpreter_changed(self):
        versions = ServerHandler.versions()
        interpreter = self.interpreter_combo_box.currentText()
        for package in ["timml", "ttim", "gistim"]:
            self.version_widgets[package][1].setText(versions[interpreter][package])
        return
