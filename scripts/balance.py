import os.path
from datetime import datetime, timezone
import logging
import sys
import time
import serial.tools.list_ports
import re
from typing import NamedTuple

address = 0
delta = 0.030

NUM_PAT = '([+-]?[0-9]*[.]?[0-9]+)'
CHAR_PAT = '([^0-9])'
BATSUM_PATTERN = '(\$\d{2}[a-z]\d{1})\s+(.)(.)\s+([+-]?[0-9]*[.]?[0-9]+)\s+([+-]?[0-9]*[.]?[0-9]+)\s+([+-]?[0-9]*[.]?[0-9]+)\s+([+-]?[0-9]*[.]?[0-9]+)\s+([+-]?[0-9]*[.]?[0-9]+)\s+([+-]?[0-9]*[.]?[0-9]+)\s+([+-]?[0-9]*[.]?[0-9]+)\s+([+-]?[0-9]*[.]?[0-9]+:[+-]?[0-9]*[.]?[0-9]+:[+-]?[0-9]*[.]?[0-9]+)\s+([a-z])\s+([+-]?[0-9]*[.]?[0-9]+)\s+([+-]?[0-9]*[.]?[0-9]+)\s+([+-]?[0-9]*[.]?[0-9]+)'
VERSUM_PATTERN = '(\$\d{2}[a-z]\d{1})\s+([+-]?[0-9]*[.]?[0-9]+)\s+(.)\s+([+-]?[0-9]*[.]?[0-9]+)\s+([+-]?[0-9]*[.]?[0-9]+)\s+([+-]?[0-9]*[.]?[0-9]+)\s+([+-]?[0-9]*[.]?[0-9]+)\s+(.*)\s+\r'
CELLSUM_PATTERN = '\s+([+-]?[0-9]*[.]?[0-9]+)'

def get_port():
    try:
        port = str(sys.argv[1])
    except:
        available_ports = [v.name for v in serial.tools.list_ports.comports()]
        for port in available_ports:
            with SBM(port, address = address) as sbm:
                versum = sbm.get_version_summary()
                if not isinstance(versum.sn, int):
                    continue
                else:
                    break
    return port

def main():
    port = get_port()
    with SBM(port, address = address) as sbm:
        sbm.reset_battery()

        versum = sbm.get_version_summary()
        _date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        console = initialize_logger(2,versum.sn, _date)
        console.debug(f"{'-'*35} New Run {'-'*35}")
        console.info(f'Connected to Battery {versum.sn}.')
        console.info(f'Battery FW Version: {versum.firmware_info}.')

        current_address = sbm.get_address()
        console.info(f"Current Battery Address: {current_address}")

        summary = sbm.get_summary()
        console.info(f"Current Temperature: {summary.max_temperature}")
        console.info(f"Minimum Cell Voltage: {summary.min_cell_voltage}")
        console.info(f"Maximum Cell Voltage: {summary.max_cell_voltage}")

        state, current_state = sbm.get_state()
        console.info(f"Initial Battery State: {current_state}")

        error, error_state = sbm.get_error_state()
        console.info(f"Initial Error State: {error_state}")

        voltages = sbm.get_cell_voltages()
        console.debug(f"Cell Voltages: {voltages}")

        balanced = sbm.is_balanced(delta=delta)
        if balanced is True:
            console.info('Battery is balanced. Turning off battery.')
            sbm.off()
            console.info('Exiting application.')
            exit()
        else:
            i = 0
            console.info('Starting balancing loop...')
            while balanced is False:
                i += 1
                lstart = time.monotonic()
                summary = sbm.get_summary()
                console.info(f"Balance Loop: {i}")
                console.info(f'Current Temperature: {summary.max_temperature}')

                voltages = sbm.get_cell_voltages()
                console.debug(f"Cell Voltages: {voltages}")

                # Issue Catch: Exceeding maximum allowed temperature.
                if summary.max_temperature >= 42:
                    msg = f"Maximum cell temperature exceeds 42 degrees. Allow battery to cool down before balancing again."
                    console.critical(msg)
                    raise TimeoutError(msg)
                    exit()

                console.info('Balancing cells...')
                sbm.balance_non_min_cells(console)

                balanced = sbm.is_balanced()
                if balanced is True:
                    time.sleep(0.5)
                    console.info('Battery is balanced. Turning off battery.')
                    sbm.off()
                    console.info('Exiting application.')
                    exit()

                else:
                    lstop = time.monotonic()
                    wait = int(60-(lstop-lstart))
                    console.info(f"Starting next loop in {wait} seconds.")
                    time.sleep(wait)



