from scipy.optimize import brentq
import numpy as np
from datetime import datetime
import time, sys, os, pyvisa, subprocess
import matplotlib as mpl
import matplotlib.pyplot as plt
import time, serial


sys.path.append("..")


from Instruments.hp34461A import *
from Instruments.vna_config import *
from Instruments.power_supply import *
from Instruments.pressure_gauge import *
from Routines.res_to_temp import *
from Routines.retrieve_vna_data import *
from Routines.vna_analysis import *
from Routines.fq_data_collection import *

from Instruments.SRS_SG396_lo import *


def current_from_power(power, resistance):
    return np.sqrt(power/resistance)
    
def get_power(bkpower_addr, chan = 2):
    return float(current_query(bkpower_addr, chan))*float(voltage_query(bkpower_addr, chan))

def get_resistance(bkpower_addr, chan = 2):
    return float(current_query(bkpower_addr, chan))/float(voltage_query(bkpower_addr, chan))


def hotline_dep_heating (bkheater_addr, hp34461a, chan, heat_voltage, wait_time = 60*60*2):

    #prepping the hotline for quench condense deposition

    set_voltage(bkheater_addr, chan, heat_voltage)

    time.sleep(2)

    channel_output_toggle(bkheater_addr, chan, "ON")

    start_time = time.time()

    time_now = time.time()

    while (time_now - start_time <= wait_time): #2 hours

        time.sleep(1)

        hp34461a_get_ohm_4pt(hp34461a)

        time_now = time.time()

    

    print("line heated")


def depMon(vna_addr, hp34461a_addr, data_dir, seconds = 10, del_time = 1, f = -999, BW = -999, span = 10, power = -100, n_points = 201, name = ""):

    #Deposition monitor, write to files at the end of the sequence

    #set up the vna appropriately before sweeping
    configure_settings(vna_addr = vna_addr, type = "LIN", f = f, BW = BW, span = span, power = power, n_points = n_points, time = "MIN")

    vna = rm.open_resource(vna_addr)

    try:
    
    
        time_axis = []
        S = []
        phase = []
        T = []
        phase_rad = []

        time_stamp = str(datetime.now()).replace(":", "_")
        print("Started at " + time_stamp)
        time.sleep(1)
        for i in range(int(seconds/del_time)):
            vna.write("SENS:AVER ON")
            time.sleep(del_time)
            vs=get_smith_data(vna_addr) 
            outarray = wisform(vs)
            if i == 0:
                t0 = datetime.now()

            time_axis.append((datetime.now() - t0).total_seconds())
            S.append(outarray[1])
            phase.append(outarray[2])
            phase_rad.append(outarray[3])
            T.append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
            vna.write("SENS:AVER OFF")
        true_S = np.transpose(S)
        true_phase = np.transpose(phase)
        adjusted_phase_rad = np.transpose(phase_rad)
        save_T = pd.DataFrame(time_axis)
        save_S = pd.DataFrame(true_S)
        save_F = pd.DataFrame(outarray[0]/1e9)
        save_P = pd.DataFrame(true_phase)
        save_rad = pd.DataFrame(adjusted_phase_rad)
        save_TT = pd.DataFrame(T)

        save_T.to_csv(data_dir + "\\" + time_stamp + "_time_" + name + ".csv")
        save_S.to_csv(data_dir + "\\" + time_stamp + "_S21_" + name + ".csv")
        save_F.to_csv(data_dir + "\\" + time_stamp + "_frequency_" + name + ".csv")
        save_P.to_csv(data_dir + "\\" + time_stamp + "_phase_" + name + ".csv")
        save_TT.to_csv(data_dir + "\\" + time_stamp + "_temperature_" + name + ".csv")
        save_rad.to_csv(data_dir + "\\" + time_stamp + "_phaserad_" + name + ".csv")

        true_S_lin = 10**((true_S - np.max(true_S))/10)

        fig, (ax1, ax2, ax3, ax4) = plt.subplots(1, 4)
        
        a1 = ax1.plot(time_axis, T, color = 'red')
        a2 = ax2.pcolor(time_axis, outarray[0]/1e9, true_S)
        a3 = ax3.pcolor(time_axis, outarray[0]/1e9, true_S_lin)
        a4 = ax4.pcolor(time_axis, outarray[0]/1e9, true_phase)

        ax1.set_ylim([5, 10])
        ax1.set_ylabel("Temperature (K)")
        ax2.set_ylabel("Frequency (GHz)")
        ax1.set_xlabel("time (s)")
        ax2.set_xlabel("time (s)")
        ax3.set_xlabel("time (s)")
        ax4.set_xlabel("time (s)")
        fig.colorbar(a2, label = "S$_2$$_1$ (dB)")
        fig.colorbar(a3, label = "Linear transmission")
        fig.colorbar(a4, label = "Phase (rad)")

        fig.suptitle("Real time deposition monitor " + time_stamp)
        fig.set_size_inches([13, 4])
        fig.tight_layout()
        plt.show()
    
    finally:
        vna.close()

def evapMon(vna_addr, hp34461a_addr, heater_addr, seconds = 10, del_time = 1, f = -999, BW = -999, span = 10, power = -100, n_points = 201, target_T = 15, target_cur = 0.8, chan = 2):

    #UNUSED - evaporation monitor. Can use the deposition monitor to record evaporation data instead
    
    T_val = R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr)))
    #heater = rm.open_resource(keithley_addr)
    #heater.write(f"INST CH{str(chan)}")
    #heater.write("VOLT 25.0 V")
    #heater.write("CURR:STEP 0.030")
    #heater.write(f"CURR {target_cur} A")
    time.sleep(5)
    #heater.write("OUTP ON")

    while (T_val <= target_T):
        T_val = R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr)))
        time.sleep(1)

    
    vna.write("INIT:CONT ON") #turn on internal triggering
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
    # T_sensor.write("SENS:FUNC \'FRES\'")  set 4pt
    # T_sensor.write("SENS:FRES:RANG:AUTO ON")  Auto range
    
    time_axis = []
    S = []
    phase = []
    T = []

    time_stamp = str(datetime.now()).replace(":", "_")
    print("Started at " + time_stamp)
    time.sleep(1)
    for i in range(int(seconds/del_time)):
        vna.write("SENS:AVER ON")
        time.sleep(del_time)
        vs=get_smith_data(vna_addr) 
        outarray = wisform(vs)
        if i == 0:
            t0 = datetime.now()

        time_axis.append((datetime.now() - t0).total_seconds())
        S.append(outarray[1])
        phase.append(outarray[2])
        T.append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
        vna.write("SENS:AVER OFF")
        #if (datetime.now()-t0).total_seconds() >= 30:
            #heater.write("CURR:UP")
    true_S = np.transpose(S)
    true_phase = np.transpose(phase)
    save_T = pd.DataFrame(time_axis)
    save_S = pd.DataFrame(true_S)
    save_F = pd.DataFrame(outarray[0]/1e9)
    save_P = pd.DataFrame(true_phase)
    save_TT = pd.DataFrame(T)

    save_T.to_csv(data_dir + "\\" + time_stamp + "_time_" + f"{round(T_val, 2)}K" + ".csv")
    save_S.to_csv(data_dir + "\\" + time_stamp + "_S21_" +  f"{round(T_val, 2)}K" + ".csv")
    save_F.to_csv(data_dir + "\\" + time_stamp + "_frequency_" + f"{round(T_val, 2)}K" + ".csv")
    save_P.to_csv(data_dir + "\\" + time_stamp + "_phase_" +  f"{round(T_val, 2)}K" + ".csv")
    save_TT.to_csv(data_dir + "\\" + time_stamp + "_temperature_" + f"{round(T_val, 2)}K" + ".csv")

    true_S_lin = 10**((true_S - np.max(true_S))/10)

    fig, (ax1, ax2, ax3, ax4) = plt.subplots(1, 4)
    
    a1 = ax1.plot(time_axis, T, color = 'red')
    a2 = ax2.pcolor(time_axis, outarray[0]/1e9, true_S)
    a3 = ax3.pcolor(time_axis, outarray[0]/1e9, true_S_lin)
    a4 = ax4.pcolor(time_axis, outarray[0]/1e9, true_phase)

    ax1.set_ylim([5, 10])
    ax1.set_ylabel("Temperature (K)")
    ax2.set_ylabel("Frequency (GHz)")
    ax1.set_xlabel("time (s)")
    ax2.set_xlabel("time (s)")
    ax3.set_xlabel("time (s)")
    ax4.set_xlabel("time (s)")
    fig.colorbar(a2, label = "S$_2$$_1$ (dB)")
    fig.colorbar(a3, label = "Linear transmission")
    fig.colorbar(a4, label = "Phase (rad)")

    fig.suptitle("Real time deposition monitor " + time_stamp)
    fig.set_size_inches([13, 2.6])
    fig.tight_layout()
    plt.show()

    #heater.write("OUTP OFF")
    #heater.close()


