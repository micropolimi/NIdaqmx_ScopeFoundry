import nidaqmx
import warnings
import math
import numpy as np
import scipy.signal as sp

from nidaqmx import stream_writers

class NI_AO_device(object):
    
    def __init__(self, channel, mode, sample_mode, num_periods, rate, amplitude, waveform, frequency, offset, debug=False, dummy=False):
        
        self.dict={"continuous": nidaqmx.constants.AcquisitionType.CONTINUOUS,
                   "finite": nidaqmx.constants.AcquisitionType.FINITE}
        self.dummy = dummy
        self.debug = debug ,
        self.channel = channel
        self.mode = mode
        
        self.sample_mode=sample_mode
        self.num_periods=num_periods
        self.rate=rate
        
        self.amplitude = amplitude
        self.waveform = waveform
        self.frequency = frequency
        self.offset = offset
        
        if not self.dummy:            
            self.Task()
    
    def Task(self):
        if hasattr(self, 'task'):
            self.close()
            
        self.task = nidaqmx.Task()
        self.task.ao_channels.add_ao_voltage_chan(physical_channel=self.channel, min_val=-10.0, max_val=10.0) #add an analog output channel
        if self.mode =="ao_voltage":
            self.set_ampl(self.amplitude)        
        elif self.mode == "ao_waveform":
            self.num_samples=self.num_periods*int(self.rate/self.frequency)
            try:
                self.task.timing.cfg_samp_clk_timing(rate= self.rate, sample_mode=self.dict.get(self.sample_mode), samps_per_chan=self.num_samples)
                writer= stream_writers.AnalogSingleChannelWriter(self.task.out_stream, auto_start=False)
                array=np.linspace(start=0, stop=2*np.pi*self.num_periods, num=self.num_samples, endpoint=False)
                if self.waveform == "sine":
                    samples=self.amplitude*np.sin(array)+self.offset
                elif self.waveform == "triangle":
                    samples=self.amplitude*sp.sawtooth(array, width=0.5)+self.offset
                elif self.waveform == "square":
                    samples=self.amplitude*sp.square(array)+self.offset
                writer.write_many_sample(samples)
            except Exception as e: 
                print(e)
                print ("ERROR: Use a rate of at least twice the frequency of the waveform!")
            
    def start_task(self):
        if self.task.is_task_done()==True:
            self.task.start()
        
    def stop_task(self):
        #suppress warning that might occurr when task i stopped during acquisition
        #warnings.filterwarnings('ignore', category=nidaqmx.DaqWarning)
        self.task.stop() #stop the task(different from the closing of the task, I suppose)
        #warnings.filterwarnings('default',category=nidaqmx.DaqWarning)
        
            
    def close(self):
        
        self.task.close() #close the task
        
    def write(self, data):
        
        self.task.write(data, auto_start = True)
        
        
    def set_mode(self, mode):
        
        self.mode = mode
        self.Task()

    def set_ampl(self, amplitude):
         
        self.amplitude = amplitude
        if self.mode == "ao_voltage":
            self.stop_task()
            self.write(amplitude)
        elif self.mode == "ao_waveform":
            self.stop_task()
            self.Task()
            
    def set_waveform(self, waveform):
         
        self.waveform = waveform
        if self.mode == "ao_waveform":
            self.stop_task()
            self.Task()
            
    def set_frequency(self, frequency):
         
        self.frequency = frequency
        if self.mode == "ao_waveform":
            self.stop_task()
            self.Task()
            
    def set_offset(self, offset):
         
        self.offset = offset
        if self.mode == "ao_waveform":
            self.stop_task()
            self.Task()
            
            
    def set_rate(self, rate):
        self.rate = rate
        if self.mode == "ao_waveform":
            self.stop_task()
            self.Task()
                
    def set_sample_mode(self,sample_mode):
        self.sample_mode=sample_mode
        if self.mode == "ao_waveform":
            self.stop_task()
            self.Task()
         
    def set_num_periods(self, num_periods):
        self.num_periods=num_periods
        if self.mode == "ao_waveform":
            self.stop_task()
            self.Task()
            
        
        
        
