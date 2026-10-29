from scipy.optimize import brentq
from scipy.optimize import curve_fit
import numpy as np
from datetime import datetime
import time, sys, os, pyvisa, subprocess
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from matplotlib.collections import LineCollection
import time
from matplotlib.colors import LinearSegmentedColormap


#Extracting collected data for analysis and appropriate plotting

sys.path.append("..")

from Routines.vna_analysis import *


def vapor_pressure_equation(temp):
    return np.power(10, (3.75641 - 95.599/(temp-1.503)))




triple_point = 24.553

pressure_triple_point = vapor_pressure_equation(triple_point)

critical_point = 44.4

pressure_critical_point = vapor_pressure_equation(critical_point)

C0 = 185.85413


def calibration_polynomial(x, a, b, c, d):

    return a + b*x + c*x**2 + d*x**3

def poly5_zeroed(x, b, c, d, e, f):

    return b*x + c*x**2 + d*x**3 + e*x**4 + f*x**5



#This section configures the model files read from the csv

liq_first_thickness = pd.read_csv(r"C:\Users\crow104\Desktop\IceT_SD\SpatialNeon\Models\w20_g5_ceo210_liquid.csv").iloc[:, 1].to_numpy()
liq_second_thickness = pd.read_csv(r"C:\Users\crow104\Desktop\IceT_SD\SpatialNeon\Models\w20_g5_ceo210_20um_liquid.csv").iloc[:, 1].to_numpy()

liq_first_cap = pd.read_csv(r"C:\Users\crow104\Desktop\IceT_SD\SpatialNeon\Models\w20_g5_ceo210_liquid.csv").iloc[:, 2].to_numpy()
liq_second_cap = pd.read_csv(r"C:\Users\crow104\Desktop\IceT_SD\SpatialNeon\Models\w20_g5_ceo210_20um_liquid.csv").iloc[:, 2].to_numpy()

liq_thickness = np.concatenate(([0], liq_first_thickness, liq_second_thickness))

liq_cap = np.concatenate(([C0], liq_first_cap, liq_second_cap))

liq_freq = (np.sqrt(C0/liq_cap) - 1)*100

liq_param, liq_cov = curve_fit(poly5_zeroed, liq_freq, liq_thickness)
#Now solid components
sol_first_thickness = pd.read_csv(r"C:\Users\crow104\Desktop\IceT_SD\SpatialNeon\Models\w20_g5_ceo210.csv").iloc[:, 1].to_numpy()
sol_second_thickness = pd.read_csv(r"C:\Users\crow104\Desktop\IceT_SD\SpatialNeon\Models\w20_g5_ceo210_20um.csv").iloc[:, 1].to_numpy()

sol_first_cap = pd.read_csv(r"C:\Users\crow104\Desktop\IceT_SD\SpatialNeon\Models\w20_g5_ceo210.csv").iloc[:, 2].to_numpy()
sol_second_cap = pd.read_csv(r"C:\Users\crow104\Desktop\IceT_SD\SpatialNeon\Models\w20_g5_ceo210_20um.csv").iloc[:, 2].to_numpy()

sol_thickness = np.concatenate(([0], sol_first_thickness, sol_second_thickness))

sol_cap = np.concatenate(([C0], sol_first_cap, sol_second_cap))

sol_freq = (np.sqrt(C0/sol_cap) - 1) * 100

sol_param, sol_cov = curve_fit(poly5_zeroed, sol_freq, sol_thickness)


