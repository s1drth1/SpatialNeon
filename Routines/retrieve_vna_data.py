"""
File for retrieving VNA data

@author - sidharth

@date - Feb 12, 2025


"""


import numpy as np
from datetime import datetime
import os
import pyvisa
import time
import matplotlib.pyplot as plt
import pandas as pd
from scipy.optimize import curve_fit
import math
import sys
import csv



rm = pyvisa.ResourceManager()

sys.path.append("..")

data_dir = r"C:\Users\Crow108\OneDrive\Desktop\IceT_SD\Data\power_scan"

from Instruments.vna_config import *
from Instruments.hp34461A import *
from Routines.res_to_temp import *



def wisform(smith):
    outarray = np.row_stack((smith.freqs,smith.log_mag,smith.wrapped_phase,smith.phase_rad))
    #print(outarray)
    return outarray

def wisform_cw(smith):
    #For a cw scan specifically
    outarray = np.row_stack((smith.times, smith.log_mag, smith.wrapped_phase, smith.phase_rad))
    return outarray

def wisform_realimag(smith):
    outarray = np.row_stack((smith.freqs, smith.real, smith.imag, smith.lin_mag, smith.wrapped_phase))
    return outarray


def wait(t):
    for i in range(t):
        time.sleep(1)


def SingleScan_VNA(vna_gpib, f = -999, span = 2, del_time = 60, n_points = 101, BW = -999, power = -100, name = '', forplot = True, to_save = True, data_dir = r"C:\Users\Crow108\OneDrive\Desktop\IceT_SD\Data", meas = "S21"):
    #retreive a single VNA scan data and plot the data accordingly
    try:
        vna = rm.open_resource(vna_gpib)
        time_stamp = str(datetime.now()).replace(":", "_")
        vna.write("INIT:CONT ON") #turn on internal triggering
        #BNC.write("OUTP OFF")
        vna.write("SENS:SWE:TYPE LIN")
        vna.write("SENS:AVER:COUN 60000")
        vna.write("SENS:AVER OFF")
        if f != -999: vna.write("SENSe1:FREQuency:CENTer " + str(f) + "ghz")
        print(f)
        vna.write("SENSe1:FREQuency:SPAN " + str(span) + "mhz")
        print(span) 
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
        vs=get_smith_data(vna_gpib, meas=meas) 
        outarray = wisform(vs)
        f = outarray[0]/1e9
        S = outarray[1]
        L = 10**((S - np.max(S))/10)
        phase = outarray[2]

        if forplot:

            plt.plot(f, S)
            plt.locator_params(axis='x', nbins=4) 
            plt.xlabel("Frequency (GHz)")
            plt.ylabel("S$_2$$_1$ (dB)")
            plt.title(time_stamp)

            plt.show()

        if to_save:
            oo = pd.DataFrame(outarray)
            oo.to_csv(data_dir + "\\" + time_stamp + "_outarray_" + name + ".csv")


        return f, S, L, time_stamp
        
    
    finally:
        vna.close()