def liquid_dep_cooldown(vna_addr, bkpower_addr, hp34461a_addr, data_save, f_search, wait_time = 60*60, focus_span = 30, silent = False, chan = 2, del_power = 0.25, del_time = 1, name = ""):

    
    #Liquid cooldown to base temp dependent on the delta power specified (power steps)

    configure_settings(vna_addr, f = f_search, BW = 1E3, span = focus_span, power = -20, n_points = 501, time = "MIN")

    vna = rm.open_resource(vna_addr)

    starting_power = get_power(bkpower_addr, chan)

    power_array = np.arange(0, starting_power, del_power)

    current_array = np.sqrt(power_array/20.02)

    current_array = np.round(current_array[::-1], 3)




    try:
        time_axis = []
        S = []
        phase = []
        T = []
        phase_rad = []
        
        f_array =[]

        time_stamp = str(datetime.now()).replace(":", "_")
        print("Started at " + time_stamp)
        t0 = datetime.now()
        time_started = t0

        for i in current_array:

            t0 = datetime.now()

            while ((datetime.now() - t0).total_seconds()) <= wait_time :
                vna.write("SENS:AVER ON")
                time.sleep(del_time)
                vs=get_smith_data(vna_addr) 
                outarray = wisform(vs)

                time_axis.append((datetime.now() - time_started).total_seconds())
                S.append(outarray[1])
                phase.append(outarray[2])
                phase_rad.append(outarray[3])
                T.append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
                vna.write("SENS:AVER OFF")
            
            set_current(bkpower_addr, chan, i)

            f_array = outarray[0]

        
            true_S = np.transpose(S)
            true_phase = np.transpose(phase)
            adjusted_phase_rad = np.transpose(phase_rad)
            save_T = pd.DataFrame(time_axis)
            save_S = pd.DataFrame(true_S)
            save_F = pd.DataFrame(f_array/1e9)
            save_P = pd.DataFrame(true_phase)
            save_rad = pd.DataFrame(adjusted_phase_rad)
            save_TT = pd.DataFrame(T)

            save_T.to_csv(data_save + "\\" + time_stamp + "_time_" + name + ".csv")
            save_S.to_csv(data_save + "\\" + time_stamp + "_S21_" + name + ".csv")
            save_F.to_csv(data_save + "\\" + time_stamp + "_frequency_" + name + ".csv")
            save_P.to_csv(data_save + "\\" + time_stamp + "_phase_" + name + ".csv")
            save_TT.to_csv(data_save + "\\" + time_stamp + "_temperature_" + name + ".csv")
            save_rad.to_csv(data_save + "\\" + time_stamp + "_phaserad_" + name + ".csv")

            true_S_lin = 10**((true_S - np.max(true_S))/10)


        fig, (ax1, ax2, ax3, ax4) = plt.subplots(1, 4)
    
        a1 = ax1.plot(time_axis, T, color = 'red')
        a2 = ax2.pcolor(time_axis, f_array/1e9, true_S)
        a3 = ax3.pcolor(time_axis, f_array/1e9, true_S_lin)
        a4 = ax4.pcolor(time_axis, f_array/1e9, true_phase)

        #ax1.set_ylim([5, 10])
        ax1.set_ylabel("Temperature (K)")
        ax2.set_ylabel("Frequency (GHz)")
        ax1.set_xlabel("time (s)")
        ax2.set_xlabel("time (s)")
        ax3.set_xlabel("time (s)")
        ax4.set_xlabel("time (s)")
        fig.colorbar(a2, label = "S$_2$$_1$ (dB)")
        fig.colorbar(a3, label = "Linear transmission")
        fig.colorbar(a4, label = "Phase (rad)")

        fig.suptitle("Real time deposition monitor " + time_stamp)
        fig.set_size_inches([13, 2.6])
        fig.tight_layout()
        plt.show()

    finally:
        
        vna.close()



def liquid_dep_warmup_cooldown_pressure(vna_addr, bkpower_addr, arduino_addr, hp34461a_addr, data_save, f_search, current_array, baud = 9600, aver = 1, wait_time = 60*60, focus_span = 30, silent = False, chan = 2, del_power = 0.25, del_time = 1, name = ""):
    
    
    #Raster through a current array and record data. Write to file after every sample

    configure_settings(vna_addr, f = f_search, BW = 1E3, span = focus_span, power = -20, n_points = 501, aver = aver, time = "MIN")

    #Open arduino and VNA communication
    vna = rm.open_resource(vna_addr)

    arduino = serial.Serial(arduino_addr, baud, timeout=2)  
    

    # Wait for Arduino to initialize
    time.sleep(2)

    set_voltage(bkpower_addr, chan, 30.0)
    channel_output_toggle(bkpower_addr, 2, 'ON')



    try:
        time_axis = []
        S = []
        phase = []
        T = []
        phase_rad = []
        pressure = []
        f_array =[]

        time_stamp = str(datetime.now()).replace(":", "_")
        print("Started at " + time_stamp)
        t0 = datetime.now()
        time_started = t0

        for i in current_array:

            t0 = datetime.now()

            while ((datetime.now() - t0).total_seconds()) <= wait_time :
                vna.write("SENS:AVER ON")
                time.sleep(del_time)
                vs=get_smith_data(vna_addr) 
                outarray = wisform(vs)

                time_axis.append((datetime.now() - time_started).total_seconds())
                S.append(outarray[1])
                phase.append(outarray[2])
                phase_rad.append(outarray[3])
                arduino.write(b'SYSTem:PRESsure:GETMbar?\n') #Reading pressure
                response = arduino.readline().decode('utf-8').strip()
                pressure.append(int(response)) #storing pressure
                T.append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
                vna.write("SENS:AVER OFF")
            
            set_current(bkpower_addr, chan, i)

            f_array = outarray[0]

        
            true_S = np.transpose(S)
            true_phase = np.transpose(phase)
            adjusted_phase_rad = np.transpose(phase_rad)
            save_T = pd.DataFrame(time_axis)
            save_S = pd.DataFrame(true_S)
            save_F = pd.DataFrame(outarray[0]/1e9)
            save_P = pd.DataFrame(true_phase)
            save_rad = pd.DataFrame(adjusted_phase_rad)
            save_TT = pd.DataFrame(T)
            save_Pres = pd.DataFrame(pressure)

            save_T.to_csv(data_save + "\\" + time_stamp + "_time_" + name + ".csv")
            save_S.to_csv(data_save + "\\" + time_stamp + "_S21_" + name + ".csv")
            save_F.to_csv(data_save + "\\" + time_stamp + "_frequency_" + name + ".csv")
            save_P.to_csv(data_save + "\\" + time_stamp + "_phase_" + name + ".csv")
            save_TT.to_csv(data_save + "\\" + time_stamp + "_temperature_" + name + ".csv")
            save_rad.to_csv(data_save + "\\" + time_stamp + "_phaserad_" + name + ".csv")
            save_Pres.to_csv(data_save + "\\" + time_stamp + "_pressure_" + name + ".csv")

            true_S_lin = 10**((true_S - np.max(true_S))/10)



        fig, (ax1, ax2, ax3, ax4) = plt.subplots(1, 4)
        
        a1 = ax1.plot(time_axis, T, color = 'red')
        a2 = ax2.pcolor(time_axis, outarray[0]/1e9, true_S)
        a3 = ax3.plot(time_axis, pressure, color = 'green')
        a4 = ax4.pcolor(time_axis, outarray[0]/1e9, true_phase)

        #ax1.set_ylim([5, 10])
        ax1.set_ylabel("Temperature (K)")
        ax2.set_ylabel("Frequency (GHz)")
        ax3.set_ylabel("Pressure (mbar)")
        ax1.set_xlabel("time (s)")
        ax2.set_xlabel("time (s)")
        ax3.set_xlabel("time (s)")
        ax4.set_xlabel("time (s)")
        fig.colorbar(a2, label = "S$_2$$_1$ (dB)")
        fig.colorbar(a4, label = "Phase (rad)")

        fig.suptitle("Real time deposition monitor " + time_stamp)
        fig.set_size_inches([13, 4])
        fig.tight_layout()
        plt.show()
    
    finally:
        vna.close()
        arduino.close()


