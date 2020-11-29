import json
import os
from pathlib import Path
import socket
import subprocess

from qgis.PyQt import QtGui, QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal, QVariant
from PyQt5.QtWidgets import QAction, QFileDialog
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsField,
    QgsPointXY,
    QgsFeature,
    QgsGeometry,
    QgsVectorFileWriter,
    QgsMeshLayer,
    QgsSettings,
)
from qgis.gui import QgsMessageBar
from qgistim.timml_elements import create_timml_layer
from qgistim import geopackage
from qgistim.server_handler import ServerHandler


FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "qt/qgistim_dockwidget_base.ui")
)


class QgisTimDockWidget(QtWidgets.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, iface, parent=None):
        super(QgisTimDockWidget, self).__init__(parent)
        self.iface = iface
        self.setupUi(self)
        # Dataset management
        self.newGeopackageButton.clicked.connect(self.new_geopackage)
        self.openGeopackageButton.clicked.connect(self.open_geopackage)
        # Elements
        self.wellButton.clicked.connect(lambda: self.timml_element("Well"))
        self.headWellButton.clicked.connect(lambda: self.timml_element("HeadWell"))
        self.uniformFlowButton.clicked.connect(
            lambda: self.timml_element("UniformFlow")
        )
        self.headLineSinkButton.clicked.connect(
            lambda: self.timml_element("HeadLineSink")
        )
        self.lineSinkDitchButton.clicked.connect(
            lambda: self.timml_element("LineSinkDitch")
        )
        self.impLineDoubletButton.clicked.connect(
            lambda: self.timml_element("LineDoublet")
        )
        self.leakyLineDoubletButton.clicked.connect(
            lambda: self.timml_element("LeakyLineDoublet")
        )
        self.polygonInhomButton.clicked.connect(
            lambda: self.timml_element("PolygonInhom")
        )
        # Special case entry
        self.circularAreaSinkButton.clicked.connect(self.circular_area_sink)
        # Domain
        self.domainButton.clicked.connect(self.domain)
        # Solve
        self.computeButton.clicked.connect(self.compute)
        # Initialize buttons disabled, since dataset hasn't been loaded yet.
        self.toggle_element_buttons(False)
        # Just used as a viewing port
        self.datasetLineEdit.setEnabled(False)
        # To connect with TimServer
        self.server_handler = ServerHandler()
        self.serverButton.clicked.connect(self.start_server)

    def toggle_element_buttons(self, state):
        self.wellButton.setEnabled(state)
        self.headWellButton.setEnabled(state)
        self.uniformFlowButton.setEnabled(state)
        self.headLineSinkButton.setEnabled(state)
        self.lineSinkDitchButton.setEnabled(state)
        self.impLineDoubletButton.setEnabled(state)
        self.leakyLineDoubletButton.setEnabled(state)
        self.polygonInhomButton.setEnabled(state)
        self.circularAreaSinkButton.setEnabled(state)

    def closeEvent(self, event):
        self.server_handler.kill()
        self.closingPlugin.emit()
        event.accept()

    @property
    def path(self):
        return self.datasetLineEdit.text()

    @property
    def crs(self):
        return self.iface.mapCanvas().mapSettings().destinationCrs()

    def add_layer(self, layer):
        maplayer = QgsProject.instance().addMapLayer(layer, False)
        self.group.addLayer(maplayer)

    def add_geopackage_layers(self, path):
        # Adapted from PyQGIS cheatsheet:
        # https://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/cheat_sheet.html#layers
        for layername in geopackage.layers(self.path):
            layer = QgsVectorLayer(f"{path}|layername={layername}", layername)
            self.add_layer(layer)

    def load_geopackage(self):
        path = self.path
        root = QgsProject.instance().layerTreeRoot()
        self.group = root.addGroup(str(Path(path).stem))
        self.add_geopackage_layers(path)

    def new_geopackage(self):
        path, _ = QFileDialog.getSaveFileName(self, "Select file", "", "*.gpkg")
        if path != "":  # Empty string in case of cancel button press
            self.datasetLineEdit.setText(path)
            self.new_timml_model()
            self.load_geopackage()
            self.toggle_element_buttons(True)

    def open_geopackage(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select file", "", "*.gpkg")
        if path != "":  # Empty string in case of cancel button press
            self.datasetLineEdit.setText(path)
            self.load_geopackage()
            self.toggle_element_buttons(True)

    def new_timml_model(self):
        # Write the aquifer properties
        layer = create_timml_layer("Aquifer", "", self.crs)
        _ = geopackage.write_layer(self.path, layer, "timmlAquifer", newfile=True)
        # Write a single constant (reference) head
        layer = create_timml_layer("Constant", "", self.crs)
        _ = geopackage.write_layer(self.path, layer, "timmlConstant")

    def timml_element(self, elementtype):
        dialog = NameDialog()
        dialog.show()
        ok = dialog.exec_()
        if ok:
            layername = dialog.lineEdit.text()
            layer = create_timml_layer(elementtype, layername, self.crs)
            written_layer = geopackage.write_layer(
                self.path, layer, f"timml{elementtype}:{layername}"
            )
            self.add_layer(written_layer)

    def domain(self):
        layer = QgsVectorLayer("polygon", "timmlDomain", "memory", crs=self.crs)
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
        written_layer = geopackage.write_layer(self.path, layer, "timmlDomain")
        QgsProject.instance().addMapLayer(written_layer)

    def circular_area_sink(self):
        dialog = RadiusDialog()
        dialog.show()
        ok = dialog.exec_()
        if ok:
            layername = dialog.layerEdit.text()
            radius = float(dialog.radiusEdit.text())
            layer = create_timml_layer(
                "CircularAreaSink",
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
                self.path, layer, f"timmlCircularAreaSink:{layername}"
            )
            QgsProject.instance().addMapLayer(written_layer)

    def load_result(self, path, cellsize):
        netcdf_path = (path.parent / f"{path.name}-{cellsize}").with_suffix(".nc")
        layer = QgsMeshLayer(str(netcdf_path), f"{path.name}-{cellsize}", "mdal")
        self.add_layer(layer)

    def start_server(self):
        self.server_handler.start_server()

    def compute(self):
        cellsize = self.cellsizeSpinBox.value()
        path = Path(self.path).absolute()
        data = json.dumps(
            {"path": str(path), "cellsize": cellsize}
        )
        handler = self.server_handler
        received = handler.send(data)
       
        if received == "0":
            self.load_result(path, cellsize)
        else:
            self.iface.messageBar().pushMessage(
                "Error", "Something seems to have gone wrong, "
                "try checking the server window...",
                level=QgsMessageBar.CRITICAL,
            )

FORM_CLASS_LAYERNAMEDIALOG, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "qt/qgistim_name_dialog_base.ui")
)


class NameDialog(QtWidgets.QDialog, FORM_CLASS_LAYERNAMEDIALOG):
    def __init__(self, parent=None):
        super(NameDialog, self).__init__(parent)
        self.setupUi(self)


FORM_CLASS_RADIUSDIALOG, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "qt/qgistim_radius_dialog_base.ui")
)


class RadiusDialog(QtWidgets.QDialog, FORM_CLASS_RADIUSDIALOG):
    def __init__(self, parent=None):
        super(RadiusDialog, self).__init__(parent)
        self.setupUi(self)
