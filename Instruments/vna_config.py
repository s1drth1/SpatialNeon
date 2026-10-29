# -*- coding: utf-8 -*-
"""
Created on Wed Feb 12 10:47:41 2020

@author: J. Monroe
@date: Feb 12, 2020

modified for cw capability
@author: sidharth
@date: Feb 12, 2025
"""
import numpy as np
import time

import pyvisa
rm = pyvisa.ResourceManager()

class Smith_data():
    
    def __init__(self, vna_smith_data, f_min=None, f_max=None, time_start = None, time_stop = None):
        self.real = np.array( vna_smith_data[0::2] )
        num_points = self.real.size
        self.imag = np.array( vna_smith_data[1::2] )
        self.lin_mag = np.sqrt(self.real**2 + self.imag**2)
        self.log_mag = 20*np.log10(self.lin_mag)
        # arctan2 chooses the quadrant based on the sign of each step
        self.wrapped_phase = np.arctan2(self.imag, self.real)
        

        if f_min and f_max:
            self.freqs = np.linspace(f_min, f_max, num_points)
        else:
            self.freqs = None

        
        ## unwrap the phase
        unwrapped = np.unwrap(self.wrapped_phase)
        # a quick linear fit to subtract off electrical delay. 
        # calculating physical ED requires frequency information. I'll instead
        #   keep this function robust.    
        xs = np.arange(num_points)
        # solve y = mx +b as  y = A.f where A is Nx2 with x as first  column and 
        # ones as second column f is 2x1 of coefficients m and b.
        # fit by minimizing (data-A.f)^2
        A_mat = np.array([xs, np.ones(xs.shape)]).T 
        m, b = np.linalg.lstsq(A_mat, unwrapped, rcond=None)[0]
        
        self.phase_rad = unwrapped - (m*xs + b)
        self.phase_deg = self.phase_rad/np.pi*180


        #setting frequencies/times if set for a CW vs regular
              
        
        
        if time_stop:
            self.times = np.linspace(time_start, time_stop, num_points)
        else:
            self.times = None
        
    ##END __init__
##END Smith_data
        

def get_smith_data(vna_address, restart_average=False, cw = False, meas = "S21"):
    '''
    DESCRIPTION: Talk to VNA instrument to extract smith data from either cw or linmag
    INPUT: active visa session handle for VNA
    OUTPUT: Smith_data object
    '''
    # note that "fdata" returns the same as sdata, but the even-index values are 
    #   whatever is displayed on screen and odd-index values are 0
    
    vna_handle = rm.open_resource(vna_address)
    try:
        if restart_average:
            # start averaging by toggling the "Avg Trigger" setting. Upon next trigger
            # (assume internal), the average will restart
            vna_handle.write("sens:aver 0"); 
            vna_handle.write("sens:AVER 1")
            ##TODO: WAIT FOR COLLECtion to end?
            num_avgs = float(vna_handle.query("sens1:aver:coun?") )
            sweep_time = float(vna_handle.query("sense1:swe:time?") )
            delay_time = sweep_time*num_avgs
            print("VNA waiting {:.2f} seconds".format(delay_time)) 
            time.sleep(delay_time)
            
        ## a quick hack to allow data to come off
        vna_handle.write(f":calc1:par:def \"FOO\", {meas}")
        vna_handle.write(":calc1:par:sel \"FOO\"")
        vna_handle.write(f":calc1:par:mod {meas}")
        vna_handle.write(":FORM:DATA ascii")    
        
        ## offload data
        string_data = vna_handle.query('calc1:data? sdata')
        numerical_data = np.array(string_data.split(','), dtype='float')
    
        ## get frequency range
        
        
        ## parse data
        if cw:
            t_start = float(0)
            t_stop = float(vna_handle.query("SENSe1:SWEep:TIME?"))
            smith_data = Smith_data(numerical_data, time_start=t_start, time_stop = t_stop)
        else:
            f_start = float( vna_handle.query('SENS1:FREQ:start?') )
            f_stop = float( vna_handle.query('SENS1:FREQ:stop?') )
            smith_data = Smith_data(numerical_data, f_min=f_start, f_max=f_stop)
        return smith_data
    finally:
        vna_handle.close()
##END get_smith_data


#exclusive CW sweep preperation
def prepare_for_cw_spec(vna_freq_GHz, vna_power_dBm, bw_hz = 10, num_points=201, vna_gpib='GPIB0::16::INSTR', aver = 1, trigger = 'single'):

   
    try:
        vna_handle = rm.open_resource(vna_gpib)
        
