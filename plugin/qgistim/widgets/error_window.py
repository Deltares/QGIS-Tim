from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget


class ErrorWindow(QScrollArea):
    """
    A scrollable window for reporting (many) errors.
    """

    def __init__(self, title: str, message: str):
        super().__init__()
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop)
        layout.addWidget(QLabel(message))
        self.setWidget(widget)
        self.setWidgetResizable(True)
        self.setWindowTitle(title)
