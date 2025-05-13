from GSIOC_Online import gsioc
from time import sleep

g=gsioc()
def create_connection(port):
    g.createSerial(port,100,19200)
    g.connect(20) #autosampler

def home():
    g.bCommand('H')
    sleep(0.5)
    print('Moving the arm back to its home position')
    pass

def diverter(status):
    '''
    To direct the stream from reactor to either waste container or vial for sample collection
    '''
    if status == 'sampling':
        g.bCommand('F1')
    elif status == 'waste':
        g.bCommand('F0')
    else:
        print('Invalid Input')
    
    sleep(0.5)

def tray_selection(n_tray=0,y=20):
    '''
    move the arm to the specified tray in X-direction
    '''
    d_interslot = 31
    d_intertray = 55
    for n in range(3):
        if n_tray == n:
            x = n*(2*d_interslot+d_intertray) + 45
            g.bCommand('X{}/{}'.format(str(x),str(y)))
    else:
        print('Tray specified is not within the range (0-2)')
    
    sleep(0.5)
    pass       

def slot_selection(n_loc):
    '''
    n_loc = location specified by the user
    '''
    d_interslot = 31
    d_intertray = 55
    
    if n_loc <=8:
        x = 45 
        y = 20 + n_loc*d_interslot
        print(x,y)
        g.bCommand('X{}/{}'.format(str(x),str(y)))
        print('Moving to the location')

    elif 8 < n_loc <= 17:
        x = 77.5
        y = 20 + (n_loc-9)*d_interslot
        g.bCommand('X{}/{}'.format(str(x),str(y)))
        print('Moving to the location')

    elif 17 < n_loc <= 25:
        x =110
        y = 20 + (n_loc-18)*d_interslot
        g.bCommand('X{}/{}'.format(str(x),str(y)))
        print('Moving to the location')

    else:
        print('Location specified is not within the range (0-26)')
    
    sleep(0.5)
    pass

def liquid_level(h = 80):
    g.bCommand("Z{}".format(h))
    sleep(0.5)
    pass  

