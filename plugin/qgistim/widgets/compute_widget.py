import datetime
from pathlib import Path
from typing import Tuple

from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
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
    QgsPalLayerSettings,
    QgsTask,
    QgsVectorLayerSimpleLabeling,
)
from qgis.gui import QgsMapLayerComboBox

from ..core import layer_styling
from ..core.processing import mesh_contours
from ..core.task import BaseServerTask


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
        self.parent.parent.set_interpreter_interaction(True)
        if result:
            self.push_success_message()
            self.parent.parent.load_mesh_result(
                self.data["outpath"],
                self.data["as_trimesh"],
            )
        else:
            self.push_failure_message()
        return


class ComputeWidget(QWidget):
    def __init__(self, parent=None):
        super(ComputeWidget, self).__init__(parent)
        self.compute_task = None
        self.start_task = None
        self.parent = parent
        self.domain_button = QPushButton("Domain")
        self.transient_combo_box = QComboBox()
        self.transient_combo_box.addItems(["Steady-state", "Transient"])
        self.transient_combo_box.currentTextChanged.connect(self.on_transient_changed)
        self.compute_button = QPushButton("Compute")
        self.compute_button.clicked.connect(self.compute)
        self.cellsize_spin_box = QDoubleSpinBox()
        self.cellsize_spin_box.setMinimum(0.0)
        self.cellsize_spin_box.setMaximum(10_000.0)
        self.cellsize_spin_box.setSingleStep(1.0)
        self.cellsize_spin_box.setValue(25.0)
        self.domain_button.clicked.connect(self.domain)
        # self.mesh_checkbox = QCheckBox("Trimesh")
        self.output_line_edit = QLineEdit()
        self.output_button = QPushButton("Save as ...")
        self.output_button.clicked.connect(self.set_output_path)
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
        compute_layout = QVBoxLayout()
        compute_grid = QGridLayout()
        compute_grid.addWidget(self.domain_button, 0, 0)
        cellsize_row = QHBoxLayout()
        cellsize_row.addWidget(QLabel("Cellsize:"))
        cellsize_row.addWidget(self.cellsize_spin_box)
        # label.setFixedWidth(45)
        compute_grid.addLayout(cellsize_row, 0, 1)
        contour_row = QHBoxLayout()
        contour_row2 = QHBoxLayout()
        contour_row.addWidget(self.contour_checkbox)
        contour_row.addWidget(self.contour_min_box)
        contour_row.addWidget(QLabel("to"))
        contour_row.addWidget(self.contour_max_box)
        contour_row2.addWidget(QLabel("Increment:"))
        contour_row2.addWidget(self.contour_step_box)
        compute_grid.addLayout(contour_row, 1, 0)
        compute_grid.addLayout(contour_row2, 1, 1)
        compute_grid.addWidget(self.transient_combo_box, 3, 0)
        compute_grid.addWidget(self.output_line_edit, 2, 0)
        compute_grid.addWidget(self.output_button, 2, 1)
        compute_row = QHBoxLayout()
        # compute_row.addWidget(self.mesh_checkbox)
        compute_row.addWidget(self.compute_button)
        compute_grid.addLayout(compute_row, 3, 1)
        compute_grid.addWidget(self.contour_layer, 4, 0)
        compute_grid.addWidget(self.contour_button, 4, 1)
        compute_layout.addLayout(compute_grid)
        compute_layout.addStretch()
        self.setLayout(compute_layout)

    @property
    def transient(self) -> bool:
        return self.transient_combo_box.currentText() == "Transient"

    def on_transient_changed(self) -> None:
        self.parent.on_transient_changed()

    def contour_range(self) -> Tuple[float, float, float]:
        return (
            float(self.contour_min_box.value()),
            float(self.contour_max_box.value()),
            float(self.contour_step_box.value()),
        )

    def export_contours(self) -> None:
        layer = self.contour_layer.currentLayer()
        renderer = layer.rendererSettings()
        index = renderer.activeScalarDatasetGroup()
        qgs_index = QgsMeshDatasetIndex(group=index, dataset=0)
        name = layer.datasetGroupMetadata(qgs_index).name()
        start, stop, step = self.contour_range()
        contour_layer = mesh_contours(
            layer=layer,
            index=index,
            name=name,
            start=start,
            stop=stop,
            step=step,
        )
        # Labeling
        pal_layer = QgsPalLayerSettings()
        pal_layer.fieldName = "head"
        pal_layer.enabled = True
        pal_layer.placement = QgsPalLayerSettings.Line
        labels = QgsVectorLayerSimpleLabeling(pal_layer)
        contour_layer.setLabeling(labels)
        contour_layer.setLabelsEnabled(True)
        # Renderer: simple black lines
        renderer = layer_styling.contour_renderer()
        self.parent.add_layer(contour_layer, "output", renderer=renderer, on_top=True)

    def set_output_path(self) -> None:
        current = self.output_line_edit.text()
        path, _ = QFileDialog.getSaveFileName(
            self, "Save output as...", current, "*.nc"
        )
        if path != "":  # Empty string in case of cancel button press
            self.output_line_edit.setText(path)
            # Note: Qt does pretty good validity checking of the Path in the
            # Dialog, there is no real need to validate path here.

    def set_default_path(self, text: str) -> None:
        """
        Called when different dataset path is chosen.
        """
        if text is None:
            return
        path = Path(text)
        parent = path.parent
        stem = path.stem
        outpath = (parent / stem).with_suffix(".nc").absolute()
        self.output_line_edit.setText(str(outpath))

    def compute(self) -> None:
        """
        Run a TimML computation with the current state of the currently active
        GeoPackage dataset.
        """
        active_elements = self.parent.active_elements()
        cellsize = self.cellsize_spin_box.value()
        inpath = Path(self.parent.path).absolute()
        outpath = Path(self.output_line_edit.text()).absolute()
        mode = self.transient_combo_box.currentText().lower()
        as_trimesh = False  # self.mesh_checkbox.isChecked()
        data = {
            "operation": "compute",
            "inpath": str(inpath),
            "outpath": str(outpath),
            "cellsize": cellsize,
            "mode": mode,
            "active_elements": active_elements,
            "as_trimesh": as_trimesh,
        }
        # https://gis.stackexchange.com/questions/296175/issues-with-qgstask-and-task-manager
        # It seems the task goes awry when not associated with a Python object!
        # -- we just assign it to the widget here.
        #
        # To run the tasks without the QGIS task manager:
        # result = task.run()
        # task.finished(result)

        self.compute_task = ComputeTask(self, data)
        self.start_task = self.parent.start_interpreter_task()
        if self.start_task is not None:
            self.compute_task.addSubTask(
                self.start_task, [], QgsTask.ParentDependsOnSubTask
            )
        self.parent.set_interpreter_interaction(False)
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

    def contouring(self) -> Tuple[bool, float, float, float]:
        contour = self.contour_checkbox.isChecked()
        start, stop, step = self.contour_range()
        return contour, start, stop, step
