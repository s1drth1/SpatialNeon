import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import sys, os
import time

sys.path.append("..")



def Lorentzian(x, x0, a, c, g):
    return a/(g*(1 + (x - x0)**2/g**2)) + c


def internalQLorentzian(x, x0, Qi, Ql, c):
    return ((4*Qi*9000)/(Qi+9000)**2)*(1/(1 + 4*Ql**2*((x-x0)/x0)**2)) + c


def poly3(x, a, b, c, d):
    return a + b*x + c*x**2 + d*x**3


def single_scan_analysis (f, S, L, time_stamp, forplot = True):
    param, cov = curve_fit(Lorentzian, f, L, 
                           p0 = [np.average(f), 1, 0, 0.2*(np.max(f) - np.min(f))],
                           maxfev = 100000, bounds = ((np.average(f) - 0.5, 0, -np.inf, 0), (np.average(f) + 0.5, 1.5, np.inf, 2 * (np.max(f) - np.min(f)))))


    fit = Lorentzian(f, param[0], param[1], param[2], param[3])
    S_fit = np.log10(fit) * 10 + np.max(S)

    Q = param[0]/param[3]/2
    lgd = ["Data"]

    
    if forplot:
        plt.plot(f, S)
        plt.locator_params(axis='x', nbins=4) 
        plt.xlabel("Frequency (GHz)")
        plt.ylabel("S$_2$$_1$ (dB)")
        plt.title(time_stamp)

        plt.plot(f, S_fit)
        lgd.append("f = " + str(round(param[0], 6)) + " GHz\nQ = " + str(round(Q)) + "\nMax at " +str(f[np.argmax(S)]) + " GHz")
        plt.legend(lgd)


        plt.show()

    print(str(param[0]))
    
    print("Q is: " + str(Q))


    return param[0], Q


def single_scan_analysis_silent (f, S, L, time_stamp, forplot = True):

    #Quiet analysis code
    param, cov = curve_fit(Lorentzian, f, L, 
                           p0 = [np.average(f), 1, 0, 0.2*(np.max(f) - np.min(f))],
                           maxfev = 100000, bounds = ((np.average(f) - 0.5, 0, -np.inf, 0), (np.average(f) + 0.5, 1.5, np.inf, 2 * (np.max(f) - np.min(f)))))
    

    fit = Lorentzian(f, param[0], param[1], param[2], param[3])
    S_fit = np.log10(fit) * 10 + np.max(S)

    Q = param[0]/param[3]/2
    lgd = ["Data"]

    
    if forplot:
        plt.plot(f, S)
        plt.locator_params(axis='x', nbins=4) 
        plt.xlabel("Frequency (GHz)")
        plt.ylabel("S$_2$$_1$ (dB)")
        plt.title(time_stamp)

        plt.plot(f, S_fit)
        lgd.append("f = " + str(round(param[0], 6)) + " GHz\nQ = " + str(round(Q)) + "\nMax at " +str(f[np.argmax(S)]) + " GHz")
        plt.legend(lgd)


        plt.show()

    #print(str(param[0]))
    
    #print("Q is: " + str(Q))


    return param[0], Q


def fq_load_plot(data_dir, forplot = True):

    #Loading the FQ vs T data from a saved file and plotting
    
    fitted_f0 = []

    fitted_Q = []

    T_data = []


    for file_name in (os.listdir(data_dir)):
        df = pd.read_csv(data_dir + "\\" + file_name)
        f_data = df.iloc[0, 1:].to_numpy()/1e9
        S_data = df.iloc[1, 1:].to_numpy()
        phase_data = df.iloc[2, 1:].to_numpy()
        L_data = 10**((S_data - np.max(S_data))/10)
        
        initial_split = (file_name.split('_')[-3])
        T_val = float(initial_split.split(' ')[0])

        fit_f0, fit_Q = single_scan_analysis(f_data, S_data, L_data, time_stamp = time.time(), forplot = False)

        fitted_f0.append(fit_f0)
        fitted_Q.append(fit_Q)
        T_data.append(T_val)

    if forplot:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize = (8, 8), sharex = True)
        ax1.scatter(T_data, fitted_f0)
        ax1.set_xlabel("Temperature (K)")
        ax1.set_ylabel('Frequency (GHz)')

        ax2.scatter(T_data, fitted_Q)
        ax2.set_xlabel("Temperature (K)")
        ax2.set_ylabel("Q")

        plt.tight_layout()

        plt.show()

    return fitted_f0, fitted_Q, T_data