def initialize_logger(console_level,sn,str_date):
    logger = logging.getLogger('bluefin')
    save_dir = os.path.join(os.path.expanduser('~'),'bluefin')
    os.makedirs(save_dir, exist_ok=True)
    save_filepath = os.path.join(save_dir, f'bluefin1.5kwh_{sn}_{str_date}.txt')
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        console = logging.StreamHandler()
        filelog = logging.FileHandler(save_filepath)
        if console_level == 0:
            console.setLevel(logging.ERROR)
            filelog.setLevel(logging.ERROR)
        elif console_level == 1:
            console.setLevel(logging.INFO)
            filelog.setLevel(logging.INFO)
        elif console_level == 2:
            console.setLevel(logging.DEBUG)
            filelog.setLevel(logging.DEBUG)
        else:
            raise ValueError("Console level must be an int between 0-2.")
        dtfmt = '%Y-%m-%dT%H:%M:%S'
        strfmt = '%(asctime)s.%(msecs)03dZ | %(levelname)-8s | %(message)s'
        fmt = logging.Formatter(strfmt, datefmt=dtfmt)
        fmt.converter = time.gmtime
        console.setFormatter(fmt)
        filelog.setFormatter(fmt)

        logger.addHandler(console)
        logger.addHandler(filelog)

    if logger:
        return logger
    else:
        raise ReferenceError("Logger not found.")



class BATTERY_SUMMARY(NamedTuple):
    state: str
    error_state: str
    voltage: float
    current: float
    max_temperature: float
    min_cell_voltage: float
    max_cell_voltage: float
    water_leak_detect: int
    power: float
    runtime: str
    mode: str
    discharge_status_1: int
    discharge_status_2: int
    sleep_timer: int

class VERSION_SUMMARY(NamedTuple):
    address: str
    mode: str
    board_sn: int
    sn: int
    voltage_rating: float
    current_rating: float
    firmware_info: str

class CELL_SUMMARY(NamedTuple):
    cell_1: float
    cell_2: float
    cell_3: float
    cell_4: float
    cell_5: float
    cell_6: float
    cell_7: float
    cell_8: float


