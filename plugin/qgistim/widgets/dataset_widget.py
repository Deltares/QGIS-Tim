"""
This widgets displays the available elements in the GeoPackage.

This widget also allows enabling or disabling individual elements for a
computation. It also forms the link between the geometry layers and the
associated layers for homogeneities, or for timeseries layers for ttim
elements.

Not every TimML element has a TTim equivalent (yet). This means that when a
user chooses the transient simulation mode, a number of elements must be
disabled (such as inhomogeneities).
"""
from pathlib import Path
from typing import Any, List, Set

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qgis.core import QgsMapLayer, QgsProject

from ..core.tim_elements import Aquifer, Domain, load_elements_from_geopackage

SUPPORTED_TTIM_ELEMENTS = set(
    [
        "Aquifer",
        "Domain",
        "Constant",
        "Uniform Flow",
        "Well",
        "Head Well",
        "Head Line Sink",
        "Line Sink Ditch",
        "Circular Area Sink",
        "Impermeable Line Doublet",
        "Leaky Line Doublet",
    ]
)


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

    def add_item(self, timml_name: str, ttim_name: str = None, enabled: bool = True):
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
        # These are mandatory elements, cannot be unticked
        if isinstance(element, (Domain, Aquifer)):
            enabled = False
        else:
            enabled = True

        item = self.add_item(
            timml_name=element.timml_name, ttim_name=element.ttim_name, enabled=enabled
        )
        item.element = element

    def on_transient_changed(self, transient: bool) -> None:
        """
        Disable elements that are not supported by TTim, such as
        Inhomogeneities, or switch them on again.
        """
        self.setColumnHidden(2, not transient)
        self.setColumnHidden(3, not transient)
        # Disable unsupported ttim items, such as inhomogeneities
        for item in self.items():
            if item.text(1).split(":")[0] in SUPPORTED_TTIM_ELEMENTS:
                if transient:
                    item.timml_checkbox.setChecked(False)
                    item.timml_checkbox.setEnabled(False)
                else:
                    item.timml_checkbox.setEnabled(True)

    def remove_geopackage_layers(self) -> None:
        """
        Remove layers from:

        * The dataset tree widget
        * The QGIS layer panel
        * The geopackage
        """

        # Collect the selected items
        selection = self.selectedItems()
        selection = [
            item
            for item in selection
            if not isinstance(item.element, (Aquifer, Domain))
        ]
        # Append associated items
        for item in selection:
            if item.assoc_item is not None and item.assoc_item not in selection:
                selection.append(item.assoc_item)

        # Warn before deletion
        message = "\n".join([f"- {item.text(1)}" for item in selection])
        reply = QMessageBox.question(
            self,
            "Deleting from Geopackage",
            f"Deleting:\n{message}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.No:
            return

        # Start deleting
        elements = set([item.element for item in selection])
        qgs_instance = QgsProject.instance()

        for element in elements:
            for layer in [
                element.timml_layer,
                element.ttim_layer,
                element.assoc_layer,
            ]:
                # QGIS layers
                if layer is None:
                    continue
                try:
                    qgs_instance.removeMapLayer(layer.id())
                except (RuntimeError, AttributeError) as e:
                    if e.args[0] in (
                        "wrapped C/C++ object of type QgsVectorLayer has been deleted",
                        "'NoneType' object has no attribute 'id'",
                    ):
                        pass
                    else:
                        raise

            # Geopackage
            element.remove_from_geopackage()

        for item in selection:
            # Dataset tree
            index = self.indexOfTopLevelItem(item)
            self.takeTopLevelItem(index)

        return


# Keys for the storing and retrieving plugin state.
# State is written to the QGIS file under these entries.
PROJECT_SCOPE = "QgisTim"
GPGK_PATH_ENTRY = "tim_geopackage_path"
GPKG_LAYERS_ENTRY = "tim_geopackage_layers"
TIM_GROUP_ENTRY = "tim_group"
TIMML_GROUP_ENTRY = "timml_group"
TTIM_GROUP_ENTRY = "ttim_group"
TIMOUTPUT_GROUP_ENTRY = "timoutput_group"


class DatasetWidget(QWidget):
    def __init__(self, parent):
        super(DatasetWidget, self).__init__(parent)
        self.parent = parent
        self.dataset_tree = DatasetTreeWidget()
        self.dataset_tree.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.dataset_line_edit = QLineEdit()
        self.dataset_line_edit.setEnabled(False)  # Just used as a viewing port
        self.new_geopackage_button = QPushButton("New")
        self.open_geopackage_button = QPushButton("Open")
        self.remove_button = QPushButton("Remove from Dataset")
        self.add_button = QPushButton("Add to QGIS")
        self.new_geopackage_button.clicked.connect(self.new_geopackage)
        self.open_geopackage_button.clicked.connect(self.open_geopackage)
        self.remove_button.clicked.connect(self.remove_geopackage_layer)
        self.add_button.clicked.connect(self.add_selection_to_qgis)
        self.suppress_popup_checkbox = QCheckBox("Suppress attribute form pop-up")
        self.suppress_popup_checkbox.stateChanged.connect(self.suppress_popup_changed)
        # Layout
        dataset_layout = QVBoxLayout()
        dataset_row = QHBoxLayout()
        layer_row = QHBoxLayout()
        dataset_row.addWidget(self.dataset_line_edit)
        dataset_row.addWidget(self.open_geopackage_button)
        dataset_row.addWidget(self.new_geopackage_button)
        dataset_layout.addLayout(dataset_row)
        dataset_layout.addWidget(self.dataset_tree)
        layer_row.addWidget(self.add_button)
        layer_row.addWidget(self.remove_button)
        dataset_layout.addLayout(layer_row)
        dataset_layout.addWidget(self.suppress_popup_checkbox)
        self.setLayout(dataset_layout)
        # Connect to reading of project file
        instance = QgsProject().instance()
        instance.readProject.connect(self.read_plugin_state_from_project)
        instance.projectSaved.connect(self.write_plugin_state_to_project)

    @property
    def path(self) -> str:
        """Returns currently active path to GeoPackage"""
        return self.dataset_line_edit.text()

    def add_layer(
        self,
        layer: Any,
        destination: Any,
        renderer: Any = None,
        suppress: bool = None,
        on_top: bool = False,
    ) -> QgsMapLayer:
        return self.parent.add_layer(
            layer,
            destination,
            renderer,
            suppress,
            on_top,
        )

    def add_item_to_qgis(self, item) -> None:
        layers = item.element.from_geopackage()
        suppress = self.suppress_popup_checkbox.isChecked()
        timml_layer, renderer = layers[0]
        maplayer = self.add_layer(timml_layer, "timml", renderer, suppress)
        self.add_layer(layers[1][0], "ttim")
        self.add_layer(layers[2][0], "timml")
        # Set cell size if the item is a domain layer
        if item.element.timml_name.split(":")[0] == "timml Domain":
            if maplayer.featureCount() <= 0:
                return
            feature = next(iter(maplayer.getFeatures()))
            extent = feature.geometry().boundingBox()
            ymax = extent.yMaximum()
            ymin = extent.yMinimum()
            self.parent.set_cellsize_from_domain(ymax, ymin)

    def add_selection_to_qgis(self) -> None:
        selection = self.dataset_tree.selectedItems()
        for item in selection:
            self.add_item_to_qgis(item)

    def load_geopackage(self) -> None:
        """
        Load the layers of a GeoPackage into the Layers Panel
        """
        self.dataset_tree.clear()
        elements = load_elements_from_geopackage(self.path)
        for element in elements:
            self.dataset_tree.add_element(element)
        name = str(Path(self.path).stem)
        self.parent.create_groups(name)
        for item in self.dataset_tree.items():
            self.add_item_to_qgis(item)

    def write_plugin_state_to_project(self) -> None:
        project = QgsProject().instance()
        # Store geopackage path
        project.writeEntry(PROJECT_SCOPE, GPGK_PATH_ENTRY, self.path)

        # Store maplayers
        maplayers = QgsProject().instance().mapLayers()
        names = [layer for layer in maplayers]
        entry = "␞".join(names)
        project.writeEntry(PROJECT_SCOPE, GPKG_LAYERS_ENTRY, entry)

        # Store root group
        for (group, entry) in (
            (self.parent.group, TIM_GROUP_ENTRY),
            (self.parent.timml_group, TIMML_GROUP_ENTRY),
            (self.parent.ttim_group, TTIM_GROUP_ENTRY),
            (self.parent.output_group, TIMOUTPUT_GROUP_ENTRY),
        ):
            try:
                group_name = group.name()
            except (RuntimeError, AttributeError):
                group_name = ""
            project.writeEntry(PROJECT_SCOPE, entry, group_name)

        project.blockSignals(True)
        project.write()
        project.blockSignals(False)

    def read_plugin_state_from_project(self) -> None:
        project = QgsProject().instance()
        path, _ = project.readEntry(PROJECT_SCOPE, GPGK_PATH_ENTRY)
        if path == "":
            return

        group_name, _ = project.readEntry(PROJECT_SCOPE, TIM_GROUP_ENTRY)
        timml_group_name, _ = project.readEntry(PROJECT_SCOPE, TIMML_GROUP_ENTRY)
        ttim_group_name, _ = project.readEntry(PROJECT_SCOPE, TTIM_GROUP_ENTRY)
        output_group_name, _ = project.readEntry(PROJECT_SCOPE, TIMOUTPUT_GROUP_ENTRY)
        root = QgsProject.instance().layerTreeRoot()
        self.group = root.findGroup(group_name)
        if self.group is None:
            self.create_groups()
        if self.group is not None:
            self.parent.timml_group = self.group.findGroup(timml_group_name)
            self.parent.ttim_group_name = self.group.findGroup(ttim_group_name)
            self.parent.output_group_name = self.group.findGroup(output_group_name)
            if self.parent.timml_group is None:
                self.parent.timml_group = self.group.addGroup(f"{group_name}-timml")
            if self.parent.ttim_group is None:
                self.parent.ttim_group = self.group.addGroup(f"{group_name}-ttim")
            if self.parent.output_group is None:
                self.parent.output_group = self.group.addGroup(f"{group_name}-output")

        entry, success = project.readEntry(PROJECT_SCOPE, GPKG_LAYERS_ENTRY)
        if success:
            names = entry.split("␞")
        else:
            names = []

        self.dataset_tree.clear()
        self.dataset_line_edit.setText(path)
        self.parent.toggle_element_buttons(True)

        maplayers_dict = QgsProject().instance().mapLayers()
        maplayers = {v.name(): v for k, v in maplayers_dict.items() if k in names}
        elements = load_elements_from_geopackage(self.path)
        for element in elements:
            element.timml_layer = maplayers.get(element.timml_name, None)
            element.ttim_layer = maplayers.get(element.ttim_name, None)
            element.assoc_layer = maplayers.get(element.assoc_name, None)
            self.dataset_tree.add_element(element)

    def new_geopackage(self) -> None:
        """
        Create a new GeoPackage file, and set it as the active dataset.
        """
        path, _ = QFileDialog.getSaveFileName(self, "Select file", "", "*.gpkg")
        if path != "":  # Empty string in case of cancel button press
            self.dataset_line_edit.setText(path)
            for element in (Aquifer, Domain):
                instance = element(self.path, "")
                instance.create_layers(self.parent.crs)
                instance.write()
            self.load_geopackage()
            self.parent.toggle_element_buttons(True)
        self.parent.on_transient_changed()

    def open_geopackage(self) -> None:
        """
        Open a GeoPackage file, containing qgis-tim
        """
        self.dataset_tree.clear()
        path, _ = QFileDialog.getOpenFileName(self, "Select file", "", "*.gpkg")
        if path != "":  # Empty string in case of cancel button press
            self.dataset_line_edit.setText(path)
            self.load_geopackage()
            self.parent.toggle_element_buttons(True)
        self.dataset_tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.parent.on_transient_changed()

    def remove_geopackage_layer(self) -> None:
        """
        Remove layers from:
        * The dataset tree widget
        * The QGIS layer panel
        * The geopackage
        """
        self.dataset_tree.remove_geopackage_layers()

    def suppress_popup_changed(self):
        suppress = self.suppress_popup_checkbox.isChecked()
        for item in self.dataset_tree.items():
            layer = item.element.timml_layer
            if layer is not None:
                config = layer.editFormConfig()
                config.setSuppress(suppress)
                layer.setEditFormConfig(config)

    def active_elements(self):
        active_elements = {}
        for item in self.dataset_tree.items():
            active_elements[item.text(1)] = not (item.timml_checkbox.isChecked() == 0)
            active_elements[item.text(3)] = not (item.ttim_checkbox.isChecked() == 0)
        return active_elements

    def domain_item(self):
        # Find domain entry
        for item in self.dataset_tree.items():
            if isinstance(item.element, Domain):
                return item
        else:
            # Create domain instead?
            raise ValueError("Geopackage does not contain domain")

    def selection_names(self) -> Set[str]:
        selection = self.dataset_tree.items()
        # Append associated items
        for item in selection:
            if item.assoc_item is not None and item.assoc_item not in selection:
                selection.append(item.assoc_item)
        return set([item.element.name for item in selection])

    def on_transient_changed(self, transient: bool) -> None:
        self.dataset_tree.on_transient_changed(transient)

    def add_element(self, element) -> None:
        self.dataset_tree.add_element(element)
