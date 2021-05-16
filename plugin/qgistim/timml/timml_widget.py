"""
This module contains the logic connecting the buttons of the plugin dockwidget
to the actual functionality.
"""
import json
import os
from functools import partial
from pathlib import Path
from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qgis.core import (
    Qgis,
    QgsBrowserModel,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)
from qgis.gui import QgsBrowserGuiModel, QgsBrowserTreeView
from qgis.PyQt import QtGui, QtWidgets, uic
from qgis.PyQt.QtCore import QVariant, pyqtSignal
from qgistim import geopackage, layer_styling
from qgistim.server_handler import ServerHandler

from .extraction_widget import DataExtractionWidget
from .timml_elements import ELEMENT_SPEC, create_timml_layer


class QgisTimmlWidget(QWidget):
    def __init__(self, parent, iface):
        super(QgisTimmlWidget, self).__init__(parent)
        self.iface = iface
        # Data extraction
        self.extraction_widget = DataExtractionWidget(iface)
        self.extraction_widget.extract_button.clicked.connect(self.extract)
        # Dataset management
        self.dataset_line_edit = QLineEdit()
        self.new_geopackage_button = QPushButton("New")
        self.open_geopackage_button = QPushButton("Open")
        self.remove_button = QPushButton("Remove Layer")
        self.dataset_line_edit.setEnabled(False)  # Just used as a viewing port
        self.new_geopackage_button.clicked.connect(self.new_geopackage)
        self.open_geopackage_button.clicked.connect(self.open_geopackage)
        self.remove_button.clicked.connect(self.remove_geopackage_layer)
        self.dataset_tree = DatasetTreeWidget()
        self.dataset_tree.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        # Elements
        self.element_buttons = {}
        for element in ELEMENT_SPEC:
            # Skip associated table
            if "Properties" in element:
                continue
            button = QPushButton(element)
            button.clicked.connect(partial(self.timml_element, elementtype=element))
            self.element_buttons[element] = button
        self.toggle_element_buttons(False)  # no dataset loaded yet
        # Interpreter combo box
        self.server_handler = ServerHandler()  # To connect with TimServer
        self.interpreter_combo_box = QComboBox()
        self.interpreter_combo_box.insertItems(0, self.server_handler.interpreters())
        self.interpreter_button = QPushButton("Start")
        self.interpreter_button.clicked.connect(self.start_server)
        # Solution
        self.domain_button = QPushButton("Domain")
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
        extraction_group.setMaximumHeight(80)
        extraction_layout = QVBoxLayout()
        extraction_layout.addWidget(self.extraction_widget)
        extraction_group.setLayout(extraction_layout)
        # Dataset
        dataset_groupbox = QGroupBox("Dataset")
        dataset_layout = QVBoxLayout()
        dataset_row = QHBoxLayout()
        dataset_row.addWidget(QLabel("Dataset:"))
        dataset_row.addWidget(self.dataset_line_edit)
        dataset_row.addWidget(self.open_geopackage_button)
        dataset_row.addWidget(self.new_geopackage_button)
        dataset_layout.addLayout(dataset_row)
        dataset_layout.addWidget(self.dataset_tree)
        dataset_layout.addWidget(self.remove_button)
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
        solution_groupbox = QGroupBox("Solution")
        solution_groupbox.setMaximumHeight(150)
        solution_grid = QGridLayout()
        solution_grid.addWidget(self.domain_button, 0, 0)
        label = QLabel("Cellsize:")
        label.setFixedWidth(45)
        solution_grid.addWidget(label, 0, 1)
        solution_grid.addWidget(self.cellsize_spin_box, 0, 2)
        solution_grid.addWidget(self.compute_button, 1, 0)
        vertical_spacer = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
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

    def closeEvent(self, event: Any) -> None:
        """
        Closes the plugin
        """
        self.server_handler.kill()
        self.closingPlugin.emit()
        event.accept()

    @property
    def path(self) -> str:
        """Returns currently active path to GeoPackage"""
        return self.dataset_line_edit.text()

    @property
    def crs(self) -> Any:
        """Returns coordinate reference system of current mapview"""
        return self.iface.mapCanvas().mapSettings().destinationCrs()

    def add_layer(
        self, layer: Any, renderer: Any = None, to_dataset_tree: bool = True
    ) -> None:
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
        if to_dataset_tree:
            self.dataset_tree.add_layer(layer)

    def add_geopackage_layers(self, path: str) -> None:
        """
        Add all the layers from a geopackage to the Layers Panel.

        Parameters
        ----------
        path: str
            Path to the GeoPackage
        """
        # Adapted from PyQGIS cheatsheet:
        # https://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/cheat_sheet.html#layers
        for layername in geopackage.layers(self.path):
            layer = QgsVectorLayer(f"{path}|layername={layername}", layername)
            if layername == "timml Domain":
                renderer = layer_styling.domain_renderer()
                bbox = layer.getFeature(1).geometry().boundingBox()
                ymax = bbox.yMaximum()
                ymin = bbox.yMinimum()
                self.set_cellsize_from_domain(ymax, ymin)
            elif "timml Circular Area Sink" in layername:
                renderer = layer_styling.circareasink_renderer()
            else:
                renderer = None
            self.add_layer(layer, renderer)

    def load_geopackage(self) -> None:
        """
        Load the layers of a GeoPackage into the Layers Panel
        """
        path = self.path
        root = QgsProject.instance().layerTreeRoot()
        self.group = root.addGroup(str(Path(path).stem))
        self.add_geopackage_layers(path)

    def new_geopackage(self) -> None:
        """
        Create a new GeoPackage file, and set it as the active dataset.
        """
        path, _ = QFileDialog.getSaveFileName(self, "Select file", "", "*.gpkg")
        if path != "":  # Empty string in case of cancel button press
            self.dataset_line_edit.setText(path)
            self.new_timml_model()
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

    def new_timml_model(self) -> None:
        """
        Create a new TimML model; writes a new GeoPackage file.
        """
        # Write the aquifer properties
        self.dataset_tree.clear()
        layer = create_timml_layer("Aquifer", "", self.crs)
        _ = geopackage.write_layer(self.path, layer, "timml Aquifer", newfile=True)

    def remove_geopackage_layer(self) -> None:
        selection = self.dataset_tree.selectedItems()
        qgs_instance = QgsProject.instance()
        for item in selection:
            layer = item.layer
            qgs_instance.removeMapLayer(layer.id())
            geopackage.remove_layer(self.path, item.text(0))
            index = self.dataset_tree.indexOfTopLevelItem(item)
            self.dataset_tree.takeTopLevelItem(index)

    def timml_element(self, elementtype: str) -> None:
        """
        Create a new TimML element input layer.

        Parameters
        ----------
        elementtype: str
            Name of the element type. Used to search for the required geometry
            and attributes (columns).

        """
        if elementtype == "Circular Area Sink":
            self.circ_area_sink()
        else:
            dialog = NameDialog()
            dialog.show()
            ok = dialog.exec_()
            if ok:
                layername = dialog.name_line_edit.text()
                if elementtype in ("Polygon Inhomogeneity", "Building Pit"):
                    self.timml_polygon_element(elementtype, layername)
                else:
                    layer = create_timml_layer(elementtype, layername, self.crs)
                    written_layer = geopackage.write_layer(
                        self.path, layer, f"timml {elementtype}:{layername}"
                    )
                    self.add_layer(written_layer)

    def timml_polygon_element(self, elementtype: str, layername: str) -> None:
        """
        Create a new TimML element input layer, which stores geometry and
        properties in two separate tables.

        Parameters
        ----------
        elementtype: str
            Name of the element type. Used to search for the required geometry
            and attributes (columns).

        """
        properties_elementtype = f"{elementtype} Properties"
        geometry_layer = create_timml_layer(elementtype, layername, self.crs)
        property_layer = create_timml_layer(properties_elementtype, layername, self.crs)
        written_geometry = geopackage.write_layer(
            self.path, geometry_layer, f"timml {elementtype}:{layername}"
        )
        written_property = geopackage.write_layer(
            self.path,
            property_layer,
            f"timml {properties_elementtype}:{layername}",
        )
        self.add_layer(written_geometry)
        self.add_layer(written_property)

    def domain(self) -> None:
        """
        Write the current viewing extent as rectangle to the GeoPackage.
        """
        layer = QgsVectorLayer("polygon", "timml Domain", "memory", crs=self.crs)
        provider = layer.dataProvider()
        extent = self.iface.mapCanvas().extent()
        xmin = extent.xMinimum()
        ymin = extent.yMinimum()
        xmax = extent.xMaximum()
        ymax = extent.yMaximum()
        points = [
            QgsPointXY(xmin, ymax),
            QgsPointXY(xmax, ymax),
            QgsPointXY(xmax, ymin),
            QgsPointXY(xmin, ymin),
        ]
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPolygonXY([points]))
        provider.addFeatures([feature])
        written_layer = geopackage.write_layer(self.path, layer, "timml Domain")

        # Remove the previous domain specification
        for existing_layer in QgsProject.instance().mapLayers().values():
            if Path(existing_layer.source()) == Path(
                str(self.path) + "|layername=timml Domain"
            ):
                QgsProject.instance().removeMapLayer(existing_layer.id())

        renderer = layer_styling.domain_renderer()
        self.add_layer(written_layer, renderer, to_dataset_tree=False)
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

    def circ_area_sink(self) -> None:
        """
        Create a circular area sink layer.

        A circle with a specified radius cannot be directly created. This
        creates a "circle-like" geometry instead, by buffering a point and the
        center point of view.

        The radius can later be extracted again by computing the distance from a
        vertex to the midpoint.
        """
        dialog = RadiusDialog()
        dialog.show()
        ok = dialog.exec_()
        if ok:
            elementtype = "Circular Area Sink"
            layername = dialog.name_line_edit.text()
            radius = float(dialog.radius_line_edit.text())
            layer = create_timml_layer(
                elementtype,
                layername,
                self.crs,
            )
            provider = layer.dataProvider()
            feature = QgsFeature()
            center = self.iface.mapCanvas().center()
            feature.setGeometry(QgsGeometry.fromPointXY(center).buffer(radius, 5))
            provider.addFeatures([feature])
            layer.updateFields()
            written_layer = geopackage.write_layer(
                self.path, layer, f"timml {elementtype}:{layername}"
            )
            renderer = layer_styling.circareasink_renderer()
            self.add_layer(written_layer, renderer)

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
                netcdf_path, f"{path.stem}-{band - 1}-{cellsize}", "gdal"
            )
            renderer = layer_styling.pseudocolor_renderer(
                layer, band, colormap="Magma", nclass=10
            )
            self.add_layer(layer, renderer, to_dataset_tree=False)

    def start_server(self) -> None:
        """Start an external interpreter running gistim"""
        interpreter = self.interpreter_combo_box.currentText()
        self.server_handler.start_server(interpreter)

    def compute(self) -> None:
        """
        Run a TimML computation with the current state of the currently active
        GeoPackage dataset.
        """
        cellsize = self.cellsize_spin_box.value()
        path = Path(self.path).absolute()
        data = json.dumps(
            {"operation": "compute", "path": str(path), "cellsize": cellsize}
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
        if self.server_handler.PORT is not None:
            handler = self.server_handler
        else:
            handler = None
        interpreter = self.interpreter_combo_box.currentText()
        env_vars = self.server_handler.environmental_variables()
        self.extraction_widget.extract(interpreter, env_vars, handler)


class DatasetTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super(DatasetTreeWidget, self).__init__(parent)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setHeaderHidden(True)
        self.setSortingEnabled(True)

    def add_layer(self, layer):
        item = QTreeWidgetItem([layer.name()])
        item.layer = layer
        self.addTopLevelItem(item)


class NameDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(NameDialog, self).__init__(parent)
        self.name_line_edit = QLineEdit()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        first_row = QHBoxLayout()
        first_row.addWidget(QLabel("Layer name"))
        first_row.addWidget(self.name_line_edit)
        second_row = QHBoxLayout()
        second_row.addStretch()
        second_row.addWidget(self.ok_button)
        second_row.addWidget(self.cancel_button)
        layout = QVBoxLayout()
        layout.addLayout(first_row)
        layout.addLayout(second_row)
        self.setLayout(layout)


class RadiusDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(RadiusDialog, self).__init__(parent)
        self.name_line_edit = QLineEdit()
        self.radius_line_edit = QLineEdit()
        self.radius_line_edit.setValidator(QDoubleValidator())
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        first_row = QHBoxLayout()
        first_row.addWidget(QLabel("Layer name"))
        first_row.addWidget(self.name_line_edit)
        second_row = QHBoxLayout()
        second_row.addWidget(QLabel("Radius"))
        first_row.addWidget(self.radius_line_edit)
        third_row = QHBoxLayout()
        third_row.addStretch()
        third_row.addWidget(self.ok_button)
        third_row.addWidget(self.cancel_button)
        layout = QVBoxLayout()
        layout.addLayout(first_row)
        layout.addLayout(second_row)
        layout.addLayout(third_row)
        self.setLayout(layout)