def fq_fitting(T_data, fitted_f0, temp_range = [5, 35], num_points = 151, forplot = True):

    #fitting the F&Q vs T curve

    temp_freq_param, temp_freq_cov = curve_fit(poly3, T_data, fitted_f0)
    x_temp_freq = np.linspace(temp_range[0], temp_range[1], num_points)
    y_temp_freq = poly3(x_temp_freq, temp_freq_param[0], temp_freq_param[1], temp_freq_param[2], temp_freq_param[3])
    
    if forplot:
        plt.scatter(T_data, fitted_f0, color = 'red', label = "Measured Data")
        plt.plot(x_temp_freq, y_temp_freq, color = 'black', label = "Fitted Curve")

        plt.title("Frequency vs Temperature - Fitted")

        plt.xlabel('Temperature (K)')

        plt.ylabel('Resonant Frequency (GHz)')
        plt.legend()
        plt.show()

    return temp_freq_param, temp_freq_cov


def real_time_monitor_load_plot(data_dir, temp_bounds = [5, 15], forplot = True):
    
    for file in os.listdir(data_dir):
        read_val = (file.split('_')[-2])
        if read_val == "frequency":
            freq_df = pd.read_csv(data_dir + "\\" + file)
        elif read_val == "phaserad":
            phase_rad_df = pd.read_csv(data_dir + "\\" + file)
        elif read_val == "phase":
            phase_df = pd.read_csv(data_dir + "\\" + file)
        elif read_val == "S21":
            s21_df = pd.read_csv(data_dir + "\\" + file)
        elif read_val == "temperature":
            temp_df = pd.read_csv(data_dir + "\\" + file)
        elif read_val == "time":
            time_df = pd.read_csv(data_dir + "\\" + file)
    

    freq_array = freq_df.iloc[:,1].to_numpy()
    phase_array = phase_df.iloc[:, 1:].to_numpy()
    phase_rad_array = phase_rad_df.iloc[:, 1:].to_numpy()
    temp_array = temp_df.iloc[:, -1].to_numpy()
    s21_array = s21_df.iloc[:, 1:].to_numpy()
    time_array = time_df.iloc[:, 1].to_numpy()
    true_S_lin = 10**((s21_array - np.max(s21_array))/10)

    if forplot:
        fig, (ax1, ax2, ax3, ax4) = plt.subplots(1, 4)

        a1 = ax1.plot(time_array, temp_array, color = 'red')
        a2 = ax2.pcolor(time_array, freq_array, s21_array)
        a3 = ax3.pcolor(time_array, freq_array, true_S_lin)
        a4 = ax4.pcolor(time_array, freq_array, phase_rad_array)

        ax1.set_ylim(temp_bounds)
        ax1.set_ylabel("Temperature (K)")
        ax2.set_ylabel("Frequency (GHz)")
        ax1.set_xlabel("time (s)")
        ax2.set_xlabel("time (s)")
        ax3.set_xlabel("time (s)")
        ax4.set_xlabel("time (s)")
        fig.colorbar(a2, label = "S$_2$$_1$ (dB)")
        fig.colorbar(a3, label = "Linear transmission")
        fig.colorbar(a4, label = "Phase (rad)")

        fig.suptitle("Real time deposition monitor " + data_dir.split("\\")[-1])
        fig.set_size_inches([13, 2.6])
        fig.tight_layout()
        plt.show()

    return freq_array, phase_array, phase_rad_array, temp_array, s21_array, time_array, true_S_lin


