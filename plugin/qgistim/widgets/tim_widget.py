"""
This module forms the high level DockWidget.

It ensures the underlying widgets can talk to each other. It also manages the
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
from qgis.core import QgsApplication, QgsEditFormConfig, QgsMapLayer, QgsProject
from qgistim.core.server_handler import ServerHandler
from qgistim.core.task import BaseServerTask
from qgistim.widgets.compute_widget import ComputeWidget
from qgistim.widgets.dataset_widget import DatasetWidget
from qgistim.widgets.elements_widget import ElementsWidget
from qgistim.widgets.version_dialog import VersionDialog

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

    def _create_group(self):
        """
        If a Group with the name already exists in the Layers Panel, remove the
        subgroups.

        If the name does not exist, create a new group.
        """
        self.group = self.root.findGroup(self.name)
        if self.group is not None:
            for child in self.group.children():
                self.subgroups[child.name()] = child
                child.removeAllChildren()
            return
        self.group = self.root.addGroup(self.name)
        return

    def create_subgroup(self, part: str) -> None:
        if self.subgroups.get(part) is not None:
            return
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
                # Search first
                group = self.root.findGroup(destination)
                if group is not None:
                    self.subgroups[destination] = group
                else:
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
            config.setSuppress(
                QgsEditFormConfig.SuppressOn
                if suppress
                else QgsEditFormConfig.SuppressDefault
            )
        if renderer is not None:
            maplayer.setRenderer(renderer)
        if labels is not None:
            layer.setLabeling(labels)
            layer.setLabelsEnabled(True)
        # Now add it to the Layers panel.
        self.add_to_group(maplayer, destination, on_top)
        return maplayer


class InputGroup(LayersPanelGroup):
    def create_group(self) -> None:
        self._create_group()
        self.create_subgroup("timml")
        self.create_subgroup("ttim")
        return


class OutputGroup(LayersPanelGroup):
    def create_group(self) -> None:
        self._create_group()
        self.create_subgroup("vector")
        self.create_subgroup("mesh")
        self.create_subgroup("raster")
        return


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

        self.dataset_widget = DatasetWidget(self)
        self.elements_widget = ElementsWidget(self)
        self.compute_widget = ComputeWidget(self)
        self.version_dialog = VersionDialog(self)

        self.config_button = QPushButton("Versions")
        self.config_button.clicked.connect(self.version_dialog.show)
        self.config_button.setIcon(QgsApplication.getThemeIcon("/mActionOptions.svg"))

        # Layout
        self.layout = QVBoxLayout()
        self.tabwidget = QTabWidget()
        self.layout.addWidget(self.tabwidget)
        self.tabwidget.addTab(self.dataset_widget, "Model Manager")
        self.tabwidget.addTab(self.elements_widget, "Elements")
        self.tabwidget.addTab(self.compute_widget, "Results")
        self.layout.addWidget(self.config_button, stretch=0, alignment=Qt.AlignRight)
        self.setLayout(self.layout)

        # Default to the GeoPackage tab
        self.tabwidget.setCurrentIndex(0)

        # Set a default output path and link with GeoPackage path change.
        self.dataset_widget.dataset_line_edit.textChanged.connect(
            self.compute_widget.set_default_path
        )
        # Clear the plugin when a different project is loaded.
        self.iface.projectRead.connect(self.reset)
        self.iface.newProjectCreated.connect(self.reset)

        # QGIS Layers Panel groups
        self.input_group = None
        self.output_group = None

        # Connect to the project saved signal.
        # Note that the project is a singleton instance, so it's always up to date.
        self.qgs_project = QgsProject.instance()
        return

    # Inter-widget communication
    # --------------------------
    def reset(self):
        self.input_group = None
        self.output_group = None
        self.shutdown_server()
        self.dataset_widget.reset()
        self.compute_widget.reset()
        return

    def start_interpreter_task(self) -> Union[StartTask, None]:
        if not self.server_handler.alive():
            interpreter = self.version_dialog.interpreter_combo_box.currentText()
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

    def enable_geopackage_buttons(self) -> None:
        """
        By default, a number of buttons are disabled until a GeoPackage is loaded.
        """
        self.compute_widget.domain_button.setEnabled(True)
        self.compute_widget.compute_button.setEnabled(True)
        self.dataset_widget.save_geopackage_button.setEnabled(True)
        self.dataset_widget.python_convert_button.setEnabled(True)
        self.dataset_widget.json_convert_button.setEnabled(True)
        self.elements_widget.enable_element_buttons()

    def set_interpreter_interaction(self, value: bool) -> None:
        """
        Disable interaction with the external interpreter. Some task may take a
        minute or so to run. No additional tasks should be scheduled in the
        mean time.
        """
        self.compute_widget.compute_button.setEnabled(value)
        self.dataset_widget.python_convert_button.setEnabled(value)
        self.dataset_widget.json_convert_button.setEnabled(value)
        return

    def shutdown_server(self) -> None:
        if self.server_handler.process is not None:
            self.server_handler.kill()
        return

    @property
    def path(self) -> str:
        return self.dataset_widget.path

    @property
    def crs(self) -> Any:
        return self.dataset_widget.model_crs

    @property
    def transient(self) -> bool:
        return self.compute_widget.transient

    def set_spacing_from_domain(self, ymax: float, ymin: float) -> None:
        self.compute_widget.set_spacing_from_domain(ymax, ymin)

    def active_elements(self) -> Dict[str, bool]:
        return self.dataset_widget.active_elements()

    def domain_item(self) -> QTreeWidgetItem:
        return self.dataset_widget.domain_item()

    def selection_names(self):
        return self.dataset_widget.selection_names()

    def add_element(self, element: Any):
        suppress = self.dataset_widget.suppress_popup_checkbox.isChecked()
        self.dataset_widget.add_element(element)
        self.input_group.add_layer(
            element.timml_layer,
            "timml",
            renderer=element.renderer(),
            suppress=suppress,
        )
        self.input_group.add_layer(element.ttim_layer, "ttim")
        self.input_group.add_layer(element.assoc_layer, "timml")

    # QGIS layers
    # -----------
    def create_input_group(self, name: str) -> None:
        root = self.qgs_project.layerTreeRoot()
        self.input_group = InputGroup(root, name)
        return

    def create_output_group(self, name: str) -> None:
        root = self.qgs_project.layerTreeRoot()
        self.output_group = OutputGroup(root, name)
        return
