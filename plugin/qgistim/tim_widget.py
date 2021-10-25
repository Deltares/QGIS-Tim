"""
This module contains the logic connecting the buttons of the plugin dockwidget
to the actual functionality.
"""
import json
import re
import tempfile
from functools import partial
from pathlib import Path
from typing import Any, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsMapLayerProxyModel,
    QgsMeshDatasetIndex,
    QgsMeshLayer,
    QgsProject,
    QgsRasterLayer,
)
from qgis.gui import QgsMapLayerComboBox
from qgistim import layer_styling
from qgistim.server_handler import ServerHandler

from .dataset_tree_widget import DatasetTreeWidget
from .dummy_ugrid import write_dummy_ugrid
from .extraction_widget import DataExtractionWidget
from .processing import mesh_contours
from .tim_elements import ELEMENTS, Aquifer, Domain, load_elements_from_geopackage

# Keys for the storing and retrieving plugin state.
# State is written to the QGIS file under these entries.
PROJECT_SCOPE = "QgisTim"
GPGK_PATH_ENTRY = "tim_geopackage_path"
GPKG_LAYERS_ENTRY = "tim_geopackage_layers"
TIM_GROUP_ENTRY = "tim_group"
TIMML_GROUP_ENTRY = "timml_group"
TTIM_GROUP_ENTRY = "ttim_group"
TIMOUTPUT_GROUP_ENTRY = "timoutput_group"


