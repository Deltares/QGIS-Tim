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
from qgistim.core.server_handler import ServerHandler


class VersionDialog(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setWindowTitle("QGIS-Tim Version Info")

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
            widgets = (
                QLabel(package),
                version_view,
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

    def on_interpreter_changed(self):
        versions = ServerHandler.versions()
        interpreter = self.interpreter_combo_box.currentText()
        for package in ["timml", "ttim", "gistim"]:
            self.version_widgets[package][1].setText(versions[interpreter][package])
        return
