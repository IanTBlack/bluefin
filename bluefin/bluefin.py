from datetime import datetime,timezone
from bluefin.bluefin import SERCOM
import re
import time

class SBM():    
    def __init__(self,port,address=0):
        """Instantiate a serial object on the specified port.
        @param port -- a system specific port given as a string.
        @param address -- the integer address of the battery (0-250)
        
        Note: At instantiation, the connection to the battery is made, so 
        there is no need to call for a connection to the battery after calling
        this class. However, once operations are complete, the connection 
        should be closed using the close_connection() function.
        """
        self.rs485 = SERCOM()
        self.port = port
        self.bytesize = 8
        self.baudrate = 9600
        self.parity = 'N'
        self.stopbits = 1
        self.flowcontrol = 0
        self.timeout = 3          
        try:
            if self.open_connection() is True:
                self.address = self._format_address(address)
        except:
            msg = "Unable to connect to a battery on {} at {} bps."
            raise ValueError(msg.format(port,self.baudrate))
    
    def open_connection(self):
        """Open a connection to the battery at a 9600 bps.
        @return -- True if the connection was successful.
            False if the connection was not successful.
            
        NOTE: If communicating through a Thetis profiler passthru, the baudrate
            should be set to 115200.
        """  
        connected = self.rs485.connect(self.port,self.baudrate,
                                       self.bytesize,self.parity,self.stopbits,
                                       self.flowcontrol,self.timeout)
        self.rs485.clear_buffers()
        return connected          
    
    def close_connection(self):
        """Close the serial port.
        @return -- True if the connection closed successfully.
            False if the connection did not close successfully.
        """
        disconnected = self.rs485.disconnect()
        return disconnected        

    def _format_address(self,address):
        """Formats a decimal value into a hexadecimal value that works
            with the Bluefin 1.5 kWh (SmallBattMod).
        @param address -- a decimal value ranging between 0 and 250.
        @return -- the address as a hexadecimal value if the input address
            was between 0 and 250. False if the address is outside of that 
            range.
        """
        address = int(address)
        if address >=1 and address <= 250:
           address = hex(int(address)) #Convert address if between 0-250.
           if len(address) == 3: #Take the last char and append a zero.
               address = str(address[-1]).rjust(2,'0')
           elif len(address) == 4:
               address = address[-2:] #Take the last two char.              
           return address
        elif address == 0:
            address = '00'
            return address
        else:
            return False
        