class measuredData:

    def __init__(self, filepath):

        self.filepath = filepath

        self.data_dict = {}

        for file in os.listdir(self.filepath):

            path = os.path.join(self.filepath, file)

            self.data_dict[file.split('_')[-2]] = pd.read_csv(path, delimiter = ' ').to_numpy()
        #Load data into a dictionary with multiple arrays
    def res_frequency_extraction(self, to_plot = False):

        f0_list = []

        for slice in self.data_dict["S21"].transpose():
            f0_list.append(self.data_dict["frequency"][np.argmin(slice)])

        self.f0_list = np.array(f0_list[:-1])
        
        #Find minima of each s21 slice and take that to be the resonant frequency
        if to_plot:

            fig, (ax1, ax2) = plt.subplots(1, 2, sharey= True)
            ax1.plot(self.data_dict["time"], self.f0_list, color= "black")
            ax1.set_xlabel("Time (s)")
            ax1.ylabel("Frequency (GHz)")

            ax2.plot(self.data_dict["temperature"], self.f0_list, color = 'red')
            ax2.set_xlabel("Temperature (K)")
            fig.suptitle("Real-time Frequency Tracking")

            plt.tight_layout()

            plt.show()

    def normalized_frequency_extraction(self, to_plot = False):
        base_frequency = calibration_polynomial(self.data_dict["temperature"], *self.calibration_parameters)


        normalized_freq_shift = ((self.f0_list - base_frequency)/base_frequency)*100


        if to_plot:
            fig, (ax1, ax2) = plt.subplots(1, 2, sharey= True)
            ax1.plot(self.data_dict["time"], normalized_freq_shift, color= "black")
            ax1.set_xlabel("Time (s)")
            ax1.ylabel("Normalized Shift")

            ax2.plot(self.data_dict["temperature"], normalized_freq_shift, color = 'red')
            ax2.set_xlabel("Temperature (K)")
            fig.suptitle("Real-time Frequency Tracking")

            plt.tight_layout()

            plt.show()

        self.normalized_frequencies = normalized_freq_shift


    def calculate_calibration_parameters(self, calibration_file, to_plot = True):

        fitted_f0 = []

        T_data = []

        self.calibration_file = calibration_file
        for file_name in (os.listdir(self.calibration_file)):
            df = pd.read_csv(self.calibration_file + "\\" + file_name)
            f_data = df.iloc[0, 1:].to_numpy()/1e9
            S_data = df.iloc[1, 1:].to_numpy()
            phase_data = df.iloc[2, 1:].to_numpy()
            L_data = 10**((S_data - np.max(S_data))/10)
            
            initial_split = (file_name.split('_')[-3])
            T_val = float(initial_split.split(' ')[0])

            f_min = f_data[np.argmin(S_data)]

            fitted_f0.append(f_min)

            T_data.append(T_val)

        temp_freq_param, temp_freq_cov = curve_fit(calibration_polynomial, T_data, fitted_f0)

        self.calibration_parameters = temp_freq_param
        
        if to_plot:
            x_fit = np.linspace(T_data[0], T_data[-1], 151)

            y_fit = calibration_polynomial(x_fit, *self.calibration_parameters)

            plt.scatter(T_data, fitted_f0, color = 'red', label = "Measured Data")
        
            plt.plot(x_fit, y_fit, color = 'black', label = "Fitted Curve")

            plt.title("Frequency vs Temperature - Fitted")

            plt.xlabel('Temperature (K)')

            plt.ylabel('Resonant Frequency (GHz)')
            plt.legend()
            plt.show()

    def map_to_thickness(self, to_plot = False, triple_temperature = 24.25):

        mask_solid = (self.data_dict["temperature"] < triple_temperature)

        mask_liquid = (self.data_dict["temperature"] >= triple_temperature)

        solid_thickness = poly5_zeroed(self.normalized_frequencies[mask_solid], *sol_param)

        liquid_thickness = poly5_zeroed(self.normalized_frequencies[mask_liquid], *liq_param)

        self.thickness = np.concatenate((liquid_thickness, solid_thickness))

        if to_plot:
            fig, (ax1, ax2) = plt.subplots(2, 1, sharex= True)

            temp_range = np.linspace(23.0, 29.0, 1001)
            vapor_pressure = vapor_pressure_equation(temp_range)

            ax1.set_ylim((0.1, 2))
            ax1.plot(temp_range, vapor_pressure, color = 'black')
            ax1.scatter(triple_point, pressure_triple_point, s = 50, color = 'red', label = 'Triple Point')
            ax1.plot([triple_point, triple_point], [pressure_triple_point, 2], color = 'black')
            ax1.set_yscale('log')

            ax1.scatter(self.data_dict["temperature"], self.data_dict["pressure"]/1000, color = 'green', s = 10)

            ax1.set_ylabel = "Pressure (Bar)"


            ax2.plot(self.data_dict["temperature"], self.thickness, color = 'green')
            ax2.set_ylabel("Thickness (um)")
            ax2.set_xlabel("Temperature (K)")

            fig.suptitle("Pressure, Thickness, Temperature Tracking")

            plt.tight_layout()

            plt.show()

    
    def triplepoint_ratefinder(self, triple_point = 24.53, rate_range = 1):

        closest_index = int(np.argmin(np.abs(self.data_dict["temperature"] - triple_point)))
        print("Closest index:", self.data_dict["temperature"][closest_index])

        rate = abs(
        (self.data_dict["temperature"][closest_index + rate_range] - self.data_dict["temperature"][closest_index - rate_range])
        / (self.data_dict["time"][closest_index + rate_range] - self.data_dict["time"][closest_index - rate_range])
    )

        rate *= 60

        self.rate = rate
        return rate
    
    



