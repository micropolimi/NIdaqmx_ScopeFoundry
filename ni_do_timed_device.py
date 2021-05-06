import nidaqmx
import numpy as np

from nidaqmx import stream_writers

class NI_DO_device(object):
    
    def __init__(self, port, debug = False, dummy = False, verbose = True):
        
        self.dummy = dummy
        self.debug = debug
        self.verbose = verbose

        self.port = port
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
        '''creates a task and add an digital output port'''            
        if hasattr(self, 'task'):
            self.close_task()
            
        self.task = nidaqmx.Task()
        self.task.do_channels.add_do_chan(lines=self.port)
        
    
    def _set_trigger(self, trigger = False, trigger_source = "/Dev1/PFI0", trigger_edge_key = 'rising'):
        # not availbale in DO port
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
        self.close_task()
        self.create_task()
        if self.verbose: print(f'DO task recreated, now operating in {mode} mode')
        
    def reset_task_on_port_change(self, port):
        self.close_task()
        self.port = port
        self.create_task()
        if self.verbose: print(f'DO task recreated, now operating in line {port}')
        
    def write_single_value(self, val): 
        self.stop_task()
        self.task.write(int(val), auto_start = True) # TODO check if the 8 ports can all be set here
        if self.verbose: print(f'DO port set to {val} = {bin(val)}' )
       
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
        rate = self.rate # TODO: DO board use external timing, the rate should be set to the maximum rate of the external timing
        
        try:
            self.stop_task()
            self.task.timing.cfg_samp_clk_timing(rate = rate, 
                                                 source = source,
                                                 sample_mode = sample_mode,
                                                 active_edge = self.trigger_edge_modes['rising'], #TODO check if there is any form of trigger
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
            '''set all lines to True: 0b11111111 = 255 '''
            width = 0.5
            samples = 255* ( (t) % T < (width*T) )
        
        elif waveform_type == "custom": 
            '''set line0 to a rect with width0
                   line1 to a rect with width1
                   line2 to not line0
                   line3 to line0 and line1
                   All other lines to 0'''
            
            line = []
            width0 = 0.5
            line.append( ( (t) % T < (width0*T) ).astype('bool') )
            width1 = 0.1
            line.append( ( (t) % T < (width1*T) ).astype('bool') )
            
            line.append ( np.bitwise_not(line[0]))
            line.append ( np.bitwise_and(line[0],line[1]))
            
            samples = sum([b << i for i, b in enumerate(line)]).astype('uint8')

        else:
            raise(ValueError('Waveform not specified in DO device'))    
        
        self.samples = samples
              
    def start_task(self):
        
        if not hasattr(self, 'task'):
            raise(AttributeError('Task not active, unable to start'))
        
        if self.task.is_task_done():
            self.task.start()
        
    def stop_task(self):
        try:
            self.task.stop()
        except AttributeError as err:
            if self.verbose:  print('Task not active: ', err)
            
    def close_task(self):
        
        try:
            self.task.stop()
            self.task.close()
            delattr(self, 'task')
        except AttributeError as err:
            if self.verbose:  print('Task not active: ', err)
            
            
if __name__ == '__main__':
    
    import time  
    from matplotlib import pyplot as plt
       
    dev = NI_DO_device('Dev1/port0')
    #dev = NI_DO_device('Dev1/PFI0')
    
    try:
        
        dev.create_task()
        #dev.set_trigger(False, '/Dev1/PFI12','rising')
        dev.generate_signal(waveform_type = 'custom',
                            num_periods = 3, 
                            frequency = 200,
                            samples_per_period = 1000)
        
        dev.write_waveform(source = '/Dev1/ao/SampleClock', 
                           sample_mode_key = 'continuous')
        
        if hasattr(dev, 'samples'):
             dev.start_task()
             plt.figure() 
             plt.plot(dev.samples)
             
        time.sleep(0.2)    
        dev.stop_task()
        
        dev.create_task()
        dev.start_task()
        dev.write_single_value(0b0)
        dev.close_task()
        
    finally:
        dev.close_task()
        pass
       
        