def liquid_dep_warmup_cooldown_pressure_buffer(vna_addr, bkpower_addr, arduino_addr, hp34461a_addr, data_save, f_search, current_array, baud = 9600, buffer_time = 60*10, wait_time = 60*60, focus_span = 30, silent = False, chan = 2, del_power = 0.25, del_time = 1, name = ""):
    
    
    #Raster through a current array and record data. Write to file after every sample

    configure_settings(vna_addr, f = f_search, BW = 1E3, span = focus_span, power = -20, n_points = 501, time = "MIN")

    #Open arduino and VNA communication
    vna = rm.open_resource(vna_addr)

    arduino = serial.Serial(arduino_addr, baud, timeout=2)  
    

    # Wait for Arduino to initialize
    time.sleep(2)

    set_voltage(bkpower_addr, chan, 30.0)
    channel_output_toggle(bkpower_addr, 2, 'ON')



    try:
        time_axis = []
        S = []
        phase = []
        T = []
        phase_rad = []
        pressure = []
        f_array =[]

        time_stamp = str(datetime.now()).replace(":", "_")
        print("Started at " + time_stamp)
        t0 = datetime.now()
        time_started = t0

        for i in current_array:

            t0 = datetime.now()

            while ((datetime.now() - t0).total_seconds()) <= wait_time :
                vna.write("SENS:AVER ON")
                time.sleep(del_time)
                vs=get_smith_data(vna_addr) 
                outarray = wisform(vs)

                time_axis.append((datetime.now() - time_started).total_seconds())
                S.append(outarray[1])
                phase.append(outarray[2])
                phase_rad.append(outarray[3])
                arduino.write(b'SYSTem:PRESsure:GETMbar?\n') #Reading pressure
                response = arduino.readline().decode('utf-8').strip()
                pressure.append(int(response)) #storing pressure
                T.append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
                vna.write("SENS:AVER OFF")
            
            set_current(bkpower_addr, chan, i)

            f_array = outarray[0]

        
            true_S = np.transpose(S)
            true_phase = np.transpose(phase)
            adjusted_phase_rad = np.transpose(phase_rad)
            save_T = pd.DataFrame(time_axis)
            save_S = pd.DataFrame(true_S)
            save_F = pd.DataFrame(outarray[0]/1e9)
            save_P = pd.DataFrame(true_phase)
            save_rad = pd.DataFrame(adjusted_phase_rad)
            save_TT = pd.DataFrame(T)
            save_Pres = pd.DataFrame(pressure)

            save_T.to_csv(data_save + "\\" + time_stamp + "_time_" + name + ".csv")
            save_S.to_csv(data_save + "\\" + time_stamp + "_S21_" + name + ".csv")
            save_F.to_csv(data_save + "\\" + time_stamp + "_frequency_" + name + ".csv")
            save_P.to_csv(data_save + "\\" + time_stamp + "_phase_" + name + ".csv")
            save_TT.to_csv(data_save + "\\" + time_stamp + "_temperature_" + name + ".csv")
            save_rad.to_csv(data_save + "\\" + time_stamp + "_phaserad_" + name + ".csv")
            save_Pres.to_csv(data_save + "\\" + time_stamp + "_pressure_" + name + ".csv")

            true_S_lin = 10**((true_S - np.max(true_S))/10)

        #buffer to capture behavior after the rate drop
        buffer_start = datetime.now()
        while((datetime.now() - buffer_start).total_seconds()) <= buffer_time:
            vna.write("SENS:AVER ON")
            time.sleep(del_time)
            vs=get_smith_data(vna_addr) 
            outarray = wisform(vs)

            time_axis.append((datetime.now() - time_started).total_seconds())
            S.append(outarray[1])
            phase.append(outarray[2])
            phase_rad.append(outarray[3])
            arduino.write(b'SYSTem:PRESsure:GETMbar?\n') #Reading pressure
            response = arduino.readline().decode('utf-8').strip()
            pressure.append(int(response)) #storing pressure
            T.append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
            vna.write("SENS:AVER OFF")

            true_S = np.transpose(S)
            true_phase = np.transpose(phase)
            adjusted_phase_rad = np.transpose(phase_rad)
            save_T = pd.DataFrame(time_axis)
            save_S = pd.DataFrame(true_S)
            save_F = pd.DataFrame(outarray[0]/1e9)
            save_P = pd.DataFrame(true_phase)
            save_rad = pd.DataFrame(adjusted_phase_rad)
            save_TT = pd.DataFrame(T)
            save_Pres = pd.DataFrame(pressure)

            save_T.to_csv(data_save + "\\" + time_stamp + "_time_" + name + ".csv")
            save_S.to_csv(data_save + "\\" + time_stamp + "_S21_" + name + ".csv")
            save_F.to_csv(data_save + "\\" + time_stamp + "_frequency_" + name + ".csv")
            save_P.to_csv(data_save + "\\" + time_stamp + "_phase_" + name + ".csv")
            save_TT.to_csv(data_save + "\\" + time_stamp + "_temperature_" + name + ".csv")
            save_rad.to_csv(data_save + "\\" + time_stamp + "_phaserad_" + name + ".csv")
            save_Pres.to_csv(data_save + "\\" + time_stamp + "_pressure_" + name + ".csv")

            true_S_lin = 10**((true_S - np.max(true_S))/10)


        fig, (ax1, ax2, ax3, ax4) = plt.subplots(1, 4)
        
        a1 = ax1.plot(time_axis, T, color = 'red')
        a2 = ax2.pcolor(time_axis, outarray[0]/1e9, true_S)
        a3 = ax3.plot(time_axis, pressure, color = 'green')
        a4 = ax4.pcolor(time_axis, outarray[0]/1e9, true_phase)

        #ax1.set_ylim([5, 10])
        ax1.set_ylabel("Temperature (K)")
        ax2.set_ylabel("Frequency (GHz)")
        ax3.set_ylabel("Pressure (mbar)")
        ax1.set_xlabel("time (s)")
        ax2.set_xlabel("time (s)")
        ax3.set_xlabel("time (s)")
        ax4.set_xlabel("time (s)")
        fig.colorbar(a2, label = "S$_2$$_1$ (dB)")
        fig.colorbar(a4, label = "Phase (rad)")

        fig.suptitle("Real time deposition monitor " + time_stamp)
        fig.set_size_inches([13, 4])
        fig.tight_layout()
        plt.show()
    
    finally:
        vna.close()
        arduino.close()

