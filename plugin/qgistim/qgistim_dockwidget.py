import json
import os
import socket
import subprocess
import tempfile
from pathlib import Path

from PyQt5.QtWidgets import QAction, QFileDialog
from qgis.core import (
    Qgis,
    QgsFeature,
    QgsField,
    QgsFillSymbol,
    QgsGeometry,
    QgsMeshLayer,
    QgsPointXY,
    QgsProject,
    QgsRasterBandStats,
    QgsRasterLayer,
    QgsSettings,
    QgsSingleBandPseudoColorRenderer,
    QgsStyle,
    QgsVectorFileWriter,
    QgsVectorLayer,
)
from qgis.PyQt import QtGui, QtWidgets, uic
from qgis.PyQt.QtCore import QVariant, pyqtSignal
from qgistim import geopackage, layer_styling
from qgistim.server_handler import ServerHandler
from qgistim.timml_elements import create_timml_layer

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
        self.constantButton.clicked.connect(lambda: self.timml_element("Constant"))
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
            lambda: self.timml_element("ImpLineDoublet")
        )
        self.leakyLineDoubletButton.clicked.connect(
            lambda: self.timml_element("LeakyLineDoublet")
        )
        self.polygonInhomButton.clicked.connect(
            lambda: self.timml_element("PolygonInhom")
        )
        # Special case entry
        self.circAreaSinkButton.clicked.connect(self.circ_area_sink)
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
        self.constantButton.setEnabled(state)
        self.wellButton.setEnabled(state)
        self.headWellButton.setEnabled(state)
        self.uniformFlowButton.setEnabled(state)
        self.headLineSinkButton.setEnabled(state)
        self.lineSinkDitchButton.setEnabled(state)
        self.impLineDoubletButton.setEnabled(state)
        self.leakyLineDoubletButton.setEnabled(state)
        self.polygonInhomButton.setEnabled(state)
        self.circAreaSinkButton.setEnabled(state)

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

    def add_layer(self, layer, renderer=None):
        maplayer = QgsProject.instance().addMapLayer(layer, False)
        if renderer is not None:
            maplayer.setRenderer(renderer)
        self.group.addLayer(maplayer)

    def add_geopackage_layers(self, path):
        # Adapted from PyQGIS cheatsheet:
        # https://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/cheat_sheet.html#layers
        for layername in geopackage.layers(self.path):
            layer = QgsVectorLayer(f"{path}|layername={layername}", layername)
            if layername == "timmlDomain":
                renderer = layer_styling.domain_renderer()
            else:
                renderer = None
            self.add_layer(layer, renderer)

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

        # Remove the previous domain specification
        for existing_layer in QgsProject.instance().mapLayers().values():
            if Path(existing_layer.source()) == Path(
                str(self.path) + "|layername=timmlDomain"
            ):
                QgsProject.instance().removeMapLayer(existing_layer.id())

        renderer = layer_styling.domain_renderer()
        self.add_layer(written_layer, renderer)

    def circ_area_sink(self):
        dialog = RadiusDialog()
        dialog.show()
        ok = dialog.exec_()
        if ok:
            layername = dialog.layerEdit.text()
            radius = float(dialog.radiusEdit.text())
            layer = create_timml_layer(
                "CircAreaSink",
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
                self.path, layer, f"timmlCircAreaSink:{layername}"
            )
            renderer = layer_styling.circareasink_renderer()
            self.add_layer(written_layer, renderer)

    def load_result(self, path, cellsize):
        netcdf_path = str(
            (path.parent / f"{path.stem}-{cellsize}".replace(".", "_")).with_suffix(
                ".nc"
            )
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            dirpath = Path(tmpdir)
            # Loop through layers first. If the path already exists as a layer source, remove it.
            # Otherwise QGIS will not the load the new result (this feels like a bug?).
            exists = False
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
                    netcdf_path, f"{path.stem}-{band}-{cellsize}", "gdal"
                )
                renderer = layer_styling.pseudocolor_renderer(
                    layer, band, colormap="Magma", nclass=10
                )
                self.add_layer(layer, renderer)

    def start_server(self):
        self.server_handler.start_server()

    def compute(self):
        cellsize = self.cellsizeSpinBox.value()
        path = Path(self.path).absolute()
        data = json.dumps({"path": str(path), "cellsize": cellsize})
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
