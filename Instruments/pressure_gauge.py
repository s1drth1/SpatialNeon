# -*- coding: utf-8 -*-
"""
Created on Wednesday 04/23/2025

@author: sidharthduthaluru

SCPI Commandset for the Arduino pressure gauge. Tentative folder, will add more functions

ALERT!! Not using this library anymore, on account of Pyvisa not reading the arduino . Writing pyserial code directly into functions (04/28/2025)
"""


import numpy as np
import pyvisa
import time

rm = pyvisa.ResourceManager()

def get_identity(gaugeAddress):

    pg = rm.open_resource(gaugeAddress)

    identity = pg.query("*IDN?")

    pg.close()

    return identity
    

def get_pressure(gaugeAddress):

    pg = rm.open_resource(gaugeAddress)

    pressure = pg.write("SYST:PRES:GETMbar")

    pg.close()

    return pressure