#---------------------------Battery Commands---------------------------------#
    def set_address(self,address):
        """Sets the battery address. 
        The battery must be the only battery on the RS485 bus.
        @param address -- a decimal value ranging between 0 and 250
        """ 
        new_address = self._format_address(address)
        self.rs485.write_command('#00?8 {}'.format(new_address))
        self.rs485.clear_buffers()
        time.sleep(0.2)
        
    def get_address(self):
        """Get the battery address. 
        This function only works when the battery is the 
        only battery on the bus.
        @return -- the address as a decimal value.
        """
        self.rs485.clear_buffers()
        self.rs485.write_command('#00?0')
        response = self.rs485.read_response()
        pattern = '\$.*? (.*?) \r\n'
        hexval = re.findall(pattern,response).pop()
        address = int(hexval,16)
        return address
    
    def get_summary(self):
        """Get the battery summary info of the battery at the givenn address.
        @return -- a single line summary string.
        """
        self.rs485.write_command('#{}q0'.format(self.address),EOL='\r\n')
        response = self.rs485.read_until_byte_string('\r\n')
        return response
    
    def get_battery_state(self):
        """Get the battery state and print a message.
        @return -- a character indicating the battery state. See BF manual.
        """
        summary = self.get_summary()
        pattern = '\$....\s+(.).\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.\s+.*?\s+.*?\s+.\s+.\s+.\s+.*?\r\n'
        state = re.findall(pattern,summary).pop()
        if state == 'f':
            msg = 'OFF'
        elif state == 'd':
            msg = 'DISCHARGING.'
        elif state == 'c':
            msg = 'CHARGING.'
        elif state == 'b':
            msg = 'BALANCING.'
        return state,msg
    
    def get_error_state(self):
        """Get the battery error state and print a message.
        @return -- a character indicating the error state. See BF manual.
        """
        summary = self.get_summary()
        pattern = '\$....\s+.(.)\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.\s+.*?\s+.*?\s+.\s+.\s+.\s+.*?\r\n'
        error = re.findall(pattern,summary).pop()
        if error == '-':
            msg = 'No Error'
        elif error == 'V':
            msg = 'Battery over voltage'
        elif error == 'v':
            msg = 'Battery under voltage'
        elif error == 'I':
            msg = 'Battery over current'
        elif error == 'C':
            msg = 'Battery max cell over voltage'
        elif error == 'c':
            msg = 'Battery min cell under voltage'
        elif error == 'x':
            msg = 'Battery min cell under fault voltage (2.0V)'
        elif error == 'T':
            msg = 'Battery over temperature'
        elif error == 'W':
            msg = 'Battery moisture intrusion detected by H2O sensors'
        elif error == 'H' or error == 'h':
            msg = 'Battery internal hardware fault'
        elif error == 'm':
            msg = 'Battery watchdog timeout'
        return error,msg
    
    def get_voltage(self):
        """Get the battery voltage
        @return -- a float value representing the overall battery voltage.
        """
        summary = self.get_summary()
        pattern = '\$....\s+..\s+(.*?)\s+.*?\s+.*?\s+.*?\s+.*?\s+.\s+.*?\s+.*?\s+.\s+.\s+\s+.*?\r\n'
        voltage = float(re.findall(pattern,summary).pop())
        return voltage
        
    def get_current(self):
        """Get the battery current.
        @return -- a float value representing the battery current.
        """
        summary = self.get_summary()
        pattern = '\$....\s+..\s+.*?\s+(.*?)\s+.*?\s+.*?\s+.*?\s+.\s+.*?\s+.*?\s+.\s+.\s+.\s+.*?\r\n'
        current = float(re.findall(pattern,summary).pop())
        return current

    def get_temperature(self):
        """Get the battery oil temperature.
        @return -- a float value representing the temperature of the oil.
        """
        summary = self.get_summary()
        pattern = '\$....\s+..\s+.*?\s+.*?\s+(.*?)\s+.*?\s+.*?\s+.\s+.*?\s+.*?\s+.\s+.\s+.\s+.*?\r\n'
        temperature = float(re.findall(pattern,summary).pop())
        return temperature
    
    def get_min_cell_voltage(self):
        """Get the minimum cell voltage.
        @return -- the minimum cell voltage as a float value.
        """
        summary = self.get_summary()
        pattern = '\$....\s+..\s+.*?\s+.*?\s+.*?\s+(.*?)\s+.*?\s+.\s+.*?\s+.*?\s+.\s+.\s+.\s+.*?\r\n'
        minv = float(re.findall(pattern,summary).pop())
        return minv
    
    def get_max_cell_voltage(self):
        """Get the maximum cell voltage.
        @return -- the maximum cell voltage as a float value.
        """        
        summary = self.get_summary()
        pattern = '\$....\s+..\s+.*?\s+.*?\s+.*?\s+.*?\s+(.*?)\s+.\s+.*?\s+.*?\s+.\s+.\s+.\s+.*?\r\n'
        maxv = float(re.findall(pattern,summary).pop())
        return maxv        
        
    def water_detected(self):
        """Get the water intrusion detection state.
        @return -- True if water intrusion is detected. False if not water
            intrusion is detected.
        """
        summary = self.get_summary()
        pattern = '\$....\s+..\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+(.)\s+.*?\s+.*?\s+.\s+.\s+.\s+.*?\r\n'
        water = int(re.findall(pattern,summary).pop())
        if water == 0:
            return False
        elif water == 1:
            return True 
         
    def get_wattage(self):
        """Get the battery wattage.
        @return -- the wattage as a float value.
        """
        summary = self.get_summary()
        pattern = '\$....\s+..\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.\s+(.*?)\s+.*?\s+.\s+.\s+.\s+.*?\r\n'
        watts = float(re.findall(pattern,summary).pop())        
        return watts
    
    def get_runtime(self):
        """Get the amount of time the battery has been enabled.
        @return -- a three element list of strings consisting 
            of [hours, minutes,seconds].
        """
        summary = self.get_summary()
        pattern = '\$....\s+..\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.\s+.*?\s+(.*?)\s+.\s+.\s+.\s+.*?\r\n'
        runtime = re.findall(pattern,summary).pop()  
        hms = runtime.split(':')
        msg = 'Battery has been enabled for {}h, {}m, and {}s.'
        print(msg.format(hms[0],hms[1],hms[2]))
        return hms
    
    def get_sleep_timer(self):
        '''Get the number of seconds until the battery goes to sleep.
        @return -- the number of seconds until the battery goes to sleep.
        '''
        summary = self.get_summary()
        pattern = '\$....\s+..\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.\s+.*?\s+.*?\s+.\s+.\s+.( .*?)\r\n'
        timer = int(re.findall(pattern,summary).pop())        
        if timer == 0:
            print('Sleep timer is disabled.')
        else:
            print('Battery will go to sleep in {} seconds.'.format(timer))
        return timer
        
    def get_version_summary(self):
        '''Get the battery info summary.
        @return -- the version summary as an unparsed string.
        '''
        self.rs485.write_command('#{}z0'.format(self.address))
        response = self.rs485.read_response()
        return response
    
    def get_battery_sn(self):
        '''Get the battery serial number.
        @return -- the serial number as an integer.
        '''
        summary = self.get_version_summary()
        pattern = '\$.*?\s+.*?\s+.*?\s+.*?\s+(.*?)\s+.*?\s+.*?\s+.*?\s+.*?\r\n'
        battery_number = int(re.findall(pattern, summary).pop())
        return battery_number
    
    def get_fw_version(self):
        """Get the firmware version.
        @return -- the firmware as a string
        """
        summary = self.get_version_summary()
        pattern = '\$.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+(.*?)\s+\r\n'
        fw_version = re.findall(pattern,summary).pop()
        return fw_version

    def get_battery_model(self):
        """Get the battery board device model.
        @return -- the model as a string
        """
        summary = self.get_version_summary()
        pattern = '\$.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+(.*?)\s+.*?\s+\r\n'
        model = re.findall(pattern,summary).pop()
        return model
    
    def get_voltage_rating(self):
        """Get the battery's voltage rating.
        @return -- the voltage rating as an integer
        """
        summary = self.get_version_summary()
        pattern = '\$.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+(.*?)\s+.*?\s+.*?\s+.*?\s+\r\n'
        rating = int(re.findall(pattern,summary).pop())
        return rating
    
    def get_current_rating(self):
        """Get the battery's current rating.
        @return -- the current rating as an integer
        """
        summary = self.get_version_summary()
        pattern = '\$.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+(.*?)\s+.*?\s+.*?\s+\r\n'
        rating = int(re.findall(pattern,summary).pop())
        return rating    
    
    def get_mode(self):
        """Get the battery mode.
        @return -- the battery mode as a single character string (m or s)
        """
        summary = self.get_version_summary()
        pattern = '\$.*?\s+.*?\s+(.*?)\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+\r\n'
        mode = re.findall(pattern,summary).pop()
        return mode  
    
    def get_device_sn(self):
        """Get the board serial number.
        @return -- the device serial number as an integer.
        """
        summary = self.get_version_summary()
        pattern = '\$.*?\s+.*?\s+.*?\s+(.*?)\s+.*?\s+.*?\s+.*?\s+.*?\s+.*?\s+\r\n'
        mcu_sn = int(re.findall(pattern,summary).pop())
        return mcu_sn          
    
    def sleep(self,length=10):
        """Put the battery to sleep.
        @param length -- the number of seconds to wait before going to sleep.
        """
        self.rs485.write_command('#{}bs {}'.format(self.address,length))    
    
    def off(self):
        """Turn off the battery.
        This resets any existing errors.
        """
        self.rs485.write_command('#{}bf'.format(self.address))
        time.sleep(1)
     
    def balance_cell(self,cell):
        '''Discharge a cell of the battery for balancing.
        @param cell -- the whole number value for a cell (0-7)
        @return -- True if the command was accepted. False if not.
        '''
        self.rs485.write_command('#{}b{}'.format(self.address,cell))
        response = self.rs485.read_response()
        if '1' in response:
            return True
        elif '0' in response:
            return False

    def get_cell_voltages(self):
        '''Get the cell voltages of all 8 cells (0-7, left to right).
        @return -- a list of of cell voltages as floats.
        '''
        self.rs485.write_command('#{}q1'.format(self.address))
        response = self.rs485.read_response() 
        pattern = '.*?([0-9]\.[0-9]{1,3}).*?'
        voltages = list(map(float,re.findall(pattern,response)))
        return voltages
    
