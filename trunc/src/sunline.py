import modbus_tk.defines as cst
from modbus_tk import modbus_rtu
from modbus_tk.modbus import ModbusInvalidResponseError
from PyQt5.QtCore import pyqtSignal, QObject
from threading import Thread, Event
from modbus_tk import modbus
from serial import Serial
from datetime import datetime

class Communicate(QObject):
    RegistersUpdated = pyqtSignal()
    RegistersCommited = pyqtSignal()
    ErrorReadingRegister = pyqtSignal(str)
    ErrorCommitingRegister = pyqtSignal(str)


def get_modbus_funccode(reg_type: int, action: str = 'read'):
    reg_types = {cst.COILS: [cst.READ_COILS, cst.WRITE_SINGLE_COIL, cst.WRITE_MULTIPLE_COILS],
                 cst.DISCRETE_INPUTS: [cst.READ_DISCRETE_INPUTS],
                 cst.HOLDING_REGISTERS: [cst.READ_DISCRETE_INPUTS, cst.WRITE_SINGLE_REGISTER, cst.WRITE_MULTIPLE_REGISTERS],
                 cst.ANALOG_INPUTS: [cst.READ_INPUT_REGISTERS]}
    actions = {'read': [cst.READ_COILS, cst.READ_DISCRETE_INPUTS, cst.READ_HOLDING_REGISTERS, cst.READ_INPUT_REGISTERS],
               'write': [cst.WRITE_MULTIPLE_REGISTERS, cst.WRITE_MULTIPLE_COILS]}
    return list(set(reg_types[reg_type]) & set(actions[action]))[0]


class Register:
    def __init__(self, device, name: str, regtype: int, address: int):
        self.name = name
        self.reg_type = regtype
        self.address = address
        self.device = device
        # Текущее значение региста. Показывает текущее состояние регистра устройства.
        self.__value__ = None
        # Это значение было записано в регистр, и может быть отправлено в устройство с помощью метода commit()
        self.__commit_buffer__ = None

    def __get_value__(self):
        if self.__commit_buffer__ is None:
            if self.__value__ is not None:
                return self.__value__
            else:
                self.device.communicate.ErrorReadingRegister.emit('Reg value is None')
                return -1
        else:
            return self.__commit_buffer__

    def __set_value__(self, value: int):
        if self.__commit_buffer__ != value:
            self.__commit_buffer__ = value

    def __internal_commit__(self):
        try:
            funcode = get_modbus_funccode(self.reg_type, 'write')
        except IndexError:
            raise Exception('This register for read only')
        try:
            self.device.rtu_master.execute(1, funcode, self.address, output_value=[int(self.__commit_buffer__)])
        except ModbusInvalidResponseError as e:
            self.device.communicate.ErrorCommitingRegister.emit('Error while writing %s' % self.name)
        except modbus.struct.error as ste:
            pass
        self.__value__ = self.__commit_buffer__
        self.__commit_buffer__ = None

    def commit(self):
        writer = Thread(target=self.__internal_commit__)
        writer.start()

    def __get_modified__(self):
        return not self.__commit_buffer__ is None

    def reset(self):
        if not self.__commit_buffer__ is None:
            self.__value__ = self.__commit_buffer__
        self.__commit_buffer__ = None

    value = property(__get_value__, __set_value__)
    modified = property(__get_modified__)


