from ScopeFoundry import HardwareComponent

from NIdaqmx_ScopeFoundry.ni_ao_device import NI_AO_device

import nidaqmx.system as ni

class NI_AO_hw(HardwareComponent):
    
    name = 'NI_DAQ_AO_hw' 
    
    def setup(self):
        
        board, terminals, trig =self.detect_channels()
        
        self.devices = self.add_logged_quantity('device',  dtype=str, 
                                                initial=board)        
        self.channel = self.add_logged_quantity('channel', dtype=str, 
                                                choices=terminals, initial=terminals[0])
        self.mode = self.add_logged_quantity('mode', dtype=str, 
                                             choices=['ao_voltage', 'ao_waveform'],
                                             initial='ao_waveform')
        self.sample_mode = self.add_logged_quantity('sample_mode', dtype = str,
                                                    choices=[ "continuous", "finite"],
                                                    initial = 'continuous')
        self.num_periods = self.add_logged_quantity('num_periods', dtype = int ,
                                                    si = False, ro = 0,
                                                    vmin=1, initial = 3)
        self.amplitude = self.add_logged_quantity('amplitudes', dtype = float,
                                                  si = False, ro = 0, initial = 1.,
                                                  vmin=-10, vmax=10, unit='V')
        self.waveform = self.add_logged_quantity('waveform', dtype=str,
                                                 choices=[ "sine", "rect","step"],
                                                 initial='sine')
        self.frequency = self.add_logged_quantity('frequency', dtype = float,
                                                  si = False, ro = 0,
                                                  initial = 100, unit='Hz')
        self.offset = self.add_logged_quantity('offset', dtype = float,
                                               si = False, ro = 0,
                                               initial = 0, unit='V')
        self.samples_per_period = self.add_logged_quantity('samples_per_period', dtype = int,
                                                           si = False, ro = 0,
                                                           vmin= 2, initial = 200)
        self.trigger = self.add_logged_quantity('trigger', dtype = bool,
                                                si = False, ro = 0, initial = False)
        self.trigger_source = self.add_logged_quantity('trigger_source', dtype=str,
                                                       choices=trig, initial=trig[0])
        self.trigger_edge = self.add_logged_quantity('trigger_edge', dtype=str,
                                                     choices= ['rising', 'falling'], initial='rising')
        self.spike_amplitude = self.add_logged_quantity('spike_amplitude', dtype = float,
                                                        si = False, ro = 0, initial = 0., unit='V')
        self.spike_duration = self.add_logged_quantity('spike_duration', dtype = float,
                                                       si = False, ro = 0,
                                                       spinbox_decimals = 4, spinbox_step=0.001,
                                                       initial = 0., vmin= 0., unit='s')
        
        self.add_operation("start_task", self.start)
        self.add_operation("stop_task", self.stop)
        
    def connect(self):

        self.AO_device = NI_AO_device(self.channel.val, verbose = True)
        self.AO_device.create_task()
        self.mode.hardware_set_func = self.AO_device.reset_task_on_mode_change
        self.channel.hardware_set_func = self.AO_device.reset_task_on_channel_change
        
    def disconnect(self):
        
        if hasattr(self, 'AO_device'):
            self.AO_device.close()
            del self.AO_device
        
        for lq in self.settings.as_list():
            lq.hardware_read_func = None
            lq.hardware_set_func = None
            
    def start(self):
    
        if not hasattr(self.AO_device, 'task'):
            self.AO_device.create_task()
        
        if self.mode.val == 'ao_waveform':
            self.AO_device.set_trigger(self.trigger.val, 
                                       self.trigger_source.val, 
                                       self.trigger_edge.val)
            
            self.AO_device.write_waveform(self.sample_mode.val,
                                            self.waveform.val,  
                                            self.num_periods.val,
                                            self.amplitude.val, 
                                            self.frequency.val,
                                            self.spike_amplitude.val,
                                            self.spike_duration.val,
                                            self.samples_per_period.val,
                                            self.offset.val ) 
        elif self.mode.val == 'ao_voltage':
            self.AO_device.write_constant_voltage(self.amplitude.val)
        else: 
            raise(AttributeError('Waveform not specified'))
        
        self.AO_device.start_task()
        
    def stop(self):
        self.AO_device.stop_task()
        
    def detect_channels(self):
        ''' Find a NI device and return board + do_terminals'''
        system = ni.System.local()
        device = system.devices[0]
        board = device.product_type + ' : ' + device.name
        terminals = []
        for line in device.ao_physical_chans:
            terminals.append(line.name)
        trig = []
        for j in device.terminals:
            if 'PFI' in j:
                trig.append(j)
        return board, terminals, trig