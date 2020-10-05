import os
from pathlib import Path

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
)
from qgistim.timml_elements import create_timml_layer
from qgistim import geopackage


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
        self.selectGeopackageButton.clicked.connect(self.select_geopackage)
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

    def closeEvent(self, event):
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

    def select_geopackage(self):
        path, _filter = QFileDialog.getSaveFileName(self, "Select file", "", "*.gpkg")
        self.datasetLineEdit.setText(path)
        root = QgsProject.instance().layerTreeRoot()
        self.group = root.addGroup(str(Path(path).stem))
        # This serves to create the geopackage if it doesn't already exist
        if not Path(path).exists():
            self.new_timml_model()
        self.add_geopackage_layers(path)

    def new_timml_model(self):
        # Write the aquifer properties
        layer = create_timml_layer("Aquifer", "", None)
        _ = geopackage.write_layer(self.path, layer, "timmlAquifer", newfile=True)
        # Write a single constant (reference) head
        layer = create_timml_layer("Constant", "", None)
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