class SunlineDevice:
    discrete_input_list = []
    coil_list = []
    input_register_list = []
    holding_register_list = []

    class StopableThread(Thread):
        def __init__(self, proc, interval):
            Thread.__init__(self)
            self.interval = interval
            self._stopevent = Event()
            self.proc = proc
        def run(self):
            self._stopevent.clear()
            while not self._stopevent.isSet():
                self.proc()
                self._stopevent.wait(self.interval)
        def stop(self):
            self._stopevent.set()

    def __init__(self, port, baudrate, autoupdate, autocommit, update_interval, commit_interval):
        self.update_interval = update_interval
        self.commit_interval = commit_interval
        self.autoupdate = autoupdate
        self.autocommit = autocommit

        self.rtu_master = modbus_rtu.RtuMaster(Serial(port=port, baudrate=baudrate, \
                                                      bytesize=8, parity='N', stopbits=1, xonxoff=0))
        self.rtu_master.set_timeout(3)

        self.discrete_regs = [Register(*reg) for reg in self.discrete_input_list]
        self.coil_regs = [Register(*reg) for reg in self.coil_list]
        self.input_regs = [Register(*reg) for reg in self.input_register_list]
        self.holding_regs = [Register(*reg) for reg in self.holding_register_list]

        self.regs = self.discrete_regs + self.coil_regs + self.input_regs + self.holding_regs

        self.communicate = Communicate()

        self.start()

    def commit_coils(self): raise NotImplementedError

    def commit_holding(self): raise NotImplementedError

    def commit_registers(self):
        if not self.commit_coils():
            self.commit_holding()

        self.communicate.RegistersCommited.emit()

        #print(datetime.now(), ' commited!')

    def internal_update_discrete_inputs(self): raise NotImplementedError

    def internal_update_coil_data(self): raise NotImplementedError

    def internal_update_analog_data(self): raise NotImplementedError

    def internal_update_holding_data(self): raise NotImplementedError

    def update_discrete_inputs(self):
        try:
            self.internal_update_discrete_inputs()
        except modbus_rtu.ModbusInvalidResponseError as e:
            self.communicate.ErrorReadingRegister.emit('Error while getting discrete')
        except Exception as e:
            self.communicate.ErrorReadingRegister.emit(str(e))

    def update_coil_data(self):
        try:
            self.internal_update_coil_data()
        except modbus_rtu.ModbusInvalidResponseError as e:
            self.communicate.ErrorReadingRegister.emit('Error while getting coil')
        except Exception as e:
            self.communicate.ErrorReadingRegister.emit(str(e))

    def update_analog_data(self):
        try:
            self.internal_update_analog_data()
        except modbus_rtu.ModbusInvalidResponseError as e:
            self.communicate.ErrorReadingRegister.emit('Error while getting analog')
        except Exception as e:
            self.communicate.ErrorReadingRegister.emit(str(e))

    def update_holding_data(self):
        try:
            self.internal_update_holding_data()
        except modbus_rtu.ModbusInvalidResponseError as e:
            self.communicate.ErrorReadingRegister.emit('Error while getting holding')
        except Exception as e:
            self.communicate.ErrorReadingRegister.emit(str(e))

    def update_registers(self):
        self.update_discrete_inputs()
        self.update_coil_data()
        self.update_analog_data()
        self.update_holding_data()

        self.communicate.RegistersUpdated.emit()

        #print(datetime.now(), 'updated!')

        if not self.commiter._started.is_set() and self.autocommit:
            self.commiter.start()

    def reset_modified(self):
        for reg in self.regs:
            reg.__commit_buffer__ = None

    def stop(self):
        self.rtu_master.close()
        self.commiter.stop()
        self.updater.stop()

    def start(self):
        #if self.rtu_master._is_opened():
        #    raise Exception
        self.rtu_master.open()
        self.updater = self.StopableThread(self.update_registers, self.update_interval)
        self.commiter = self.StopableThread(self.commit_registers, self.commit_interval)
        if self.autoupdate:
            self.updater.start()

    def __getitem__(self, name: str):
        for reg in self.regs:
            if reg.name == name:
                return reg
        return None


