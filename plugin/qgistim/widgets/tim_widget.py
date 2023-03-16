"""
This module forms the high level DockWidget.

It ensures the underlying widgets can talk to each other.  It also manages the
connection to the QGIS Layers Panel, and ensures there is a group for the Tim
layers there.
"""
from typing import Any, Dict, Union

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QPushButton,
    QTabWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qgis.core import Qgis, QgsApplication, QgsMapLayer, QgsProject, QgsUnitTypes
from qgistim.core.server_handler import ServerHandler
from qgistim.core.task import BaseServerTask
from qgistim.widgets.compute_widget import ComputeWidget
from qgistim.widgets.dataset_widget import DatasetWidget
from qgistim.widgets.elements_widget import ElementsWidget
from qgistim.widgets.extraction_widget import DataExtractionWidget
from qgistim.widgets.options_dialog import OptionsDialog

PYQT_DELETED_ERROR = "wrapped C/C++ object of type QgsLayerTreeGroup has been deleted"


class LayersPanelGroup:
    def __init__(
        self,
        root,
        name: str,
    ):
        self.name = name
        self.root = root
        self.subgroups = {}
        self.create_group()

    def create_group(self):
        self.group = self.root.addGroup(self.name)
        return

    def create_subgroup(self, part: str) -> None:
        try:
            value = self.group.addGroup(part)
            self.subgroups[part] = value
        except RuntimeError as e:
            if e.args[0] == PYQT_DELETED_ERROR:
                # This means the main group has been deleted. Create the group
                # again.
                self.create_group()
                # And try again.
                self.create_subgroup(part)
            else:
                raise e
        return

    def add_to_group(
        self,
        maplayer,
        destination: str,
        on_top: bool,
    ) -> None:
        # The group might not exist yet: create it.
        group = self.subgroups.get(destination)
        if group is None:
            self.create_subgroup(destination)
            group = self.subgroups[destination]

        # Or it might've existed, but the user deleted it from the Layers
        # Panel.
        try:
            if on_top:
                group.insertLayer(0, maplayer)
            else:
                group.addLayer(maplayer)
        except RuntimeError as e:
            if e.args[0] == PYQT_DELETED_ERROR:
                # Then re-create groups and try again
                self.create_subgroup(destination)
                self.add_to_group(maplayer, destination, on_top)
            else:
                raise e
        return

    def add_layer(
        self,
        layer: Any,
        destination: Any,
        renderer: Any = None,
        suppress: bool = None,
        on_top: bool = False,
        labels: Any = None,
    ) -> QgsMapLayer:
        """
        Add a layer to the Layers Panel

        Parameters
        ----------
        layer:
            QGIS map layer, raster or vector layer. May be None, in which case
            nothing is done (useful for optional ttim and associated layers).
        destination: str
            Legend group
        renderer:
            QGIS layer renderer, optional
        suppress:
            optional, bool. Default value is None.
            This controls whether attribute form popup is suppressed or not.
            Only relevant for vector (input) layers.
        on_top: optional, bool. Default value is False.
            Whether to place the layer on top in the destination legend group.
            Handy for transparent layers such as contours.
        labels: QgsVectorLayerSimpleLabeling, optional, default value is None
            Preset labeling for e.g. observations and contours.

        Returns
        -------
        maplayer: QgsMapLayer or None
        """
        if layer is None:
            return

        # second argument False: Do not add the maplayer yet to the LayerPanel
        maplayer = QgsProject.instance().addMapLayer(layer, False)
        if suppress is not None:
            config = maplayer.editFormConfig()
            config.setSuppress(1)
            maplayer.setEditFormConfig(config)
        if renderer is not None:
            maplayer.setRenderer(renderer)
        if labels is not None:
            layer.setLabeling(labels)
            layer.setLabelsEnabled(True)
        # Now add it to the Layers panel.
        self.add_to_group(maplayer, destination, on_top)
        return maplayer


class StartTask(BaseServerTask):
    @property
    def task_description(self):
        return "starting server"

    def run(self):
        try:
            self.response = self.parent.server_handler.start_server(
                self.data["interpreter"]
            )
            if not self.response["success"]:
                return False
            return True
        except Exception as exception:
            self.exception = exception
            return False


