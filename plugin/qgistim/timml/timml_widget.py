"""
This module contains the logic connecting the buttons of the plugin dockwidget
to the actual functionality.
"""
import json
import os
import re
from collections import defaultdict
from functools import partial
from pathlib import Path
from typing import Any, List, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator, QHeaderView, QMessageBox
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from xarray.core.common import T
from qgis.core import (
    Qgis,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)
from qgis.PyQt import QtWidgets
from qgistim import geopackage, layer_styling
from qgistim.server_handler import ServerHandler

from .dataset_tree_widget import DatasetTreeWidget
from .extraction_widget import DataExtractionWidget
from .tim_elements import (
    Aquifer,
    Domain,
    ELEMENTS,
    load_elements_from_geopackage,
)


class QgisTimmlWidget(QWidget):
    def __init__(self, parent, iface):
        super(QgisTimmlWidget, self).__init__(parent)
        self.iface = iface
        # Data extraction
        self.extraction_widget = DataExtractionWidget(iface)
        self.extraction_widget.extract_button.clicked.connect(self.extract)
        # Dataset management
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
        self.group = None
        self.dataset_tree = DatasetTreeWidget()
        self.dataset_tree.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        # Connect to reading of project file
        instance = QgsProject().instance()
        instance.readProject.connect(self.read_plugin_state_from_project)
        instance.projectSaved.connect(self.write_plugin_state_to_project)
        # Element
        self.element_buttons = {}
        for element in ELEMENTS:
            if element in ("Aquifer", "Domain"):
                continue
            button = QPushButton(element)
            button.clicked.connect(partial(self.tim_element, element_type=element))
            self.element_buttons[element] = button
        self.toggle_element_buttons(False)  # no dataset loaded yet
        # Interpreter combo box
        self.server_handler = None  # ServerHandler()  # To connect with TimServer
        self.interpreter_combo_box = QComboBox()
        self.interpreter_combo_box.insertItems(0, ServerHandler.interpreters())
        self.interpreter_button = QPushButton("Start")
        self.interpreter_button.clicked.connect(self.start_server)
        # Solution
        self.domain_button = QPushButton("Domain")
        self.transient_combo_box = QComboBox()
        self.transient_combo_box.addItems(["Steady-state", "Transient"])
        self.compute_button = QPushButton("Compute")
        self.cellsize_spin_box = QDoubleSpinBox()
        self.cellsize_spin_box.setMinimum(0.0)
        self.cellsize_spin_box.setMaximum(10_000.0)
        self.cellsize_spin_box.setSingleStep(1.0)
        self.cellsize_spin_box.setValue(25.0)
        self.domain_button.clicked.connect(self.domain)
        self.compute_button.clicked.connect(self.compute)
        # Layout
        # External interpreter
        interpreter_groupbox = QGroupBox("Interpreter")
        interpreter_groupbox.setMaximumHeight(60)
        interpreter_layout = QVBoxLayout()
        interpreter_row = QHBoxLayout()
        interpreter_row.addWidget(self.interpreter_combo_box)
        interpreter_row.addWidget(self.interpreter_button)
        interpreter_layout.addLayout(interpreter_row)
        interpreter_groupbox.setLayout(interpreter_layout)
        # Data extraction
        extraction_group = QGroupBox("Data extraction")
        extraction_group.setMaximumHeight(110)
        extraction_layout = QVBoxLayout()
        extraction_layout.addWidget(self.extraction_widget)
        extraction_group.setLayout(extraction_layout)
        # Dataset
        dataset_groupbox = QGroupBox("Input: GeoPackage Dataset")
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
        dataset_groupbox.setLayout(dataset_layout)
        # Elements
        element_groupbox = QGroupBox("Elements")
        element_grid = QGridLayout()
        n_row = -(len(self.element_buttons) // -2)  # Ceiling division
        for i, button in enumerate(self.element_buttons.values()):
            if i < n_row:
                element_grid.addWidget(button, i, 0)
            else:
                element_grid.addWidget(button, i % n_row, 1)
        element_groupbox.setLayout(element_grid)
        # Solution
        solution_groupbox = QGroupBox("Output")
        solution_groupbox.setMaximumHeight(150)
        solution_grid = QGridLayout()
        solution_grid.addWidget(self.domain_button, 0, 0)
        label = QLabel("Cellsize:")
        label.setFixedWidth(45)
        solution_grid.addWidget(label, 0, 1)
        solution_grid.addWidget(self.cellsize_spin_box, 0, 2)
        solution_grid.addWidget(self.transient_combo_box, 1, 0)
        solution_grid.addWidget(self.compute_button, 1, 2)
        solution_groupbox.setLayout(solution_grid)
        # Set for the dock widget
        layout = QVBoxLayout()
        layout.addWidget(interpreter_groupbox)
        layout.addWidget(extraction_group)
        layout.addWidget(dataset_groupbox)
        layout.addWidget(element_groupbox)
        layout.addWidget(solution_groupbox)
        self.setLayout(layout)

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

    @property
    def path(self) -> str:
        """Returns currently active path to GeoPackage"""
        return self.dataset_line_edit.text()

    @property
    def crs(self) -> Any:
        """Returns coordinate reference system of current mapview"""
        return self.iface.mapCanvas().mapSettings().destinationCrs()

    def add_layer(self, layer: Any, renderer: Any = None) -> None:
        """
        Add a layer to the Layers Panel

        Parameters
        ----------
        layer:
            QGIS map layer, raster or vector layer
        renderer:
            QGIS layer renderer, optional
        """
        maplayer = QgsProject.instance().addMapLayer(layer, False)
        if renderer is not None:
            maplayer.setRenderer(renderer)
        self.group.addLayer(maplayer)

    def load_geopackage(self) -> None:
        """
        Load the layers of a GeoPackage into the Layers Panel
        """
        self.dataset_tree.clear()
        elements = load_elements_from_geopackage(self.path)
        print(elements)
        for element in elements:
            self.dataset_tree.add_element(element)
        path = self.path
        root = QgsProject.instance().layerTreeRoot()
        self.group = root.addGroup(str(Path(path).stem))
        for item in self.dataset_tree.items():
            self.add_item_to_qgis(item)

    def write_plugin_state_to_project(self) -> None:
        PROJECT_SCOPE = "QgisTim"
        GPGK_PATH_ENTRY = "tim_geopackage_path"
        GPKG_LAYERS_ENTRY = "tim_geopackage_layers"
        TIMML_GROUP_ENTRY = "tim_group"

        project = QgsProject().instance()
        # Store geopackage path
        project.writeEntry(PROJECT_SCOPE, GPGK_PATH_ENTRY, self.path)

        # Store maplayers
        maplayers = QgsProject().instance().mapLayers()
        names = [layer for layer in maplayers]
        entry = "␞".join(names)
        project.writeEntry(PROJECT_SCOPE, GPKG_LAYERS_ENTRY, entry)

        # Store root group
        try:
            group_name = self.group.name()
        except (RuntimeError, AttributeError):
            group_name = ""
        project.writeEntry(PROJECT_SCOPE, TIMML_GROUP_ENTRY, group_name)

        project.blockSignals(True)
        project.write()
        project.blockSignals(False)

    def read_plugin_state_from_project(self) -> None:
        PROJECT_SCOPE = "QgisTim"
        GPGK_PATH_ENTRY = "tim_geopackage_path"
        GPKG_LAYERS_ENTRY = "tim_geopackage_layers"
        TIMML_GROUP_ENTRY = "tim_group"

        project = QgsProject().instance()
        path, _ = project.readEntry(PROJECT_SCOPE, GPGK_PATH_ENTRY)
        if path == "":
            return

        group_name, _ = project.readEntry(PROJECT_SCOPE, TIMML_GROUP_ENTRY)
        root = QgsProject.instance().layerTreeRoot()
        self.group = root.findGroup(group_name)
        if self.group is None:
            self.group = root.addGroup(str(Path(path).stem))

        entry, success = project.readEntry(PROJECT_SCOPE, GPKG_LAYERS_ENTRY)
        if success:
            names = entry.split("␞")
        else:
            names = []

        self.dataset_tree.clear()
        self.dataset_line_edit.setText(path)
        self.toggle_element_buttons(True)

        gpkg_names = geopackage.layers(path)
        grouped_names = self.group_geopackage_names(gpkg_names)
        
        maplayers_dict = QgsProject().instance().mapLayers()
        maplayers = {v.name(): v for k, v in maplayers_dict.items() if k in names}
        for timml_name, ttim_name in grouped_names:
            timml_layer = maplayers.get(timml_name, None)
            ttim_layer = maplayers.get(ttim_name, None)
            item = self.dataset_tree.add_layer(timml_name, ttim_name)
            item.layers = [timml_layer, ttim_layer]

    def new_geopackage(self) -> None:
        """
        Create a new GeoPackage file, and set it as the active dataset.
        """
        path, _ = QFileDialog.getSaveFileName(self, "Select file", "", "*.gpkg")
        if path != "":  # Empty string in case of cancel button press
            self.dataset_line_edit.setText(path)
            for element in (Aquifer, Domain):
                instance = element(self.path, "")
                instance.create_layers(self.crs)
                instance.write()
            self.load_geopackage()
            self.toggle_element_buttons(True)

    def open_geopackage(self) -> None:
        """
        Open a GeoPackage file, containing qgis-tim
        """
        self.dataset_tree.clear()
        path, _ = QFileDialog.getOpenFileName(self, "Select file", "", "*.gpkg")
        if path != "":  # Empty string in case of cancel button press
            self.dataset_line_edit.setText(path)
            self.load_geopackage()
            self.toggle_element_buttons(True)
        self.dataset_tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)

    def remove_geopackage_layer(self) -> None:
        selection = self.dataset_tree.selectedItems()
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
        # Delete from:
        # * QGIS layers
        # * Geopackage 
        # * Dataset tree
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
            index = self.dataset_tree.indexOfTopLevelItem(item)
            self.dataset_tree.takeTopLevelItem(index)

    def add_item_to_qgis(self, item) -> None:
        names = [item.text(1), item.text(3)]
        layers = item.element.from_geopackage(names)
        for layer, renderer in layers:
            self.add_layer(layer, renderer)

    def add_selection_to_qgis(self) -> None:
        selection = self.dataset_tree.selectedItems()
        for item in selection:
            self.add_item_to_qgis(item)

    def tim_element(self, element_type: str) -> None:
        """
        Create a new TimML element input layer.

        Parameters
        ----------
        element_type: str
            Name of the element type. 
        """
        klass = ELEMENTS[element_type]
        element = klass.dialog(self.path, self.crs, self.iface, klass)
        if element is None: # cancelled
            return
        # Write to geopackage
        element.write()
        # Add to QGIS
        self.add_layer(element.timml_layer, element.renderer())
        for layer in [
            element.ttim_layer,
            element.assoc_layer,
        ]:
            if layer is not None:
                self.add_layer(element.timml_layer)
        # Add to dataset tree
        self.dataset_tree.add_element(element)

    def domain(self) -> None:
        """
        Write the current viewing extent as rectangle to the GeoPackage.
        """
        # Find domain entry
        for item in self.dataset_tree.items():
            if isinstance(item.element, Domain):
                break
        else:
            # Create domain instead?
            raise ValueError("Geopackage does not contain domain")
        ymax, ymin = item.element.update_extent(self.iface)
        self.set_cellsize_from_domain(ymax, ymin)

    def set_cellsize_from_domain(self, ymax, ymin):
        # Guess a reasonable value for the cellsize: about 50 rows
        dy = (ymax - ymin) / 50.0
        if dy > 500.0:
            dy = round(dy / 500.0) * 500.0
        elif dy > 50.0:
            dy = round(dy / 50.0) * 50.0
        elif dy > 5.0:  # round to five
            dy = round(dy / 5.0) * 5.0
        elif dy > 1.0:
            dy = round(dy)
        self.cellsize_spin_box.setValue(dy)

    def on_transient_changed(self) -> None:
        transient = self.transient_combo_box.text() == "Transient"
        if transient:
            self.dataset_tree.on_transient_changed(transient)

    def load_result(self, path: Path, cellsize: float) -> None:
        """
        Load the result of a compute call into the Layers panel.

        path:
            Path to the GeoPackage
        cellsize: float
            Cellsize value, as defined in the spinbox, and sent to the
            interpreter running TimML.
        """
        netcdf_path = str(
            (path.parent / f"{path.stem}-{cellsize}".replace(".", "_")).with_suffix(
                ".nc"
            )
        )
        # Loop through layers first. If the path already exists as a layer source, remove it.
        # Otherwise QGIS will not the load the new result (this feels like a bug?).
        for layer in QgsProject.instance().mapLayers().values():
            if Path(netcdf_path) == Path(layer.source()):
                QgsProject.instance().removeMapLayer(layer.id())

        # For a Mesh Layer, use:
        # layer = QgsMeshLayer(str(netcdf_path), f"{path.stem}-{cellsize}", "mdal")

        # Check layer for number of bands
        layer = QgsRasterLayer(netcdf_path, "", "gdal")
        bandcount = layer.bandCount()
        for band in range(1, bandcount + 1):  # Bands use 1-based indexing
            layer = QgsRasterLayer(
                netcdf_path, f"{path.stem}-layer{band - 1}-{cellsize}", "gdal"
            )
            renderer = layer_styling.pseudocolor_renderer(
                layer, band, colormap="Magma", nclass=10
            )
            self.add_layer(layer, renderer)

    def start_server(self) -> None:
        """Start an external interpreter running gistim"""
        self.server_handler = ServerHandler()
        interpreter = self.interpreter_combo_box.currentText()
        self.server_handler.start_server(interpreter)

    def shutdown_server(self) -> None:
        if self.server_handler is not None:
            self.server_handler.kill()
            self.server_handler = None

    def compute(self) -> None:
        """
        Run a TimML computation with the current state of the currently active
        GeoPackage dataset.
        """
        # Collect checked elements
        active_elements = {}
        for item in self.dataset_tree.items():
            active_elements[item.text(1)] = not (item.timml_checkbox.isChecked() == 0)
            active_elements[item.text(3)] = not (item.ttim_checkbox.isChecked() == 0)

        cellsize = self.cellsize_spin_box.value()
        path = Path(self.path).absolute()
        data = json.dumps(
            {
                "operation": "compute",
                "path": str(path),
                "cellsize": cellsize,
                "active_elements": active_elements,
            }
        )
        handler = self.server_handler
        received = handler.send(data)

        if received == "0":
            self.load_result(path, cellsize)
        else:
            self.iface.messageBar().pushMessage(
                "Error",
                "Something seems to have gone wrong, "
                "try checking the TimServer window...",
                level=Qgis.Critical,
            )

    def extract(self) -> None:
        interpreter = self.interpreter_combo_box.currentText()
        env_vars = self.server_handler.environmental_variables()
        self.extraction_widget.extract(interpreter, env_vars, self.server_handler)

