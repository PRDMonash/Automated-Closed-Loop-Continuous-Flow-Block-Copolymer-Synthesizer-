import serial
from time import sleep

class SwitchValve():
    def __init__(self, port, name = 'UNKNOWN (Switch Valve)'):
        '''
        port: str
            port number, e.g. COM3
        '''
        
        self.con = serial.Serial(port)
        
        self.name = name 
        
        print('{} at {}'.format(self.name, self.con.port))
    
    def __repr__(self) -> str:
        return "Switch Valve"

    def toPositionA(self):
        command = 'start'
        
        self.con.write(b'CW\r')

    
    def toPositionB(self):
        command = 'start'
        
        self.con.write(b'CC\r')

        