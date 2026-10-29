# -*- coding: utf-8 -*-
"""
Created on Mon Aug  7 13:15:01 2023

@author: Crow108
"""
# -*- coding: utf-8 -*-
"""
Created on Mon Aug  7 10:56:29 2023

@author: Crow108
"""
import numpy as np
from datetime import datetime
import os
import pyvisa
import time
import matplotlib.pyplot as plt
from vna_analysis import *
import pandas as pd
from scipy.optimize import curve_fit
#import vna_analysis
import math
#import nidaqmx

import sys
sys.path.append("C:/Users/crow108/Documents/analyzer")
#import instruments
import csv

#p = instruments.load('proteus8ch')


res_hi = 1
res_lo = -1

trap_hi = 1
trap_lo = -1

guard_hi = 1
guard_lo = -1

pinch_hi = 1
pinch_lo = -1




data_dir = r"C:\Users\Crow108\Downloads\resMeasurement\resMeasurement\neonPackage_FPv2"

rm = pyvisa.ResourceManager()
vna_gpib='GPIB0::16::INSTR'
vna = rm.open_resource(vna_gpib)



# plsGen_gpib = 'GPIB0::10::INSTR'
# plsGen = rm.open_resource(plsGen_gpib)
# # res_Keithley_address = 'GPIB0::24::INSTR'
# # r_source = rm.open_resource(res_Keithley_address)

# # r_source.write(":SOUR:FUNC VOLT")

# twpa_Keithley_address = 'GPIB0::26::INSTR'
# t_source = rm.open_resource(twpa_Keithley_address)

# #t_source.write(":SOUR:FUNC VOLT")

# e_gpib ='GPIB0::20::INSTR'
# e_source = rm.open_resource(e_gpib)


# #e_source.write("OUTP OFF")

# e_source.write(":SOUR:FUNC VOLT")
# e_source.write(":SENS:FUNC 'CURR:DC'")


# res = nidaqmx.Task()
# res.ao_channels.add_ao_voltage_chan('cDAQ1Mod1/ao8', 'res_bias', res_lo, res_hi)

# trap = nidaqmx.Task()
# trap.ao_channels.add_ao_voltage_chan('cDAQ1Mod1/ao2', 'trap_bias', trap_lo, trap_hi)

# tg = nidaqmx.Task()
# tg.ao_channels.add_ao_voltage_chan('cDAQ1Mod1/ao1', 'tg_top', guard_lo, guard_hi)
# #tg.ao_channels.add_ao_voltage_chan('cDAQ1Mod1/ao6', 'tg_bot', guard_lo, guard_hi)

# # rg = nidaqmx.Task()
# # rg.ao_channels.add_ao_voltage_chan('cDAQ1Mod1/ao4', 'rg_bot', guard_lo, guard_hi)
# # #rg.ao_channels.add_ao_voltage_chan('cDAQ1Mod1/ao4', 'rg_top', guard_lo, guard_hi)

# pinch = nidaqmx.Task()
# pinch.ao_channels.add_ao_voltage_chan('cDAQ1Mod1/ao5', 'pinch_bias', pinch_lo, pinch_hi)
# def singleLineCSV(filename, arr):
#     file = open(filename, 'a')
#     writer = csv.writer(file)
#     writer.writerow(arr)
#     file.close()

def wisform(smith):
    outarray = np.row_stack((smith.freqs,smith.log_mag,smith.wrapped_phase,smith.phase_rad))
    #print(outarray)
    return outarray


def Lorentzian(x, x0, a, c, g):
    return a/(g*(1 + (x - x0)**2/g**2)) + c



def wait(t):
    for i in range(t):
        time.sleep(1)
        
 
def resScan(f = -999, span = 2, del_time = 60, n_points = 101, BW = -999, power = -100,
            fit_yes = 1, name = ""):
    time_stamp = str(datetime.now()).replace(":", "_")
    vna.write("INIT:CONT ON") #turn on internal triggering
    #BNC.write("OUTP OFF")
    vna.write("SENS:AVER:COUN 60000")
    vna.write("SENS:AVER OFF")
    if f != -999: vna.write("SENSe1:FREQuency:CENTer " + str(f) + "ghz")
    vna.write("SENSe1:FREQuency:SPAN " + str(span) + "mhz") 
    #vna.write("DISP:WIND:TRAC:Y:AUTO")
    if BW != -999: vna.write("SENS:BWID " + str(BW) + "HZ")
    vna.write("SENS:SWE:POIN " + str(n_points)) 
    vna.write("SENS:SWE:TIME MIN")
    vna.write("OUTP ON")
    if power != -100: vna.write(f"SOUR:POW {power}")
    time_stamp = str(datetime.now()).replace(":", "_")
    print("Started at " + time_stamp)
    time.sleep(2)
    vna.write("SENS:AVER ON")
    
    
    
    wait(del_time)
    vs=get_smith_data(vna_gpib) 
    outarray = wisform(vs)
    f = outarray[0]/1e9
    S = outarray[1]
    L = 10**((S - np.max(S))/10)
    param, cov = curve_fit(Lorentzian, f, L, 
                           p0 = [np.average(f), 1, 0, 0.2*(np.max(f) - np.min(f))],
                           maxfev = 100000, bounds = ((np.average(f) - 0.5, 0, -np.inf, 0), (np.average(f) + 0.5, 1.5, np.inf, 2 * (np.max(f) - np.min(f)))))
    plt.plot(f, S)
    plt.locator_params(axis='x', nbins=4) 
    plt.xlabel("Frequency (GHz)")
    plt.ylabel("S$_2$$_1$ (dB)")
    plt.title(time_stamp)
    
    fit = Lorentzian(f, param[0], param[1], param[2], param[3])
    S_fit = np.log10(fit) * 10 + np.max(S)
    
    Q = param[0]/param[3]/2
    lgd = ["Data"]
    if fit_yes == 1:
        plt.plot(f, S_fit)
        lgd.append("f = " + str(round(param[0], 6)) + " GHz\nQ = " + str(round(Q)) + "\nMax at " +str(f[np.argmax(S)]) + " GHz")
    plt.legend(lgd)
    
    print(str(param[0]))
    
    print("Q is: " + str(Q))
    oo = pd.DataFrame(outarray)
    oo.to_csv(data_dir + "\\" + time_stamp + "_outarray_" + name + ".csv")
    
    #plt.text(0.6, 0.6, "Q: " + str(Q))
    plt.show()
    return outarray, param[0]
    
