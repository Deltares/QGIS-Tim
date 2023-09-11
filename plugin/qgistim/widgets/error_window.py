from typing import Any, Dict

from PyQt5.QtWidgets import QDialog, QHBoxLayout, QPushButton, QTextBrowser, QVBoxLayout


def format_errors(errors: Dict[str, Dict[str, Any]]):
    messages = []
    for element, element_errors in errors.items():
        messages.append(f"<b>{element}</b>")
        for variable, var_errors in element_errors.items():
            messages.append("<ul>")
            messages.extend(f"<li>{variable}: {error}</li>" for error in var_errors)
            messages.append("</ul>")
    return "".join(messages)


class ValidationDialog(QDialog):
    def __init__(self, errors: Dict[str, Dict[str, Any]]):
        super().__init__()
        self.cancel_button = QPushButton("Close")
        self.cancel_button.clicked.connect(self.reject)
        self.textbox = QTextBrowser()
        self.textbox.setReadOnly(True)
        self.textbox.setHtml(format_errors(errors))
        first_row = QHBoxLayout()
        first_row.addWidget(self.textbox)
        second_row = QHBoxLayout()
        second_row.addStretch()
        second_row.addWidget(self.cancel_button)
        layout = QVBoxLayout()
        layout.addLayout(first_row)
        layout.addLayout(second_row)
        self.setLayout(layout)
        self.setWindowTitle("Invalid model input")
        self.textbox.setMinimumWidth(500)
        self.textbox.setMinimumHeight(500)
        self.show()