#----------------------------------Tests-------------------------------------#   
    def is_balanced(self,delta=0.030):
        """Compare the min and max cell voltages. If the delta between values
        exceeds 0.03V, it is recommended that the battery be balanced.
        @return -- True/False in relation to the balanced state.
        """
        mincell = self.get_min_cell_voltage()
        maxcell = self.get_max_cell_voltage()
        if abs(maxcell-mincell) > delta:
            return False
        else:
            return True

#--------------------------------Balance-------------------------------------#   
    def balance_non_min_cells(self):
        '''Discharge and balance cells that are not the minimum voltage cell
        '''
        voltages = self.get_cell_voltages()
        print(voltages)
        if self._check_all_cells(voltages) is True:
            print('All cells are within 30mV of each other. Exiting utility.')
            exit()
        for i in range(len(voltages)):
            if voltages[i] == min(voltages):
                continue
            elif voltages[i] - 0.030 < min(voltages) < voltages[i] + 0.030:
                continue
            else:
                now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                if self.balance_cell(i) is True:
                    print(now,end='')
                    print(', ',end='')
                    print('Cell #{} discharging.'.format(i))
                    time.sleep(1)
                else:
                    print('Unable to discharge cell #{}.'.format(i))
                    error,error_msg = self.get_error_state()
                    if error == 'm':
                        print('Reason: Watchdog timeout. Resetting.')
                    self.off()
                    time.sleep(1)
                    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                    self.balance_cell(i)
                    print(now,end='')
                    print(', ',end='')
                    print('Cell #{} discharging.'.format(i))
                    time.sleep(1)
                    continue
    
    def _check_all_cells(self,voltages):
        '''Check if all cells are within 30mV of the minimum cell.'''
        for voltage in voltages:
            if voltage < min(voltages) - 0.030 or voltage > min(voltages) + 0.030:
                return False
        return True
            