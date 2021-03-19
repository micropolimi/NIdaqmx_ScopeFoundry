import nidaqmx
import numpy as np

from nidaqmx import stream_writers

class NI_AO_device(object):
    
    def __init__(self, channel, debug = False, dummy = False, verbose = True):
        
        self.dummy = dummy
        self.debug = debug
        self.verbose = verbose

        self.channel = channel
        self.sample_modes = {"continuous": nidaqmx.constants.AcquisitionType.CONTINUOUS,
                             "finite": nidaqmx.constants.AcquisitionType.FINITE,
                             "hw_timed": nidaqmx.constants.AcquisitionType.HW_TIMED_SINGLE_POINT
                             }
        self.trigger = False
        self.trigger_edge_modes = {"rising": nidaqmx.constants.Edge.RISING,
                                   "falling": nidaqmx.constants.Edge.FALLING
                                   }
        
        self.create_task()

    def create_task(self):
        '''creates a task and add an analog output channel'''            
        if hasattr(self, 'task'):
            self.close()
            
        self.task = nidaqmx.Task()
        self.task.ao_channels.add_ao_voltage_chan(physical_channel=self.channel,
                                                  min_val=-10.0, max_val=10.0) 
    
    def set_trigger(self, trigger = False, trigger_source = "/Dev1/PFI0", trigger_edge_key = 'rising'):
        
        self.trigger = trigger
        
        if not hasattr(self, 'task'):
            raise(AttributeError('AO task not active, unable to set trigger'))  
        self.stop_task()
        if trigger:
            self.task.triggers.start_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_EDGE
            self.task.triggers.start_trigger.cfg_dig_edge_start_trig(trigger_source = trigger_source,
                                                                     trigger_edge = self.trigger_edge_modes[trigger_edge_key])
        else:
            self.task.triggers.start_trigger.disable_start_trig()  
            
        if self.verbose: print(f'trigger set to {trigger} on {trigger_source}')
     
    def reset_task_on_mode_change(self, mode):
        self.close()
        self.create_task()
        if self.verbose: print(f'AO task recreated, now operating in {mode} mode')
        
    def reset_task_on_channel_change(self, channel):
        self.close()
        self.channel = channel
        self.create_task()
        if self.verbose: print(f'AO task recreated, now operating in channel {channel}')
        
    def write_constant_voltage(self, voltage): 
        self.stop_task()
        self.task.write(voltage, auto_start = True)
        if self.verbose: print(f'voltage set to {voltage}' )
       
    def write_waveform( self, sample_mode_key = 'continuous'):
        '''Write the samples on the DAQ AO board without starting the generation 
        '''
        if not hasattr(self, 'task'):
            raise(AttributeError('AO task not active, unable to write signal'))  
            
        if not hasattr(self, 'samples'):
            raise(AttributeError('Samples not generated, unable to write signal'))      
            
        sample_mode = self.sample_modes[sample_mode_key]
            
        samples = self.samples
        num_samples = len(samples) # self.num_periods * int(self.rate/self.frequency)
        rate = self.rate
        
        try:
            self.stop_task()
            self.task.timing.cfg_samp_clk_timing(rate = rate, 
                                                 sample_mode = sample_mode, 
                                                 samps_per_chan = num_samples)
            writer = stream_writers.AnalogSingleChannelWriter(self.task.out_stream, auto_start = False)
            written_num = writer.write_many_sample(samples)
            if self.verbose: print(f'successfully written {written_num} samples' )
            
        except Exception as err: 
            print (err)
        
    def generate_waveform(self, waveform_type = 'sine',
                            num_periods = 6, 
                            amplitude = 1,        
                            frequency = 50,
                            spike_amplitude = 0., spike_duration = 0., 
                            samples_per_period = 100,
                            steps = 3,
                            offset = 0):
        '''For waveform_type == step a function with steps of the specified amplitude in generated
        Is spike_amplitude > 0 a voltage spike is generated at the beginning of each period 
        '''
        rate = frequency * samples_per_period 
        if rate >= 250000:
            raise(ValueError('Frequency too high, unable to set NIDAQ analog output'))
         
        self.rate = rate
        dt = 1/rate
        T = 1/frequency # Hz
        
        epsilon = 1e-9 # 1ns delay to avoid approximation error in rect and step function
        t = np.arange(0, num_periods*T, dt) + epsilon

        if waveform_type == "sine":
            samples = amplitude * np.sin(2*np.pi*t/T)
        
        elif waveform_type == "rect": 
            width = 0.5
            samples =  amplitude * ( (t) % T < (width*T) ).astype('float')
        
        elif waveform_type == "step": 
            Nsteps = steps # number of steps is set to 3 here
            deltaAmp = amplitude # the voltage increase in each step is deltaAmp
            samples =  deltaAmp * ( (t//T) % Nsteps ).astype('float')
        else:
            raise(ValueError('Waveform not specified'))
            
        if spike_amplitude > 0:
            # spikeT = 0.0005 #s
            # spikeT = 0.05/freq # percentage of the step duration
            samples += spike_amplitude * ( (t%T) < spike_duration)
        
        samples += offset
        self.samples = samples
              
    def start_task(self):
        
        if not hasattr(self, 'task'):
            raise(AttributeError('Task not active, unable to start'))
        
        if self.task.is_task_done()==True:
            self.task.start()
        
    def stop_task(self):
        if not hasattr(self, 'task'):
            raise(AttributeError('Task not active, unable to stop'))
        # suppress warning that might occurr when task i stopped during acquisition
        # warnings.filterwarnings('ignore', category=nidaqmx.DaqWarning)
        self.task.stop() #stop the task(different from the closing of the task, I suppose)
        # warnings.filterwarnings('default',category=nidaqmx.DaqWarning)      
            
    def close(self):
        if not hasattr(self, 'task'):
            raise(AttributeError('Task not active, unable to close'))
        self.task.close()
        delattr(self, 'task')
        

if __name__ == '__main__':
    
    import time  
    from matplotlib import pyplot as plt
       
    dev = NI_AO_device('Dev2/ao0')
    
    try:
        dev.create_task()
        dev.set_trigger(False, '/Dev2/PFI0','rising')
        
        dev.generate_waveform(waveform_type = 'step',
                         num_periods = 6, 
                         amplitude = 1.,        
                         frequency = 100,
                         spike_amplitude = 1., spike_duration = 0.0005, 
                         samples_per_period = 100,
                         steps = 3,
                         offset = 0.)
        
        dev.write_waveform(sample_mode_key = 'finite') 
                         
        if hasattr(dev, 'samples'):
            dev.start_task()
            time.sleep(1.1)
            plt.figure() 
            plt.plot(dev.samples)
            
        dev.stop_task()
    finally:
        dev.close()
       
        