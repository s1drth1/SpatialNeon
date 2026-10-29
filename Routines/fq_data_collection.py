from scipy.optimize import brentq
import numpy as np
from datetime import datetime
import time, sys, os, pyvisa, subprocess
import matplotlib as mpl
import matplotlib.pyplot as plt
import time
from resonator_tools import circuit

sys.path.append("..")


from Instruments.hp34461A import *
from Instruments.vna_config import *
from Instruments.power_supply import *
from Routines.res_to_temp import *
from Routines.retrieve_vna_data import *
from Routines.vna_analysis import *






def realTime_fq_mon(data_save, vna_addr = 'GPIB0::16::INSTR', keithley_addr = 'USB0::0x2EC7::0x9130::800885011797670040::INSTR', 
                    hp34461a_addr = 'GPIB0::22::INSTR', stop_temp = 33, curr_step = 0.025, chan = 2, f_search = 7.014, focus_span = 40, silent = False):
    
    #Increments current through heater , waits for the temperature to stabilize, then records and fits VNA data for f0 & Q. Continues until
    #stop temperature

    f0 = []
    Q = []
    T = []
    time_arr = []
    #Retrieve temperature
    T_val = R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr)))


    #Initial settings for the power supply, which drives the heater
    set_voltage(keithley_addr, chan, 30.0)
    set_current(keithley_addr, chan, 0.0)
    current_step(keithley_addr, chan, curr_step)
    time.sleep(5)
    output_toggle(keithley_addr, "ON")



    while (T_val >= 4 and T_val <= stop_temp):
 
        #waits for a stable temperature
        wait_for_stable_resistance(delta = 0.0075)

        T_val = R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr)))
        print(f"done, T = {T_val}")

        #Initial scan to pick out peak

        freq_initial, s_data_initial, L_data_initial, times = SingleScan_VNA(vna_addr, f = f_search, span = 100, del_time = 60, n_points = 201, BW = 1E3, power = -10.00, name = f'{round(T_val, 2)} K_first_scan', forplot = False, to_save = False, data_dir = data_save)
        
        #Second scan centered around peak on a smaller span
        freqs, s_data, L_data, times = SingleScan_VNA(vna_addr, f = freq_initial[np.argmax(s_data_initial)], span = focus_span, del_time = 60, n_points = 201, BW = 1E3, power = -10.00, name = f'{round(T_val, 2)} K_second_scan, 0dBm', forplot = False, to_save = True, data_dir = data_save)

        #data is analyzed
        fit_f, fit_q = single_scan_analysis (freqs, s_data, L_data, times, forplot = False if silent else True)

        f0.append(fit_f)
        Q.append(fit_q)
        T.append(T_val)
        time_arr.append(times)


        f_search = fit_f

        #increment the current by the step that you have set.
        current_increment(keithley_addr, chan, "UP")

    output_toggle(keithley_addr, "OFF")

    time.sleep(2)

    #plot for f0, Q

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize = (8, 8), sharex = True)
    ax1.scatter(T, f0)
    ax1.set_xlabel("Temperature (K)")
    ax1.set_ylabel('Frequency (GHz)')


    ax2.scatter(T, Q, color = 'g')
    ax2.set_xlabel("Temperature (K)")
    ax2.set_ylabel("Q")

    plt.tight_layout()

    plt.show()
    return f0, Q, T



def multiRes_fq_characterization(data_save, vna_addr = 'GPIB0::16::INSTR', keithley_addr = 'USB0::0x2EC7::0x9130::800885011797670040::INSTR', modenumber = 9,
                    hp34461a_addr = 'GPIB0::22::INSTR', stop_temp = 33, curr_step = 0.025, chan = 2, focus_span = 20, initial_scan = [3.7, 3.9, 4.3, 4.4, 4.6, 4.9, 5.2, 5.4, 5.6], silent = False, num_points = 201, power = -10, current = 0.0, reset = True):
    


    #Initialization of dictionaries to store data
    f_dict = {}
    temp_array = []
    time_array = []
    for mode in range(modenumber):

        f_dict[mode] = []

        os.makedirs(data_save + '\\' + f"mode{mode}" ,exist_ok = True)

    T_val = R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr)))


    #Initial settings for the power supply, which drives the heater
    set_voltage(keithley_addr, chan, 30.0)
    set_current(keithley_addr, chan, current)
    current_step(keithley_addr, chan, curr_step)
    time.sleep(5)
    output_toggle(keithley_addr, "ON")

    while (T_val >= 4 and T_val <= stop_temp):
        wait_for_stable_resistance(delta = 0.0075)

        T_val = R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(hp34461a_addr)))
        print(f"done, T = {T_val}")


        for key in f_dict.keys():

            path = data_save + '\\' + f"mode{key}"

            #Initial scan to pick out peak

            freq_initial, s_data_initial, L_data_initial, times = SingleScan_VNA(vna_addr, f = initial_scan[key], span = 80, del_time = 30, n_points = 201, BW = 1E3, power = -10.00, name = f'{round(T_val, 2)} K_first_scan', forplot = False, to_save = False, data_dir = path)
        
            #Second scan centered around peak on a smaller span
            freqs, s_data, L_data, times = SingleScan_VNA(vna_addr, f = freq_initial[np.argmin(s_data_initial)], span = focus_span, del_time = 30, n_points = num_points, BW = 1E3, power = power, name = f'{round(T_val, 2)} K_second_scan, 0dBm', forplot = True, to_save = True, data_dir = path)
 
            #append data

            new_f = freqs[np.argmin(s_data)]

            f_dict[key].append(new_f)


            initial_scan[key] = new_f
        
        temp_array.append(T_val)
        time_array.append(times)

        current_increment(keithley_addr, chan, "UP")


    if reset:
        output_toggle(keithley_addr, "OFF")

    time.sleep(2)

    #plot for f0, Q

    outarray = np.vstack([temp_array, time_array, list(f_dict.values())])

    df = pd.DataFrame(outarray)

    #df.to_csv(data_save)

    time.sleep(2)

    for key,value in f_dict.items():

        plt.scatter(temp_array, value, label = f"mode{key}")

    plt.xlabel("Temperature (K)")

    plt.ylabel("Res Frequency (GHz)")

    plt.show()



