from pathlib import Path
from typing import Tuple

from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from qgis.core import (
    QgsMapLayerProxyModel,
    QgsMeshDatasetIndex,
    QgsPalLayerSettings,
    QgsVectorLayerSimpleLabeling,
)
from qgis.gui import QgsMapLayerComboBox

from ..core import layer_styling
from ..core.processing import mesh_contours


class ComputeWidget(QWidget):
    def __init__(self, parent=None):
        super(ComputeWidget, self).__init__(parent)
        self.parent = parent
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
        # self.mesh_checkbox = QCheckBox("Trimesh")
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
        compute_grid.addWidget(self.transient_combo_box, 2, 0)
        compute_row = QHBoxLayout()
        # compute_row.addWidget(self.mesh_checkbox)
        compute_row.addWidget(self.compute_button)
        compute_grid.addLayout(compute_row, 2, 1)
        compute_grid.addWidget(self.contour_layer, 3, 0)
        compute_grid.addWidget(self.contour_button, 3, 1)
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
        print("exporting_contours", start, stop, step)
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

    def compute(self) -> None:
        """
        Run a TimML computation with the current state of the currently active
        GeoPackage dataset.
        """
        active_elements = self.parent.active_elements()
        cellsize = self.cellsize_spin_box.value()
        path = Path(self.parent.path).absolute()
        mode = self.transient_combo_box.currentText().lower()
        as_trimesh = False  # self.mesh_checkbox.isChecked()
        data = {
            "operation": "compute",
            "path": str(path),
            "cellsize": cellsize,
            "mode": mode,
            "active_elements": active_elements,
            "as_trimesh": as_trimesh,
        }
        received = self.parent.execute(data)

        if received == "0":
            self.parent.load_mesh_result(path, cellsize, as_trimesh)
            # self.load_raster_result(path, cellsize)

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
