"""
Setup a dockwidget to hold the qgistim plugin widgets.
"""
from pathlib import Path

from qgis.gui import QgsDockWidget
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction


class TimDockWidget(QgsDockWidget):
    def closeEvent(self, event) -> None:
        """
        Make sure the external interpreter is shutdown as well.
        """
        widget = self.widget()
        widget.shutdown_server()
        event.accept()


class QgisTimPlugin:
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        self.tim_widget = None
        self.plugin_dir = Path(__file__).parent
        self.pluginIsActive = False
        self.toolbar = iface.addToolBar("QgisTim")
        self.toolbar.setObjectName("QgisTim")
        return

    def add_action(self, icon_name, text="", callback=None, add_to_menu=False):
        icon = QIcon(str(self.plugin_dir / icon_name))
        action = QAction(icon, text, self.iface.mainWindow())
        action.triggered.connect(callback)
        if add_to_menu:
            self.toolbar.addAction(action)
        return action

    def initGui(self):
        icon_name = "icon.png"
        self.action_timml = self.add_action(
            icon_name, "QGIS-Tim", self.toggle_timml, True
        )

    def toggle_timml(self):
        if self.tim_widget is None:
            from .widgets.tim_widget import QgisTimWidget

            self.tim_widget = TimDockWidget("QGIS-Tim")
            self.tim_widget.setObjectName("QgisTimDock")
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.tim_widget)
            widget = QgisTimWidget(self.tim_widget, self.iface)
            self.tim_widget.setWidget(widget)
            self.tim_widget.hide()
        self.tim_widget.setVisible(not self.tim_widget.isVisible())

    def unload(self):
        self.toolbar.deleteLater()
