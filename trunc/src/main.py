import sys
import serial
from modbus_tk import modbus_rtu
from sunline import AutoTransformer
from mainform import Ui_MainWindow
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtWidgets import QMessageBox, QStyleFactory


class MyMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("Sunline", "sunline-automation");
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.readSettings()

    def writeSettings(self):
        geometry = self.saveGeometry()
        self.settings.setValue('geometry', geometry)

        dockwidget_visible = self.ui.dockWidget.isVisible()
        self.settings.setValue('dockwidget_visible', dockwidget_visible)

        dockwidget_floating = self.ui.dockWidget.isFloating()
        self.settings.setValue('dockwidget_floating', dockwidget_floating)

        dockwidget_geometry = self.ui.dockWidget.saveGeometry()
        self.settings.setValue('dockwidget_geometry', dockwidget_geometry)

        area = self.dockWidgetArea(self.ui.dockWidget)
        self.settings.setValue('dockwidget_area', area)

    def readSettings(self):
        geometry = self.settings.value('geometry', type=QtCore.QByteArray)
        self.restoreGeometry(geometry)

        dockwidget_visible = self.settings.value('dockwidget_visible', type=bool)
        self.ui.dockWidget.setVisible(dockwidget_visible)
        self.ui.actShowHideDockWidget.setChecked(dockwidget_visible)

        dockwidget_floating = self.settings.value('dockwidget_floating', type=bool)
        self.ui.dockWidget.setFloating(dockwidget_floating)

        dockwidget_geometry = self.settings.value('dockwidget_geometry', type=QtCore.QByteArray)
        self.ui.dockWidget.restoreGeometry(dockwidget_geometry)

        area = self.settings.value('dockwidget_area')
        if area is None:
            area = QtCore.Qt.DockWidgetArea(8)
        self.addDockWidget(area, self.ui.dockWidget)

    def closeEvent(self, e):
        reply = QMessageBox.question(self,
            'Подтверждение',
            "Выйти из приложения?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.form_close()
            self.writeSettings()
            e.accept()
        else:
            e.ignore()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()

try:
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle(QStyleFactory.keys()[3])
    MainWindow = MyMainWindow()
    MainWindow.show()

    sys.exit(app.exec_())
except Exception as e:
    print(e)
