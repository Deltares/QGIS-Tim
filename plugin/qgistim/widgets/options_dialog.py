import subprocess
import sys
from functools import partial

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)
from qgistim.core.server_handler import ServerHandler

INSTALL_COMMANDS = {
    "Git": "{interpreter} -m pip install git+{repo_url} {package}",
    "conda-forge": "mamba install -c conda-forge {package}",
}
INSTALL_VERSION_COMMANDS = {
    "Git": INSTALL_COMMANDS["Git"] + "@{version}",
    "conda-forge": INSTALL_COMMANDS["conda-forge"] + "={version}",
}

REPOSITORY_URLS = {
    "timml": "https://github.com/mbakker7/timml.git",
    "ttim": "https://github.com/mbakker7/ttim.git",
    "gistim": "https://gitlab.com/deltares/imod/qgis-tim.git",
}


class NotSupportedDialog(QMessageBox):
    def __init__(self, parent=None, command: str = ""):
        QMessageBox.__init__(self, parent)
        self.setWindowTitle("Install unsupported")
        self.setIcon(QMessageBox.Information)
        self.setText(
            "Installing new versions via this menu is not (yet) supported for "
            "this operating system. Please run the following command in the "
            f"appropriate command line:\n\n{command}"
        )
        return


class OptionsDialog(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setWindowTitle("QGIS-Tim Options")

        self.install_task = None
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.reject)

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
        _, _, origin_combo_box, version_line_edit, _ = self.version_widgets[package]
        origin = origin_combo_box.currentText()
        version = version_line_edit.text()

        lowered_version = version.lower().strip()
        url = REPOSITORY_URLS[package]
        if lowered_version in ("latest", ""):
            command = INSTALL_COMMANDS[origin]
        else:
            command = INSTALL_VERSION_COMMANDS[origin]

        command = command.format(
            interpreter=interpreter,
            package=package,
            version=version,
            repo_url=url,
        )
        env_vars = ServerHandler.environmental_variables()[interpreter]

        if sys.platform == "win32":
            subprocess.Popen(
                f"cmd.exe /k {command}",
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                env=env_vars,
                text=True,
            )
        else:
            NotSupportedDialog(self, command).show()

        return

    def on_interpreter_changed(self):
        versions = ServerHandler.versions()
        interpreter = self.interpreter_combo_box.currentText()
        for package in ["timml", "ttim", "gistim"]:
            self.version_widgets[package][1].setText(versions[interpreter][package])
        return
