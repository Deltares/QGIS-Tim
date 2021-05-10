import json
import subprocess

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from qgis.core import (
    QgsGeometry,
    QgsLineString,
    QgsMapLayerType,
    QgsMultiLineString,
    QgsPoint,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
    QgsWkbTypes,
)
from qgis.gui import QgsMapLayerComboBox, QgsMapTool, QgsRubberBand

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


class UpdatingQgsMapLayerComboBox(QgsMapLayerComboBox):
    def enterEvent(self, e):
        self.update_layers()
        super(UpdatingQgsMapLayerComboBox, self).enterEvent(e)

    def update_layers(self):
        # Allow:
        # * Point data with associated IPF borehole data
        # * Mesh layers
        # * Raster layers
        excepted_layers = []
        for layer in QgsProject.instance().mapLayers().values():
            if not is_netcdf_layer(layer):
                excepted_layers.append(layer)
        self.setExceptedLayerList(excepted_layers)


class DataExtractionWidget(QWidget):
    def __init__(self, iface, parent=None):
        super(DataExtractionWidget, self).__init__(parent)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        layout = QHBoxLayout()
        self.layer_selection = UpdatingQgsMapLayerComboBox()
        self.layer_selection.setMinimumWidth(200)
        self.select_polygon_button = QPushButton("Select by Polygon")
        self.select_polygon_button.clicked.connect(self.draw_selection)
        self.polygon_tool = SelectionMapTool(iface)
        self.extract_button = QPushButton("Extract")
        layout.addWidget(self.layer_selection)
        layout.addWidget(self.select_polygon_button)
        layout.addWidget(self.extract_button)
        self.setLayout(layout)

    def draw_selection(self):
        self.canvas.setMapTool(self.polygon_tool)

    def extract(self, interpreter, env_vars, handler):
        layer = self.layer_selection.currentLayer()
        geometries = self.polygon_tool.selected_geometries
        if len(geometries) == 0 or layer is None:
            return
        wkts = ";".join([geom.asWkt() for geom in geometries])
        outpath, _ = QFileDialog.getSaveFileName(self, "New file", "", "*.csv")
        if outpath == "":
            return

        inpath = layer.dataProvider().dataSourceUri().split('"')[1]
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
