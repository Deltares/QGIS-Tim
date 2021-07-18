from pathlib import Path

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.gui import QgsDockWidget


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
        self.menu = u"Qgis-Tim"
        self.actions = []
        
    def add_action(self, icon_name, text="", callback=None, add_to_menu=False):
        icon = QIcon(str(self.plugin_dir / icon_name))
        action = QAction(icon, text, self.iface.mainWindow())
        action.triggered.connect(callback)
        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)
        self.actions.append(action)
        return action

    def initGui(self):
        icon_name = "icon.png"
        self.action_timml = self.add_action(
            icon_name, "Qgis-TimML", self.toggle_timml, True
        )

    def toggle_timml(self):
        if self.tim_widget is None:
            from .tim_widget import QgisTimmlWidget
            self.tim_widget = TimDockWidget("Qgis-TimML")
            self.tim_widget.setObjectName("QgisTimmlDock")
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.tim_widget)
            widget = QgisTimmlWidget(self.tim_widget, self.iface)
            self.tim_widget.setWidget(widget)
            self.tim_widget.hide()
        self.tim_widget.setVisible(not self.tim_widget.isVisible())

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu("Qgis-Tim", action)