#        # save VNA settings to be reloaded after sweep
#        vna_handle.write(':MMEM:STOR "recent_state.sta"')
    
        # setup source to single frequency
        vna_handle.write(f":SOUR:POW {vna_power_dBm}")
        vna_handle.write(f"SENSE:SWE:TYPE CW")
        #ideally collect cw frequency from an earlier lin/logmag sweep
        vna_handle.write(f":SENSE:FREQ:CW {vna_freq_GHz*1E9}")
        
        # configure sweep        
        vna_handle.write(f":SENSE:BAND {bw_hz}")
        vna_handle.write(":SENS:SWE:GEN ANAL")
        vna_handle.write(f":SENS:SWE:TIME MIN")
        vna_handle.write(f":SENS:SWE:POIN {num_points}")
        vna_handle.write(f":SENS:AVER ON;  AVER:COUN {aver}")
        sweep_time = vna_handle.query(":SENS:SWE:TIME?")
        point_number = vna_handle.query(":SENS:SWE:POIN?")

        #vna_handle.write("INIT:CONT ON")

        #Triggering switched to manual (single)
        if trigger == 'single':    
            vna_handle.write("INIT:CONT OFF")
            
            vna_handle.write("TRIG:SEQ:SOUR MAN")
            time.sleep(1)
            vna_handle.write("INIT:IMM")

        else:
            vna_handle.write("TRIG:SEQ:SOUR IMM")
            time.sleep(1)
            vna_handle.write("INIT:CONT ON")

        

        #returns sweep time and dwell sec to delay over before collecting the data from the CW sweep
        return sweep_time, point_number
        
        #In future - write for a trigger source
    finally:
        vna_handle.close()



def marker_find_max(vna_gpib = 'GPIB0::16::INSTR', format = "MLOG"):
    
    try:
        vna_handle = rm.open_resource(vna_gpib)

        #Finds maximum on sweep with marker
        vna_handle.write("CALC1:MARK ON")
        vna_handle.write(f"CALC1:MARK:FORMAT {format}")
        vna_handle.write("CALC1:MARK:TYPE NORM")
        vna_handle.write("CALC1:MARK:FUNC:EXEC MAX")
        
        # returns x & y data to store  
        marker_x = float(vna_handle.query("CALC1:MARK:X?"))
        marker_y = float(vna_handle.query("CALC1:MARK:Y?"))

        #turn marker off
        vna_handle.write("CALC:MARK:AOFF")
        
        return marker_x, marker_y     
        

    finally:
        
        vna_handle.close()

def configure_display(vna_gpib = 'GPIB0::16::INSTR', format = "MLOG", scale = "AUTO"):
    #autoscales by default

    try:
        vna_handle = rm.open_resource(vna_gpib)

        vna_handle.write(f"CALCulate1:FORM {format}")

        vna_handle.write("Display:WINDow1:TRACe1:STATe ON")

        vna_handle.write(f"Display:WINDow1:TRACe1:Y:Scale:{scale}")

    
    finally:
        vna_handle.close()

def configure_settings(vna_addr, type = "LIN",f = -999, BW = -999, span = 10, power = -100, n_points = 201, aver = 60000, time = "MIN"):

    #configure vna settings  
    
    vna = rm.open_resource(vna_addr)

    try:
        vna.write("INIT:CONT ON") #turn on internal triggering
        #BNC.write("OUTP OFF")
        vna.write(f"SENS:SWE:TYPE {type}")
        vna.write(f"SENS:AVER:COUN {aver}")
        vna.write("SENS:AVER OFF")
        if f != -999: vna.write("SENSe1:FREQuency:CENTer " + str(f) + "ghz")
        print(f)
        vna.write("SENSe1:FREQuency:SPAN " + str(span) + "mhz")
        print(span) 
        #vna.write("DISP:WIND:TRAC:Y:AUTO")
        if BW != -999: vna.write("SENS:BWID " + str(BW) + "HZ")
        vna.write("SENS:SWE:POIN " + str(n_points)) 
        vna.write(f"SENS:SWE:TIME {time}")
        vna.write("OUTP ON")
        if power != -100: vna.write(f"SOUR:POW {power}")

    finally:
        vna.close()



#def set_edelay(vna_gpib = 'GPIB0::16::INSTR', edelay = 21):
    
    
    
