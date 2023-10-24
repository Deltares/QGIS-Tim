import datetime
import tempfile
from pathlib import Path
from typing import Tuple, Union

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from qgis.core import (
    QgsApplication,
    QgsMapLayerProxyModel,
    QgsMeshDatasetIndex,
    QgsMeshLayer,
    QgsProject,
    QgsRasterLayer,
    QgsTask,
    QgsVectorLayer,
    QgsVectorLayerTemporalProperties,
)
from qgis.gui import QgsMapLayerComboBox
from qgistim.core import geopackage, layer_styling
from qgistim.core.dummy_ugrid import write_dummy_ugrid
from qgistim.core.elements import ELEMENTS, parse_name
from qgistim.core.processing import mesh_contours
from qgistim.core.task import BaseServerTask


class ComputeTask(BaseServerTask):
    @property
    def task_description(self):
        return "Tim computation"

    def run(self):
        self.starttime = datetime.datetime.now()
        return super().run()

    def success_message(self):
        runtime = datetime.datetime.now() - self.starttime
        hours, remainder = divmod(runtime.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        return (
            f"Tim computation completed in: {hours} hours, {minutes} minutes, "
            f"and {round(seconds, 2)} seconds."
        )

    def finished(self, result):
        self.parent.set_interpreter_interaction(True)
        if result:
            self.push_success_message()

            self.parent.clear_outdated_output(self.data["path"])
            # Load whatever data is available in the geopackage.
            if self.data["head_observations"] or self.data["discharge"]: 
                self.parent.load_vector_result(self.data["path"])

            if self.data["mesh"]:
                self.parent.load_mesh_result(
                    self.data["path"], self.data["contours"]
                )
            if self.data["raster"]:
                self.parent.load_raster_result(self.data["path"])

        else:
            self.push_failure_message()
        return


class ComputeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.compute_task = None
        self.start_task = None
        self.parent = parent

        self.dummy_ugrid_path = Path(tempfile.mkdtemp()) / "qgistim-dummy-ugrid.nc"
        write_dummy_ugrid(self.dummy_ugrid_path)

        self.domain_button = QPushButton("Set to current extent")
        self.compute_button = QPushButton("Compute")
        self.compute_button.clicked.connect(self.compute)

        self.mesh_checkbox = QCheckBox("Mesh")
        self.raster_checkbox = QCheckBox("Raster")
        self.contours_checkbox = QCheckBox("Contours")
        self.head_observations_checkbox = QCheckBox("Head Observations")
        self.discharge_checkbox = QCheckBox("Discharge")
        self.discharge_observations_checkbox = QCheckBox("Discharge Observations")

        self.cellsize_spin_box = QDoubleSpinBox()
        self.cellsize_spin_box.setMinimum(0.0)
        self.cellsize_spin_box.setMaximum(10_000.0)
        self.cellsize_spin_box.setSingleStep(1.0)
        self.cellsize_spin_box.setValue(25.0)
        self.domain_button.clicked.connect(self.domain)
        # By default: all output
        self.mesh_checkbox.setChecked(True)
        self.raster_checkbox.setChecked(False)
        self.contours_checkbox.setChecked(False)
        self.head_observations_checkbox.setChecked(True)
        self.discharge_checkbox.setChecked(False)

        self.mesh_checkbox.toggled.connect(self.contours_checkbox.setEnabled)
        self.mesh_checkbox.toggled.connect(
            lambda checked: not checked and self.contours_checkbox.setChecked(False)
        )

        # self.mesh_checkbox = QCheckBox("Trimesh")
        self.output_line_edit = QLineEdit()
        self.output_button = QPushButton("Set path as ...")
        self.output_button.clicked.connect(self.set_output_path)
        self.contour_button = QPushButton("Redraw contours")
        self.contour_button.clicked.connect(self.redraw_contours)
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
        layout = QVBoxLayout()
        domain_group = QGroupBox("Domain")
        result_group = QGroupBox("Output")
        contour_group = QGroupBox("Contour")
        domain_layout = QVBoxLayout()
        result_layout = QVBoxLayout()
        contour_layout = QVBoxLayout()
        domain_group.setLayout(domain_layout)
        result_group.setLayout(result_layout)
        contour_group.setLayout(contour_layout)

        domain_row = QHBoxLayout()
        domain_row.addWidget(QLabel("Grid spacing"))
        domain_row.addWidget(self.cellsize_spin_box)
        domain_layout.addWidget(self.domain_button)
        domain_layout.addLayout(domain_row)

        output_row = QHBoxLayout()
        output_row.addWidget(self.output_line_edit)
        output_row.addWidget(self.output_button)

        button_row = QHBoxLayout()
        button_row.addWidget(self.compute_button)
        result_layout.addLayout(output_row)

        result_layout.addWidget(self.mesh_checkbox)
        result_layout.addWidget(self.raster_checkbox)
        result_layout.addWidget(self.contours_checkbox)
        result_layout.addWidget(self.head_observations_checkbox)
        result_layout.addWidget(self.discharge_checkbox)

        result_layout.addLayout(button_row)

        contour_row1 = QHBoxLayout()
        to_label = QLabel("to")
        to_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        step_label = QLabel("Step")
        step_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        contour_row1.addWidget(self.contour_min_box)
        contour_row1.addWidget(to_label)
        contour_row1.addWidget(self.contour_max_box)
        contour_row1.addWidget(step_label)
        contour_row1.addWidget(self.contour_step_box)
        contour_row2 = QHBoxLayout()
        contour_row2.addWidget(self.contour_layer)
        contour_row2.addWidget(self.contour_button)
        contour_layout.addLayout(contour_row1)
        contour_layout.addLayout(contour_row2)

        layout.addWidget(domain_group)
        layout.addWidget(result_group)
        layout.addWidget(contour_group)
        layout.addStretch()
        self.setLayout(layout)

    def reset(self):
        self.cellsize_spin_box.setValue(25.0)
        self.transient_combo_box.setCurrentIndex(0)
        self.output_line_edit.setText("")
        self.raster_checkbox.setCheckState(False)
        self.mesh_checkbox.setCheckState(True)
        self.contours_checkbox.setCheckState(False)
        self.head_observations_checkbox.setCheckState(True)
        self.discharge_checkbox.setCheckState(False)
        self.contour_min_box.setValue(-5.0)
        self.contour_max_box.setValue(5.0)
        self.contour_step_box.setValue(0.5)
        return

    def set_interpreter_interaction(self, value: bool):
        self.parent.set_interpreter_interaction(value)

    def shutdown_server(self):
        self.parent.shutdown_server()

    def contour_range(self) -> Tuple[float, float, float]:
        return (
            float(self.contour_min_box.value()),
            float(self.contour_max_box.value()),
            float(self.contour_step_box.value()),
        )

    def add_contour_layer(self, layer) -> None:
        # Labeling
        labels = layer_styling.number_labels("head")
        # Renderer: simple black lines
        renderer = layer_styling.contour_renderer()
        self.parent.output_group.add_layer(
            layer, "vector", renderer=renderer, on_top=True, labels=labels
        )

    @property
    def output_path(self) -> str:
        return self.output_line_edit.text()

    def clear_outdated_output(self, path: str) -> None:
        path = Path(path)
        gpkg_path = path.with_suffix(".output.gpkg")
        netcdf_paths = (path.with_suffix(".nc"), path.with_suffix(".ugrid.nc"))
        for layer in QgsProject.instance().mapLayers().values():
            source = layer.source()
            if (
                Path(source) in netcdf_paths
                or Path(source.partition("|")[0]) == gpkg_path
            ):
                QgsProject.instance().removeMapLayer(layer.id())
        return

    def redraw_contours(self) -> None:
        path = Path(self.output_path)
        layer = self.contour_layer.currentLayer()
        renderer = layer.rendererSettings()
        index = renderer.activeScalarDatasetGroup()
        qgs_index = QgsMeshDatasetIndex(group=index, dataset=0)
        name = layer.datasetGroupMetadata(qgs_index).name()
        contours_name = f"{path.stem}-contours-{name}"
        start, stop, step = self.contour_range()
        gpkg_path = str(path.with_suffix(".output.gpkg"))

        layer = mesh_contours(
            gpkg_path=gpkg_path,
            layer=layer,
            index=index,
            name=contours_name,
            start=start,
            stop=stop,
            step=step,
        )

        # Re-use layer if it already exists. Otherwise add a new layer.
        project_layers = {
            layer.name(): layer for layer in QgsProject.instance().mapLayers().values()
        }
        project_layer = project_layers.get(contours_name)
        if (
            (project_layer is not None)
            and (project_layer.name() == layer.name())
            and (project_layer.source() == layer.source())
        ):
            project_layer.reload()
        else:
            self.add_contour_layer(layer)
        return

    def set_output_path(self) -> None:
        current = self.output_path
        path, _ = QFileDialog.getSaveFileName(
            self, "Save output as...", current, "*.gpkg"
        )

        if path != "":  # Empty string in case of cancel button press
            self.output_line_edit.setText(str(Path(path).with_suffix("")))
            # Note: Qt does pretty good validity checking of the Path in the
            # Dialog, there is no real need to validate path here.

    def set_default_path(self, text: str) -> None:
        """
        Called when different dataset path is chosen.
        """
        if text is None:
            return
        path = Path(text)
        self.output_line_edit.setText(str(path.parent / path.stem))

    def compute(self) -> None:
        """
        Run a TimML computation with the current state of the currently active
        GeoPackage dataset.
        """
        cellsize = self.cellsize_spin_box.value()
        transient = self.parent.dataset_widget.transient
        output_options = {
            "raster": self.raster_checkbox.isChecked(),
            "mesh": self.mesh_checkbox.isChecked(),
            "contours": self.contours_checkbox.isChecked(),
            "head_observations": self.head_observations_checkbox.isChecked(),
            "discharge": self.discharge_checkbox.isChecked(),
        }

        path = Path(self.output_path).absolute().with_suffix(".json")
        invalid_input = self.parent.dataset_widget.convert_to_json(
            path, cellsize=cellsize, transient=transient, output_options=output_options
        )
        # Early return in case some problems are found.
        if invalid_input:
            return

        data = {
            "operation": "compute",
            "path": str(path),
            "transient": transient,
            **output_options,
        }
        # https://gis.stackexchange.com/questions/296175/issues-with-qgstask-and-task-manager
        # It seems the task goes awry when not associated with a Python object!
        # -- we just assign it to the widget here.
        #
        # To run the tasks without the QGIS task manager:
        # result = task.run()
        # task.finished(result)

        # Remove the output layers from QGIS, otherwise they cannot be overwritten.
        gpkg_path = str(path)
        for layer in QgsProject.instance().mapLayers().values():
            if Path(gpkg_path) == Path(layer.source()):
                QgsProject.instance().removeMapLayer(layer.id())

        self.compute_task = ComputeTask(self, data, self.parent.message_bar)
        self.start_task = self.parent.start_interpreter_task()
        if self.start_task is not None:
            self.compute_task.addSubTask(
                self.start_task, [], QgsTask.ParentDependsOnSubTask
            )
        self.set_interpreter_interaction(False)
        QgsApplication.taskManager().addTask(self.compute_task)

    def domain(self) -> None:
        """
        Write the current viewing extent as rectangle to the GeoPackage.
        """
        item = self.parent.domain_item()
        ymax, ymin = item.element.update_extent(self.parent.iface)
        self.set_cellsize_from_domain(ymax, ymin)
        self.parent.iface.mapCanvas().refreshAllLayers()

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

    def load_mesh_result(self, path: Union[Path, str], load_contours: bool) -> None:
        path = Path(path)
        # String for QGIS functions
        netcdf_path = str(path.with_suffix(".ugrid.nc"))
        layer = QgsMeshLayer(netcdf_path, f"{path.stem}", "mdal")
        indexes = layer.datasetGroupsIndexes()
        contour_layers = []
        for index in indexes:
            qgs_index = QgsMeshDatasetIndex(group=index, dataset=0)
            name = layer.datasetGroupMetadata(qgs_index).name()
            if "head_layer_" not in name:
                continue
            index_layer = QgsMeshLayer(str(netcdf_path), f"{path.stem}-{name}", "mdal")
            renderer = index_layer.rendererSettings()
            renderer.setActiveScalarDatasetGroup(index)

            scalar_settings = renderer.scalarSettings(index)
            scalar_settings.setDataResamplingMethod(0)
            renderer.setScalarSettings(index, scalar_settings)

            index_layer.setRendererSettings(renderer)
            self.parent.output_group.add_layer(index_layer, "mesh")

            if load_contours:
                # Should generally result in 20 contours.
                start = scalar_settings.classificationMinimum()
                stop = scalar_settings.classificationMaximum()
                step = (stop - start) / 21

                contour_layer = mesh_contours(
                    gpkg_path=str(path.with_suffix(".output.gpkg")),
                    layer=index_layer,
                    index=index,
                    name=f"{path.stem}-contours-{name}",
                    start=start,
                    stop=stop,
                    step=step,
                )
                contour_layers.append(contour_layer)

        # Add the contours in the appropriate order: highest (deepest) layer first!
        if load_contours:
            for contour_layer in contour_layers[::-1]:
                self.add_contour_layer(contour_layer)

        return

    def load_raster_result(self, path: Union[Path, str]) -> None:
        def steady_or_first(name: str) -> bool:
            if "time=" not in name:
                return True
            elif "time=0" in name:
                return True
            return False

        # String for QGIS functions
        path = Path(path)
        raster_path = str(path.with_suffix(".nc"))
        layer = QgsRasterLayer(raster_path, "", "gdal")

        bands = [i + 1 for i in range(layer.bandCount())]
        bandnames = [layer.bandName(band) for band in bands]
        bands = [band for band, name in zip(bands, bandnames) if steady_or_first(name)]

        for i, band in enumerate(bands):
            layer = QgsRasterLayer(raster_path, f"{path.stem}-head_layer_{i}", "gdal")
            renderer = layer_styling.pseudocolor_renderer(
                layer, band=band, colormap="Plasma", nclass=10
            )
            layer.setRenderer(renderer)
            self.parent.output_group.add_layer(layer, "raster")

        #            if contour:
        #                contour_layer = raster_steady_contours(
        #                    layer=layer,
        #                    name=name,
        #                    start=start,
        #                    stop=stop,
        #                    step=step,
        #                )
        #                self.add_contour_layer(contour_layer)

        return

    def load_vector_result(self, path: Union[Path, str]) -> None:
        path = Path(path)
        gpkg_path = path.with_suffix(".output.gpkg")

        if not gpkg_path.exists():
            return

        for layername in geopackage.layers(str(gpkg_path)):
            layers_panel_name = f"{path.stem}-{layername}"

            layer = QgsVectorLayer(
                f"{gpkg_path}|layername={layername}", layers_panel_name
            )

            # Set the temporal properties if it's a temporal layer
            temporal_properties = layer.temporalProperties()
            fields = [field.name() for field in layer.fields()]
            if ("datetime_start" in fields) and ("datetime_end" in fields):
                temporal_properties.setStartField("datetime_start")
                temporal_properties.setEndField("datetime_end")
                temporal_properties.setMode(
                    QgsVectorLayerTemporalProperties.ModeFeatureDateTimeStartAndEndFromFields
                )
                temporal_properties.setIsActive(True)
            else:
                temporal_properties.setIsActive(False)

            if (
                "timml Head Observation:" in layername
                or "ttim Head Observation" in layername
            ):
                labels = layer_styling.number_labels("head_layer0")
            elif "discharge-" in layername:
                labels = layer_styling.number_labels("discharge_layer0")
            else:
                labels = None

            _, element_type, _ = parse_name(layername)
            renderer = ELEMENTS[element_type].renderer()
            self.parent.output_group.add_layer(
                layer, "vector", renderer=renderer, labels=labels
            )

        return
