"""
This module forms the high level DockWidget.

It ensures the underlying widgets can talk to each other.  It also manages the
connection to the QGIS Layers Panel, and ensures there is a group for the Tim
layers there.
"""
import tempfile
from pathlib import Path
from typing import Any, Tuple

from PyQt5.QtWidgets import QTabWidget, QVBoxLayout, QWidget
from qgis.core import QgsMapLayer, QgsMeshDatasetIndex, QgsMeshLayer, QgsProject

from .dataset_tree_widget import DatasetWidget
from .dummy_ugrid import write_dummy_ugrid
from .elements_widget import ElementsWidget
from .extraction_widget import DataExtractionWidget
from .interpreter_widget import InterpreterWidget
from .processing import mesh_contours
from .solution_widget import SolutionWidget


class QgisTimmlWidget(QWidget):
    def __init__(self, parent, iface):
        super(QgisTimmlWidget, self).__init__(parent)

        self.iface = iface
        self.dummy_ugrid_path = Path(tempfile.mkdtemp()) / "qgistim-dummy-ugrid.nc"
        write_dummy_ugrid(self.dummy_ugrid_path)

        self.extraction_widget = DataExtractionWidget(self)
        self.dataset_widget = DatasetWidget(self)
        self.elements_widget = ElementsWidget(self)
        self.interpreter_widget = InterpreterWidget(self)
        self.solution_widget = SolutionWidget(self)

        # Connect this one outside of the widget
        self.extraction_widget.extract_button.clicked.connect(self.extract)

        # Layout
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.interpreter_widget)
        self.tabwidget = QTabWidget()
        self.layout.addWidget(self.tabwidget)
        self.tabwidget.addTab(self.extraction_widget, "Extract")
        self.tabwidget.addTab(self.dataset_widget, "GeoPackage")
        self.tabwidget.addTab(self.elements_widget, "Elements")
        self.tabwidget.addTab(self.solution_widget, "Solution")
        self.setLayout(self.layout)

    # Inter-widget communication
    # --------------------------
    def on_transient_changed(self, transient) -> None:
        self.dataset_widget.dataset_tree.on_transient_changed(transient)

    @property
    def path(self) -> str:
        return self.dataset_widget.path

    @property
    def crs(self) -> Any:
        """Returns coordinate reference system of current mapview"""
        return self.iface.mapCanvas().mapSettings().destinationCrs()

    def extract(self) -> None:
        interpreter = self.interpreter_combo_box.currentText()
        env_vars = self.server_handler.environmental_variables()
        self.extraction_widget.extract(interpreter, env_vars, self.server_handler)

    # QGIS layers
    # -----------
    def create_groups(self, name: str) -> None:
        """
        Create an empty legend group in the QGIS Layers Panel.
        """
        root = QgsProject.instance().layerTreeRoot()
        self.group = root.addGroup(name)
        self.timml_group = self.group.addGroup(f"{name}-timml")
        self.ttim_group = self.group.addGroup(f"{name}-ttim")
        self.output_group = self.group.addGroup(f"{name}-output")

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
            if on_top:
                destination.insertLayer(0, maplayer)
            else:
                destination.addLayer(maplayer)
        return maplayer

    def load_mesh_result(self, path: Path, cellsize: float, as_trimesh: bool) -> None:
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

            if not as_trimesh:
                scalar_settings = renderer.scalarSettings(index)
                # Set renderer to DataResamplingMethod.None = 0
                scalar_settings.setDataResamplingMethod(0)
                renderer.setScalarSettings(index, scalar_settings)

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
                self.add_layer(contour_layer, self.output_group, on_top=True)
