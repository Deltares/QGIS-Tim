"""
This widget enables drawing of a polygon, which is then used to sample from a
netCDF dataset. Most of the drawing logic comes from this plugin:
https://github.com/lutraconsulting/serval

Apart from the drawing logic, it contains some logic to add all the different
layers of the dataset with some default styling.
"""
import json
import subprocess
from pathlib import Path

from osgeo import gdal
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from qgis.core import (
    Qgis,
    QgsGeometry,
    QgsLayerTreeGroup,
    QgsMapLayerType,
    QgsProject,
    QgsRasterLayer,
    QgsWkbTypes,
)
from qgis.gui import QgsMapTool, QgsRubberBand

from ..core import layer_styling

RUBBER_BAND_COLOR = QColor(Qt.yellow)


class SelectionMapTool(QgsMapTool):
    """
    Raster cells selection tool
    """

    NEW_SELECTION = "New selection"
    ADD_TO_SELECTION = "Add to selection"
    REMOVE_FROM_SELECTION = "Remove from selection"

    def __init__(self, iface):
        super(SelectionMapTool, self).__init__(iface.mapCanvas())
        self.iface = iface
        self.mode = None
        self.geom_type = QgsWkbTypes.PolygonGeometry
        self.current_rubber_band = QgsRubberBand(
            self.iface.mapCanvas(), QgsWkbTypes.PolygonGeometry
        )
        self.selected_rubber_band = QgsRubberBand(
            self.iface.mapCanvas(), QgsWkbTypes.PolygonGeometry
        )
        self.current_points = []
        self.selected_geometries = []
        self.last_pos = None
        self.sel_line_width = 1
        self.cur_sel_color = Qt.yellow
        self.cur_sel_fill_color = QColor(Qt.yellow)
        self.cur_sel_fill_color.setAlpha(20)
        self.sel_color = Qt.yellow
        self.sel_fill_color = QColor(Qt.yellow)
        self.sel_fill_color.setAlpha(20)

    def set_prev_tool(self, prev_tool):
        self.prev_tool = prev_tool

    def deactivate(self):
        QgsMapTool.deactivate(self)

    def reset(self):
        self.current_rubber_reset()
        self.selected_rubber_reset()
        self.raster = None
        self.current_points = []
        self.selected_geometries = []

    def selecting_finished(self):
        self.current_selection_reset()

    def current_rubber_reset(
        self, col=None, fill_col=None, width=1, geom_type=QgsWkbTypes.PolygonGeometry
    ):
        if self.current_rubber_band is None:
            return
        self.current_rubber_band.reset(geom_type)
        self.current_rubber_band.setColor(col if col else self.cur_sel_color)
        self.current_rubber_band.setWidth(width)
        self.current_rubber_band.setFillColor(
            fill_col if fill_col else self.cur_sel_fill_color
        )

    def current_selection_reset(self):
        self.current_points = []
        self.current_rubber_reset()

    def selected_rubber_reset(
        self, col=None, fill_col=None, width=1, geom_type=QgsWkbTypes.PolygonGeometry
    ):
        if self.selected_rubber_band is None:
            return
        self.selected_rubber_band.reset(geom_type)
        self.selected_rubber_band.setColor(col if col else self.sel_color)
        self.selected_rubber_band.setWidth(width)
        self.selected_rubber_band.setFillColor(
            fill_col if fill_col else self.sel_fill_color
        )

    def clear_all_selections(self):
        self.current_selection_reset()
        self.selected_rubber_reset()
        self.selected_geometries = []

    def create_selecting_geometry(self, cur_position=None):
        pt = [cur_position] if cur_position else []
        if self.geom_type == QgsWkbTypes.LineGeometry:
            geom = QgsGeometry.fromPolylineXY(self.current_points + pt).buffer(
                self.sel_line_width / 2.0, 5
            )
        else:
            if len(self.current_points) < 2:
                geom = QgsGeometry.fromPolylineXY(self.current_points + pt)
            else:
                poly_pts = [self.current_points + pt]
                geom = QgsGeometry.fromPolygonXY(poly_pts)
        return geom

    def current_rubber_update(self, cur_position=None):
        self.current_rubber_reset()
        if not self.current_points:
            return
        geom = self.create_selecting_geometry(cur_position=cur_position)
        self.current_rubber_band.addGeometry(geom, None)
        if geom.isGeosValid():
            # self.uc.clear_bar_messages()
            pass
        else:
            # self.uc.bar_warn("Selected geometry is invalid")
            print("Selected geometry is invalid")

    def selected_rubber_update(self):
        self.selected_rubber_reset()
        if self.selected_geometries is None:
            return
        for geom in self.selected_geometries:
            self.selected_rubber_band.addGeometry(geom, None)

    def canvasMoveEvent(self, e):
        if len(self.current_points) == 0:
            return
        self.current_rubber_update(self.toMapCoordinates(e.pos()))
        self.last_pos = self.toMapCoordinates(e.pos())

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            # self.uc.bar_info("Tool aborted")
            print("Tool aborted")
            self.selecting_finished()
        elif e.key() == Qt.Key_Backspace:
            if self.current_points:
                self.current_points.pop()
            self.current_rubber_update(
                cur_position=self.last_pos if self.last_pos else None
            )

    def canvasReleaseEvent(self, e):
        if e.button() == Qt.RightButton:
            modifiers = QApplication.keyboardModifiers()
            if modifiers == Qt.ShiftModifier:
                self.selection_mode = self.REMOVE_FROM_SELECTION
            elif modifiers == Qt.ControlModifier:
                self.selection_mode = self.ADD_TO_SELECTION
            else:
                self.selection_mode = self.NEW_SELECTION
            self.update_selection()
            return
        if e.button() != Qt.LeftButton:
            return

        cur_pos = self.toMapCoordinates(e.pos())
        if len(self.current_points) == 0:
            self.current_points = [cur_pos]
        else:
            self.current_points.append(cur_pos)
        self.current_rubber_update(cur_position=cur_pos)

    def update_selection(self):
        if len(self.current_points) == 0:
            return

        new_geom = self.create_selecting_geometry()
        if new_geom.isEmpty():
            return
        if self.selection_mode == self.NEW_SELECTION:
            self.selected_geometries = [new_geom]
        elif self.selection_mode == self.ADD_TO_SELECTION:
            self.selected_geometries.append(new_geom)
        else:
            # distract from existing geometries
            new_geoms = []
            for exist_geom in self.selected_geometries:
                geom = exist_geom.difference(new_geom)
                if (
                    not geom.isGeosValid()
                    or not geom.type() == QgsWkbTypes.PolygonGeometry
                ):
                    continue
                new_geoms.append(geom)
            self.selected_geometries = new_geoms
        self.selected_rubber_update()
        self.current_selection_reset()
        # self.uc.bar_info("Selection created")


