# -*- coding: utf-8 -*-
"""
Created on Thursday 01/30/2025

@author: sidharthduthaluru

Configuring and controlling our BK Precision 9130C DC Power Supply
SCPI commands can work for other supplies as well, so check and confirm

"""


import numpy as np
import pyvisa
import time

rm = pyvisa.ResourceManager()

def set_voltage(address, channel, voltage):

    #sets voltage on specified channel

    bkpower = rm.open_resource(address)

    bkpower.write(f"INST:NSEL {channel}")

    bkpower.write("INST:NSEL?")

    print(f"Channel set to {bkpower.read()}")

    bkpower.write(f"VOLT {voltage}")

    bkpower.write("VOLT?")
    print(f"Voltage set to {bkpower.read()}V")

    bkpower.close()

def set_current(address, channel, current):

    #sets current on specified channel

    bkpower = rm.open_resource(address)

    bkpower.write(f"INST:NSEL {channel}")

    bkpower.write("INST:NSEL?")

    print(f"Channel set to {bkpower.read()}")

    bkpower.write(f"CURR {current}")

    bkpower.write("CURR?")
    print(f"Current set to {bkpower.read()}A")

    bkpower.close()

def current_step(address, channel, current_step):

     #sets current step on specified channel

    bkpower = rm.open_resource(address)

    bkpower.write(f"INST:NSEL {channel}")

    bkpower.write(f"CURR:STEP {current_step}")

    bkpower.write("CURR:STEP?")
    print(f"Current step set to {bkpower.read()}A")

    bkpower.close()

def voltage_step(address, channel, voltage_step):
    #sets current step on specified channel

    bkpower = rm.open_resource(address)

    bkpower.write(f"INST:NSEL {channel}")

    bkpower.write(f"VOLT:STEP {current_step}")

    bkpower.write("VOLT:STEP?")
    print(f"Voltage step set to {bkpower.read()}V")

    bkpower.close()


def output_toggle(address, output_state):
    #toggle output on or off
    
    bkpower = rm.open_resource(address)

    bkpower.write(f"OUTP {output_state}")

    bkpower.write("OUTP?")
    print(f"OUTPUT IS {bkpower.read()}")

    bkpower.close()

def channel_output_toggle(address, channel, state):

    #toggles output state of specific channel

    bkpower = rm.open_resource(address)

    bkpower.write(f"INST:NSEL {channel}")

    bkpower.write(f"CHAN:OUTP {state}")

    bkpower.write("CHAN:OUTP?")
    print(f"Channel {channel} OUTPUT IS {bkpower.read()}")

    bkpower.close()

def current_increment(address, channel, up_or_down):
    #toggles current level up or down by the already-configured step

    bkpower = rm.open_resource(address)

    bkpower.write(f"INST:NSEL {channel}")

    bkpower.write(f"CURR:{up_or_down}")

    bkpower.write("CURR?")
    print(f"Channel {channel} CURRENT IS {bkpower.read()}")

    bkpower.close()

def voltage_increment(address, channel, up_or_down):
    #toggles voltage level up or down by the already-configured step

    bkpower = rm.open_resource(address)

    bkpower.write(f"INST:NSEL {channel}")

    bkpower.write(f"VOLT:{up_or_down}")

    bkpower.write("VOLT?")
    print(f"Channel {channel} VOLTAGE IS {bkpower.read()}")

    bkpower.close()

def current_query(address, channel):

    bkpower = rm.open_resource(address)

    bkpower.write(f"INST:NSEL {channel}")

    return  bkpower.query("MEAS:CURR?")


def voltage_query(address, channel):

    bkpower = rm.open_resource(address)

    bkpower.write(f"INST:NSEL {channel}")

    return  bkpower.query("MEAS:VOLT?")

def power_query(address, channel):

    bkpower = rm.open_resource(address)

    bkpower.write(f"INST:NSEL {channel}")

    return  bkpower.query("MEAS:POW?")



