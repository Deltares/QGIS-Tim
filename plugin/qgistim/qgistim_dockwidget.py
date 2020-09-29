import os

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

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "qt/qgistim_dockwidget_base.ui")
)


class QgisTimDockWidget(QtWidgets.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, iface, parent=None):
        """Constructor."""
        super(QgisTimDockWidget, self).__init__(parent)
        self.iface = iface
        self.setupUi(self)
        self.pushButton.clicked.connect(self.select_file)
        # Elements
        self.aquiferButton.clicked.connect(self.aquifer_properties)
        self.constantButton.clicked.connect(self.constant)
        self.wellButton.clicked.connect(self.well)
        self.headWellButton.clicked.connect(self.headwell)
        self.circularAreaSinkButton.clicked.connect(self.circular_area_sink)
        self.uniformFlowButton.clicked.connect(self.uniform_flow)
        self.headLineSinkButton.clicked.connect(self.head_line_sink)
        self.lineSinkDitchButton.clicked.connect(self.line_sink_ditch)
        self.impLineDoubletButton.clicked.connect(self.imp_line_doublet)
        self.leakyLineDoubletButton.clicked.connect(self.leaky_line_doublet)
        self.polygonInhomButton.clicked.connect(self.polygon_inhom)
        # Domain
        self.domainButton.clicked.connect(self.domain)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def select_file(self):
        filename, _filter = QFileDialog.getSaveFileName(self, "Select file", "", "*")
        self.lineEdit.setText(filename)

    def write_layer(self, layer):
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.layerName = "_".join(layer.name().split(" "))
        QgsVectorFileWriter.writeAsVectorFormat(layer, self.gpkg_path, options)
        # options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
        # _writer = QgsVectorFileWriter.writeAsVectorFormat(lyr, gpkgPath, options)
        # if _writer:
        #    print(lyr.name(), _writer)

    def crs(self):
        return self.iface.mapCanvas().mapSettings().destinationCrs()

    def well(self):
        dialog = NameDialog()
        dialog.show()
        ok = dialog.exec_()
        if ok:
            layer_name = dialog.lineEdit.text()
            well_layer = QgsVectorLayer(
                "Point", f"timmlWell:{layer_name}", "memory", crs=self.crs()
            )
            provider = well_layer.dataProvider()
            provider.addAttributes(
                [
                    QgsField("discharge", QVariant.Double),
                    QgsField("radius", QVariant.Double),
                    QgsField("resistance", QVariant.Double),
                    QgsField("layer", QVariant.Int),
                    QgsField("label", QVariant.String),
                ]
            )
            well_layer.updateFields()
            QgsProject.instance().addMapLayer(well_layer)

    def headwell(self):
        dialog = NameDialog()
        dialog.show()
        ok = dialog.exec_()
        if ok:
            layer_name = dialog.lineEdit.text()
            well_layer = QgsVectorLayer(
                "Point", f"timmlHeadWell{layer_name}", "memory", crs=self.crs()
            )
            provider = well_layer.dataProvider()
            provider.addAttributes(
                [
                    QgsField("head", QVariant.Double),
                    QgsField("radius", QVariant.Double),
                    QgsField("resistance", QVariant.Double),
                    QgsField("layer", QVariant.Int),
                    QgsField("label", QVariant.String),
                ]
            )
            well_layer.updateFields()
            QgsProject.instance().addMapLayer(well_layer)

    def aquifer_properties(self):
        properties = QgsVectorLayer("No geometry", "timmlAquifer", "memory")
        provider = properties.dataProvider()
        provider.addAttributes(
            [
                QgsField("conductivity", QVariant.Double),
                QgsField("resistance", QVariant.Double),
                QgsField("top", QVariant.Double),
                QgsField("bottom", QVariant.Double),
            ]
        )
        properties.updateFields()
        QgsProject.instance().addMapLayer(properties)

    def domain(self):
        bbox = QgsVectorLayer("polygon", "timmlDomain", "memory", crs=self.crs())
        provider = bbox.dataProvider()
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
        QgsProject.instance().addMapLayer(bbox)

    def constant(self):
        constant_layer = QgsVectorLayer(
            "Point", "timmlConstant", "memory", crs=self.crs()
        )
        provider = constant_layer.dataProvider()
        provider.addAttributes(
            [
                QgsField("head", QVariant.Double),
                QgsField("layer", QVariant.Int),
                QgsField("label", QVariant.String),
            ]
        )
        constant_layer.updateFields()
        QgsProject.instance().addMapLayer(constant_layer)

    def circular_area_sink(self):
        dialog = RadiusDialog()
        dialog.show()
        ok = dialog.exec_()
        if ok:
            layer_name = dialog.layerEdit.text()
            radius = float(dialog.radiusEdit.text())
            sink_layer = QgsVectorLayer(
                "Polygon",
                f"timmlCircularAreaSink:{layer_name}",
                "memory",
                crs=self.crs(),
            )
            provider = sink_layer.dataProvider()
            feature = QgsFeature()
            center = self.iface.mapCanvas().center()
            feature.setGeometry(QgsGeometry.fromPointXY(center).buffer(radius, 5))
            provider.addAttributes(
                [
                    QgsField("rate", QVariant.Double),
                    QgsField("layer", QVariant.Int),
                    QgsField("label", QVariant.String),
                ]
            )
            provider.addFeatures([feature])
            sink_layer.updateFields()
            QgsProject.instance().addMapLayer(sink_layer)

    def uniform_flow(self):
        uflow = QgsVectorLayer("No geometry", "timmlUniformFlow", "memory")
        provider = uflow.dataProvider()
        provider.addAttributes(
            [
                QgsField("slope", QVariant.Double),
                QgsField("angle", QVariant.Double),
                QgsField("label", QVariant.String),
            ]
        )
        uflow.updateFields()
        QgsProject.instance().addMapLayer(uflow)

    def head_line_sink(self):
        dialog = NameDialog()
        dialog.show()
        ok = dialog.exec_()
        if ok:
            layer_name = dialog.lineEdit.text()
            line_layer = QgsVectorLayer(
                "Linestring",
                f"timmlHeadLineSink:{layer_name}",
                "memory",
                crs=self.crs(),
            )
            provider = line_layer.dataProvider()
            provider.addAttributes(
                [
                    QgsField("head", QVariant.Double),
                    QgsField("resistance", QVariant.Double),
                    QgsField("width", QVariant.Double),
                    QgsField("order", QVariant.Int),
                    QgsField("layer", QVariant.Int),
                    QgsField("label", QVariant.String),
                ]
            )
            line_layer.updateFields()
            QgsProject.instance().addMapLayer(line_layer)

    def line_sink_ditch(self):
        dialog = NameDialog()
        dialog.show()
        ok = dialog.exec_()
        if ok:
            layer_name = dialog.lineEdit.text()
            line_layer = QgsVectorLayer(
                "Linestring",
                f"timmlLineSinkDitch:{layer_name}",
                "memory",
                crs=self.crs(),
            )
            provider = line_layer.dataProvider()
            provider.addAttributes(
                [
                    QgsField("discharge", QVariant.Double),
                    QgsField("resistance", QVariant.Double),
                    QgsField("width", QVariant.Double),
                    QgsField("order", QVariant.Int),
                    QgsField("layer", QVariant.Int),
                    QgsField("label", QVariant.String),
                ]
            )
            line_layer.updateFields()
            QgsProject.instance().addMapLayer(line_layer)

    def imp_line_doublet(self):
        dialog = NameDialog()
        dialog.show()
        ok = dialog.exec_()
        if ok:
            layer_name = dialog.lineEdit.text()
            line_layer = QgsVectorLayer(
                "Linestring",
                f"timmlImpLineDoublet:{layer_name}",
                "memory",
                crs=self.crs(),
            )
            provider = line_layer.dataProvider()
            provider.addAttributes(
                [
                    QgsField("order", QVariant.Int),
                    QgsField("layer", QVariant.Int),
                    QgsField("label", QVariant.String),
                ]
            )
            line_layer.updateFields()
            QgsProject.instance().addMapLayer(line_layer)

    def leaky_line_doublet(self):
        dialog = NameDialog()
        dialog.show()
        ok = dialog.exec_()
        if ok:
            layer_name = dialog.lineEdit.text()
            line_layer = QgsVectorLayer(
                "Line", f"timmlLeakyLineDoublet:{layer_name}", "memory", crs=self.crs()
            )
            provider = line_layer.dataProvider()
            provider.addAttributes(
                [
                    QgsField("resistance", QVariant.Double),
                    QgsField("order", QVariant.Int),
                    QgsField("layer", QVariant.Int),
                    QgsField("label", QVariant.String),
                ]
            )
            line_layer.updateFields()
            QgsProject.instance().addMapLayer(line_layer)

    def polygon_inhom(self):
        dialog = NameDialog()
        dialog.show()
        ok = dialog.exec_()
        if ok:
            layer_name = dialog.lineEdit.text()
            properties = QgsVectorLayer(
                "No geometry", "timmlPolygonInhom:{layer_name}", "memory"
            )
            provider = properties.dataProvider()
            provider.addAttributes(
                [
                    QgsField("conductivity", QVariant.Double),
                    QgsField("resistance", QVariant.Double),
                    QgsField("top", QVariant.Double),
                    QgsField("bottom", QVariant.Double),
                    QgsField("topconfined", QVariant.Bool),
                    QgsField("tophead", QVariant.Double),
                    QgsField("order", QVariant.Int),
                    QgsField("ndegrees", QVariant.Int),
                ]
            )
            properties.updateFields()
            QgsProject.instance().addMapLayer(properties)


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