def SingleScan_VNA_phase(vna_gpib, f = -999, span = 2, del_time = 60, n_points = 101, BW = -999, power = -100, name = '', forplot = True, to_save = True, aver = 1, data_dir = r"C:\Users\Crow108\OneDrive\Desktop\IceT_SD\Data", meas = "S21"):
    #retreive a single VNA scan data and plot the data accordingly
    try:
        vna = rm.open_resource(vna_gpib)
        time_stamp = str(datetime.now()).replace(":", "_")
        vna.write("INIT:CONT ON") #turn on internal triggering
        #BNC.write("OUTP OFF")
        vna.write("SENS:SWE:TYPE LIN")
        vna.write(f"SENS:AVER:COUN {aver}")
        vna.write("SENS:AVER OFF")
        if f != -999: vna.write("SENSe1:FREQuency:CENTer " + str(f) + "ghz")
        print(f)
        vna.write("SENSe1:FREQuency:SPAN " + str(span) + "mhz")
        print(span) 
        #print(vna.query("CALC:CORR:EDEL:TIME?"))
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
        vs=get_smith_data(vna_gpib, meas=meas) 
        outarray = wisform(vs)
        f = outarray[0]/1e9
        S = outarray[1]
        L = 10**((S - np.max(S))/10)
        phase = outarray[2]
        phase_rad = outarray[3]

        if forplot:

            plt.plot(f, S)
            plt.locator_params(axis='x', nbins=4) 
            plt.xlabel("Frequency (GHz)")
            plt.ylabel("S$_2$$_1$ (dB)")
            plt.title(time_stamp)

            plt.show()

            plt.plot(f, phase_rad)
            plt.xlabel("Frequency (GHz)")
            plt.ylabel("Phase")
            plt.title(time_stamp)
            plt.show()

        if to_save:
            oo = pd.DataFrame(outarray)
            oo.to_csv(data_dir + "\\" + time_stamp + "_outarray_" + name + ".csv")


        return f, S, phase, phase_rad, time_stamp
        
    
    finally:
        vna.close()
        

    


def retrieve_cw_data(vna_gpib = "GPIBO::16::INSTR", del_time = 60, num_avgs = 1, name = "cw_sweep", forplot = True, to_save = True, data_dir = r"C:\Users\Crow108\OneDrive\Desktop\IceT_SD\Data"):
    
    vna_handle = rm.open_resource(vna_gpib)
    
    try:
        
        
        wait(del_time*num_avgs)

        time_stamp = str(datetime.now()).replace(":", "_")

        vs = get_smith_data(vna_gpib, cw = True)

        outarray = wisform_cw(vs)

        time = outarray[0]
        S = outarray[1]
        L = 10**((S - np.max(S))/10)
        phase = outarray[2]
        phase_rad = outarray[3]


        if forplot:
            plt.plot(time, phase)
            plt.locator_params(axis='x', nbins=4) 
            plt.xlabel("Time (s)")
            plt.ylabel("Phase(rad)")
            plt.title(time_stamp)

            plt.show()

        if to_save:

            oo = pd.DataFrame(outarray)
            oo.to_csv(data_dir + "\\" + time_stamp + "_outarray_" + name + ".csv")

        return time, S, L, phase, phase_rad

    finally:
        vna_handle.close()

        
def singlescan_updateddatasave(vna_addr, f_search, focus_span, pow, aver, data_save, wait_time = 10, average_time = 60*1, n_points = 501, name = '', hp34461a_addr = 'GPIB0::22::INSTR'):
    configure_settings(vna_addr, f = f_search, BW = 1E3, span = focus_span, power = pow, aver= aver, n_points = 501, time = "MIN")

    time.sleep(60*wait_time)
    temp = R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr)))
    freqs, s_data, phase, phaserad, savetime = SingleScan_VNA_phase(vna_addr, f = f_search, span = focus_span, del_time = average_time, n_points =  n_points, aver=1, BW = 1E3, power = pow, name = '', forplot = False, to_save=False, data_dir = data_save)

    freqs_df = pd.DataFrame(freqs)
    s_data_df = pd.DataFrame(s_data)
    phase_df= pd.DataFrame(phase)
    phaserad_df = pd.DataFrame(phaserad)
    s_lin = 10**((s_data - np.max(s_data))/10)
    s_lin_df = pd.DataFrame(s_lin)

    print(temp)


    freqs_df.to_csv(data_save + "\\" + savetime + "_frequency_" + name + ".csv")
    s_data_df.to_csv(data_save + "\\" + savetime + "_S21_" + name + ".csv")
    phase_df.to_csv(data_save + "\\" + savetime + "_phase_" + name + ".csv")
    phaserad_df.to_csv(data_save + "\\" + savetime + "_phaserad_" + name + ".csv")
    s_lin_df.to_csv(data_save + "\\" + savetime + "_slin_" + name + ".csv")



