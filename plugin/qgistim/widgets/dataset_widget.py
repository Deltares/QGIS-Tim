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
        super().__init__(parent)
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
PLUGIN_GROUP = "tim_group"
GROUPS = {
    "timml": "timml_group",
    "ttim": "ttim_group",
    "output:vector": "output_vector_group",
    "output:mesh": "output_mesh_group",
    "output:raster": "output_raster_group",
}


class DatasetWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
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
        self.suppress_popup_checkbox = QCheckBox("Suppress attribute form pop-up")
        self.suppress_popup_checkbox.stateChanged.connect(self.suppress_popup_changed)
        self.remove_button.clicked.connect(self.remove_geopackage_layer)
        self.add_button.clicked.connect(self.add_selection_to_qgis)
        self.convert_button = QPushButton("Convert GeoPackage to Python script")
        self.convert_button.clicked.connect(self.convert)
        # Layout
        dataset_layout = QVBoxLayout()
        dataset_row = QHBoxLayout()
        layer_row = QHBoxLayout()
        dataset_row.addWidget(self.dataset_line_edit)
        dataset_row.addWidget(self.open_geopackage_button)
        dataset_row.addWidget(self.new_geopackage_button)
        dataset_layout.addLayout(dataset_row)
        dataset_layout.addWidget(self.dataset_tree)
        dataset_layout.addWidget(self.suppress_popup_checkbox)
        layer_row.addWidget(self.add_button)
        layer_row.addWidget(self.remove_button)
        dataset_layout.addLayout(layer_row)
        dataset_layout.addWidget(self.convert_button)
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
        """
        QGIS project file supports reading and storing settings in the project file:
        https://docs.qgis.org/3.22/en/docs/pyqgis_developer_cookbook/settings.html

        We communicate (read & store) the following state:

        * Which layers in the Layers panel are QGIS-Tim layers.
        * In which geopackage these layers are stored.
        * We connect these with Layer groups of the tim_widget.
        * Connect the map layers with the elements of the DatasetWidget.
        """

        subgroups = self.parent.subgroups
        if subgroups is None:
            return
        project = QgsProject().instance()
        # Store geopackage path
        project.writeEntry(PROJECT_SCOPE, GPGK_PATH_ENTRY, self.path)

        # Store maplayers
        maplayers = QgsProject().instance().mapLayers()
        names = [layer for layer in maplayers]
        entry = "␞".join(names)
        project.writeEntry(PROJECT_SCOPE, GPKG_LAYERS_ENTRY, entry)
        plugin_group_name = self.parent.group.name()
        project.writeEntry(PROJECT_SCOPE, PLUGIN_GROUP, plugin_group_name)

        for key, entry_name in GROUPS.items():
            group = subgroups[key]
            try:
                group_name = group.name()
            except (RuntimeError, AttributeError):
                group_name = ""
            project.writeEntry(PROJECT_SCOPE, entry_name, group_name)

        project.blockSignals(True)
        project.write()
        project.blockSignals(False)

    def read_plugin_state_from_project(self) -> None:
        """
        Initialize the plugin state from the settings stored in the project
        file, and the available groups and layers in the Layers Panel.

        * Find the geopackage path.
        * Find the plugin group in the Layers Panel
        * Set the plugin group in the QgisTimWidget.group.
        * Set the subgroups in the QgisTimWidget.subgroups dictionary.
        * Attach the map layers to the DatasetItem elements.

        Early return on failure to find the geopackage path or the plugin
        group.
        """
        project = QgsProject().instance()
        path, success = project.readEntry(PROJECT_SCOPE, GPGK_PATH_ENTRY)
        if not success or path == "":
            return

        plugin_group_name, success = project.readEntry(PROJECT_SCOPE, PLUGIN_GROUP)
        if not success:
            return

        root = QgsProject.instance().layerTreeRoot()
        plugin_group = root.findGroup(plugin_group_name)
        if plugin_group is None:
            return

        self.parent.group = plugin_group
        subgroups = self.parent.subgroups

        for key, entry_name in GROUPS.items():
            name, success = project.readEntry(PROJECT_SCOPE, entry_name)
            if success:
                subgroup = plugin_group.findGroup(name)
            else:
                subgroup = None

            if subgroup is None:
                # If the subgroup doesn't exist, recreate it:
                # and set the subgroup in tim_widget.group
                subgroups[key] = plugin_group.addGroup(name)
            else:
                subgroups[key] = plugin_group.findGroup(name)

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

        return

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
        return

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
        return

    def remove_geopackage_layer(self) -> None:
        """
        Remove layers from:
        * The dataset tree widget
        * The QGIS layer panel
        * The geopackage
        """
        self.dataset_tree.remove_geopackage_layers()
        return

    def suppress_popup_changed(self):
        suppress = self.suppress_popup_checkbox.isChecked()
        for item in self.dataset_tree.items():
            layer = item.element.timml_layer
            if layer is not None:
                config = layer.editFormConfig()
                config.setSuppress(suppress)
                layer.setEditFormConfig(config)
        return

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
        return

    def add_element(self, element) -> None:
        self.dataset_tree.add_element(element)
        return

    def convert(self) -> None:
        outpath, _ = QFileDialog.getSaveFileName(self, "Select file", "", "*.py")
        if outpath != "":  # Empty string in case of cancel button press
            data = {
                "operation": "convert",
                "inpath": self.path,
                "outpath": outpath,
            }
            self.parent.execute(data)
        return