class measuredBeforeandAfter:

    def __init__(self, before_filepath, after_filepath, temperature, calibration_file):

        self.before_filepath = before_filepath

        self.after_filepath = after_filepath

        self.temperature = temperature

        self.calibration_file = calibration_file


        df_before = pd.read_csv(self.before_filepath)
        df_after = pd.read_csv(self.after_filepath)

        self.before_freq = df_before.iloc[0, 1:]/1E9
        self.before_real = df_before.iloc[1, 1:]
        self.before_imag = df_before.iloc[2, 1:]
        self.before_linmag = df_before.iloc[3, 1:]
        self.before_phase = df_before.iloc[4, 1:]

        self.after_freq = df_after.iloc[0, 1:]/1E9
        self.after_real = df_after.iloc[1, 1:]
        self.after_imag = df_after.iloc[2, 1:]
        self.after_linmag = df_after.iloc[3, 1:]
        self.after_phase = df_after.iloc[4, 1:]

    def calculate_calibration_parameters(self, forplot = True):

        fitted_f0 = []

        T_data = []

        for file_name in (os.listdir(self.calibration_file)):
            df = pd.read_csv(self.calibration_file + "\\" + file_name)
            f_data = df.iloc[0, 1:].to_numpy()/1e9
            S_data = df.iloc[1, 1:].to_numpy()
            phase_data = df.iloc[2, 1:].to_numpy()
            L_data = 10**((S_data - np.max(S_data))/10)
            
            initial_split = (file_name.split('_')[-3])
            T_val = float(initial_split.split(' ')[0])

            f_min = f_data[np.argmin(S_data)]

            fitted_f0.append(f_min)

            T_data.append(T_val)

        temp_freq_param, temp_freq_cov = curve_fit(calibration_polynomial, T_data, fitted_f0)

        self.calibration_parameters = temp_freq_param
        
        if forplot:
            x_fit = np.linspace(T_data[0], T_data[-1], 151)

            y_fit = calibration_polynomial(x_fit, *self.calibration_parameters)

            plt.scatter(T_data, fitted_f0, color = 'red', label = "Measured Data")
        
            plt.plot(x_fit, y_fit, color = 'black', label = "Fitted Curve")

            plt.title("Frequency vs Temperature - Fitted")

            plt.xlabel('Temperature (K)')

            plt.ylabel('Resonant Frequency (GHz)')
            plt.legend()
            plt.show()

    def res_frequency_normalized_extraction(self):

        base_frequency = calibration_polynomial(self.temperature, *self.calibration_parameters)

        self.before_normalized = (self.before_freq-base_frequency)/base_frequency

        self.after_normalized = (self.after_freq - base_frequency)/base_frequency

    
    def map_to_thickness(self, triple_point = 24.5):

        if self.temperature >= triple_point:

            self.thickness = poly5_zeroed(self.after_normalized, *liq_param)

        else:

            self.thickness = poly5_zeroed(self.after_normalized,*sol_param)
