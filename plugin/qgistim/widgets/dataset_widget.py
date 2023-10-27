"""
This widgets displays the available elements in the GeoPackage.

This widget also allows enabling or disabling individual elements for a
computation. It also forms the link between the geometry layers and the
associated layers for homogeneities, or for timeseries layers for ttim
elements.

Not every TimML element has a TTim equivalent (yet). This means that when a
user chooses the transient simulation mode, a number of elements must be
disabled (such as inhomogeneities).
"""
import json
from pathlib import Path
from shutil import copy
from typing import Any, Dict, List, NamedTuple, Set, Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qgis.core import Qgis, QgsProject
from qgistim.core.elements import Aquifer, Domain, load_elements_from_geopackage
from qgistim.core.formatting import data_to_json, data_to_script
from qgistim.widgets.error_window import ValidationDialog

SUPPORTED_TTIM_ELEMENTS = set(
    [
        "Aquifer",
        "Domain",
        "Constant",
        "Uniform Flow",
        "Well",
        "Head Well",
        "Head Line Sink",
        "Line Sink Ditch",
        "Circular Area Sink",
        "Impermeable Line Doublet",
        "Leaky Line Doublet",
        "Head Observation",
    ]
)


class Extraction(NamedTuple):
    timml: Dict[str, Any] = None
    ttim: Dict[str, Any] = None
    success: bool = True


class DatasetTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setHeaderHidden(True)
        self.setSortingEnabled(True)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.setHeaderLabels(["", "steady", "transient"])
        self.setHeaderHidden(False)
        header = self.header()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionsMovable(False)
        self.setColumnCount(3)
        self.setColumnWidth(0, 1)
        self.domain = None

    def items(self) -> List[QTreeWidgetItem]:
        root = self.invisibleRootItem()
        return [root.child(i) for i in range(root.childCount())]

    def reset(self):
        for item in self.items():
            index = self.indexOfTopLevelItem(item)
            self.takeTopLevelItem(index)
        return

    def add_item(self, timml_name: str, ttim_name: str = None, enabled: bool = True):
        item = QTreeWidgetItem()
        self.addTopLevelItem(item)
        item.timml_checkbox = QCheckBox()
        item.timml_checkbox.setChecked(True)
        item.timml_checkbox.setEnabled(enabled)
        self.setItemWidget(item, 0, item.timml_checkbox)
        item.setText(1, timml_name)
        item.setText(2, ttim_name)
        item.assoc_item = None
        return item

    def add_element(self, element) -> None:
        # These are mandatory elements, cannot be unticked
        if isinstance(element, (Domain, Aquifer)):
            enabled = False
        else:
            enabled = True

        item = self.add_item(
            timml_name=element.timml_name, ttim_name=element.ttim_name, enabled=enabled
        )
        item.element = element
        return

    def on_transient_changed(self, transient: bool) -> None:
        """
        Disable elements that are not supported by TTim, such as
        Inhomogeneities, or switch them on again.
        """
        self.setColumnHidden(2, not transient)
        # Disable unsupported ttim items, such as inhomogeneities
        for item in self.items():
            prefix, _ = item.text(1).split(":")
            _, elementtype = prefix.split("timml ")
            if elementtype not in SUPPORTED_TTIM_ELEMENTS:
                item.timml_checkbox.setChecked(not transient)
                item.timml_checkbox.setEnabled(not transient)

            # Hide transient columns in the TimML layers:
            item.element.on_transient_changed(transient)

        return

    def remove_geopackage_layers(self) -> None:
        """
        Remove layers from:

        * The dataset tree widget
        * The QGIS layer panel
        * The geopackage
        """

        # Collect the selected items
        selection = self.selectedItems()
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

        # Start deleting
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
            index = self.indexOfTopLevelItem(item)
            self.takeTopLevelItem(index)

        return

    def extract_data(self, transient: bool) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extract the data of the Geopackage.

        Validates all data while converting, and returns a list of validation
        errors if something is amiss.
        """
        data = {}
        errors = {}
        elements = {
            item.text(1): item.element
            for item in self.items()
            if item.timml_checkbox.isChecked()
        }

        # First convert the aquifer, since we need its data to validate
        # other elements.
        name = "timml Aquifer:Aquifer"
        aquifer = elements.pop(name)
        aquifer_extraction = aquifer.extract_data(transient)
        if aquifer_extraction.errors:
            errors[name] = aquifer_extraction.errors
            return errors, None

        raw_data = aquifer_extraction.data
        aquifer_data = aquifer.aquifer_data(raw_data, transient=transient)
        data[name] = aquifer_data
        if transient:
            data["start_date"] = str(raw_data["start_date"].toPyDateTime())

        times = set()
        other = {"aquifer layers": raw_data["layer"], "global_aquifer": raw_data}
        for name, element in elements.items():
            print(name)
            try:
                extraction = element.extract_data(transient, other)
                if extraction.errors:
                    errors[name] = extraction.errors
                elif extraction.data:  # skip empty tables
                    data[name] = extraction.data
                    if extraction.times:
                        times.update(extraction.times)
            except RuntimeError as e:
                if (
                    e.args[0]
                    == "wrapped C/C++ object of type QgsVectorLayer has been deleted"
                ):
                    # Delay of Qt garbage collection to blame?
                    pass
                else:
                    raise e

        if transient:
            if times:
                data["timml Aquifer:Aquifer"]["tmax"] = max(times)
            else:
                errors["Model"] = {"TTim input:": ["No transient forcing defined."]}

        return errors, data


class DatasetWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.dataset_tree = DatasetTreeWidget()
        self.start_task = None
        self.dataset_tree.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.dataset_line_edit = QLineEdit()
        self.dataset_line_edit.setEnabled(False)  # Just used as a viewing port
        self.new_geopackage_button = QPushButton("New")
        self.open_geopackage_button = QPushButton("Open")
        self.copy_geopackage_button = QPushButton("Copy")
        self.transient_combo_box = QComboBox()
        self.transient_combo_box.addItems(["Steady-state", "Transient"])
        self.transient_combo_box.currentTextChanged.connect(self.on_transient_changed)
        self.remove_button = QPushButton("Remove from GeoPackage")
        self.add_button = QPushButton("Add to QGIS")
        self.new_geopackage_button.clicked.connect(self.new_geopackage)
        self.open_geopackage_button.clicked.connect(self.open_geopackage)
        self.copy_geopackage_button.clicked.connect(self.copy_geopackage)
        self.suppress_popup_checkbox = QCheckBox("Suppress attribute form pop-up")
        self.suppress_popup_checkbox.stateChanged.connect(self.suppress_popup_changed)
        self.remove_button.clicked.connect(self.remove_geopackage_layer)
        self.add_button.clicked.connect(self.add_selection_to_qgis)
        self.convert_button = QPushButton("Export to Python script")
        self.convert_button.clicked.connect(self.convert_to_python)
        # Layout
        dataset_layout = QVBoxLayout()
        mode_row = QHBoxLayout()
        dataset_row = QHBoxLayout()
        layer_row = QHBoxLayout()
        dataset_row.addWidget(self.dataset_line_edit)
        dataset_row.addWidget(self.open_geopackage_button)
        dataset_row.addWidget(self.new_geopackage_button)
        dataset_row.addWidget(self.copy_geopackage_button)
        dataset_layout.addLayout(dataset_row)
        mode_row.addWidget(self.transient_combo_box)
        dataset_layout.addLayout(mode_row)
        dataset_layout.addWidget(self.dataset_tree)
        dataset_layout.addWidget(self.suppress_popup_checkbox)
        layer_row.addWidget(self.add_button)
        layer_row.addWidget(self.remove_button)
        dataset_layout.addLayout(layer_row)
        dataset_layout.addWidget(self.convert_button)
        self.setLayout(dataset_layout)
        self.validation_dialog = None

    @property
    def path(self) -> str:
        """Returns currently active path to GeoPackage"""
        return self.dataset_line_edit.text()

    def reset(self):
        # Set state back to defaults
        self.start_task = None
        self.dataset_line_edit.setText("")
        self.dataset_tree.reset()
        return

    def add_item_to_qgis(self, item) -> None:
        # Get all the relevant data.
        element = item.element
        element.load_layers_from_geopackage()
        suppress = self.suppress_popup_checkbox.isChecked()
        # Start adding the layers
        maplayer = self.parent.input_group.add_layer(
            element.timml_layer, "timml", element.renderer(), suppress
        )
        self.parent.input_group.add_layer(element.ttim_layer, "ttim")
        self.parent.input_group.add_layer(element.assoc_layer, "timml")
        # Set cell size if the item is a domain layer
        if item.element.timml_name.split(":")[0] == "timml Domain":
            if maplayer.featureCount() <= 0:
                return
            feature = next(iter(maplayer.getFeatures()))
            extent = feature.geometry().boundingBox()
            ymax = extent.yMaximum()
            ymin = extent.yMinimum()
            self.parent.set_cellsize_from_domain(ymax, ymin)
        return

    def add_selection_to_qgis(self) -> None:
        selection = self.dataset_tree.selectedItems()
        for item in selection:
            self.add_item_to_qgis(item)
        return

    def load_geopackage(self) -> None:
        """
        Load the layers of a GeoPackage into the Layers Panel
        """
        self.dataset_tree.clear()

        name = str(Path(self.path).stem)
        self.parent.create_input_group(name)
        self.parent.create_output_group(name)

        elements = load_elements_from_geopackage(self.path)
        for element in elements:
            self.dataset_tree.add_element(element)

        transient = self.transient
        for item in self.dataset_tree.items():
            self.add_item_to_qgis(item)
            item.element.on_transient_changed(transient)

        self.dataset_tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.parent.toggle_element_buttons(True)
        self.on_transient_changed()
        return

    def new_geopackage(self) -> None:
        """
        Create a new GeoPackage file, and set it as the active dataset.
        """
        try:
            crs = self.parent.crs
        except ValueError:
            return

        path, _ = QFileDialog.getSaveFileName(self, "Select file", "", "*.gpkg")
        if path != "":  # Empty string in case of cancel button press
            self.dataset_line_edit.setText(path)
            # Writing here creates a new Geopackage.
            for element in (Aquifer, Domain):
                instance = element(self.path, "")
                instance.create_layers(crs)
                instance.write()
            # Next, we load the newly written layers.
            self.load_geopackage()
        return

    def open_geopackage(self) -> None:
        """
        Open a GeoPackage file, containing qgis-tim
        """
        self.dataset_tree.clear()
        path, _ = QFileDialog.getOpenFileName(self, "Select file", "", "*.gpkg")
        if path != "":  # Empty string in case of cancel button press
            self.dataset_line_edit.setText(path)
            self.load_geopackage()
        return

    def copy_geopackage(self) -> None:
        """
        Copy a GeoPackage file, containing qgis-tim, and open it.
        """
        self.dataset_tree.clear()
        target_path, _ = QFileDialog.getSaveFileName(self, "Select file", "", "*.gpkg")
        if target_path != "":  # Empty string in case of cancel button press
            source_path = Path(self.path)
            target_path = Path(target_path)
            copy(source_path, target_path)
            # Take into account the wal (write-ahead-logging) and shm files as well:
            for suffix in (".gpkg-wal", ".gpkg-shm"):
                extra_source = source_path.with_suffix(suffix)
                extra_target = target_path.with_suffix(suffix)
                if extra_source.exists():
                    copy(extra_source, extra_target)

            self.dataset_line_edit.setText(str(target_path))
            self.load_geopackage()
        return

    def remove_geopackage_layer(self) -> None:
        """
        Remove layers from:
        * The dataset tree widget
        * The QGIS layer panel
        * The geopackage
        """
        self.dataset_tree.remove_geopackage_layers()
        return

    @property
    def transient(self) -> bool:
        return self.transient_combo_box.currentText() == "Transient"

    def on_transient_changed(self) -> None:
        self.dataset_tree.on_transient_changed(self.transient)
        return

    def suppress_popup_changed(self):
        suppress = self.suppress_popup_checkbox.isChecked()
        for item in self.dataset_tree.items():
            layer = item.element.timml_layer
            if layer is not None:
                config = layer.editFormConfig()
                config.setSuppress(suppress)
                layer.setEditFormConfig(config)
        return

    def active_elements(self):
        active_elements = {}
        for item in self.dataset_tree.items():
            active_elements[item.text(1)] = not (item.timml_checkbox.isChecked() == 0)
            active_elements[item.text(2)] = not (item.timml_checkbox.isChecked() == 0)
        return active_elements

    def domain_item(self):
        # Find domain entry
        for item in self.dataset_tree.items():
            if isinstance(item.element, Domain):
                return item
        else:
            # Create domain instead?
            raise ValueError("Geopackage does not contain domain")

    def selection_names(self) -> Set[str]:
        selection = self.dataset_tree.items()
        # Append associated items
        for item in selection:
            if item.assoc_item is not None and item.assoc_item not in selection:
                selection.append(item.assoc_item)
        return set([item.element.name for item in selection])

    def add_element(self, element) -> None:
        self.dataset_tree.add_element(element)
        return

    def set_interpreter_interaction(self, value: bool):
        self.parent.set_interpreter_interaction(value)
        return

    def _extract_data(self, transient: bool) -> Extraction:
        if self.validation_dialog:
            self.validation_dialog.close()
            self.validation_dialog = None

        errors, timml_data = self.dataset_tree.extract_data(transient=False)
        if errors:
            self.validation_dialog = ValidationDialog(errors)
            return Extraction(success=False)

        ttim_data = None
        if transient:
            errors, ttim_data = self.dataset_tree.extract_data(transient=True)
            if errors:
                self.validation_dialog = ValidationDialog(errors)
                return Extraction(success=False)

        return Extraction(timml=timml_data, ttim=ttim_data)

    def convert_to_python(self) -> None:
        transient = self.transient
        outpath, _ = QFileDialog.getSaveFileName(self, "Select file", "", "*.py")
        if outpath == "":  # Empty string in case of cancel button press
            return

        extraction = self._extract_data(transient=transient)
        if not extraction.success:
            return

        script = data_to_script(extraction.timml, extraction.ttim)
        with open(outpath, "w") as f:
            f.write(script)

        self.parent.message_bar.pushMessage(
            title="Info",
            text=f"Converted geopackage to Python script: {outpath}",
            level=Qgis.Info,
        )
        return

    def convert_to_json(
        self,
        path: str,
        cellsize: float,
        transient: bool,
        output_options: Dict[str, bool],
    ) -> bool:
        """
        Parameters
        ----------
        path: str
            Path to JSON file to write.
        cellsize: float
            Cell size to use to compute the head grid.
        transient: bool
            Steady-state (False) or transient (True).

        Returns
        -------
        invalid_input: bool
            Whether validation has succeeded.
        """
        extraction = self._extract_data(transient=transient)
        if not extraction.success:
            return True

        json_data = data_to_json(
            extraction.timml,
            extraction.ttim,
            cellsize=cellsize,
            output_options=output_options,
        )

        crs = self.parent.crs
        organization, srs_id = crs.authid().split(":")
        json_data["crs"] = {
            "description": crs.description(),
            "organization": organization,
            "srs_id": srs_id,
            "wkt": crs.toWkt(),
        }

        with open(path, "w") as fp:
            json.dump(json_data, fp=fp, indent=4)

        self.parent.message_bar.pushMessage(
            title="Info",
            text=f"Converted geopackage to JSON: {path}",
            level=Qgis.Info,
        )
        return False
