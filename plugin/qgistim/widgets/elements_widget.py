from functools import partial

from core.tim_elements import ELEMENTS, Domain
from PyQt5.QtWidgets import QGridLayout, QPushButton, QVBoxLayout, QWidget


class ElementsWidget(QWidget):
    def __init__(self, parent):
        super(ElementsWidget, self).__init__(parent)

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

        selection = self.dataset_tree.items()
        # Append associated items
        for item in selection:
            if item.assoc_item is not None and item.assoc_item not in selection:
                selection.append(item.assoc_item)
        names = set([item.element.name for item in selection])

        element = klass.dialog(
            self.parent.path, self.parent.crs, self.parent.iface, klass, names
        )
        if element is None:  # dialog cancelled
            return
        # Write to geopackage
        element.write()
        # Add to QGIS
        self.add_layer(element.timml_layer, self.timml_group, element.renderer())
        self.add_layer(element.ttim_layer, self.ttim_group)
        self.add_layer(element.assoc_layer, self.timml_group)
        # Add to dataset tree
