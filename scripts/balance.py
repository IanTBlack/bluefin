import os.path
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
    delta = float(sys.argv[3])
except:
    delta = 0.030


sbm = SBM(port,address)

sn = sbm.get_battery_sn()
print("Connected to SBM {}!".format(sn))
if sbm.is_balanced(delta=delta):
    print('Battery already appears to be well balanced. Exiting utility.')
    for i in range(3):
        sbm.off()
        time.sleep(0.5)
    exit()

uid = os.path.expanduser('~')
today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
log_location = "{}/bluefin/operational/bluefin/log/SBM{}_{}.txt".format(uid,sn,today)
log = open("{}".format(log_location),'a')
log.write("Bluefin 1.5kWh {} Balance Log\n".format(sn))
log.write("\n\n\n")
log.write("datetime,voltage_array,temperature\n")
start = time.monotonic()
while True:
    lstart = time.monotonic()
    temp = sbm.get_temperature()
    print('Battery Temperature: {} degC'.format(temp))
    if temp > 42:
        print("Battery temperature exceeded 42 degrees. Wait for it to cool down and apply a fan for next attempt. Exiting utility.")
        time.sleep(0.5)
        log.close()
        sbm.off()
        sbm.close_connection()
        exit()
    if time.monotonic() - start > 60*60*24*14:
        print("Balancing program 14 day timeout. It shouldn't take this long to balance a battery. Something is weird and you should probably contact GDMS.")
        time.sleep(0.5)
        log.close()
        sbm.off()
        sbm.close_connection()
        exit()
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    print('Balancing cells...')
    sbm.balance_non_min_cells()
    print('Checking balanced state...', end = '')
    time.sleep(1)
    if sbm.is_balanced(delta):
        print('battery is balanced. Exiting utility.')
        time.sleep(0.5)
        log.close()
        sbm.off()
        sbm.close_connection()
        exit()
    else:
        print('battery is not balanced.')
    log.write("{},{},{}\n".format(now,sbm.get_cell_voltages(),temp))
    lstop = time.monotonic()
    wait = int(60-(lstop-lstart))
    if wait <= 0:
        continue
    else:
        print('Waiting {} seconds before checking again.'.format(wait))
        time.sleep(wait)