def liquid_dep_warmup_cooldown_pressure_ratecompare(vna_addr, bkpower_addr, arduino_addr, hp34461a_addr, data_save, f_search, time_array, baud = 9600, cur_lims = [0.505, 0.460], buffer_time = 60*10, aver = 1, wait_time = 60*60, focus_span = 30, pow = -20, silent = False, chan = 2, del_power = 0.25, del_time = 1, name = ""):
    
    
    #Raster through a current array and record data. Write to file after every sample

    configure_settings(vna_addr, f = f_search, BW = 1E3, span = focus_span, power = pow, aver= aver, n_points = 501, time = "MIN")

    #Open arduino and VNA communication
    vna = rm.open_resource(vna_addr)

    arduino = serial.Serial(arduino_addr, baud, timeout=2)  
    

    # Wait for Arduino to initialize
    time.sleep(2)

    set_voltage(bkpower_addr, chan, 30.0)
    channel_output_toggle(bkpower_addr, 2, 'ON')



    try:
        time_axis = []
        S = []
        phase = []
        T = []
        phase_rad = []
        pressure = []
        f_array =[]

        time_stamp = str(datetime.now()).replace(":", "_")
        print("Started at " + time_stamp)
        t0 = datetime.now()
        time_started = t0



        for times in time_array:

            current_root_array = np.linspace(np.sqrt(cur_lims[0]), np.sqrt(cur_lims[1]), times)
            current_array = current_root_array**2
            warmup_current_array = current_array[::-1]


            for i in current_array:

                t0 = datetime.now()

                while ((datetime.now() - t0).total_seconds()) <= wait_time :
                    vna.write("SENS:AVER ON")
                    time.sleep(del_time)
                    vs=get_smith_data(vna_addr) 
                    outarray = wisform(vs)

                    time_axis.append((datetime.now() - time_started).total_seconds())
                    S.append(outarray[1])
                    phase.append(outarray[2])
                    phase_rad.append(outarray[3])
                    arduino.write(b'SYSTem:PRESsure:GETMbar?\n') #Reading pressure
                    response = arduino.readline().decode('utf-8').strip()
                    pressure.append(int(response)) #storing pressure
                    T.append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
                    vna.write("SENS:AVER OFF")
                
                set_current(bkpower_addr, chan, i)

                f_array = outarray[0]

            
                true_S = np.transpose(S)
                true_phase = np.transpose(phase)
                adjusted_phase_rad = np.transpose(phase_rad)
                save_T = pd.DataFrame(time_axis)
                save_S = pd.DataFrame(true_S)
                save_F = pd.DataFrame(outarray[0]/1e9)
                save_P = pd.DataFrame(true_phase)
                save_rad = pd.DataFrame(adjusted_phase_rad)
                save_TT = pd.DataFrame(T)
                save_Pres = pd.DataFrame(pressure)

                save_T.to_csv(data_save + "\\" + time_stamp + "_time_" + name + ".csv")
                save_S.to_csv(data_save + "\\" + time_stamp + "_S21_" + name + ".csv")
                save_F.to_csv(data_save + "\\" + time_stamp + "_frequency_" + name + ".csv")
                save_P.to_csv(data_save + "\\" + time_stamp + "_phase_" + name + ".csv")
                save_TT.to_csv(data_save + "\\" + time_stamp + "_temperature_" + name + ".csv")
                save_rad.to_csv(data_save + "\\" + time_stamp + "_phaserad_" + name + ".csv")
                save_Pres.to_csv(data_save + "\\" + time_stamp + "_pressure_" + name + ".csv")

                true_S_lin = 10**((true_S - np.max(true_S))/10)

            #buffer to capture behavior after the rate drop
            buffer_start = datetime.now()
            while((datetime.now() - buffer_start).total_seconds()) <= buffer_time:
                vna.write("SENS:AVER ON")
                time.sleep(del_time)
                vs=get_smith_data(vna_addr) 
                outarray = wisform(vs)

                time_axis.append((datetime.now() - time_started).total_seconds())
                S.append(outarray[1])
                phase.append(outarray[2])
                phase_rad.append(outarray[3])
                arduino.write(b'SYSTem:PRESsure:GETMbar?\n') #Reading pressure
                response = arduino.readline().decode('utf-8').strip()
                pressure.append(int(response)) #storing pressure
                T.append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
                vna.write("SENS:AVER OFF")

                true_S = np.transpose(S)
                true_phase = np.transpose(phase)
                adjusted_phase_rad = np.transpose(phase_rad)
                save_T = pd.DataFrame(time_axis)
                save_S = pd.DataFrame(true_S)
                save_F = pd.DataFrame(outarray[0]/1e9)
                save_P = pd.DataFrame(true_phase)
                save_rad = pd.DataFrame(adjusted_phase_rad)
                save_TT = pd.DataFrame(T)
                save_Pres = pd.DataFrame(pressure)

                save_T.to_csv(data_save + "\\" + time_stamp + "_time_" + name + ".csv")
                save_S.to_csv(data_save + "\\" + time_stamp + "_S21_" + name + ".csv")
                save_F.to_csv(data_save + "\\" + time_stamp + "_frequency_" + name + ".csv")
                save_P.to_csv(data_save + "\\" + time_stamp + "_phase_" + name + ".csv")
                save_TT.to_csv(data_save + "\\" + time_stamp + "_temperature_" + name + ".csv")
                save_rad.to_csv(data_save + "\\" + time_stamp + "_phaserad_" + name + ".csv")
                save_Pres.to_csv(data_save + "\\" + time_stamp + "_pressure_" + name + ".csv")

                true_S_lin = 10**((true_S - np.max(true_S))/10)
            
            #After waiting for buffer, do the warmup scan at the same rate
            for i in warmup_current_array:

                t0 = datetime.now()

                while ((datetime.now() - t0).total_seconds()) <= wait_time :
                    vna.write("SENS:AVER ON")
                    time.sleep(del_time)
                    vs=get_smith_data(vna_addr) 
                    outarray = wisform(vs)

                    time_axis.append((datetime.now() - time_started).total_seconds())
                    S.append(outarray[1])
                    phase.append(outarray[2])
                    phase_rad.append(outarray[3])
                    arduino.write(b'SYSTem:PRESsure:GETMbar?\n') #Reading pressure
                    response = arduino.readline().decode('utf-8').strip()
                    pressure.append(int(response)) #storing pressure
                    T.append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
                    vna.write("SENS:AVER OFF")
                
                set_current(bkpower_addr, chan, i)

                f_array = outarray[0]

            
                true_S = np.transpose(S)
                true_phase = np.transpose(phase)
                adjusted_phase_rad = np.transpose(phase_rad)
                save_T = pd.DataFrame(time_axis)
                save_S = pd.DataFrame(true_S)
                save_F = pd.DataFrame(outarray[0]/1e9)
                save_P = pd.DataFrame(true_phase)
                save_rad = pd.DataFrame(adjusted_phase_rad)
                save_TT = pd.DataFrame(T)
                save_Pres = pd.DataFrame(pressure)

                save_T.to_csv(data_save + "\\" + time_stamp + "_time_" + name + ".csv")
                save_S.to_csv(data_save + "\\" + time_stamp + "_S21_" + name + ".csv")
                save_F.to_csv(data_save + "\\" + time_stamp + "_frequency_" + name + ".csv")
                save_P.to_csv(data_save + "\\" + time_stamp + "_phase_" + name + ".csv")
                save_TT.to_csv(data_save + "\\" + time_stamp + "_temperature_" + name + ".csv")
                save_rad.to_csv(data_save + "\\" + time_stamp + "_phaserad_" + name + ".csv")
                save_Pres.to_csv(data_save + "\\" + time_stamp + "_pressure_" + name + ".csv")

                true_S_lin = 10**((true_S - np.max(true_S))/10)

            #Another buffer before restarting cooldown

            buffer_start = datetime.now()
            while((datetime.now() - buffer_start).total_seconds()) <= buffer_time:
                vna.write("SENS:AVER ON")
                time.sleep(del_time)
                vs=get_smith_data(vna_addr) 
                outarray = wisform(vs)

                time_axis.append((datetime.now() - time_started).total_seconds())
                S.append(outarray[1])
                phase.append(outarray[2])
                phase_rad.append(outarray[3])
                arduino.write(b'SYSTem:PRESsure:GETMbar?\n') #Reading pressure
                response = arduino.readline().decode('utf-8').strip()
                pressure.append(int(response)) #storing pressure
                T.append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
                vna.write("SENS:AVER OFF")

                true_S = np.transpose(S)
                true_phase = np.transpose(phase)
                adjusted_phase_rad = np.transpose(phase_rad)
                save_T = pd.DataFrame(time_axis)
                save_S = pd.DataFrame(true_S)
                save_F = pd.DataFrame(outarray[0]/1e9)
                save_P = pd.DataFrame(true_phase)
                save_rad = pd.DataFrame(adjusted_phase_rad)
                save_TT = pd.DataFrame(T)
                save_Pres = pd.DataFrame(pressure)

                save_T.to_csv(data_save + "\\" + time_stamp + "_time_" + name + ".csv")
                save_S.to_csv(data_save + "\\" + time_stamp + "_S21_" + name + ".csv")
                save_F.to_csv(data_save + "\\" + time_stamp + "_frequency_" + name + ".csv")
                save_P.to_csv(data_save + "\\" + time_stamp + "_phase_" + name + ".csv")
                save_TT.to_csv(data_save + "\\" + time_stamp + "_temperature_" + name + ".csv")
                save_rad.to_csv(data_save + "\\" + time_stamp + "_phaserad_" + name + ".csv")
                save_Pres.to_csv(data_save + "\\" + time_stamp + "_pressure_" + name + ".csv")

                true_S_lin = 10**((true_S - np.max(true_S))/10)

        fig, (ax1, ax2, ax3, ax4) = plt.subplots(1, 4)
        
        a1 = ax1.plot(time_axis, T, color = 'red')
        a2 = ax2.pcolor(time_axis, outarray[0]/1e9, true_S)
        a3 = ax3.plot(time_axis, pressure, color = 'green')
        a4 = ax4.pcolor(time_axis, outarray[0]/1e9, true_phase)

        #ax1.set_ylim([5, 10])
        ax1.set_ylabel("Temperature (K)")
        ax2.set_ylabel("Frequency (GHz)")
        ax3.set_ylabel("Pressure (mbar)")
        ax1.set_xlabel("time (s)")
        ax2.set_xlabel("time (s)")
        ax3.set_xlabel("time (s)")
        ax4.set_xlabel("time (s)")
        fig.colorbar(a2, label = "S$_2$$_1$ (dB)")
        fig.colorbar(a4, label = "Phase (rad)")

        fig.suptitle("Real time deposition monitor " + time_stamp)
        fig.set_size_inches([13, 4])
        fig.tight_layout()
        plt.show()
    
    finally:
        vna.close()
        arduino.close()


def mfc_depMon(vna_addr, hp34461a_addr, data_dir, seconds = 10, del_time = 1, f = -999, BW = -999, span = 10, power = -100, n_points = 201, name = ""):


    #Monitor mfc deposition, writing dataframe to file after every collected point
    
    #set up the vna appropriately before sweeping
    configure_settings(vna_addr = vna_addr, type = "LIN", f = f, BW = BW, span = span, power = power, n_points = n_points, time = "MIN")

    vna = rm.open_resource(vna_addr)

    try:
    
    
        time_axis = []
        S = []
        phase = []
        T = []
        phase_rad = []

        time_stamp = str(datetime.now()).replace(":", "_")
        print("Started at " + time_stamp)
        time.sleep(1)
        for i in range(int(seconds/del_time)):
            vna.write("SENS:AVER ON")
            time.sleep(del_time)
            vs=get_smith_data(vna_addr) 
            outarray = wisform(vs)
            if i == 0:
                t0 = datetime.now()

            time_axis.append((datetime.now() - t0).total_seconds())
            S.append(outarray[1])
            phase.append(outarray[2])
            phase_rad.append(outarray[3])
            T.append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
            vna.write("SENS:AVER OFF")
            true_S = np.transpose(S)
            true_phase = np.transpose(phase)
            adjusted_phase_rad = np.transpose(phase_rad)
            save_T = pd.DataFrame(time_axis)
            save_S = pd.DataFrame(true_S)
            save_F = pd.DataFrame(outarray[0]/1e9)
            save_P = pd.DataFrame(true_phase)
            save_rad = pd.DataFrame(adjusted_phase_rad)
            save_TT = pd.DataFrame(T)

            save_T.to_csv(data_dir + "\\" + time_stamp + "_time_" + name + ".csv")
            save_S.to_csv(data_dir + "\\" + time_stamp + "_S21_" + name + ".csv")
            save_F.to_csv(data_dir + "\\" + time_stamp + "_frequency_" + name + ".csv")
            save_P.to_csv(data_dir + "\\" + time_stamp + "_phase_" + name + ".csv")
            save_TT.to_csv(data_dir + "\\" + time_stamp + "_temperature_" + name + ".csv")
            save_rad.to_csv(data_dir + "\\" + time_stamp + "_phaserad_" + name + ".csv")

        true_S_lin = 10**((true_S - np.max(true_S))/10)

        fig, (ax1, ax2, ax3, ax4) = plt.subplots(1, 4)
        
        a1 = ax1.plot(time_axis, T, color = 'red')
        a2 = ax2.pcolor(time_axis, outarray[0]/1e9, true_S)
        a3 = ax3.pcolor(time_axis, outarray[0]/1e9, true_S_lin)
        a4 = ax4.pcolor(time_axis, outarray[0]/1e9, true_phase)

        #ax1.set_ylim([5, 10])
        ax1.set_ylabel("Temperature (K)")
        ax2.set_ylabel("Frequency (GHz)")
        ax1.set_xlabel("time (s)")
        ax2.set_xlabel("time (s)")
        ax3.set_xlabel("time (s)")
        ax4.set_xlabel("time (s)")
        fig.colorbar(a2, label = "S$_2$$_1$ (dB)")
        fig.colorbar(a3, label = "Linear transmission")
        fig.colorbar(a4, label = "Phase (rad)")

        fig.suptitle("Real time deposition monitor " + time_stamp)
        fig.set_size_inches([13, 4])
        fig.tight_layout()
        plt.show()
    
    finally:
        vna.close()


