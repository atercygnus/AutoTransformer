from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QMessageBox
from sunline import AutoTransformer
import modbus_tk.defines as cst
from modbus_tk import exceptions
from serial.tools import list_ports


def serial_ports():
    return [comport.device for comport in list_ports.comports()]
    """ports = ['COM%s' % (i + 1) for i in range(256)]
    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result"""


class Ui_Dialog(QtWidgets.QDialog):
    device = None
    accept = None
    def __init__(self, device):
        super().__init__()
        self.device = device
        self.setObjectName("Dialog")
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.resize(258, 97)
        self.formLayout = QtWidgets.QFormLayout(self)
        self.formLayout.setObjectName("formLayout")
        self.lb_baud = QtWidgets.QLabel(self)
        self.lb_baud.setObjectName("label")
        self.lb_baud.setText("Скорость соединения, бод:")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.lb_baud)
        self.baud = QtWidgets.QComboBox(self)
        self.baud.setObjectName("baud")
        self.baud.addItems(["300", '1200', '2400', '4800', '9600', '19200', '28800', '38400', '57600'])
        self.baud.setCurrentIndex(self.baud.findText('19200', QtCore.Qt.MatchFixedString))
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.baud)
        self.lb_port = QtWidgets.QLabel(self)
        self.lb_port.setObjectName("lb_port")
        self.lb_port.setText("Порт:")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.lb_port)
        self.port = QtWidgets.QComboBox(self)
        self.port.setObjectName("port")
        self.port.addItems(serial_ports())
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.port)
        self.buttonBox = QtWidgets.QDialogButtonBox(self)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.rejected.connect(self.reject_)
        self.buttonBox.accepted.connect(self.accept_)
        self.buttonBox.setObjectName("buttonBox")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.SpanningRole, self.buttonBox)
        self.setWindowTitle("Соединение с устройством")

        QtCore.QMetaObject.connectSlotsByName(self)

    def reject_(self):
        self.accept = False
        self.close()

    def accept_(self):
        self.accept = True
        baud_ = self.baud.currentText()
        port_ = self.port.currentText()
        try:
            if self.device is None:
                self.device = AutoTransformer(port_, baud_, autoupdate=True, autocommit=True)
                self.device.rtu_master.execute(1, cst.READ_DISCRETE_INPUTS, 0, 1)
            else:
                self.device.rtu_master._serial.port = port_
                self.device.rtu_master._serial.baudrate = baud_
                self.device.rtu_master._serial.close()
                self.device.rtu_master._serial.open()
                self.device.rtu_master.execute(1, cst.READ_DISCRETE_INPUTS, 0, 1)
        except exceptions.ModbusInvalidResponseError:
            QMessageBox.critical(self, 'Ошибка', 'Не удалось установить соединение.', QMessageBox.Ok, QMessageBox.Ok)
            self.accept = False
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', 'Произошла ошибка.\n%s' % str(e), QMessageBox.Ok, QMessageBox.Ok)
            self.accept = False

        if self.accept:
            self.close()
