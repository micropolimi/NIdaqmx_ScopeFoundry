import nidaqmx
import numpy as np

from nidaqmx import stream_writers

class NI_DO_device(object):
    
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
        # self.task.ao_channels.add_ao_voltage_chan(physical_channel=self.channel,
        #                                          min_val=-10.0, max_val=10.0) 
        self.task.do_channels.add_do_chan(lines=self.channel)
        
    
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
        if self.verbose: print(f'DO task recreated, now operating in {mode} mode')
        
    def reset_task_on_channel_change(self, channel):
        self.close()
        self.channel = channel
        self.create_task()
        if self.verbose: print(f'DO task recreated, now operating in line {channel}')
        
    def write_single_value(self, val): 
        self.stop_task()
        self.task.write(bool(val), auto_start = True)
        if self.verbose: print(f'DO port set to {bool(val)}' )
       
    def write_waveform( self, 
                        source = '/Dev1/ao/SampleClock',
                        sample_mode_key = 'continuous'):
                       
        
        if not hasattr(self, 'task'):
            raise(AttributeError('DO task not active, unable to write'))
            
        if not hasattr(self, 'samples'):
            raise(AttributeError('Samples not generated, unable to write'))      
  
        sample_mode = self.sample_modes[sample_mode_key]
        
        samples = self.samples
        num_samples = len(samples) # self.num_periods * int(self.rate/self.frequency)
        rate = self.rate
        
        try:
            self.stop_task()
            self.task.timing.cfg_samp_clk_timing(rate = rate, 
                                                 source = source,
                                                 sample_mode = sample_mode, 
                                                 samps_per_chan = num_samples)
            writer = stream_writers.DigitalSingleChannelWriter(self.task.out_stream, auto_start = False)
            written_num = writer.write_many_sample_port_byte(samples.astype('uint8'))
            if self.verbose: print(f'successfully written {written_num} samples' )
            
        except Exception as err: 
            print (err)
        
    def generate_signal(self,  
                        waveform_type = 'rect',
                        frequency = 50,
                        num_periods = 6,
                        samples_per_period = 100,
                        ):
        
        rate = frequency * samples_per_period 
        # if rate >= 250000:
        #    raise(ValueError('Frequency too high, unable to set DO'))
        self.rate = rate
        
        T = 1/frequency # Hz 
        dt = 1/rate
        
        Ncycles = num_periods
        epsilon = 1e-9 # 1ns delay to avoid approximation error in rect and step function
        t = np.arange(0, Ncycles*T, dt) + epsilon

        if waveform_type == "rect": 
            width = 0.5
            samples =  ( (t) % T < (width*T) ).astype('bool')
        
        elif waveform_type == "step": 
            Nsteps = 3 # number of steps is set to 3 here
            #deltaAmp = amplitude # the voltage increase in each step is deltaAmp
            samples =   ( (t//T) % Nsteps ).astype('bool')
        else:
            raise(ValueError('Waveform not specified'))
            
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
       
    dev = NI_DO_device('Dev2/port0/line0')
    
    try:
        dev.create_task()
        #dev.set_trigger(False, '/Dev1/PFI12','rising')
        dev.generate_signal(waveform_type = 'rect',
                            num_periods = 3, 
                            frequency = 200,
                            samples_per_period = 100)
        
        dev.write_waveform(source = '/Dev1/ao/SampleClock', 
                           sample_mode_key = 'continuous')
        
        # dev.write_single_value(0.)
        if hasattr(dev, 'samples'):
             dev.start_task()
             
             plt.figure() 
             plt.plot(dev.samples)
        time.sleep(1.1)    
        dev.stop_task()
    finally:
        dev.close()
       
        