def mfc_depMon(vna_addr, hp34461a_addr, data_dir, seconds = 10, del_time = 1, f = -999, BW = -999, span = 10, power = -100, n_points = 201, name = ""):


    #Monitor mfc deposition, writing dataframe to file after every collected point
    
    #set up the vna appropriately before sweeping
    configure_settings(vna_addr = vna_addr, type = "LIN", f = f, BW = BW, span = span, power = power, n_points = n_points, time = "MIN")

    vna = rm.open_resource(vna_addr)

    try:
    
    
        time_axis = []
        S = []
        phase = []
        T = []
        phase_rad = []

        time_stamp = str(datetime.now()).replace(":", "_")
        print("Started at " + time_stamp)
        time.sleep(1)
        for i in range(int(seconds/del_time)):
            vna.write("SENS:AVER ON")
            time.sleep(del_time)
            vs=get_smith_data(vna_addr) 
            outarray = wisform(vs)
            if i == 0:
                t0 = datetime.now()

            time_axis.append((datetime.now() - t0).total_seconds())
            S.append(outarray[1])
            phase.append(outarray[2])
            phase_rad.append(outarray[3])
            T.append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
            vna.write("SENS:AVER OFF")
            true_S = np.transpose(S)
            true_phase = np.transpose(phase)
            adjusted_phase_rad = np.transpose(phase_rad)
            save_T = pd.DataFrame(time_axis)
            save_S = pd.DataFrame(true_S)
            save_F = pd.DataFrame(outarray[0]/1e9)
            save_P = pd.DataFrame(true_phase)
            save_rad = pd.DataFrame(adjusted_phase_rad)
            save_TT = pd.DataFrame(T)

            save_T.to_csv(data_dir + "\\" + time_stamp + "_time_" + name + ".csv")
            save_S.to_csv(data_dir + "\\" + time_stamp + "_S21_" + name + ".csv")
            save_F.to_csv(data_dir + "\\" + time_stamp + "_frequency_" + name + ".csv")
            save_P.to_csv(data_dir + "\\" + time_stamp + "_phase_" + name + ".csv")
            save_TT.to_csv(data_dir + "\\" + time_stamp + "_temperature_" + name + ".csv")
            save_rad.to_csv(data_dir + "\\" + time_stamp + "_phaserad_" + name + ".csv")

        true_S_lin = 10**((true_S - np.max(true_S))/10)

        fig, (ax1, ax2, ax3, ax4) = plt.subplots(1, 4)
        
        a1 = ax1.plot(time_axis, T, color = 'red')
        a2 = ax2.pcolor(time_axis, outarray[0]/1e9, true_S)
        a3 = ax3.pcolor(time_axis, outarray[0]/1e9, true_S_lin)
        a4 = ax4.pcolor(time_axis, outarray[0]/1e9, true_phase)

        #ax1.set_ylim([5, 10])
        ax1.set_ylabel("Temperature (K)")
        ax2.set_ylabel("Frequency (GHz)")
        ax1.set_xlabel("time (s)")
        ax2.set_xlabel("time (s)")
        ax3.set_xlabel("time (s)")
        ax4.set_xlabel("time (s)")
        fig.colorbar(a2, label = "S$_2$$_1$ (dB)")
        fig.colorbar(a3, label = "Linear transmission")
        fig.colorbar(a4, label = "Phase (rad)")

        fig.suptitle("Real time deposition monitor " + time_stamp)
        fig.set_size_inches([13, 4])
        fig.tight_layout()
        plt.show()
    
    finally:
        vna.close()





def mfc_depMon_pressure(vna_addr, hp34461a_addr, arduino_addr, data_dir, baud = 9600, seconds = 10, del_time = 1, f = -999, BW = -999, span = 10, power = -100, n_points = 201, name = ""):
    configure_settings(vna_addr = vna_addr, type = "LIN", f = f, BW = BW, span = span, power = power, n_points = n_points, time = "MIN")

    #Monitor mfc deposition with pressure readings as well
    
    #Open arduino and VNA communication
    vna = rm.open_resource(vna_addr)

    arduino = serial.Serial(arduino_addr, baud, timeout=2)  
    

    # Wait for Arduino to initialize
    time.sleep(2)
   

    

    try:
    
    
        time_axis = []
        S = []
        phase = []
        T = []
        phase_rad = []
        pressure = []

        time_stamp = str(datetime.now()).replace(":", "_")
        print("Started at " + time_stamp)
        time.sleep(1)
        for i in range(int(seconds/del_time)):
            vna.write("SENS:AVER ON")
            time.sleep(del_time)
            vs=get_smith_data(vna_addr) 
            outarray = wisform(vs)
            if i == 0:
                t0 = datetime.now()

            time_axis.append((datetime.now() - t0).total_seconds())
            S.append(outarray[1]) #S matrix element
            phase.append(outarray[2]) #phase wrapped
            phase_rad.append(outarray[3]) #Phase unwrapped
            T.append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
            arduino.write(b'SYSTem:PRESsure:GETMbar?\n') #Reading pressure
            response = arduino.readline().decode('utf-8').strip()
            pressure.append(int(response)) #storing pressure
            vna.write("SENS:AVER OFF")
            true_S = np.transpose(S)
            true_phase = np.transpose(phase)
            adjusted_phase_rad = np.transpose(phase_rad)
            #Storing all of this in the dataframe and writing to the file
            save_T = pd.DataFrame(time_axis)
            save_S = pd.DataFrame(true_S)
            save_F = pd.DataFrame(outarray[0]/1e9)
            save_P = pd.DataFrame(true_phase)
            save_rad = pd.DataFrame(adjusted_phase_rad)
            save_TT = pd.DataFrame(T)
            save_Pres = pd.DataFrame(pressure)

            save_T.to_csv(data_dir + "\\" + time_stamp + "_time_" + name + ".csv")
            save_S.to_csv(data_dir + "\\" + time_stamp + "_S21_" + name + ".csv")
            save_F.to_csv(data_dir + "\\" + time_stamp + "_frequency_" + name + ".csv")
            save_P.to_csv(data_dir + "\\" + time_stamp + "_phase_" + name + ".csv")
            save_TT.to_csv(data_dir + "\\" + time_stamp + "_temperature_" + name + ".csv")
            save_rad.to_csv(data_dir + "\\" + time_stamp + "_phaserad_" + name + ".csv")
            save_Pres.to_csv(data_dir + "\\" + time_stamp + "_pressure_" + name + ".csv")

        true_S_lin = 10**((true_S - np.max(true_S))/10)

        fig, (ax1, ax2, ax3, ax4) = plt.subplots(1, 4)
        
        a1 = ax1.plot(time_axis, T, color = 'red')
        a2 = ax2.pcolor(time_axis, outarray[0]/1e9, true_S)
        a3 = ax3.plot(time_axis, pressure, color = 'green')
        a4 = ax4.pcolor(time_axis, outarray[0]/1e9, true_phase)

        #ax1.set_ylim([5, 10])
        ax1.set_ylabel("Temperature (K)")
        ax2.set_ylabel("Frequency (GHz)")
        ax3.set_ylabel("Pressure (mbar)")
        ax1.set_xlabel("time (s)")
        ax2.set_xlabel("time (s)")
        ax3.set_xlabel("time (s)")
        ax4.set_xlabel("time (s)")
        fig.colorbar(a2, label = "S$_2$$_1$ (dB)")
        fig.colorbar(a4, label = "Phase (rad)")

        fig.suptitle("Real time deposition monitor " + time_stamp)
        fig.set_size_inches([13, 4])
        fig.tight_layout()
        plt.show()
    
    finally:
        vna.close()
        arduino.close()