class SBM():
    def __init__(self, port, address=0):
        self.rs485 = serial.Serial()
        self.rs485.port = port
        self.rs485.baudrate = 9600
        self.rs485.timeout = 1

        try:
            self.rs485.open()
            self._clear_buffers()
            self.address = self._format_address(address)
        except:
            msg = f"Unable to connect to Bluefin 1.5 kWh battery on port {self.rs485.port}."
            raise ConnectionError(msg)

    def __enter__(self):
        self._clear_buffers()
        return self

    def __exit__(self, et, ev, etb):
        self._clear_buffers()
        self.rs485.close()

    def reset_battery(self, wait = 1):
        self.off()
        time.sleep(wait)
        summary = self.get_summary()
        self._clear_buffers()

    def _clear_buffers(self):
        self.rs485.reset_input_buffer()
        self.rs485.reset_output_buffer()

    def _write_command(self, command, EOL='\r\n'):
        cmd = str.encode(command + EOL)
        self.rs485.write(cmd)

    def _read_response(self, buffer_check: None or float = None):
        if buffer_check is None:
            response = self.rs485.read(self.rs485.in_waiting)
        elif isinstance(buffer_check, (float, int)):
            if self._buffer_check(check_pause=buffer_check) is True:
                response = self.rs485.read(self.rs485.in_waiting)
        data = response.decode()
        return data

    def _buffer_check(self, check_pause=0.05):
        _buffer = self.rs485.in_waiting
        start_time = time.monotonic()
        while time.monotonic() - start_time < 30:
            incoming = self.rs485.in_waiting
            if _buffer == incoming:
                return True
            else:
                _buffer = incoming
                time.sleep(check_pause)
        msg = 'Buffer check is reading continuous data.'
        raise ConnectionError

    def _format_address(self, address):
        """Formats a decimal value into a hexadecimal value that works
            with the Bluefin 1.5 kWh (SmallBattMod).
        @param address -- a decimal value ranging between 0 and 250.
        @return -- the address as a hexadecimal value if the input address
            was between 0 and 250. False if the address is outside of that
            range.
        """
        address = int(address)
        if address >= 1 and address <= 250:
            address = hex(int(address))  # Convert address if between 0-250.
            if len(address) == 3:  # Take the last char and append a zero.
                address = str(address[-1]).rjust(2, '0')
            elif len(address) == 4:
                address = address[-2:]  # Take the last two char.
            return address
        elif address == 0:
            address = '00'
            return address
        else:
            return False

    def get_summary(self):
        cmd = f'#{self.address}q0'
        self._write_command(cmd, EOL='\r\n')
        time.sleep(0.5)
        response = self.rs485.read_until('\r\n').decode()
        [response] = re.findall(BATSUM_PATTERN, response)
        batsum = BATTERY_SUMMARY(state=str(response[1]),
                                 error_state=str(response[2]),
                                 voltage=float(response[3]),
                                 current=float(response[4]),
                                 max_temperature=float(response[5]),
                                 min_cell_voltage=float(response[6]),
                                 max_cell_voltage=float(response[7]),
                                 water_leak_detect=int(response[8]),
                                 power=float(response[9]),
                                 runtime=str(response[10]),
                                 mode=str(response[11]),
                                 discharge_status_1=int(response[12]),
                                 discharge_status_2=int(response[13]),
                                 sleep_timer=int(response[14]))
        return batsum

    def get_version_summary(self):
        cmd = f'#{self.address}z0'
        self._write_command(cmd, EOL='\r\n')
        time.sleep(0.5)
        response = self._read_response()
        [response] = re.findall(VERSUM_PATTERN, response)
        versum = VERSION_SUMMARY(address=str(response[1]),
                                 mode=str(response[2]),
                                 board_sn=int(response[3]),
                                 sn=int(response[4]),
                                 voltage_rating=float(response[5]),
                                 current_rating=float(response[6]),
                                 firmware_info=str(response[7]))
        return versum

    def get_cell_voltages(self):
        self._write_command(f'#{self.address}q1')
        time.sleep(0.5)
        response = self._read_response()
        # return response
        voltages = list(map(float, re.findall(CELLSUM_PATTERN, response)))
        if len(voltages) != 8:
            raise ValueError('Response did not return all cell voltages.')
        # cellsum = CELL_SUMMARY(cell_1 = voltages[0],
        #                        cell_2 = voltages[1],
        #                        cell_3 = voltages[2],
        #                        cell_4 = voltages[3],
        #                        cell_5 = voltages[4],
        #                        cell_6 = voltages[5],
        #                        cell_7 = voltages[6],
        #                        cell_8 = voltages[7])
        return voltages

    # ---------------------------Battery Commands---------------------------------#
    def set_address(self, address: int):
        """Sets the battery address.
        The battery must be the only battery on the RS485 bus.
        @param address -- a decimal value ranging between 0 and 250
        """
        new_address = self._format_address(address)
        self._write_command(f'#00?8 {new_address}')
        self._clear_buffers()
        time.sleep(0.2)

    def get_address(self):
        """Get the battery address.
        This function only works when the battery is the
        only battery on the bus.
        @return -- the address as a decimal value.
        """
        self._clear_buffers()
        self._write_command('#00?0')
        time.sleep(0.5)
        response = self._read_response()
        pattern = '\s+(.*?)\s+'
        [hexval] = re.findall(pattern, response)
        address = int(hexval, 16)
        return address

    def get_state(self):
        summary = self.get_summary()
        if summary.state == 'f':
            msg = 'OFF'
        elif summary.state == 'd':
            msg = 'DISCHARGING'
        elif summary.state == 'c':
            msg = 'CHARGING'
        elif summary.state == 'b':
            msg = 'BALANCING'
        return summary.state, msg

    def get_error_state(self):
        summary = self.get_summary()
        if summary.error_state == '-':
            msg = 'No Error'
        elif summary.error_state == 'V':
            msg = 'Battery over voltage'
        elif summary.error_state == 'v':
            msg = 'Battery under voltage'
        elif summary.error_state == 'I':
            msg = 'Battery over current'
        elif summary.error_state == 'C':
            msg = 'Battery max cell over voltage'
        elif summary.error_state == 'c':
            msg = 'Battery min cell under voltage'
        elif summary.error_state == 'x':
            msg = 'Battery min cell under fault voltage (2.0V)'
        elif summary.error_state == 'T':
            msg = 'Battery over temperature'
        elif summary.error_state == 'W':
            msg = 'Battery moisture intrusion detected by H2O sensors'
        elif summary.error_state == 'H' or summary.error_state == 'h':
            msg = 'Battery internal hardware fault'
        elif summary.error_state == 'm':
            msg = 'Battery watchdog timeout'
        return summary.error_state, msg

    def get_voltage(self):
        summary = self.get_summary()
        return summary.voltage

    def get_current(self):
        summary = self.get_summary()
        return summary.current

    def get_max_temperature(self):
        summary = self.get_summary()
        return summary.max_temperature

    def get_min_max_cell_voltage(self):
        summary = self.get_summary()
        return summary.min_cell_voltage, summary.max_cell_voltage

    def water_detected(self):
        summary = self.get_summary()
        if summary.water_leak_detect == 0:
            return False
        elif summary.water_leak_detect == 1:
            return True

    def get_power(self):
        summary = self.get_summary()
        return summary.power

    def get_runtime(self):
        summary = self.get_summary()
        hms = summary.runtime.split(':')
        msg = 'Battery has been enabled for {}h, {}m, and {}s.'
        print(msg.format(hms[0], hms[1], hms[2]))
        return hms

    def get_sleep_time(self):
        summary = self.get_summary()
        timer = summary.sleep_timer
        if timer == 0:
            print('Sleep timer is disabled.')
        else:
            print('Battery will go to sleep in {} seconds.'.format(timer))
        return timer

    def get_battery_sn(self):
        '''Get the battery serial number.
        @return -- the serial number as an integer.
        '''
        summary = self.get_version_summary()
        return summary.sn

    def get_fw_version(self):
        """Get the firmware version.
        @return -- the firmware as a string
        """
        summary = self.get_version_summary()
        return summary.firmware_info

    def get_voltage_rating(self):
        """Get the battery's voltage rating.
        @return -- the voltage rating as an integer
        """
        summary = self.get_version_summary()
        return summary.voltage_rating

    def get_current_rating(self):
        """Get the battery's current rating.
        @return -- the current rating as an integer
        """
        summary = self.get_version_summary()
        return summary.current_rating

    def get_mode(self):
        """Get the battery mode.
        @return -- the battery mode as a single character string (m or s)
        """
        summary = self.get_version_summary()
        return summary.mode

    def sleep(self, length=0):
        """Put the battery to sleep.
        @param length -- the number of seconds to wait before going to sleep.
        """
        self._write_command(f'#{self.address}bs {length}')
        time.sleep(3)

    def off(self):
        """Turn off the battery.
        This resets any existing errors.
        """
        self._write_command(f'#{self.address}bf')
        time.sleep(1)

    def balance_cell(self, cell):
        '''Discharge a cell of the battery for balancing.
        @param cell -- the whole number value for a cell (0-7)
        @return -- True if the command was accepted. False if not.
        '''
        self._write_command(f'#{self.address}b{cell}')
        time.sleep(0.5)
        response = self._read_response()
        pattern = '\$....\s+([0-9])\s+'

        balancing = int(re.findall(pattern, response)[-1])
        if balancing == 1:
            return True
        else:
            return False

    def balance_max_cell(self):
        self._write_command(f"#{self.address}bb")
        time.sleep(0.5)
        response = self._read_response()
        pattern = '\s+([0-9])\s+'
        [balancing] = re.findall(pattern, response)
        if balancing == 1:
            return True
        else:
            return False

    # ----------------------------------Tests-------------------------------------#
    def is_balanced(self, delta=0.030):
        """Compare the min and max cell voltages. If the delta between values
        exceeds 0.03V, it is recommended that the battery be balanced.
        @return -- True/False in relation to the balanced state.
        """
        mincell, maxcell = self.get_min_max_cell_voltage()
        if abs(maxcell - mincell) > delta:
            return False
        else:
            return True

    # --------------------------------Balance-------------------------------------#
    def balance_non_min_cells(self, logger):
        '''Discharge and balance cells that are not the minimum voltage cell
        '''
        voltages = self.get_cell_voltages()
        if self._check_all_cells(voltages) is True:
            logger.info('All cells are within 30mV of each other.')
            exit()
        for i in range(len(voltages)):
            if voltages[i] == min(voltages):
                logger.info(f"Cell #{i} is the minimum cell.")
                continue
            elif voltages[i] - 0.030 < min(voltages) < voltages[i] + 0.030:
                logger.info(f"Cell #{i} is within 30mV of the minimum cell.")
                continue
            else:
                if self.balance_cell(i) is True:
                    logger.info(f"Cell #{i} discharging...{round(voltages[i] - min(voltages),3)*1000}mV from minimum cell.")
                    time.sleep(1)
                    continue
                else:
                    logger.info(f"Unable to discharge cell #{i}.")
                    error, error_msg = self.get_error_state()
                    if error == 'm':
                        logger.error('Reason: Watchdog timeout. Resetting.')
                        self.reset_battery(5)
                        self.balance_cell()
                        logger.info(f"Cell # {i} discharging...{round(voltages[i] - min(voltages),3)*1000}mV from minimum cell.")
                        time.sleep(1)
                        continue

    def _check_all_cells(self, voltages):
        '''Check if all cells are within 30mV of the minimum cell.'''
        for voltage in voltages:
            if voltage < min(voltages) - 0.030 or voltage > min(voltages) + 0.030:
                return False
        return True


if __name__ == "__main__":
    main()