"""
Code to configure a microwave LO source, this is specifically written for the SRS SG396

Created: 01/09/2026

@author: sidharthduthaluru

"""

import pyvisa, time

import numpy as np


rm = pyvisa.ResourceManager()


def lo_set_frequency(address, freq):

    #Set frequency

    lo = rm.open_resource(address)

    lo.write(f"FREQ {freq}")

    time.sleep(0.1)
    
    print(lo.query("FREQ?"))

    time.sleep(0.1)
    
    lo.close()

def lo_set_power(address, power):

    #Set power

    lo = rm.open_resource(address)

    lo.write(f"AMPR {power}")

    time.sleep(0.1)
    
    print(lo.query("AMPR?"))
    
    time.sleep(0.1)
    
    lo.close()

def lo_on_or_off(address, on_or_off):

    #Toggle output

    lo = rm.open_resource(address)

    if on_or_off == "ON":
        lo.write("ENBR 1")
    else:
        lo.write("ENBR 0")
    time.sleep(0.1)

    print(lo.query("ENBR?"))

    time.sleep(0.1)

    lo.close()