class AutoTransformer(SunlineDevice):
    def __init__(self, port, baudrate, autoupdate, autocommit, update_interval=0.1, commit_interval=1):
        self.discrete_input_list = [
            (self, 'Alarm', cst.DISCRETE_INPUTS, 0),
            (self, 'Initial_JP', cst.DISCRETE_INPUTS, 1),
            (self, 'Press_rel', cst.DISCRETE_INPUTS, 2),
            (self, 'Motor_Termo', cst.DISCRETE_INPUTS, 3),
            (self, 'Fire_Alarm', cst.DISCRETE_INPUTS, 4),
            (self, 'Contact_Hatch', cst.DISCRETE_INPUTS, 5),
            (self, 'Fan_start', cst.DISCRETE_INPUTS, 6),
            (self, 'ZAS_state', cst.DISCRETE_INPUTS, 7)
        ]
        self.coil_list = [
            (self, 'ZAS', cst.COILS, 0),
            (self, 'FAN_START', cst.COILS, 1),
            (self, 'Reset', cst.COILS, 31)
        ]
        self.input_register_list = [
            (self, 'INTERN_TEMPER', cst.ANALOG_INPUTS, 0),
            (self, 'Alarm_code', cst.ANALOG_INPUTS, 2),
            (self, 'INT_REGUL', cst.ANALOG_INPUTS, 3),
            (self, 'EXT_REGUL', cst.ANALOG_INPUTS, 6),
            (self, 'MODE_CODE', cst.ANALOG_INPUTS, 7),
            (self, 'Power_W', cst.ANALOG_INPUTS, 8),
            (self, 'Fan_current', cst.ANALOG_INPUTS, 9)
        ]
        self.holding_register_list = [
            (self, 'DAC_LEVEL', cst.HOLDING_REGISTERS, 0),
            (self, 'SL_ADDR', cst.HOLDING_REGISTERS, 10),
            (self, 'RS485_BAUD', cst.HOLDING_REGISTERS, 11),
            (self, 'MODE_CODE_H', cst.HOLDING_REGISTERS, 12),
            (self, 'DEFAULT_POWER', cst.HOLDING_REGISTERS, 13),
            (self, 'MAX_CURRENT', cst.HOLDING_REGISTERS, 14),
            (self, 'Hatch_Timeout', cst.HOLDING_REGISTERS, 15),
            (self, 'OVERLOAD_TIME', cst.HOLDING_REGISTERS, 16),
            (self, 'MIN_CURRENT', cst.HOLDING_REGISTERS, 17),
            (self, 'Press_timeout', cst.HOLDING_REGISTERS, 18),
        ]

        super().__init__(port, baudrate, autoupdate, autocommit, update_interval, commit_interval)

    def internal_update_discrete_inputs(self):
        discrete_data = self.rtu_master.execute(1, cst.READ_DISCRETE_INPUTS, 0, 8)
        for reg in self.discrete_regs:
            reg.__value__ = discrete_data[reg.address]

    def internal_update_coil_data(self):
        coil_data = self.rtu_master.execute(1, cst.READ_COILS, 0, 32)
        for reg in self.coil_regs:
            reg.__value__ = coil_data[reg.address]

    def internal_update_analog_data(self):
        analog_data = self.rtu_master.execute(1, cst.READ_INPUT_REGISTERS, 0, 10)
        for reg in self.input_regs:
            reg.__value__ = analog_data[reg.address]

    def internal_update_holding_data(self):
        holding_data = self.rtu_master.execute(1, cst.READ_HOLDING_REGISTERS, 0, 19)
        for reg in self.holding_regs:
            reg.__value__ = holding_data[reg.address]

    def commit_holding(self):
        if self['DAC_LEVEL'].modified:
            try:
                self.rtu_master.execute(1, cst.WRITE_MULTIPLE_REGISTERS, 0, output_value=[self['DAC_LEVEL'].value])
            except:
                self.communicate.ErrorCommitingRegister.emit('Error while commiting holding register(s)')
            return True

        regs_ = [self['SL_ADDR'],
                  self['RS485_BAUD'],
                  self['MODE_CODE_H'],
                  self['DEFAULT_POWER'],
                  self['MAX_CURRENT'],
                  self['Hatch_Timeout'],
                  self['OVERLOAD_TIME'],
                  self['MIN_CURRENT'],
                  self['Press_timeout']]

        if sum([reg.modified for reg in regs_]) > 0:
            try:
                self.rtu_master.execute(1, cst.WRITE_MULTIPLE_REGISTERS, 10, output_value=[int(reg.value) for reg in regs_])
            except:
                self.communicate.ErrorCommitingRegister.emit('Error while commiting holding register(s)')
            for reg in regs_:
                reg.reset()
            return True

        return False

    def commit_coils(self):
        if self['ZAS'].modified or self['FAN_START'].modified:
            try:
                self.rtu_master.execute(1, cst.WRITE_MULTIPLE_COILS, 0, output_value=[self['ZAS'].value, self['FAN_START'].value])
            except:
                self.communicate.ErrorCommitingRegister.emit('Error while commiting coil register(s)')
            self['ZAS'].reset()
            self['FAN_START'].reset()
            return True

        if self['Reset'].modified:
            try:
                self.rtu_master.execute(1, cst.WRITE_MULTIPLE_COILS, 31, output_value=[self['Reset'].value])
            except:
                self.communicate.ErrorCommitingRegister.emit('Error while commiting coil register(s)')
            self['Reset'].reset()
            return True

        return False
