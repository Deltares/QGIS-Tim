from typing import List

from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QTreeWidget,
    QTreeWidgetItem,
)
from PyQt5.QtGui import QHeaderView
from PyQt5.QtWidgets import (
    QSizePolicy,
)

from .tim_elements import Aquifer, BuildingPit, Domain, PolygonInhomogeneity


class DatasetTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super(DatasetTreeWidget, self).__init__(parent)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setHeaderHidden(True)
        self.setSortingEnabled(True)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.setHeaderLabels(["", "steady", "", "transient"])
        self.setHeaderHidden(False)
        header = self.header()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionsMovable(False)
        self.setColumnCount(4)
        self.setColumnWidth(0, 1)
        self.setColumnWidth(2, 1)
        self.domain = None
        
    def items(self) -> List[QTreeWidgetItem]:
        root = self.invisibleRootItem()
        return [root.child(i) for i in range(root.childCount())]

    def add_item(self, timml_name: str, ttim_name: str = None, enabled: bool=True):
        item = QTreeWidgetItem()
        self.addTopLevelItem(item)
        item.timml_checkbox = QCheckBox()
        item.timml_checkbox.setChecked(True)
        item.timml_checkbox.setEnabled(enabled)
        self.setItemWidget(item, 0, item.timml_checkbox)
        item.setText(1, timml_name)
        item.ttim_checkbox = QCheckBox()
        item.ttim_checkbox.setChecked(True)
        item.ttim_checkbox.setEnabled(enabled)
        if ttim_name is None:
            item.ttim_checkbox.setChecked(False)
            item.ttim_checkbox.setEnabled(False)
        self.setItemWidget(item, 2, item.ttim_checkbox)
        item.setText(3, ttim_name)
        # Disable ttim layer when timml layer is unticked
        # as timml layer is always required for ttim layer
        item.timml_checkbox.toggled.connect(
            lambda checked: not checked and item.ttim_checkbox.setChecked(False)
        )
        item.assoc_item = None
        return item

    def add_element(self, element) -> None:
        if isinstance(element, (Domain, Aquifer)):
            enabled = False
        else:
            enabled = True
        item = self.add_item(
            timml_name=element.timml_name,
            ttim_name=element.ttim_name,
            enabled=enabled
        )
        item.element = element
        if element.assoc_layer is not None:
            assoc_item = self.add_item(
                timml_name=element.assoc_name,
                enabled=enabled
            )
            assoc_item.element = element
            # Cross-reference items
            item.assoc_item = assoc_item
            assoc_item.assoc_item = item

    def on_transient_changed(self, transient: bool) -> None:
        self.setColumnHidden(2, not transient)
        self.setColumnHidden(3, not transient)