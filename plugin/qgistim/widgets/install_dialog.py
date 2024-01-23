from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFileDialog,
    QDialog,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QGroupBox,
    QGridLayout,
)
from qgis.core import Qgis, QgsTask, QgsApplication
from qgistim.core.install_backend import install_from_github, install_from_zip


class InstallTask(QgsTask):
    def finished(self, result) -> None:
        self.parent.enable_install_buttons(True)
        self.parent.install_zip_line_edit.setText("")
        self.parent.update_versions()
        if result:
            self.message_bar.pushMessage(
                title="Info",
                text="Succesfully installed TimML and TTim server",
                level=Qgis.Info,
            )
        else:
            if self.exception is not None:
                message = "Exception: " + str(self.exception)
            else:
                message = "Unknown failure"

            self.message_bar.pushMessage(
                title="Error",
                text=f"Failed to install TimML and TTim server. {message}",
                level=Qgis.Critical,
            )
        return

    def cancel(self) -> None:
        self.parent.enable_install_buttons(True)
        super().cancel()
        return


class InstallZipTask(InstallTask):
    def __init__(self, parent, path: str, message_bar):
        super().__init__("Install from ZIP file", QgsTask.CanCancel)
        self.parent = parent
        self.path = path
        self.message_bar = message_bar
        self.exception = None

    def run(self) -> bool:
        try:
            install_from_zip(self.path)
            return True
        except Exception as exception:
            self.exception = exception
            return False


class InstallGithubTask(InstallTask):
    def __init__(self, parent, message_bar):
        super().__init__("Install from GitHub", QgsTask.CanCancel)
        self.parent = parent
        self.message_bar = message_bar
        self.exception = None

    def run(self) -> bool:
        try:
            install_from_github()
            return True
        except Exception as exception:
            self.exception = exception
            return False


class InstallDialog(QDialog):
    """
    Download and install from GitHub, or install from ZIP file.
    """

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.parent = parent
        self.setWindowTitle("Install TimML and TTim server")
        self.install_task = None

        # Define widgets
        self.install_github_button = QPushButton("Install latest release from GitHub")
        self.set_zip_button = QPushButton("Browse...")
        self.install_zip_button = QPushButton("Install")
        self.install_zip_line_edit = QLineEdit()
        self.install_zip_line_edit.setMinimumWidth(400)
        self.close_button = QPushButton("Close")

        # Connect with actions
        self.install_github_button.clicked.connect(self.install_from_github)
        self.set_zip_button.clicked.connect(self.set_zip_path)
        self.install_zip_button.clicked.connect(self.install_from_zip)
        self.close_button.clicked.connect(self.reject)

        # Set layout
        github_row = QHBoxLayout()
        github_row.addWidget(self.install_github_button)
        zip_row = QHBoxLayout()
        zip_row.addWidget(QLabel("ZIP file"))
        zip_row.addWidget(self.install_zip_line_edit)
        zip_row.addWidget(self.set_zip_button)
        zip_row.addWidget(self.install_zip_button)

        self.version_widgets, version_layout = self.initialize_version_view()
        self.update_versions()
        version_group = QGroupBox("Current Versions")
        version_group.setLayout(version_layout)
        github_group = QGroupBox("Install from GitHub")
        github_group.setLayout(github_row)
        zip_group = QGroupBox("Install from ZIP file")
        zip_group.setLayout(zip_row)

        layout = QVBoxLayout()
        layout.addWidget(version_group)
        layout.addWidget(github_group)
        layout.addWidget(zip_group)
        layout.addWidget(self.close_button, stretch=0, alignment=Qt.AlignRight)
        layout.addStretch()
        self.setLayout(layout)
 
    def initialize_version_view(self):
        version_widgets = {}
        version_layout = QGridLayout()
        for i, package in enumerate(["timml", "ttim", "gistim"]):
            version_view = QLineEdit()
            version_view.setEnabled(False)
            widgets = (
                QLabel(package),
                version_view,
            )
            version_widgets[package] = widgets
            for j, widget in enumerate(widgets):
                version_layout.addWidget(widget, i, j)
        return version_widgets, version_layout
    
    def update_versions(self):
        versions = self.parent.server_handler.versions()
        for package in ["timml", "ttim", "gistim"]:
            self.version_widgets[package][1].setText(versions.get(package))
        return

    def enable_install_buttons(self, enabled: bool) -> None:
        self.install_github_button.setEnabled(enabled)
        self.install_zip_button.setEnabled(enabled)
        return

    def set_zip_path(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select file", "", "*.zip")
        if path != "":  # Empty string in case of cancel button press
            self.install_zip_line_edit.setText(path)
        return

    def install_from_zip(self) -> None:
        path = self.install_zip_line_edit.text()
        if path == "":
            return

        reply = QMessageBox.question(
            self,
            "Install from ZIP?",
            "This will install from the selected ZIP file. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.No:
            return
        self.install_task = InstallZipTask(
            self, path=path, message_bar=self.parent.message_bar
        )
        self.enable_install_buttons(False)
        QgsApplication.taskManager().addTask(self.install_task)
        return

    def install_from_github(self) -> None:
        reply = QMessageBox.question(
            self,
            "Install from Github?",
            "This will download and install the latest release from GitHub. Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.No:
            return
        self.install_task = InstallGithubTask(self, message_bar=self.parent.message_bar)
        self.enable_install_buttons(False)
        QgsApplication.taskManager().addTask(self.install_task)
        return
