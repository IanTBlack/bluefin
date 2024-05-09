# Bluefin 1.5 kWh


## How To Use On A Raspberry Pi
1. `cd ~`
2. `git clone https://github.com/IanTBlack/bluefin.git`

To have the script automatically seek the port, do...
3. `python bluefin/scripts/balance.py`

To specify a port, do...

4. `python bluefin/scripts/balance.py /dev/ttyUSB0`, replacing /dev/ttyUSB0 with the appropriate port.