def SingleScan_VNA_realimag(vna_gpib, f = -999, span = 2, del_time = 60, n_points = 101, BW = -999, power = -100, name = '', forplot = True, to_save = True, data_dir = r"C:\Users\Crow108\OneDrive\Desktop\IceT_SD\Data", meas = "S21"):
    #retreive a single VNA scan data and plot the data accordingly
    try:
        vna = rm.open_resource(vna_gpib)
        time_stamp = str(datetime.now()).replace(":", "_")
        vna.write("INIT:CONT ON") #turn on internal triggering
        #BNC.write("OUTP OFF")
        vna.write("SENS:SWE:TYPE LIN")
        vna.write("SENS:AVER:COUN 20")
        vna.write("SENS:AVER OFF")
        if f != -999: vna.write("SENSe1:FREQuency:CENTer " + str(f) + "ghz")
        print(f)
        vna.write("SENSe1:FREQuency:SPAN " + str(span) + "mhz")
        print(span) 
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
        vs=get_smith_data(vna_gpib, meas=meas) 
        outarray = wisform_realimag(vs)
        f = outarray[0]/1e9
        real = outarray[1]
        imag = outarray[2]
        linmag = outarray[3]
        phase = outarray[4]

        if forplot:

            plt.plot(f, 20*np.log10(linmag))
            plt.locator_params(axis='x', nbins=4) 
            plt.xlabel("Frequency (GHz)")
            plt.ylabel("S$_2$$_1$ (dB)")
            plt.title(time_stamp)

            plt.show()

        if to_save:
            oo = pd.DataFrame(outarray)
            oo.to_csv(data_dir + "\\" + time_stamp + "_outarray_" + name + ".csv")


        return f, real, imag, time_stamp
        
    
    finally:
        vna.close()       


def multires_s21_scan(vna_addr, data_dir, f_search, span = 20, del_time = 30, n_points = 1501, BW = 1E3, power = 0, name = '', to_save = True):
    for f in f_search:

        f_initial, real, imag, time = SingleScan_VNA_realimag(vna_addr, f = f, span = 80, del_time = del_time, n_points = 201, BW = 1E3, power = 0, name = 'init_charac', forplot= False, to_save = False, data_dir = '')

        f_new = f_initial[np.argmin(np.sqrt(real**2 + imag**2))]

        f_final, real, imag, time = SingleScan_VNA_realimag(vna_addr, f = f_new, span = span, del_time = del_time, n_points = n_points, BW = BW, power = power, name = name, forplot = True, to_save = to_save, data_dir = data_dir)

        print(f"resonant Frequency: {f_final[np.argmin(np.sqrt(real**2 + imag**2))]} GHz")        


def multires_s21_cw(vna_addr, data_dir, f_search, del_time = 30, n_points = 1501, num_avgs = 1, BW = 1E3, power = 0, name = '', to_save = True):
    #Multi-resonator continuous wave spectroscopy using previous functions written for single resonator cw spec
    for f in f_search:

        f_initial, real, imag, time = SingleScan_VNA_realimag(vna_addr, f = f, span = 80, del_time = del_time, n_points = 201, BW = 1E3, power = 0, name = 'init_charac', forplot= False, to_save = False, data_dir = '')

        f_new = f_initial[np.argmin(np.sqrt(real**2 + imag**2))]

        f_final, real, imag, time = SingleScan_VNA_realimag(vna_addr, f = f_new, span = 20, del_time = del_time, n_points = n_points, BW = 1E3, power = power, name = name, forplot = True, to_save = False, data_dir = data_dir)

        f_res = f_final[np.argmin(np.sqrt(real**2 + imag**2))]
        print(f"resonant Frequency: {f_res} GHz")        

        time.sleep(2) 

        time, number = prepare_for_cw_spec(f_res, power, BW, n_points, aver = num_avgs) 

        time, S, L, phase, phase_rad = retrieve_cw_data(del_time=del_time, num_avgs = num_avgs, to_save = True, data_dir = data_dir)

        print("done")
