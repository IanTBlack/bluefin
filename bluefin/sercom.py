'''A base class for communicating with oceanographic sensors over serial.

Author(s): Ian Black
2020-12-13: Initial commit.
2021-01-13: Changed class name from RS232 to SERCOM to prevent confusion when
            using RS485. Implemented user defined check time for read_response.
2021-01-24: Removed connect/disconnect messages because they were annoying.
2021-01-26: Added check to read_response.
'''
import serial
import time

class SERCOM():
    def __init__(self):
        '''Set up a blank canvas at instantiation.'''
        self.sercom = serial.Serial()
                
    def connect(self,port,baudrate,
                bytesize,parity,stopbits,
                flowcontrol,timeout=1):
        self.sercom.port = port
        self.sercom.baudrate = baudrate
        self.sercom.timeout = timeout
        self.sercom.bytesize = bytesize
        self.sercom.stopbits = stopbits
        self.sercom.parity = parity
        self.sercom.xonxoff = flowcontrol
        try:
            self.sercom.open()
            return True
        except:
            return False

    def disconnect(self):
        try:
            self.sercom.close()
            return True
        except:
            return False

    def clear_buffers(self):
        self.sercom.reset_input_buffer()
        self.sercom.reset_output_buffer()              

    def write_command(self,command,EOL='\r\n'):
        cmd = str.encode(command + EOL)
        self.sercom.write(cmd)
    
    def read_bytes(self,check=0.1):
        self._buffer_check(check)
        data = self.sercom.read(self._buffer_length)
        return data
    
    def read_response(self,check=0.1):
        data = self.read_bytes(check)
        response = data.decode()
        return response
    
    def _buffer_check(self,check):
        buffer = self.sercom.in_waiting
        start = time.monotonic()
        time.sleep(check)
        while True:
            end = time.monotonic()
            incoming = self.sercom.in_waiting
            if buffer == incoming:
                self._buffer_length = buffer
                break
            else:
                if (end-start) > 30:
                    print('Forced serial read timeout.')
                    break
                buffer = incoming
                time.sleep(check)    

    def read_until_byte_string(self,byte_string):
        incoming = self.sercom.read_until(byte_string).decode()
        return incoming