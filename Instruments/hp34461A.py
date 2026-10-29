# -*- coding: utf-8 -*-
"""
Created on Sat July 2 2022

@author: shilling

"""

import numpy as np
import pyvisa
import time

rm = pyvisa.ResourceManager()

def hp34461a_get_voltage(address):
    try:
        hp34461a = rm.open_resource(address)
        hp34461a.write("SENS:FUNC \'volt:DC\'") # set volt
        # hp34461a.write("SENS:volt:dc:RANG:AUTO ON") # Auto range
        string_data = hp34461a.query("READ?")
        numerical_data = float(string_data)
    finally:
        hp34461a.close()
    return numerical_data

def hp34461a_get_ohm_4pt(address):
    try:
        hp34461a = rm.open_resource(address)
        hp34461a.write("SENS:FUNC \'FRES\'") # set 4pt
        hp34461a.write("SENS:FRES:RANG:AUTO ON") # Auto range
        string_data = hp34461a.query("READ?")
        numerical_data = float(string_data)
    finally:
        hp34461a.close()
    return numerical_data

def hp34461a_get_ohm_2pt(address):
    try:
        hp34461a = rm.open_resource(address)
        hp34461a.write("SENS:FUNC \'RES\'") # set 4pt
        # hp34461a.write("SENS:FRES:RANG:AUTO ON") # Auto range
        string_data = hp34461a.query("READ?")
        numerical_data = float(string_data)
    finally:
        hp34461a.close()
    return numerical_data