from scipy.optimize import brentq
import numpy as np
import sys
import time
import pandas as pd
from datetime import datetime
from Instruments.hp34461A import *
import matplotlib.pyplot as plt

sys.path.append("..")

def R2T_900(R):  # from 6K to 96K
    a0, a1, a2, a3, a4, a5, a6, a7, a8 = 6.75543700e+03, -1.59063022e+04, 1.92990842e+04, -1.30574569e+04, 5.39085191e+03, -1.39623593e+03, 2.22191016e+02, -1.99044732e+01, 7.69758689e-01
    
    if np.isscalar(R):
        R = np.array([R])

    if np.any(R < 946.97) or np.any(R > 1135.68):
        print('out of range: results may not be accurate')

    def f(T, R):
        log_T = np.log(T)
        return (a0 + a1 * log_T + a2 * log_T**2 + a3 * log_T**3 +
                a4 * log_T**4 + a5 * log_T**5 + a6 * log_T**6 +
                a7 * log_T**7 + a8 * log_T**8) - R

    def find_temp(R):
        try:
            return brentq(f, 0, 97, args=(R,))
        except ValueError:
            raise ValueError('root finding did not converge within the temperature range 6K to 96K')

    temperatures = np.array([find_temp(R_input) for R_input in R])
    
    if temperatures.size == 1:
        return temperatures[0]
    else:
        return temperatures
    

def R2T_900_silent(R):  # from 6K to 96K
    a0, a1, a2, a3, a4, a5, a6, a7, a8 = 6.75543700e+03, -1.59063022e+04, 1.92990842e+04, -1.30574569e+04, 5.39085191e+03, -1.39623593e+03, 2.22191016e+02, -1.99044732e+01, 7.69758689e-01
    
    if np.isscalar(R):
        R = np.array([R])

    def f(T, R):
        log_T = np.log(T)
        return (a0 + a1 * log_T + a2 * log_T**2 + a3 * log_T**3 +
                a4 * log_T**4 + a5 * log_T**5 + a6 * log_T**6 +
                a7 * log_T**7 + a8 * log_T**8) - R

    def find_temp(R):
        try:
            return brentq(f, 0, 97, args=(R,))
        except ValueError:
            raise ValueError('root finding did not converge within the temperature range 6K to 96K')

    temperatures = np.array([find_temp(R_input) for R_input in R])
    
    if temperatures.size == 1:
        return temperatures[0]
    else:
        return temperatures
    


def wait_for_stable_resistance(timeout=180, check_interval=1,machineGPIB='GPIB0::22::INSTR', delta = 0.005):
    """
    Wait until the Temperature value remains unchanged over a small delta for the specified timeout.
    
    :param timeout: The time in seconds for which the resistance value must remain unchanged.
    :param check_interval: The interval in seconds at which to check the resistance value.
    """
    start_time = time.time()
    initial_value = R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(machineGPIB)))
    
    while True:
        time.sleep(check_interval)
        current_value = R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(machineGPIB)))
        
        if np.abs(current_value - initial_value) > delta:
            start_time = time.time()
            initial_value = current_value
        
        elapsed_time = time.time() - start_time
        
        if elapsed_time >= timeout:
            print('success!')
            break


def wait_for_stable_resistance_data(data_dir, timeout=180, check_interval=1, machineGPIB='GPIB0::22::INSTR', delta = 0.005, forplot = True):
    """
    Wait until the Temperature value remains unchanged over a small delta for the specified timeout.
    
    :param timeout: The time in seconds for which the resistance value must remain unchanged.
    :param check_interval: The interval in seconds at which to check the resistance value.
    """
    time_array = []

    temp_array = []
    
    time_stamp = str(datetime.now()).replace(":", "_")
    first_time = time.time()
    start_time = first_time
    initial_value = R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(machineGPIB)))
    
    while True:
        time.sleep(check_interval)
        current_value = R2T_900_silent(np.abs(hp34461a_get_ohm_4pt(machineGPIB)))

        time_array.append(time.time() - first_time)
        temp_array.append(current_value)
        
        if np.abs(current_value - initial_value) > delta:
            start_time = time.time()
            initial_value = current_value
        
        elapsed_time = time.time() - start_time
        
        if elapsed_time >= timeout:
            print('success!')
            break

    
    save_time = pd.DataFrame(time_array)
    save_temp = pd.DataFrame(temp_array)

    save_time.to_csv(data_dir + "\\" + time_stamp + "_time_.csv")
    save_temp.to_csv(data_dir + "\\" + time_stamp + "_temperature_.csv")


    if forplot:
        plt.plot(time_array, temp_array, linewidth = 0.5, color = "red")

        plt.xlabel('Time (s)')
        plt.ylabel('Temperature (K)')

        plt.title('Time vs Temperature')
        plt.show()









    
