from ScopeFoundry import HardwareComponent

from ni_ao_device import NI_AO_device

import nidaqmx.system as ni

class NI_AO_hw(HardwareComponent):
    
    name = 'NI_DAQ_AO_hw' 
    
    def setup(self):
        #create logged quantities, that are related to the graphical interface
        board, terminals=self.update_channels()
        
        self.devices = self.add_logged_quantity('device',  dtype=str, initial=board)        
        self.channel = self.add_logged_quantity('channel', dtype=str, choices=terminals, initial=terminals[0])
        self.mode = self.add_logged_quantity('mode', dtype=str, choices=[ "ao_voltage", "ao_waveform"], initial='ao_voltage')
        
        self.sample_mode = self.add_logged_quantity('sample_mode', dtype = str, choices=[ "continuous", "finite"], initial = 'continuous')
        self.num_periods = self.add_logged_quantity('num_periods', dtype = int , si = False, ro = 0, vmin=1, initial = 1)
        self.rate = self.add_logged_quantity('rate', dtype = float, si = False, ro = 0, initial = 1000, vmin=0, vmax= 250000, unit='Hz') 
        #use a rate of at least twice the frequency of the signal
        self.amplitude = self.add_logged_quantity('amplitude', dtype = float, si = False, ro = 0, initial = 0, vmin=-10, vmax=10, unit='V')
        self.waveform = self.add_logged_quantity('waveform', dtype=str, choices=[ "sine", "triangle", "square"], initial='sine')
        self.frequency = self.add_logged_quantity('frequency', dtype = float, si = False, ro = 0, initial = 100, unit='Hz')
        self.offset = self.add_logged_quantity('offset', dtype = float, si = False, ro = 0, initial = 0, unit='V')
        
        self.add_operation("start_waveform_task", self.start)
        self.add_operation("stop_waveform_task", self.stop)
        
    def connect(self):
        #continuous_to_constant = {False:10178, True:10123} #create a dictionary for mapping the mode with the corresponding constants in nidaqmx
            
        #open connection to hardware
        self.channel.change_readonly(True)
        self.mode.change_readonly(True)
        self.AO_device = NI_AO_device(channel=self.channel.val, mode=self.mode.val, sample_mode=self.sample_mode.val,
                                          num_periods=self.num_periods.val, rate=self.rate.val,
                                          amplitude=self.amplitude.val, waveform=self.waveform.val,
                                          frequency=self.frequency.val, offset=self.offset.val, debug=self.debug_mode.val)
        
        #connect logged quantities
        self.mode.hardware_set_func = self.AO_device.set_mode
        
        self.sample_mode.hardware_set_func = self.AO_device.set_sample_mode
        self.num_periods.hardware_set_func = self.AO_device.set_num_periods
        self.rate.hardware_set_func = self.AO_device.set_rate       
        
        self.amplitude.hardware_set_func = self.AO_device.set_ampl
        self.waveform.hardware_set_func = self.AO_device.set_waveform
        self.frequency.hardware_set_func = self.AO_device.set_frequency
        self.offset.hardware_set_func = self.AO_device.set_offset
        
        
    def disconnect(self):
        self.mode.change_readonly(False)
        self.channel.change_readonly(False)
        #disconnect hardware
        if hasattr(self, 'AO_device'):
            self.AO_device.close()
            del self.AO_device
        
        for lq in self.settings.as_list():
            lq.hardware_read_func = None
            lq.hardware_set_func = None
            
    def start(self):
        
        self.AO_device.start_task()
        
    def stop(self):
        
        self.AO_device.stop_task()
        
    def update_channels(self):
        ''' Find a NI device and return board + do_terminals'''
        system = ni.System.local()
        device=system.devices[0]
        board=device.product_type + ' : ' + device.name
        terminals=[]
        for line in device.ao_physical_chans:
            terminals.append(line.name)
              
        return board, terminals
        
                    