def is_netcdf_layer(layer):
    if not (layer.type() == QgsMapLayerType.RasterLayer):
        return False
    if not "NETCDF" in layer.name():
        return False
    return True


class DataExtractionWidget(QWidget):
    def __init__(self, parent):
        super(DataExtractionWidget, self).__init__(parent)
        self.parent = parent
        self.canvas = parent.iface.mapCanvas()
        layout = QVBoxLayout()
        netcdf_row = QHBoxLayout()
        extraction_row = QHBoxLayout()
        self.netcdf_line_edit = QLineEdit()
        self.netcdf_line_edit.setEnabled(False)  # Just used as a viewing port
        self.open_netcdf_button = QPushButton("Open")
        self.open_netcdf_button.clicked.connect(self.open_netcdf)
        self.add_to_qgis_checkbox = QCheckBox("Add to QGIS")
        self.add_to_qgis_checkbox.setChecked(True)
        self.select_polygon_button = QPushButton("Select by Polygon")
        self.select_polygon_button.clicked.connect(self.draw_selection)
        self.polygon_tool = SelectionMapTool(parent.iface)
        self.extract_button = QPushButton("Extract")
        # Layout
        netcdf_row.addWidget(self.netcdf_line_edit)
        netcdf_row.addWidget(self.open_netcdf_button)
        netcdf_row.addWidget(self.add_to_qgis_checkbox)
        extraction_row.addWidget(self.select_polygon_button)
        extraction_row.addWidget(self.extract_button)
        layout.addLayout(netcdf_row)
        layout.addLayout(extraction_row)
        layout.addStretch()
        self.setLayout(layout)

    def open_netcdf(self):
        netcdf_path, _ = QFileDialog.getOpenFileName(self, "Select file", "", "*.nc")
        if netcdf_path == "":  # Empty string in case of cancel button press
            return
        self.netcdf_line_edit.setText(netcdf_path)

        if not self.add_to_qgis_checkbox.isChecked():
            return

        # Get the variables:
        ds = gdal.Open(netcdf_path)
        metadata = ds.GetMetadata("SUBDATASETS")
        paths = [v for k, v in metadata.items() if "_NAME" in k]

        root = QgsProject.instance().layerTreeRoot()
        netcdf_group = root.addGroup(Path(netcdf_path).stem)
        for path in paths:
            variable = path.split(":")[-1]
            group = QgsLayerTreeGroup(variable, False)
            group.setExpanded(False)
            netcdf_group.addChildNode(group)
            # Check layer for number of bands
            layer = QgsRasterLayer(path, "", "gdal")
            bandcount = layer.bandCount()
            for band in range(1, bandcount + 1):  # Bands use 1-based indexing
                layer = QgsRasterLayer(path, f"{variable}-{band - 1}", "gdal")
                renderer = layer_styling.pseudocolor_renderer(
                    layer, band, colormap="Magma", nclass=10
                )
                maplayer = QgsProject.instance().addMapLayer(layer, False)
                if renderer is not None:
                    maplayer.setRenderer(renderer)
                group.addLayer(maplayer)
            group.setItemVisibilityCheckedRecursive(False)

    def draw_selection(self):
        self.canvas.setMapTool(self.polygon_tool)

    def extract(self, interpreter, env_vars, handler):
        inpath = self.netcdf_line_edit.text()
        geometries = self.polygon_tool.selected_geometries
        if len(geometries) == 0:
            return

        wkts = ";".join([geom.asWkt() for geom in geometries])
        outpath, _ = QFileDialog.getSaveFileName(self, "New file", "", "*.csv")
        if outpath == "":
            return

        if handler is None:
            subprocess.Popen(
                f'{interpreter} -m gistim extract "{inpath}" "{outpath}" "{wkts}"',
                env=env_vars[interpreter],
            )
        else:
            data = json.dumps(
                {
                    "operation": "extract",
                    "inpath": inpath,
                    "outpath": outpath,
                    "wkt_geometry": wkts,
                }
            )
            received = handler.send(data)
            if received != "0":
                self.iface.messageBar().pushMessage(
                    "Error",
                    "Something seems to have gone wrong, "
                    "try checking the TimServer window...",
                    level=Qgis.Critical,
                )