class QgisTimWidget(QWidget):
    def __init__(self, parent, iface):
        super().__init__(parent)

        self.iface = iface
        self.message_bar = self.iface.messageBar()
        self.server_handler = ServerHandler()

        self.extraction_widget = DataExtractionWidget(self)
        self.dataset_widget = DatasetWidget(self)
        self.elements_widget = ElementsWidget(self)
        self.compute_widget = ComputeWidget(self)
        self.options_dialog = OptionsDialog(self)

        self.config_button = QPushButton("Options")
        self.config_button.clicked.connect(self.options_dialog.show)
        self.config_button.setIcon(QgsApplication.getThemeIcon("/mActionOptions.svg"))

        # Layout
        self.layout = QVBoxLayout()
        self.tabwidget = QTabWidget()
        self.layout.addWidget(self.tabwidget)
        self.tabwidget.addTab(self.dataset_widget, "GeoPackage")
        self.tabwidget.addTab(self.elements_widget, "Elements")
        self.tabwidget.addTab(self.compute_widget, "Compute")
        self.tabwidget.addTab(self.extraction_widget, "Extract")
        self.layout.addWidget(self.config_button, stretch=0, alignment=Qt.AlignRight)
        self.setLayout(self.layout)

        # Default to the GeoPackage tab
        self.tabwidget.setCurrentIndex(0)

        # Set a default output path and link with GeoPackage path change.
        self.dataset_widget.dataset_line_edit.textChanged.connect(
            self.compute_widget.set_default_path
        )

        # QGIS Layers Panel groups
        self.input_group = None
        self.output_group = None
        return

    # Inter-widget communication
    # --------------------------
    def start_interpreter_task(self) -> Union[StartTask, None]:
        if not self.server_handler.alive():
            interpreter = self.options_dialog.interpreter_combo_box.currentText()
            start_task = StartTask(self, {"interpreter": interpreter}, self.message_bar)
            return start_task
        else:
            return None

    def execute(self, data: Dict[str, str]) -> Dict[str, Any]:
        """
        Execute a command, and check whether it executed succesfully.
        """
        response = self.server_handler.send(data)
        return response

    def set_interpreter_interaction(self, value: bool) -> None:
        self.compute_widget.compute_button.setEnabled(value)
        self.dataset_widget.convert_button.setEnabled(value)
        self.extraction_widget.extract_button.setEnabled(value)
        return

    def shutdown_server(self) -> None:
        if self.server_handler.process is not None:
            self.server_handler.kill()
        return

    def on_transient_changed(self) -> None:
        transient = self.compute_widget.transient
        self.dataset_widget.on_transient_changed(transient)
        return

    @property
    def path(self) -> str:
        return self.dataset_widget.path

    @property
    def crs(self) -> Any:
        """
        Returns coordinate reference system of current mapview

        Returns None if the crs does not have meters as its units.
        """
        crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        if crs.mapUnits() not in (
            QgsUnitTypes.DistanceMeters,
            QgsUnitTypes.DistanceFeet,
        ):
            msg = "Project Coordinate Reference System map units are not meters or feet"
            self.message_bar.pushMessage("Error", msg, level=Qgis.Critical)
            raise ValueError(msg)
        return crs

    @property
    def transient(self) -> bool:
        return self.compute_widget.transient

    def set_cellsize_from_domain(self, ymax: float, ymin: float) -> None:
        self.compute_widget.set_cellsize_from_domain(ymax, ymin)

    def toggle_element_buttons(self, state: bool) -> None:
        self.elements_widget.toggle_element_buttons(state)

    def active_elements(self) -> Dict[str, bool]:
        return self.dataset_widget.active_elements()

    def domain_item(self) -> QTreeWidgetItem:
        return self.dataset_widget.domain_item()

    def selection_names(self):
        return self.dataset_widget.selection_names()

    def add_element(self, element: Any):
        self.dataset_widget.add_element(element)
        self.input_group.add_layer(element.timml_layer, "timml", element.renderer)
        self.input_group.add_layer(element.ttim_layer, "ttim")
        self.input_group.add_layer(element.assoc_layer, "timml")

    # QGIS layers
    # -----------
    def create_input_group(self, name: str):
        root = QgsProject.instance().layerTreeRoot()
        self.input_group = LayersPanelGroup(root, f"{name} input")
        self.input_group.create_subgroup("timml")
        self.input_group.create_subgroup("ttim")
        return

    def create_output_group(self, name: str):
        root = QgsProject.instance().layerTreeRoot()
        self.output_group = LayersPanelGroup(root, f"{name} output")
        # Pre-create the groups here to make sure the vector group ends up on top.
        # Apparently moving it destroys the group?
        self.output_group.create_subgroup("vector")
        self.output_group.create_subgroup("mesh")
        self.output_group.create_subgroup("raster")
        return
