from typing import Any, Dict

from PyQt5.QtWidgets import QDialog, QHBoxLayout, QPushButton, QTextBrowser, QVBoxLayout


def format_list(errors: Dict[str, Any]):
    """Recursive formatting"""
    messages = []
    for variable, var_errors in errors.items():
        if isinstance(var_errors, list):
            messages.append(f"<p>{variable}</p><ul>")
            messages.extend(f"<li>{error}</li>" for error in var_errors)
            messages.append("</ul>")
        else:
            messages.append(f"<p>{variable}</p><ul><li>")
            messages.extend(format_list(var_errors))
            messages.append("</ul></li>")
    return messages


def format_errors(errors: Dict[str, Dict[str, Any]]):
    messages = []
    for element, element_errors in errors.items():
        messages.append(f"<b>{element}</b>")
        messages.extend(format_list(element_errors))
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