class QgisTimmlWidget(QWidget):
    def __init__(self, parent, iface):
        super(QgisTimmlWidget, self).__init__(parent)
        self.iface = iface
        self.dummy_ugrid_path = Path(tempfile.mkdtemp()) / "qgistim-dummy-ugrid.nc"
        write_dummy_ugrid(self.dummy_ugrid_path)
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
        self.suppress_popup_checkbox = QCheckBox("Suppress attribute form pop-up")
        self.suppress_popup_checkbox.stateChanged.connect(self.suppress_popup_changed)
        self.group = None
        self.timml_group = None
        self.ttim_group = None
        self.output_group = None
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
        self.config_button = QPushButton()
        self.config_button.clicked.connect(self.configure_server)
        self.config_button.setIcon(QgsApplication.getThemeIcon("/mActionOptions.svg"))
        # Solution
        self.domain_button = QPushButton("Domain")
        self.transient_combo_box = QComboBox()
        self.transient_combo_box.addItems(["Steady-state", "Transient"])
        self.transient_combo_box.currentTextChanged.connect(self.on_transient_changed)
        self.compute_button = QPushButton("Compute")
        self.cellsize_spin_box = QDoubleSpinBox()
        self.cellsize_spin_box.setMinimum(0.0)
        self.cellsize_spin_box.setMaximum(10_000.0)
        self.cellsize_spin_box.setSingleStep(1.0)
        self.cellsize_spin_box.setValue(25.0)
        self.domain_button.clicked.connect(self.domain)
        self.mesh_checkbox = QCheckBox("Trimesh")
        self.compute_button.clicked.connect(self.compute)
        self.contour_checkbox = QCheckBox("Contour")
        self.contour_button = QPushButton("Export contours")
        self.contour_button.clicked.connect(self.export_contours)
        self.contour_layer = QgsMapLayerComboBox()
        self.contour_layer.setFilters(QgsMapLayerProxyModel.MeshLayer)
        self.contour_min_box = QDoubleSpinBox()
        self.contour_max_box = QDoubleSpinBox()
        self.contour_step_box = QDoubleSpinBox()
        self.contour_min_box.setMinimum(-1000.0)
        self.contour_min_box.setMaximum(1000.0)
        self.contour_min_box.setValue(-5.0)
        self.contour_max_box.setMinimum(-1000.0)
        self.contour_max_box.setMaximum(1000.0)
        self.contour_max_box.setValue(5.0)
        self.contour_step_box.setSingleStep(0.1)
        self.contour_step_box.setValue(0.5)
        # Layout
        # External interpreter
        interpreter_groupbox = QGroupBox("Interpreter")
        interpreter_groupbox.setMaximumHeight(60)
        interpreter_layout = QVBoxLayout()
        interpreter_row = QHBoxLayout()
        interpreter_row.addWidget(self.interpreter_combo_box)
        interpreter_row.addWidget(self.interpreter_button)
        interpreter_row.addWidget(self.config_button)
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
        dataset_layout.addWidget(self.suppress_popup_checkbox)
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
        cellsize_row = QHBoxLayout()
        cellsize_row.addWidget(QLabel("Cellsize:"))
        cellsize_row.addWidget(self.cellsize_spin_box)
        # label.setFixedWidth(45)
        solution_grid.addLayout(cellsize_row, 0, 1)
        contour_row = QHBoxLayout()
        contour_row2 = QHBoxLayout()
        contour_row.addWidget(self.contour_checkbox)
        contour_row.addWidget(self.contour_min_box)
        contour_row.addWidget(QLabel("to"))
        contour_row.addWidget(self.contour_max_box)
        contour_row2.addWidget(QLabel("Increment:"))
        contour_row2.addWidget(self.contour_step_box)
        solution_grid.addLayout(contour_row, 1, 0)
        solution_grid.addLayout(contour_row2, 1, 1)
        solution_grid.addWidget(self.transient_combo_box, 2, 0)
        compute_row = QHBoxLayout()
        compute_row.addWidget(self.mesh_checkbox)
        compute_row.addWidget(self.compute_button)
        solution_grid.addLayout(compute_row, 2, 1)
        solution_grid.addWidget(self.contour_layer, 3, 0)
        solution_grid.addWidget(self.contour_button, 3, 1)
        solution_groupbox.setLayout(solution_grid)
        # Set for the dock widget
        layout = QVBoxLayout()
        layout.addWidget(interpreter_groupbox)
        layout.addWidget(extraction_group)
        layout.addWidget(dataset_groupbox)
        layout.addWidget(element_groupbox)
        layout.addWidget(solution_groupbox)
        self.setLayout(layout)
        self.on_transient_changed()

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

    def add_layer(
        self, layer: Any, destination: Any, renderer: Any = None, suppress: bool = None
    ) -> None:
        """
        Add a layer to the Layers Panel

        Parameters
        ----------
        layer:
            QGIS map layer, raster or vector layer
        destination:
            Legend group
        renderer:
            QGIS layer renderer, optional
        suppress:
            optional, bool. Default value is None.
            This controls whether attribute form popup is suppressed or not.
            Only relevant for vector (input) layers.
        """
        if layer is None:
            return
        add_to_legend = self.group is None
        maplayer = QgsProject.instance().addMapLayer(layer, add_to_legend)
        if suppress is not None:
            config = maplayer.editFormConfig()
            config.setSuppress(1)
            maplayer.setEditFormConfig(config)
        if renderer is not None:
            maplayer.setRenderer(renderer)
        if destination is not None:
            destination.addLayer(maplayer)

    def create_groups(self, name: str) -> None:
        root = QgsProject.instance().layerTreeRoot()
        self.group = root.addGroup(name)
        self.timml_group = self.group.addGroup(f"{name}-timml")
        self.ttim_group = self.group.addGroup(f"{name}-ttim")
        self.output_group = self.group.addGroup(f"{name}-output")

    def load_geopackage(self) -> None:
        """
        Load the layers of a GeoPackage into the Layers Panel
        """
        self.dataset_tree.clear()
        elements = load_elements_from_geopackage(self.path)
        for element in elements:
            print(element.timml_name)
            print(element.ttim_name)
            print(element.assoc_name)
            self.dataset_tree.add_element(element)
        path = self.path
        name = str(Path(path).stem)
        self.create_groups(name)
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
            (self.group, TIM_GROUP_ENTRY),
            (self.timml_group, TIMML_GROUP_ENTRY),
            (self.ttim_group, TTIM_GROUP_ENTRY),
            (self.output_group, TIMOUTPUT_GROUP_ENTRY),
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
            self.timml_group = self.group.findGroup(timml_group_name)
            self.ttim_group_name = self.group.findGroup(ttim_group_name)
            self.output_group_name = self.group.findGroup(output_group_name)
            if self.timml_group is None:
                self.timml_group = self.group.addGroup(f"{group_name}-timml")
            if self.ttim_group is None:
                self.ttim_group = self.group.addGroup(f"{group_name}-ttim")
            if self.output_group is None:
                self.output_group = self.group.addGroup(f"{group_name}-output")

        entry, success = project.readEntry(PROJECT_SCOPE, GPKG_LAYERS_ENTRY)
        if success:
            names = entry.split("␞")
        else:
            names = []

        self.dataset_tree.clear()
        self.dataset_line_edit.setText(path)
        self.toggle_element_buttons(True)

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
        layers = item.element.from_geopackage()
        suppress = self.suppress_popup_checkbox.isChecked()
        timml_layer, renderer = layers[0]
        self.add_layer(timml_layer, self.timml_group, renderer, suppress)
        self.add_layer(layers[1][0], self.ttim_group)
        self.add_layer(layers[2][0], self.timml_group)

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
        if element is None:  # dialog cancelled
            return
        # Write to geopackage
        element.write()
        # Add to QGIS
        self.add_layer(element.timml_layer, self.timml_group, element.renderer())
        self.add_layer(element.ttim_layer, self.ttim_group)
        self.add_layer(element.assoc_layer, self.timml_group)
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

    def set_cellsize_from_domain(self, ymax: float, ymin: float) -> None:
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
        transient = self.transient_combo_box.currentText() == "Transient"
        self.dataset_tree.on_transient_changed(transient)

    def contour_range(self) -> Tuple[float, float, float]:
        return (
            float(self.contour_min_box.value()),
            float(self.contour_max_box.value()),
            float(self.contour_step_box.value()),
        )

    def load_raster_result(self, path: Path, cellsize: float) -> None:
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
            self.add_layer(layer, self.output_group, renderer)

    def load_mesh_result(self, path: Path, cellsize: float) -> None:
        netcdf_path = str(
            (path.parent / f"{path.stem}-{cellsize}".replace(".", "_")).with_suffix(
                ".ugrid.nc"
            )
        )
        # Loop through layers first. If the path already exists as a layer source, remove it.
        # Otherwise QGIS will not the load the new result (this feels like a bug?).
        for layer in QgsProject.instance().mapLayers().values():
            if Path(netcdf_path) == Path(layer.source()):
                QgsProject.instance().removeMapLayer(layer.id())
        # Ensure the file is properly released by loading a dummy
        QgsMeshLayer(str(self.dummy_ugrid_path), "", "mdal")

        layer = QgsMeshLayer(str(netcdf_path), f"{path.stem}-{cellsize}", "mdal")
        indexes = layer.datasetGroupsIndexes()

        contour = self.contour_checkbox.isChecked()
        start, stop, step = self.contour_range()

        for index in indexes:
            qgs_index = QgsMeshDatasetIndex(group=index, dataset=0)
            name = layer.datasetGroupMetadata(qgs_index).name()
            if "head_layer_" not in name:
                continue
            index_layer = QgsMeshLayer(
                str(netcdf_path), f"{path.stem}-{cellsize}-{name}", "mdal"
            )
            renderer = index_layer.rendererSettings()
            renderer.setActiveScalarDatasetGroup(index)
            index_layer.setRendererSettings(renderer)
            self.add_layer(index_layer, self.output_group)

            if contour:
                contour_layer = mesh_contours(
                    layer=index_layer,
                    index=index,
                    name=name,
                    start=start,
                    stop=stop,
                    step=step,
                )
                self.add_layer(contour_layer, self.output_group)

    def export_contours(self) -> None:
        layer = self.contour_layer.currentLayer()
        renderer = layer.rendererSettings()
        index = renderer.activeScalarDatasetGroup()
        qgs_index = QgsMeshDatasetIndex(group=index, dataset=0)
        name = layer.datasetGroupMetadata(qgs_index).name()
        start, stop, step = self.contour_range()
        print("exporting_contours", start, stop, step)
        contour_layer = mesh_contours(
            layer=layer,
            index=index,
            name=name,
            start=start,
            stop=stop,
            step=step,
        )
        self.add_layer(contour_layer, self.output_group)

    def suppress_popup_changed(self):
        suppress = self.suppress_popup_checkbox.isChecked()
        for item in self.dataset_tree.items():
            layer = item.element.timml_layer
            if layer is not None:
                config = layer.editFormConfig()
                config.setSuppress(suppress)
                layer.setEditFormConfig(config)

    def configure_server(self) -> None:
        return

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
        mode = self.transient_combo_box.currentText().lower()
        as_trimesh = self.mesh_checkbox.isChecked()
        data = json.dumps(
            {
                "operation": "compute",
                "path": str(path),
                "cellsize": cellsize,
                "mode": mode,
                "active_elements": active_elements,
                "as_trimesh": as_trimesh,
            }
        )
        handler = self.server_handler
        received = handler.send(data)

        if received == "0":
            self.load_mesh_result(path, cellsize)
            # self.load_raster_result(path, cellsize)
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
