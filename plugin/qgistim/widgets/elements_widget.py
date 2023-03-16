from functools import partial

from PyQt5.QtWidgets import QGridLayout, QPushButton, QVBoxLayout, QWidget
from qgistim.core.tim_elements import ELEMENTS


class ElementsWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.element_buttons = {}
        for element in ELEMENTS:
            if element in ("Aquifer", "Domain"):
                continue
            button = QPushButton(element)
            button.clicked.connect(partial(self.tim_element, element_type=element))
            self.element_buttons[element] = button
        self.toggle_element_buttons(False)  # no dataset loaded yet

        elements_layout = QVBoxLayout()
        elements_grid = QGridLayout()
        n_row = -(len(self.element_buttons) // -2)  # Ceiling division
        for i, button in enumerate(self.element_buttons.values()):
            if i < n_row:
                elements_grid.addWidget(button, i, 0)
            else:
                elements_grid.addWidget(button, i % n_row, 1)
        elements_layout.addLayout(elements_grid)
        elements_layout.addStretch()
        self.setLayout(elements_layout)

    def toggle_element_buttons(self, state: bool) -> None:
        """
        Enables or disables the element buttons.

        Parameters
        ----------
        state: bool
            True to enable, False to disable
        """
        for button in self.element_buttons.values():
            button.setEnabled(state)

    def tim_element(self, element_type: str) -> None:
        """
        Create a new TimML element input layer.

        Parameters
        ----------
        element_type: str
            Name of the element type.
        """
        klass = ELEMENTS[element_type]
        names = self.parent.selection_names()

        # Get the crs. If not a CRS in meters, abort.
        try:
            crs = self.parent.crs
        except ValueError:
            return

        element = klass.dialog(self.parent.path, crs, self.parent.iface, names)
        if element is None:  # dialog cancelled
            return
        # Write to geopackage
        element.write()
        # Add to QGIS and dataset tree
        self.parent.add_element(element)