def power_ringup_ringdown(vna_addr, hp34461a_addr, arduino_addr, data_dir, baud = 9600, buffer = 2, seconds = 10, aver = 1, del_time = 1, f = -999, BW = -999, span = 10, power = [-30, 10], n_points = 501, name = ""):

    configure_settings(vna_addr = vna_addr, type = "LIN", f = f, BW = BW, span = span, power = power[0], n_points = n_points, time = "MIN")

    #Monitor mfc deposition with pressure readings as well
    
    #Open arduino and VNA communication
    arduino = serial.Serial(arduino_addr, baud, timeout=2)  
    

    # Wait for Arduino to initialize
    time.sleep(2)
    time_axis = []
    S = []
    phase = []
    T = []
    phase_rad = []
    pressure = []

    

    time_stamp = str(datetime.now()).replace(":", "_")
    print("Started at " + time_stamp)
    configure_settings(vna_addr = vna_addr, type = "LIN", f = f, BW = BW, span = span, power = power[0], aver = aver, n_points = n_points, time = "MIN")
    t0 = datetime.now()
    while ((datetime.now()-t0).total_seconds() <= buffer):
        time_axis.append((datetime.now() - t0).total_seconds())
        vs=get_smith_data(vna_addr) 
        outarray = wisform(vs)
        S.append(outarray[1]) #S matrix element
        phase.append(outarray[2]) #phase wrapped
        phase_rad.append(outarray[3]) #Phase unwrapped
        T.append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
        arduino.write(b'SYSTem:PRESsure:GETMbar?\n') #Reading pressure
        response = arduino.readline().decode('utf-8').strip()
        pressure.append(int(response)) #storing pressure

        time.sleep(del_time)


    configure_settings(vna_addr = vna_addr, type = "LIN", f = f, BW = BW, span = span, power = power[1], n_points = n_points, time = "MIN")
    t1 = datetime.now()

    while((datetime.now() - t1).total_seconds() <= seconds):
        time_axis.append((datetime.now() - t0).total_seconds())
        vs=get_smith_data(vna_addr) 
        outarray = wisform(vs)
        S.append(outarray[1]) #S matrix element
        phase.append(outarray[2]) #phase wrapped
        phase_rad.append(outarray[3]) #Phase unwrapped
        T.append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
        arduino.write(b'SYSTem:PRESsure:GETMbar?\n') #Reading pressure
        response = arduino.readline().decode('utf-8').strip()
        pressure.append(int(response)) #storing pressure

        time.sleep(del_time)


    configure_settings(vna_addr = vna_addr, type = "LIN", f = f, BW = BW, span = span, power = power[0], n_points = n_points, time = "MIN")
    t2 = datetime.now()

    while((datetime.now() - t2).total_seconds() <= seconds):
        time_axis.append((datetime.now() - t0).total_seconds())
        vs=get_smith_data(vna_addr) 
        outarray = wisform(vs)
        S.append(outarray[1]) #S matrix element
        phase.append(outarray[2]) #phase wrapped
        phase_rad.append(outarray[3]) #Phase unwrapped
        T.append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
        arduino.write(b'SYSTem:PRESsure:GETMbar?\n') #Reading pressure
        response = arduino.readline().decode('utf-8').strip()
        pressure.append(int(response)) #storing pressure

        time.sleep(del_time)        

    vna = rm.open_resource(vna_addr)
    vna.write("SENS:AVER OFF")

    true_S = np.transpose(S)
    true_phase = np.transpose(phase)
    adjusted_phase_rad = np.transpose(phase_rad)
    #Storing all of this in the dataframe and writing to the file
    save_T = pd.DataFrame(time_axis)
    save_S = pd.DataFrame(true_S)
    save_F = pd.DataFrame(outarray[0]/1e9)
    save_P = pd.DataFrame(true_phase)
    save_rad = pd.DataFrame(adjusted_phase_rad)
    save_TT = pd.DataFrame(T)
    save_Pres = pd.DataFrame(pressure)

    save_T.to_csv(data_dir + "\\" + time_stamp + "_time_" + name + ".csv")
    save_S.to_csv(data_dir + "\\" + time_stamp + "_S21_" + name + ".csv")
    save_F.to_csv(data_dir + "\\" + time_stamp + "_frequency_" + name + ".csv")
    save_P.to_csv(data_dir + "\\" + time_stamp + "_phase_" + name + ".csv")
    save_TT.to_csv(data_dir + "\\" + time_stamp + "_temperature_" + name + ".csv")
    save_rad.to_csv(data_dir + "\\" + time_stamp + "_phaserad_" + name + ".csv")
    save_Pres.to_csv(data_dir + "\\" + time_stamp + "_pressure_" + name + ".csv")

    true_S_lin = 10**((true_S - np.max(true_S))/10)

    fig, (ax1, ax2, ax3, ax4) = plt.subplots(1, 4)
    
    a1 = ax1.plot(time_axis, T, color = 'red')
    a2 = ax2.pcolor(time_axis, outarray[0]/1e9, true_S)
    a3 = ax3.plot(time_axis, pressure, color = 'green')
    a4 = ax4.pcolor(time_axis, outarray[0]/1e9, true_phase)

    #ax1.set_ylim([5, 10])
    ax1.set_ylabel("Temperature (K)")
    ax2.set_ylabel("Frequency (GHz)")
    ax3.set_ylabel("Pressure (mbar)")
    ax1.set_xlabel("time (s)")
    ax2.set_xlabel("time (s)")
    ax3.set_xlabel("time (s)")
    ax4.set_xlabel("time (s)")
    fig.colorbar(a2, label = "S$_2$$_1$ (dB)")
    fig.colorbar(a4, label = "Phase (rad)")

    fig.suptitle("Real time deposition monitor " + time_stamp)
    fig.set_size_inches([13, 4])
    fig.tight_layout()
    plt.show()

    vna.close()
    arduino.close()



def multires_liquid_cooldown_buffer(vna_addr, hp34461a_addr, bkpower_addr, arduino_addr, data_dir, current_array = [], chan = 2, baud = 9600, buffer = 2, wait_time = 60, delay_time = 60*10, del_time = 10, f_vals = [-999], BW = -999, span = 100, power = -20, n_points = 201, name = ""):
    
    
    vna = rm.open_resource(vna_addr)

    arduino = serial.Serial(arduino_addr, baud, timeout=2)  
    

    # Wait for Arduino to initialize
    time.sleep(2)

    #INitialize heater
    set_voltage(bkpower_addr, chan, 30.0)
    #channel_output_toggle(bkpower_addr, chan, 'ON')
    time.sleep(1)


    #Will store data of each resonator as a dictionary entry - list for each entry 
    time_axis = {}
    S_axis = {}
    T_vals = {}
    f_array = {}
    p_array = {}

    #Initialize empty dicts, make subdirectories to store data
    for freq in range (len(f_vals)):
        time_axis[freq] = []
        S_axis[freq] = []
        T_vals[freq] = []
        f_array[freq] = []
        p_array[freq] = []

        os.makedirs(data_dir + '\\' + f"mode{freq}", exist_ok = True)

    #want to initialize the VNA now

    vna.write("INIT:CONT ON") #turn on internal triggering
    #BNC.write("OUTP OFF")
    vna.write(f"SENS:SWE:TYPE LIN")
    vna.write("SENS:AVER OFF")
    vna.write("SENSe1:FREQuency:SPAN " + str(span) + "mhz")
    print(span) 
    #vna.write("DISP:WIND:TRAC:Y:AUTO")
    if BW != -999: vna.write("SENS:BWID " + str(BW) + "HZ")
    vna.write("SENS:SWE:POIN " + str(n_points)) 
    vna.write(f"SENS:SWE:TIME {time}")
    vna.write("OUTP ON")
    if power != -100: vna.write(f"SOUR:POW {power}")

    try:
        time_stamp = str(datetime.now()).replace(":", "_")
        print("Started at " + time_stamp)
        t0 = datetime.now()
        time_started = t0

        for curr in current_array:

            t0 = datetime.now()
            while((datetime.now()-t0).total_seconds() <= wait_time):

                for index, f in enumerate(f_vals):
                    vna.write("SENSe1:FREQuency:CENTer " + str(f) + "ghz")

                    #Set frequency and start collecting data
                    vna.write("SENS:AVER ON")
                    time.sleep(del_time)
                    vs=get_smith_data(vna_addr) 
                    outarray = wisform(vs)

                    time_axis[index].append((datetime.now() - time_started).total_seconds())
                    f_array[index] = (outarray[0]/1E9)
                    S_axis[index].append(outarray[1])
                    arduino.write(b'SYSTem:PRESsure:GETMbar?\n') #Reading pressure
                    response = arduino.readline().decode('utf-8').strip()
                    p_array[index].append(int(response)) #storing pressure
                    T_vals[index].append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
                    time.sleep(1)
                    vna.write("SENS:AVER OFF")

                    #to ensure no overloading between measurements of the different modes
                    time.sleep(delay_time)

            set_current(bkpower_addr, chan, curr)    
        #After all 9 modes are measured for a particular current/temperature value, we want to save this data in the respective folder of each directory

            for i in range(len(f_vals)):
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_time_" + name + ".csv", np.array(time_axis[i]), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_S21_" + name + ".csv", np.array(np.transpose(S_axis[i])), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_frequency_" + name + ".csv", np.array(f_array[i]), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_temperature_" + name + ".csv", np.array(T_vals[i]), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_pressure_" + name + ".csv", np.array(p_array[i]), fmt = '%d')

                #buffer to allow file saving without hassle
                time.sleep(1)
        #Once this is all done, we now want to collect data during the buffer period as well, allow the resonator to fully settle at the 
        #desired temperature

        t_buffer = datetime.now()
        while(((datetime.now() - t_buffer).total_seconds()) <= buffer):

            for index,f in enumerate(f_vals):
                vna.write("SENSe1:FREQuency:CENTer " + str(f) + "ghz")

                #Set frequency and start collecting data
                vna.write("SENS:AVER ON")
                time.sleep(del_time)
                vs=get_smith_data(vna_addr) 
                outarray = wisform(vs)

                time_axis[index].append((datetime.now() - time_started).total_seconds())
                f_array[index] = (outarray[0]/1E9)
                S_axis[index].append(outarray[1])
                arduino.write(b'SYSTem:PRESsure:GETMbar?\n') #Reading pressure
                response = arduino.readline().decode('utf-8').strip()
                p_array[index].append(int(response)) #storing pressure
                T_vals[index].append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
                vna.write("SENS:AVER OFF")

                #to ensure no overloading between measurements of the different modes
                time.sleep(delay_time)

            for i in range(len(f_vals)):
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_time_" + name + ".csv", np.array(time_axis[i]), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_S21_" + name + ".csv", np.array(np.transpose(S_axis[i])), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_frequency_" + name + ".csv", np.array(f_array[i]), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_temperature_" + name + ".csv", np.array(T_vals[i]), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_pressure_" + name + ".csv", np.array(p_array[i]), fmt = '%d')

                #wait to allow file saving without hassle
                time.sleep(1)



        #We now plot each deposition as a 3x3 grid, Ideally, I want it to align with the placement of each resonator on the chip

        fig, axes = plt.subplots(3,3, figsize = (13, 13))

        layout = [
            [6, 7, 8],
            [5, 4, 3],
            [0, 1, 2]
        ]

        for i in range(3):
            for j in range(3):
                to_plot = layout[i][j]
                pcm = axes[i, j].pcolor(np.array(time_axis[to_plot]), np.array(f_array[to_plot]), np.array(np.transpose(S_axis[to_plot])))
                axes[i, j].set_xlabel("time (s)")
                axes[i, j].set_ylabel("Frequency (GHz)")
                axes[i, j].set_title(f"Mode {to_plot}")
                fig.colorbar(pcm, ax=axes[i,j], label = "S$_{21}$")


        fig.suptitle("Real time multires deposition monitor")
        plt.tight_layout()
        plt.show()
        
    finally:
        vna.close()
        arduino.close()


