from bluefin.bluefin import SBM
import sys

port = sys.argv[1] #Get the port from the shell run.
new = int(sys.argv[2]) #Get the desired address.

sbm = SBM(port) #Instantiate battery on the defined port at default address.
sn = sbm.get_battery_sn()  #Get the battery SN.
print('Connected to SBM {}!'.format(sn))
old = sbm.get_address()
sbm.set_address(new)
_set = sbm.get_address()
print('Battery address changed to {}.'.format(_set))
if sbm.close_connection() is True:
    print('Battery address change successful')