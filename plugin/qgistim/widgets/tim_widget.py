"""
This module forms the high level DockWidget.

It ensures the underlying widgets can talk to each other.  It also manages the
connection to the QGIS Layers Panel, and ensures there is a group for the Tim
layers there.
"""
from pathlib import Path
from typing import Any, Dict

from PyQt5.QtWidgets import QTabWidget, QTreeWidgetItem, QVBoxLayout, QWidget
from qgis.core import QgsMapLayer, QgsProject

from .compute_widget import ComputeWidget
from .dataset_widget import DatasetWidget
from .elements_widget import ElementsWidget
from .extraction_widget import DataExtractionWidget
from .interpreter_widget import InterpreterWidget

PYQT_DELETED_ERROR = "wrapped C/C++ object of type QgsLayerTreeGroup has been deleted"


class QgisTimmlWidget(QWidget):
    def __init__(self, parent, iface):
        super(QgisTimmlWidget, self).__init__(parent)

        self.iface = iface

        self.extraction_widget = DataExtractionWidget(self)
        self.dataset_widget = DatasetWidget(self)
        self.elements_widget = ElementsWidget(self)
        self.interpreter_widget = InterpreterWidget(self)
        self.compute_widget = ComputeWidget(self)

        # Layout
        self.layout = QVBoxLayout()
        self.tabwidget = QTabWidget()
        self.layout.addWidget(self.tabwidget)
        self.tabwidget.addTab(self.extraction_widget, "Extract")
        self.tabwidget.addTab(self.dataset_widget, "GeoPackage")
        self.tabwidget.addTab(self.elements_widget, "Elements")
        self.tabwidget.addTab(self.compute_widget, "Compute")
        self.layout.addWidget(self.interpreter_widget)
        self.setLayout(self.layout)

        # Default to the GeoPackage tab
        self.tabwidget.setCurrentIndex(1)

        # Set a default output path and link with GeoPackage path change.
        self.dataset_widget.dataset_line_edit.textChanged.connect(
            self.compute_widget.set_default_path
        )

        # QGIS Layers Panel groups
        self.group = None
        self.timml_group = None
        self.ttim_group = None
        self.output_group = None

    # Inter-widget communication
    # --------------------------
    def start_interpreter_task(self):
        return self.interpreter_widget.start_interpreter_task()

    def set_interpreter_interaction(self, value: bool) -> None:
        self.compute_widget.compute_button.setEnabled(value)
        self.dataset_widget.convert_button.setEnabled(value)
        self.extraction_widget.extract_button.setEnabled(value)

    def on_transient_changed(self) -> None:
        transient = self.compute_widget.transient
        self.dataset_widget.on_transient_changed(transient)

    @property
    def path(self) -> str:
        return self.dataset_widget.path

    @property
    def crs(self) -> Any:
        """Returns coordinate reference system of current mapview"""
        return self.iface.mapCanvas().mapSettings().destinationCrs()

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

    def execute(self, data: Dict[str, str]) -> str:
        return self.interpreter_widget.execute(data)

    def add_element(self, element: Any):
        self.dataset_widget.add_element(element)

    # QGIS layers
    # -----------
    def create_subgroup(self, name: str, part: str) -> None:
        try:
            value = self.group.addGroup(f"{name}-{part}")
            setattr(self, f"{part}_group", value)
        except RuntimeError as e:
            if e.args[0] == PYQT_DELETED_ERROR:
                # This means the main group has been deleted: recreate
                # everything.
                self.create_groups(name)

    def create_groups(self, name: str) -> None:
        """
        Create an empty legend group in the QGIS Layers Panel.
        """
        root = QgsProject.instance().layerTreeRoot()
        self.group = root.addGroup(name)
        self.create_subgroup(name, "timml")
        self.create_subgroup(name, "ttim")
        self.create_subgroup(name, "output")

    def add_to_group(self, maplayer: Any, destination: str, on_top: bool):
        """
        Try to add to a group; it might have been deleted. In that case, we add
        as many groups as required.
        """
        group = getattr(self, f"{destination}_group")
        try:
            if on_top:
                group.insertLayer(0, maplayer)
            else:
                group.addLayer(maplayer)
        except RuntimeError as e:
            if e.args[0] == PYQT_DELETED_ERROR:
                # Then re-create groups and try again
                name = str(Path(self.path).stem)
                self.create_subgroup(name, destination)
                self.add_to_group(maplayer, destination, on_top)
            else:
                raise e

    def add_layer(
        self,
        layer: Any,
        destination: Any,
        renderer: Any = None,
        suppress: bool = None,
        on_top: bool = False,
    ) -> QgsMapLayer:
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
        on_top: optional, bool. Default value is False.
            Whether to place the layer on top in the destination legend group.
            Handy for transparent layers such as contours.

        Returns
        -------
        maplayer: QgsMapLayer or None
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
            self.add_to_group(maplayer, destination, on_top)
        return maplayer