def multires_liquid_cooldown_power(vna_addr, hp34461a_addr, bkpower_addr, arduino_addr, data_dir, current_array = [], chan = 2, baud = 9600, buffer = 2, wait_time = 60, delay_time = 60*10, del_time = 10, f_vals = [-999], BW = -999, span = 100, power_array = [-20], n_points = 201, name = ""):
    
    
    vna = rm.open_resource(vna_addr)

    arduino = serial.Serial(arduino_addr, baud, timeout=2)  
    

    # Wait for Arduino to initialize
    time.sleep(2)

    #INitialize heater
    set_voltage(bkpower_addr, chan, 30.0)
    #channel_output_toggle(bkpower_addr, chan, 'ON')
    time.sleep(1)


    #Will store data of each resonator as a dictionary entry - list for each entry 
    time_axis = {}
    S_axis = {}
    T_vals = {}
    f_array = {}
    p_array = {}

    #Initialize empty dicts, make subdirectories to store data
    for freq in range (len(f_vals)):
        time_axis[freq] = []
        S_axis[freq] = []
        T_vals[freq] = []
        f_array[freq] = []
        p_array[freq] = []

        os.makedirs(data_dir + '\\' + f"mode{freq}", exist_ok = True)

    #want to initialize the VNA now

    vna.write("INIT:CONT ON") #turn on internal triggering
    #BNC.write("OUTP OFF")
    vna.write(f"SENS:SWE:TYPE LIN")
    vna.write("SENS:AVER OFF")
    vna.write("SENSe1:FREQuency:SPAN " + str(span) + "mhz")
    print(span) 
    #vna.write("DISP:WIND:TRAC:Y:AUTO")
    if BW != -999: vna.write("SENS:BWID " + str(BW) + "HZ")
    vna.write("SENS:SWE:POIN " + str(n_points)) 
    vna.write(f"SENS:SWE:TIME {time}")
    vna.write("OUTP ON")
    vna.write(f"SOUR:POW {power_array[0]}")

    try:
        time_stamp = str(datetime.now()).replace(":", "_")
        print("Started at " + time_stamp)
        t0 = datetime.now()
        time_started = t0

        for curr in current_array:

            t0 = datetime.now()
            while((datetime.now()-t0).total_seconds() <= wait_time):

                for index, f in enumerate(f_vals):
                    vna.write("SENSe1:FREQuency:CENTer " + str(f) + "ghz")
                    vna.write(f"SOUR:POW {power_array[index]}")

                    #Set frequency and start collecting data
                    vna.write("SENS:AVER ON")
                    time.sleep(del_time)
                    vs=get_smith_data(vna_addr) 
                    outarray = wisform(vs)

                    time_axis[index].append((datetime.now() - time_started).total_seconds())
                    f_array[index] = (outarray[0]/1E9)
                    S_axis[index].append(outarray[1])
                    arduino.write(b'SYSTem:PRESsure:GETMbar?\n') #Reading pressure
                    response = arduino.readline().decode('utf-8').strip()
                    p_array[index].append(int(response)) #storing pressure
                    T_vals[index].append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
                    time.sleep(1)
                    vna.write("SENS:AVER OFF")

                    #to ensure no overloading between measurements of the different modes
                    time.sleep(delay_time)

            set_current(bkpower_addr, chan, curr)    
        #After all 9 modes are measured for a particular current/temperature value, we want to save this data in the respective folder of each directory

            for i in range(len(f_vals)):
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_time_" + name + ".csv", np.array(time_axis[i]), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_S21_" + name + ".csv", np.array(np.transpose(S_axis[i])), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_frequency_" + name + ".csv", np.array(f_array[i]), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_temperature_" + name + ".csv", np.array(T_vals[i]), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_pressure_" + name + ".csv", np.array(p_array[i]), fmt = '%d')

                #buffer to allow file saving without hassle
                time.sleep(1)
        #Once this is all done, we now want to collect data during the buffer period as well, allow the resonator to fully settle at the 
        #desired temperature

        t_buffer = datetime.now()
        while(((datetime.now() - t_buffer).total_seconds()) <= buffer):

            for index,f in enumerate(f_vals):
                vna.write("SENSe1:FREQuency:CENTer " + str(f) + "ghz")

                #Set frequency and start collecting data
                vna.write("SENS:AVER ON")
                time.sleep(del_time)
                vs=get_smith_data(vna_addr) 
                outarray = wisform(vs)

                time_axis[index].append((datetime.now() - time_started).total_seconds())
                f_array[index] = (outarray[0]/1E9)
                S_axis[index].append(outarray[1])
                arduino.write(b'SYSTem:PRESsure:GETMbar?\n') #Reading pressure
                response = arduino.readline().decode('utf-8').strip()
                p_array[index].append(int(response)) #storing pressure
                T_vals[index].append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
                vna.write("SENS:AVER OFF")

                #to ensure no overloading between measurements of the different modes
                time.sleep(delay_time)

            for i in range(len(f_vals)):
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_time_" + name + ".csv", np.array(time_axis[i]), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_S21_" + name + ".csv", np.array(np.transpose(S_axis[i])), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_frequency_" + name + ".csv", np.array(f_array[i]), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_temperature_" + name + ".csv", np.array(T_vals[i]), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_pressure_" + name + ".csv", np.array(p_array[i]), fmt = '%d')

                #wait to allow file saving without hassle
                time.sleep(1)



        #We now plot each deposition as a 3x3 grid, Ideally, I want it to align with the placement of each resonator on the chip

        fig, axes = plt.subplots(3,3, figsize = (13, 13))

        layout = [
            [6, 7, 8],
            [5, 4, 3],
            [0, 1, 2]
        ]

        for i in range(3):
            for j in range(3):
                to_plot = layout[i][j]
                pcm = axes[i, j].pcolor(np.array(time_axis[to_plot]), np.array(f_array[to_plot]), np.array(np.transpose(S_axis[to_plot])))
                axes[i, j].set_xlabel("time (s)")
                axes[i, j].set_ylabel("Frequency (GHz)")
                axes[i, j].set_title(f"Mode {to_plot}")
                fig.colorbar(pcm, ax=axes[i,j], label = "S$_{21}$")


        fig.suptitle("Real time multires deposition monitor")
        plt.tight_layout()
        plt.show()
        
    finally:
        vna.close()
        arduino.close()

