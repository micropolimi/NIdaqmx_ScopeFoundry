from ScopeFoundry import HardwareComponent

from NIdaqmx_ScopeFoundry.ni_do_timed_device import NI_DO_device

import nidaqmx.system as ni

class NI_DO_timed_hw(HardwareComponent):
    ''' Timed digital waveform output is available on NI-6221, NI-6341
        not on NI-6212'''
    
    
    name = 'NI_DAQ_timed_DO_hw' 
    
    def setup(self):
        
        board, device, ports, lines =self.detect_ports()
        
        self.board = self.add_logged_quantity('board',  dtype = str, 
                                                initial = board)        
        self.port = self.add_logged_quantity('port', dtype=str, 
                                                choices = ports, initial = ports[0])
        self.mode = self.add_logged_quantity('mode', dtype=str, 
                                             choices=['do_constant', 'do_waveform'],
                                             initial='do_waveform')
        self.timing_source = self.add_logged_quantity('timiing_source', dtype=str, 
                                             initial=f'/{device}/ao/SampleClock')
        self.sample_mode = self.add_logged_quantity('sample_mode', dtype = str,
                                                    choices=[ "continuous", "finite"],
                                                    initial = 'continuous')
        self.num_periods = self.add_logged_quantity('num_periods', dtype = int ,
                                                    si = False, 
                                                    vmin=1, initial = 3)
        self.waveform = self.add_logged_quantity('waveform', dtype=str,
                                                 choices=["rect","custom"],
                                                 initial='rect')
        self.frequency = self.add_logged_quantity('frequency', dtype = float,
                                                  si = False, 
                                                  initial = 100, unit='Hz')
        
        self.samples_per_period = self.add_logged_quantity('samples_per_period', dtype = int,
                                                           si = False, ro = 0,
                                                           vmin= 2, initial = 200)
        self.constant_value = self.add_logged_quantity('constant_value', dtype = int,
                                                  si = False, vmin = 0, vmax = 255, 
                                                  initial = 255 )
        
        self.add_operation("start_task", self.start)
        self.add_operation("stop_task", self.close)
        
    def connect(self):

        self.DO_device = NI_DO_device(self.port.val, verbose = True)
        self.DO_device.create_task()
        self.mode.hardware_set_func = self.DO_device.reset_task_on_mode_change
        self.port.hardware_set_func = self.DO_device.reset_task_on_port_change
        
    def disconnect(self):
        
        if hasattr(self, 'DO_device'):
        #     self.DO_device.close_task()
            self.close()    
            del self.DO_device
        
        for lq in self.settings.as_list():
            lq.hardware_read_func = None
            lq.hardware_set_func = None
            
    def start(self):
    
        if not hasattr(self.DO_device, 'task'):
            self.DO_device.create_task()
        
        if self.mode.val == 'do_waveform':
            self.DO_device.generate_signal( self.waveform.val,  
                                            self.num_periods.val,
                                            self.frequency.val,
                                            self.samples_per_period.val)
            
            self.DO_device.write_waveform(self.timing_source.val,
                                          self.sample_mode.val) 
        elif self.mode.val == 'do_constant':
            self.DO_device.write_single_value(self.constant_value.val)
        else: 
            raise(AttributeError('Waveform not specified in DO hardware'))
        
        self.DO_device.start_task()
        
    def close(self):
        '''close the task, reopen a new one to set the channel to 0'''    
        self.DO_device.close_task() 
        self.DO_device.create_task()
        self.DO_device.write_single_value(0) # TODO check if it works on multiple lines
        self.DO_device.close_task()
        
                
    def detect_ports(self):
        ''' Find a NI device and return board + do ports and lines'''
        system = ni.System.local()
        device = system.devices[0]
        board = device.product_type + ' : ' + device.name
        lines = []
        for line in device.do_lines:
            lines.append(line.name)
        ports=[]
        for port in device.do_ports:
            ports.append(port.name)
        
        return board, device.name, ports, lines