from pathlib import Path

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.gui import QgsDockWidget


class QgisTimPlugin:
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        self.timml_widget = None
        self.ttim_widget = None
        self.timml_action = None
        self.ttim_action = None
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
        if self.timml_widget is None:
            from .timml import QgisTimmlWidget
            self.timml_widget = QgsDockWidget("Qgis-TimML")
            self.timml_widget.setObjectName("QgisTimmlDock")
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.timml_widget)
            widget = QgisTimmlWidget(self.timml_widget, self.iface)
            self.timml_widget.setWidget(widget)
            self.timml_widget.hide()
        self.timml_widget.setVisible(not self.timml_widget.isVisible())

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu("Qgis-Tim", action)