def mfc_multires_depMon(vna_addr, hp34461a_addr, arduino_addr, data_dir, baud = 9600, wait_time = 60*10, delay_time = 1, del_time = 10, f_vals = [-999], BW = -999, span = 100, power = -20, n_points = 201, name = ""):

    vna = rm.open_resource(vna_addr)

    arduino = serial.Serial(arduino_addr, baud, timeout=2)  
    

    # Wait for Arduino to initialize
    time.sleep(2)


    #Will store data of each resonator as a dictionary entry - list for each entry 
    time_axis = {}
    S_axis = {}
    T_vals = {}
    f_array = {}
    p_array = {}

    #Initialize empty dicts, make subdirectories to store data
    for freq in range (len(f_vals)):
        time_axis[freq] = []
        S_axis[freq] = []
        T_vals[freq] = []
        f_array[freq] = []
        p_array[freq] = []

        os.makedirs(data_dir + '\\' + f"mode{freq}", exist_ok = True)

    #want to initialize the VNA now

    vna.write("INIT:CONT ON") #turn on internal triggering
    #BNC.write("OUTP OFF")
    vna.write(f"SENS:SWE:TYPE LIN")
    vna.write("SENS:AVER OFF")
    vna.write("SENSe1:FREQuency:SPAN " + str(span) + "mhz")
    print(span) 
    #vna.write("DISP:WIND:TRAC:Y:AUTO")
    if BW != -999: vna.write("SENS:BWID " + str(BW) + "HZ")
    vna.write("SENS:SWE:POIN " + str(n_points)) 
    vna.write(f"SENS:SWE:TIME {time}")
    vna.write("OUTP ON")
    if power != -100: vna.write(f"SOUR:POW {power}")

    try:
        time_stamp = str(datetime.now()).replace(":", "_")
        print("Started at " + time_stamp)
        t0 = datetime.now()
        time_started = t0

        while(((datetime.now()-t0).total_seconds()) <= wait_time):

            for index, f in enumerate(f_vals):
                vna.write("SENSe1:FREQuency:CENTer " + str(f) + "ghz")
                vna.write(f"SOUR:POW {power_array[index]}")

                #Set frequency and start collecting data
                vna.write("SENS:AVER ON")
                time.sleep(del_time)
                vs=get_smith_data(vna_addr) 
                outarray = wisform(vs)

                time_axis[index].append((datetime.now() - time_started).total_seconds())
                f_array[index] = (outarray[0]/1E9)
                S_axis[index].append(outarray[1])
                arduino.write(b'SYSTem:PRESsure:GETMbar?\n') #Reading pressure
                response = arduino.readline().decode('utf-8').strip()
                p_array[index].append(int(response)) #storing pressure
                T_vals[index].append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
                time.sleep(1)
                vna.write("SENS:AVER OFF")

                #to ensure no overloading between measurements of the different modes
                time.sleep(delay_time)
  
        #After all 9 modes are measured for a particular current/temperature value, we want to save this data in the respective folder of each directory

            for i in range(len(f_vals)):
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_time_" + name + ".csv", np.array(time_axis[i]), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_S21_" + name + ".csv", np.array(np.transpose(S_axis[i])), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_frequency_" + name + ".csv", np.array(f_array[i]), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_temperature_" + name + ".csv", np.array(T_vals[i]), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_pressure_" + name + ".csv", np.array(p_array[i]), fmt = '%d')

                #buffer to allow file saving without hassle
                time.sleep(1)

        #We now plot each deposition as a 3x3 grid, Ideally, I want it to align with the placement of each resonator on the chip

        fig, axes = plt.subplots(3,3, figsize = (13, 13))

        layout = [
            [6, 7, 8],
            [5, 4, 3],
            [0, 1, 2]
        ]

        for i in range(3):
            for j in range(3):
                to_plot = layout[i][j]
                pcm = axes[i, j].pcolor(np.array(time_axis[to_plot]), np.array(f_array[to_plot]), np.array(np.transpose(S_axis[to_plot])))
                axes[i, j].set_xlabel("time (s)")
                axes[i, j].set_ylabel("Frequency (GHz)")
                fig.colorbar(pcm, ax=axes[i,j], label = "S$_{21}$")


        fig.suptitle("Real time multires deposition monitor")
        plt.tight_layout()
        plt.show()

    finally:
        vna.close()
        arduino.close()



def multires_singlefocus(vna_addr, hp34461a_addr, bkpower_addr, arduino_addr, lo_addr, focus_mode, focus_mode_power, data_dir, current_array = [], chan = 2, baud = 9600, buffer = 2, wait_time = 60, delay_time = 60*10, del_time = 10, f_vals = [-999], BW = -999, span = 100, power = -20, n_points = 201, name = ""):
    
    
    #Identical to multires scan, used when we have an additional LO source input to the sample for targeted microwave heating of a specific resonator
    vna = rm.open_resource(vna_addr)

    arduino = serial.Serial(arduino_addr, baud, timeout=2)  
    

    # Wait for Arduino to initialize
    time.sleep(2)

    #INitialize heater
    set_voltage(bkpower_addr, chan, 30.0)
    #channel_output_toggle(bkpower_addr, chan, 'ON')
    time.sleep(1)

    #Initialize the external lo    
    lo_set_frequency(lo_addr, focus_mode)

    lo_set_power(lo_addr, focus_mode_power)

    lo_on_or_off(lo_addr, "On")


    #Will store data of each resonator as a dictionary entry - list for each entry 
    time_axis = {}
    S_axis = {}
    T_vals = {}
    f_array = {}
    p_array = {}

    #Initialize empty dicts, make subdirectories to store data
    for freq in range (len(f_vals)):
        time_axis[freq] = []
        S_axis[freq] = []
        T_vals[freq] = []
        f_array[freq] = []
        p_array[freq] = []

        os.makedirs(data_dir + '\\' + f"mode{freq}", exist_ok = True)

    #want to initialize the VNA now

    vna.write("INIT:CONT ON") #turn on internal triggering
    #BNC.write("OUTP OFF")
    vna.write(f"SENS:SWE:TYPE LIN")
    vna.write("SENS:AVER OFF")
    vna.write("SENSe1:FREQuency:SPAN " + str(span) + "mhz")
    print(span) 
    #vna.write("DISP:WIND:TRAC:Y:AUTO")
    if BW != -999: vna.write("SENS:BWID " + str(BW) + "HZ")
    vna.write("SENS:SWE:POIN " + str(n_points)) 
    vna.write(f"SENS:SWE:TIME {time}")
    vna.write("OUTP ON")
    if power != -100: vna.write(f"SOUR:POW {power}")

    try:
        time_stamp = str(datetime.now()).replace(":", "_")
        print("Started at " + time_stamp)
        t0 = datetime.now()
        time_started = t0

        for curr in current_array:

            t0 = datetime.now()
            while((datetime.now()-t0).total_seconds() <= wait_time):

                for index, f in enumerate(f_vals):
                    vna.write("SENSe1:FREQuency:CENTer " + str(f) + "ghz")

                    #Set frequency and start collecting data
                    vna.write("SENS:AVER ON")
                    time.sleep(del_time)
                    vs=get_smith_data(vna_addr) 
                    outarray = wisform(vs)

                    if f == focus_mode:
                        f_focus = outarray[0][np.argmin(outarray[1])]

                        lo_set_frequency(lo_addr, f_focus)
                        time.sleep(0.5)
                        #take data again after setting the lo to the resonator frequency for this specific mode
                        vna.write("SENS:AVER ON")
                        time.sleep(del_time)
                        vs = get_smith_data(vna_addr)
                        outarray = wisform(vs)

                    time_axis[index].append((datetime.now() - time_started).total_seconds())
                    f_array[index] = (outarray[0]/1E9)
                    S_axis[index].append(outarray[1])
                    arduino.write(b'SYSTem:PRESsure:GETMbar?\n') #Reading pressure
                    response = arduino.readline().decode('utf-8').strip()
                    p_array[index].append(int(response)) #storing pressure
                    T_vals[index].append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
                    time.sleep(1)
                    vna.write("SENS:AVER OFF")

                    #to ensure no overloading between measurements of the different modes
                    time.sleep(delay_time)

            set_current(bkpower_addr, chan, curr)    
        #After all 9 modes are measured for a particular current/temperature value, we want to save this data in the respective folder of each directory

            for i in range(len(f_vals)):
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_time_" + name + ".csv", np.array(time_axis[i]), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_S21_" + name + ".csv", np.array(np.transpose(S_axis[i])), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_frequency_" + name + ".csv", np.array(f_array[i]), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_temperature_" + name + ".csv", np.array(T_vals[i]), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_pressure_" + name + ".csv", np.array(p_array[i]), fmt = '%d')

                #buffer to allow file saving without hassle
                time.sleep(1)
        #Once this is all done, we now want to collect data during the buffer period as well, allow the resonator to fully settle at the 
        #desired temperature

        t_buffer = datetime.now()
        while(((datetime.now() - t_buffer).total_seconds()) <= buffer):

            for index,f in enumerate(f_vals):
                vna.write("SENSe1:FREQuency:CENTer " + str(f) + "ghz")

                #Set frequency and start collecting data
                vna.write("SENS:AVER ON")
                time.sleep(del_time)
                vs=get_smith_data(vna_addr) 
                outarray = wisform(vs)

                time_axis[index].append((datetime.now() - time_started).total_seconds())
                f_array[index] = (outarray[0]/1E9)
                S_axis[index].append(outarray[1])
                arduino.write(b'SYSTem:PRESsure:GETMbar?\n') #Reading pressure
                response = arduino.readline().decode('utf-8').strip()
                p_array[index].append(int(response)) #storing pressure
                T_vals[index].append(R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr))))
                vna.write("SENS:AVER OFF")

                #to ensure no overloading between measurements of the different modes
                time.sleep(delay_time)

            for i in range(len(f_vals)):
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_time_" + name + ".csv", np.array(time_axis[i]), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_S21_" + name + ".csv", np.array(np.transpose(S_axis[i])), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_frequency_" + name + ".csv", np.array(f_array[i]), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_temperature_" + name + ".csv", np.array(T_vals[i]), fmt = '%g')
                np.savetxt(data_dir + '\\' + f"mode{i}" + '\\' + time_stamp + "_pressure_" + name + ".csv", np.array(p_array[i]), fmt = '%d')

                #wait to allow file saving without hassle
                time.sleep(1)



        #We now plot each deposition as a 3x3 grid, Ideally, I want it to align with the placement of each resonator on the chip

        fig, axes = plt.subplots(3,3, figsize = (13, 13))

        layout = [
            [6, 7, 8],
            [5, 4, 3],
            [0, 1, 2]
        ]

        for i in range(3):
            for j in range(3):
                to_plot = layout[i][j]
                pcm = axes[i, j].pcolor(np.array(time_axis[to_plot]), np.array(f_array[to_plot]), np.array(np.transpose(S_axis[to_plot])))
                axes[i, j].set_xlabel("time (s)")
                axes[i, j].set_ylabel("Frequency (GHz)")
                axes[i, j].set_title(f"Mode {to_plot}")
                fig.colorbar(pcm, ax=axes[i,j], label = "S$_{21}$")


        fig.suptitle("Real time multires deposition monitor")
        plt.tight_layout()
        plt.show()
        
    finally:
        vna.close()
        arduino.close()