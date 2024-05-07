from datetime import datetime,timezone
from bluefin.bluefin import SBM
import sys
import time

port = sys.argv[1]
try:
    address = int(sys.argv[2])
except:
    address = 0
try:
    vlim = float(sys.argv[3])
except:
    vlim = 3.81

sbm = SBM(port,address)
sn = sbm.get_battery_sn()
print("Connected to SBM {}!".format(sn))
print("Checking to see if all cells are near {}V.".format(vlim))
if all(V <=3.7 for V in sbm.get_cell_voltages()):
    print('Battery needs charging. Charge so that each cell is at 3.8V before storage.')
    exit()

while True:
    start = time.monotonic()
    voltages = sbm.get_cell_voltages()
    if all(v <= vlim for v in voltages):
        print("All cells are below {}V.".format(vlim))
        print("Battery can now be safely stored in a cool room (10 - 20degC).")
        print("Exiting utility.")
        sbm.off()
        time.sleep(0.5)
        exit()
    for i in range(len(voltages)):
        if voltages[i] >= vlim:
            now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            print(now,end='')
            print(', ',end='')
            print('Cell #{} discharging.'.format(i))
            sbm.balance_cell(i)
            time.sleep(1)
        elif sbm.get_error_state()[0] == 'm':
            print('Watchdog timeout. Resettting battery.')
            sbm.off()
            time.sleep(1)
            now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            sbm.balance_cell(i)
            print(now,end='')
            print(', ',end='')
            print('Cell #{} discharging.'.format(i))      
        else:
            continue
    voltages = sbm.get_cell_voltages()
    print("Voltages after discharge: {}".format(voltages))
    stop = time.monotonic()
    wait = 60 - int(stop-start)
    print('Waiting for {} seconds before discharging cells again.'.format(wait))
    time.sleep(wait)


