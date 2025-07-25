import pandas as pd
import numpy as np
import os 
from time import sleep
from datetime import datetime
from SF10 import SF10 
from switchValve import SwitchValve 
from GSIOC_Online import gsioc
import Autosampler as A
from datetime import date
import scipy.integrate as intg
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression

#Directory 
Experimental_Data =r'C:\ProgramData\METTLER TOLEDO\iC IR Experiments\Exp 2025-05-12 14-22'   #to retrieve the CSV files exported by IR software during the experiment for processing
Initial_spectra_1st = r'C:\ProgramData\METTLER TOLEDO\iC IR Experiments\Exp 2025-05-12 14-22\Initial'   #spectra of the initial stock solution collected before initiating experiment
timesweepmodel_first = r'S:\Sci-Chem\PRD\IR 112\WeiNian\Data\Block Statistical Copolymer\Processed Data\Timesweep_PEA100_refined.csv'   #readily available kinetic data collected in prior

#Connection establishment with instruments (USB to RS232 cable)
#Autosampler
A.create_connection('COM13')

#Pumps
pump_stocksoln1 = SF10('COM8','Stock Solution 1')
pump_stocksoln2 = SF10('COM11','Stock Solution 2')
pump_macroRAFT = SF10('COM6','Macro-Raft Agent')

#Switch Valve
switchvalve = SwitchValve('COM29','Switch Valve')

#Parameters that requires user inputs 
#Volumes of different section in the setup
V_reactor1= float(3.66) 
V_reactor2 =float (2.83)
V_autosampler = float(1.4)
V_dead1 = float(0.332)
V_dead2 = float(0.3)
V_prereactor1 = float(13)
V_prereactor2 = float(36)

#Prompt to check whether the stock solution(s) has been degassed, otherwise degassing program will be initiated before the experiment
degasser = str(input('Has the degasser been filled with reagent?(Y/N) >>' ))

#wavenumber range for monomer conversion calculation (first block)
x1 = 1644
x2 = 1612

#wavenumber range for peak area calculation (second block)
x12 = 1650
x22 = 1600

#Mixing ratio calculation
DP_target1 = 100
DP_target2 = 200
con_stock_monomer2 =3
con_macroRAFT = 0.15
monomer1 = 'EA'
monomer2 = 'EHA-co-DMAC'

#Objective for fine tuning experiment
n_iterations_max = 20 #experimental budget for fine tuning experiment (first block)
target_conversion =0.96 #conversion to be achieve in fine tuning experiment 
tolerance = 0.02 #accceptable error margin

#Data slicing 
t_step = float(2) #in min, data collection collection during fine-tuning experiment
t_scan = float(0.167) #in min, sample interval on IR software (changable on software)
n = int(t_step/t_scan)

#Functions
def peak_area_converter(Experimental_Data,peak_area_initial):
    a = Experimental_Data.iloc[:,1]
   
    #prediction 
    result_df = pd.DataFrame({'Peak Area':a})
    result_df['conversion'] = result_df['Peak Area'].apply(lambda x: 1-x/peak_area_initial)
    result_df['time/min']=Experimental_Data['time/min']
    result_df['residence time/min']=Experimental_Data['residence time/min']
    return result_df
 
peak_area_list = []
def peak_integration(file,A,B):
    with open(file) as i:
        df = pd.read_csv(i,skiprows=1,index_col=0)
        data_df = df.loc[A:B]
       
        #select wavenumber range for integration
        x_data = np.array(data_df.index)
        y_data = data_df.iloc[:,0]

        #baseline
        y_base1 = data_df.iloc[0,0]
        y_base2 = data_df.iloc[-1,0]

        #Peak integration with Trapezoidal rule
        #Total Area
        peak_area1 = abs(intg.trapezoid(x=x_data,y=y_data)) #multiply by -1 because the wavenumber is in descending order

        #Area of baseline
        peak_area2 = abs(intg.trapezoid(x=[A,B],y=[y_base1,y_base2]))
        peak_area = peak_area1-peak_area2
        peak_area_list.append(peak_area)
    return peak_area_list

#To extract the peak area associated with initial stock solution before polymerization
def experimental_data(exp_data,a,b):
    peak_area_list = []
    col = np.arange(a,b-4,-4)
    df_exp = pd.DataFrame({},columns=col)
    for file in os.scandir(exp_data):
        with open(file) as i:
            y = pd.read_csv(i,index_col=0)
            y = y.loc[a:b]
            df_exp.loc[len(df_exp)]=y.iloc[:,0].to_list()
            x_data = np.arange(a,b-4,-4)
            y_data = df_exp

            #baseline
            y_base1 = df_exp.iloc[0,0]
            y_base2 = df_exp.iloc[0,-1]

            #Peak integration with Trapezoidal rule
            #Total Area
            peak_area1 = abs(intg.trapezoid(x=x_data,y=y_data)) #multiply by -1 because the wavenumber is in descending order

            #Area of baseline
            peak_area2 = abs(intg.trapezoid(x=[a,b],y=[y_base1,y_base2]))
            peak_area = peak_area1-peak_area2
            peak_area_list.append(peak_area)
    return peak_area_list

def trxn_to_tres(df,t_scan,tres,n):
    '''
    create a scale for residence time for all the data collected
    '''
    
    tres_list = []
    tres_list.append(tres)
    for i in range(1,len(df)):
         tres=tres+t_scan/n
         tres_list.append(tres)
    return tres_list

def pump_operation(pump,flowrate):
    pump.start()
    pump.changeFlowrate(flowrate)
    sleep(1.2*(V_reactor1/flowrate*60+V_dead1/flowrate*60)) #multiply by 1.2 for stabilization
    print('collecting data now!!!')
    sleep(t_step*60)
    pump.stop()
    print('stop collecting sample now!!!')

def degasser_filling(V_prereactor1):

    '''
    program to fill degasser with stock solution 1 before experiment. Flow rate of 1ml/min is used.
    '''
    if degasser == 'N':
        pump_stocksoln1.changeFlowrate(1) 
        pump_stocksoln1.start()
        sleep(V_prereactor1/1*60) 
        pump_stocksoln1.stop()
        print('prereactor volume has been filled with reagent!')
    elif degasser == 'Y':
        return None
    else:
        print('Invalid input value!')

def degasser_filling2(FlowRate_list):
    '''
    program to mix stock solution 2 and macro-RAFT agent and pass them into degasser.
    A default value of 4 is used, meaning the solutions are mixed with flow rates that would combined to give a residence time of 4min in the reactor.
    '''
    if degasser == 'N':
        F_stocksoln2 = float(V_reactor2/4*(DP_target2*con_macroRAFT)/(con_stock_monomer2+DP_target2*con_macroRAFT))
        F_macroRAFT = V_reactor2/4-F_stocksoln2
        pump_stocksoln2.changeFlowrate(F_stocksoln2) #fill the degasser with reagent before starting the experiment
        pump_macroRAFT.changeFlowrate(F_macroRAFT)
        pump_macroRAFT.start()
        pump_stocksoln2.start()
        print('time needed to degas the solution is {}min'.format(V_prereactor2/(V_reactor2/4)))
        sleep(V_prereactor2/(V_reactor2/4)*60)
        pump_stocksoln2.stop()
        pump_macroRAFT.stop()
        print('prereactor volume has been filled with reagent!')
    elif degasser == 'Y':
        return None
    else:
        print('Invalid input value')

def timesweep_firstblock():
    '''
    This function includes 
    1. operation code for kinetic timesweep experiment.
    2. data processing from the experiment
    '''
    #Get the spectra of the stock solution (initial) as normalization standard for subsequently quantitative analysis of residual monomer
    peak_area_list = []
    peak_area_initial = experimental_data(Initial_spectra_1st,x1,x2)[-1].mean(axis=0)
    print("Initial peak area of the stock solution is: {}".format(peak_area_initial))

    #prompt to key in number of Tres and their values for timesweep
    time_list = []
    n =int(input('Please input the number of residence times that will involved in your reaction:>> '))
    for i in range(n):
        time= float(input('Please input the involved residence time one by one(seconds):>> '))
        time_list.append(time)
    print("Residence time for the experiment are: {}".format(time_list))

    FlowRate_list=[]
    for time_i in time_list:
        Flowrate = V_reactor1*60 / time_i
        FlowRate_list.append(Flowrate)
    print("Operating flowrates for the experiment are: {}".format(FlowRate_list))

    DeadTime = []
    for flow in FlowRate_list:
        t_dead = V_dead1*60 / flow
        DeadTime.append(t_dead)
    print('Time taken to travel to the IR probe from the outlet of reactor are: {}'.format(DeadTime))

    SleepTime = []
    for i in range(n):
        sleeptime = DeadTime[i] + time_list[i] 
        SleepTime.append(sleeptime)
    print('Time taken for each timesweep interval are: {}'.format(SleepTime))

    #Timesweep experiment operation
    for i in range (n):
        pump_stocksoln1.changeFlowrate(FlowRate_list[i])
        pump_stocksoln1.start()
        sleep(SleepTime[i])
    
    print('Timesweep experiment has concluded!!')
    
    #create timescale to match all the raw data collected during the
    t_exp = (np.sum(time_list) + np.sum(DeadTime) + n*(t_step*60))/60 #convert to minutes
    print('The entire experiment takes: {} min'.format(t_exp))

    t = np.arange(t_scan,t_exp,t_scan)

    peak_area_list = []
    #extract all the data files from IR during the experiment
    x=list(os.scandir(Experimental_Data))
    a = int(t_exp/t_scan)

    #peak integration to calculate peak area for monomer conversion 
    for file in x[-a:]:
        if file.is_file():
            peak_area_list = peak_integration(file,x2,x1)

    #create a dataframe and match the time scale with raw data collected
    df = pd.DataFrame({'time/min':t,'peak_area':peak_area_list})

    #data slicing based on timestamp for first timesweep
    t1 = (time_list[0]+DeadTime[0]+t_step*60+DeadTime[1])/60 #stabilized flow of the first residence time 
    t2 = t1+(time_list[1])/60 

    timesweep_df = df[df['time/min'].between(t1,t2)]
    timesweep_df['residence time/min']=trxn_to_tres(timesweep_df,t_scan,time_list[0]/60,time_list[1]/(time_list[1]-time_list[0]))

    #data slicing based on timestamp for the subsequent timesweep
    for i in range(2,n):
        ta = t2+(t_step*60+DeadTime[i])/60
        tb = ta+(time_list[i])/60

        df_i = df[df['time/min'].between(ta,tb)] 
        df_i['residence time/min']=trxn_to_tres(df_i,t_scan,time_list[i-1]/60,time_list[i]/(time_list[i]-time_list[i-1]))

        t2 = tb
        timesweep_df = pd.concat([timesweep_df,df_i])

    #convert peak area calculated to monomer conversion using Beer-Lambert equation
    result_df = peak_area_converter(timesweep_df,peak_area_initial)

    #export processed data to pre-defined directory
    result_df.to_csv(r'S:\Sci-Chem\PRD\IR 112\WeiNian\Data\Processed Data\Timesweep_P{}{}_{}1.csv'.format(monomer1,DP_target1,date.today().strftime('%d%m%Y')))

    #locate the maximum conversion achievable and it's corresponding Tres
    max_conversion = result_df['conversion'].max()
    max_residence_time = result_df['residence time/min'][result_df['conversion']==max_conversion]

    print('The maximum conversion achievable was {}, at residence time of {}min'.format(max_conversion,max_residence_time))
    return peak_area_initial,result_df,max_conversion

def timesweep_secondblock():
    '''
    
    This function includes:
    1. operation code for kinetic timesweep experiment. (2nd block)
    2. data processing from the experiment
    3. control of liquid-handling autosampler for sample collection

    flow is similar to timesweep_firstblock()

    '''

    pump_stocksoln=pump_stocksoln2
    pump_RAFT =pump_macroRAFT

    #Pump stock solution and macroRAFT agent into the auto-degasser for oxygen removal
    Timesweep = {}
    n =int(input('Please input the number of residence times that will involved in your reaction:>> '))
    for i in range(n):
        keys = i + 1 
        values = float(input('Please input the involved residence time one by one(seconds):>> '))
        Timesweep[keys] = values

    time_list = list(Timesweep.values())
    print("Residence time for the experiment are: {}".format(time_list))

    FlowRate_list=[]
    for time_i in time_list:
        Flowrate = V_reactor2*60 / time_i
        FlowRate_list.append(Flowrate)
    print("Operating flowrates for the experiment are: {}".format(FlowRate_list))

    SamplingTime = []
    for flow in FlowRate_list:
        t_sampling = V_autosampler*60 / flow #To fill up the sample tube 
        SamplingTime.append(t_sampling)
    print('Time taken to fill up the sample collection tube: {}'.format(SamplingTime))

    #Operation 
    DeadTime = []
    for flow in FlowRate_list:
        t_dead = V_dead2*60 / flow
        DeadTime.append(t_dead)
    print('Time taken to travel to the IR probe from the outlet of reactor are: {}'.format(DeadTime))

    SleepTime = []
    for i in range(n):
        sleeptime = DeadTime[i] + time_list[i] 
        SleepTime.append(sleeptime)
    print('Time taken for each timesweep interval are: {}'.format(SleepTime))

    #fill the empty space in pumps with solution before mixing and degassing:
    pump_macroRAFT.changeFlowrate(1)
    pump_stocksoln2.changeFlowrate(1)
    sleep(0.6/1*60) #0.6ml of space

    degasser_filling2(FlowRate_list)

    #Start of the timesweep experiment 
    for i in range (n+1):
        if i<n:
            F_pump2 = float(FlowRate_list[i]*(DP_target2*con_macroRAFT)/(con_stock_monomer2+DP_target2*con_macroRAFT)) 

            pump_stocksoln.changeFlowrate(F_pump2)
            pump_RAFT.changeFlowrate(FlowRate_list[i]-F_pump2)

            pump_stocksoln.start()
            pump_RAFT.start()

            #Move arm to the collection vial
            #clear solution in the syringe needle
            A.slot_selection(0)  #+0.5s
            sleep(1) #+1s
            A.liquid_level()#+0.5s
            A.diverter('sampling') #+0.5s
            sleep(0.4/FlowRate_list[i]*60-8) #to dump waste
            A.diverter('waste') #+0.5s
            A.liquid_level(125) #+0.5s
            sleep(2) #+2s

            #Move to the slot for sample collection
            A.slot_selection(i) #+0.5s
            sleep(1) #+1s
            A.liquid_level() #+0.5s
            A.diverter('sampling') #+0.5s

            sleep(SamplingTime[i]-0.4/FlowRate_list[i]*60)

            A.diverter('waste') #+0.5s
            A.home() #+0.5s

            sleep(SleepTime[i]-SamplingTime[i]-1) #Reagent reaches the IR probe
        
            print('Start collecting sample now......')

            sleep(SamplingTime[i])

            print('Proceed with the next residence time......')

        else:
            #clear solution in the syringe needle
            A.slot_selection(0)  #+0.5s
            sleep(1) #+1
            A.liquid_level()#+0.5s
            A.diverter('sampling') #+0.5s
            sleep(0.4/FlowRate_list[i-1]*60-9) 
            A.diverter('waste') #+0.5s
            A.liquid_level(125) #+0.5s
            sleep(2) #+2

            #Move to the slot for sample collection
            A.slot_selection(i) #+0.5s
            sleep(2)#+2
            A.liquid_level() #+0.5s
            A.diverter('sampling') #+0.5s

            sleep(SamplingTime[i-1]-0.4/FlowRate_list[i-1]*60)

            A.diverter('waste') #+0.5s
            A.home() #+0.5s
    
    print('Timesweep experiment has concluded!!')  
    
    
    #set timescale to the raw data dataframe
    t_exp = (np.sum(time_list) + np.sum(DeadTime) + np.sum(SamplingTime)+SamplingTime[-1])/60 #convert to minutes
    print('The entire experiment takes: {} min'.format(t_exp))


    t = np.arange(t_scan,t_exp,t_scan)
    peak_area_list = []

    #extract latest data from IR
    x=list(os.scandir(Experimental_Data)) #data exported to this directory
    a = int(t_exp/t_scan)

    for file in x[-a:]:
        if file.is_file():
            peak_area_list = peak_integration(file,x12,x22)
    
    df = pd.DataFrame({'time/min':t,'peak_area':peak_area_list})

    t1 = (time_list[0]+DeadTime[0]+SamplingTime[0]+3+DeadTime[1])/60 #stabilized flow of the first residence time 
    t2 = t1+(time_list[1])/60 

    timesweep_df = df[df['time/min'].between(t1,t2)]
    timesweep_df['residence time/min']=trxn_to_tres(timesweep_df,t_scan,time_list[0]/60,time_list[1]/(time_list[1]-time_list[0]))

    #for the subsequent timesweep:
    for i in range(2,n):
        ta = t2+(SamplingTime[i-1]+DeadTime[i])/60
        tb = ta+(time_list[i])/60

        df_i = df[df['time/min'].between(ta,tb)] 
        df_i['residence time/min']=trxn_to_tres(df_i,t_scan,time_list[i-1]/60,time_list[i]/(time_list[i]-time_list[i-1]))

        t2 = tb
        timesweep_df = pd.concat([timesweep_df,df_i])
    
    #processing the data
    timesweep_df.to_csv(r'S:\Sci-Chem\PRD\IR 112\WeiNian\Data\Block Statistical Copolymer\Processed Data\Timesweep_P{}{}_b_P{}{}_{}.csv'.format(monomer1,DP_target1,monomer2,DP_target2,date.today().strftime('%d%m%Y')))
    return timesweep_df

def conversion_fine_tuning(target_conversion,max_conversion,timesweep_df,peak_area_initial):
    '''
    This function control the autonomous self-optimizing experiment for kinetic model
    '''

    print('Maximum conversion achieved in the timesweep experiment is {}'.format(max_conversion)) 

    #Adjust the target conversion accordingly according to the timesweep experiment
    print('Maximum conversion achieved in the timesweep experiment is {}'.format(max_conversion))


    if target_conversion > max_conversion:
        target_conversion = max_conversion
    else:
        target_conversion = target_conversion

    #pseudo first order reaction. Linearize the conversion data to be used with linear regression
    target_conversion1 = (-1*np.log(1-target_conversion)).reshape(1,-1)
    y = timesweep_df['residence time/min']
    x = np.array(timesweep_df['conversion'].apply(lambda a:-1*np.log(1-a))).reshape(-1,1) 

    lr = LinearRegression()
    lr.fit(x,y)
    t = lr.predict(target_conversion1)

    #To remove double square bracket:
    for i in t:
        t=i
    
    print('residence time predicted is {} min'.format(t))

    #polymerization
    flowrate = V_reactor1/t
    pump_operation(pump_stocksoln1,flowrate)

    #To get the conversion from the latest samples:
    peak_area_list = []
    x=list(os.scandir(Experimental_Data))

    for file in x[-n:]:
        if file.is_file():
            peak_area_list=peak_integration(file,1644,1612) #1652-1620 fr EA #1660-1616 fr EGMEA
    data = np.mean(peak_area_list)

    conversion_i = 1-data/peak_area_initial
    print('conversion == {} '.format(conversion_i))
    del_conversion_abs = abs((conversion_i - target_conversion)/target_conversion)
    print('deviation from target == {}'.format(del_conversion_abs))

    timesweep_df.loc[len(timesweep_df)+1]={'Peak Area':data,'residence time/min':t,'conversion':conversion_i}

    #iteration
    counter=0
    while del_conversion_abs >= tolerance and counter<n_iterations_max:
        #Linear Regression
        sample_weight = np.ones(len(timesweep_df)-1)
        sample_weight = np.append(sample_weight,200)

        x = np.array(timesweep_df['conversion'].apply(lambda a:-1*np.log(1-a))).reshape(-1,1)
        y = timesweep_df['residence time/min']

        lr = lr.fit(x,y,sample_weight=sample_weight)
        t = lr.predict(target_conversion1)
        for i in t:
            t=i
        
        print('residence time predicted is {} min'.format(t))
        
        flowrate_i = V_reactor1/t
        pump_operation(pump_stocksoln1,flowrate_i)

        x=list(os.scandir(Experimental_Data))
        for file in x[-n:]:
            if file.is_file():
                peak_area_list = peak_integration(file,1644,1612)

        data = np.mean(peak_area_list)
        conversion_i = 1-data/peak_area_initial
        print('conversion == {} '.format(conversion_i))
        del_conversion_abs = abs((conversion_i - target_conversion)/target_conversion)
        print('deviation from target == {}'.format(del_conversion_abs))
        
        timesweep_df.loc[len(timesweep_df)+1]={'Peak Area':data,'residence time/min':t,'conversion':conversion_i}

        counter+=1
    print(timesweep_df.tail())
    print('Target conversion has been achieved!')

    #export latest kinetic data
    timesweep_df.to_csv(r'S:\Sci-Chem\PRD\IR 112\WeiNian\Data\Processed Data\Timesweep_P{}{}_refined.csv'.format(monomer1,DP_target1))

    return timesweep_df


#Execution code for experiment 
#Move the autosampler arm to home first to offset any possible error
A.home()
sleep(10)

# Move diverter valve on to direct the stream to waste bottle
A.diverter('waste')

#Direct outlet from reactor 1 to IR
switchvalve.toPositionA() 
peak_area_list = []
peak_area_initial_1st = experimental_data(Initial_spectra_1st,x1,x2)[-1].mean(axis=0)

#Timesweep experiment for homopolymerization
timesweep_model = input('Has the timesweep experiment been done before? (Y/N)>>')

#Fill the autodegasser with stock solution
degasser_filling(V_prereactor1)
if timesweep_model =='N':
    peak_area_initial_1st,timesweep_first,max_conversion = timesweep_firstblock()
elif timesweep_model == 'Y':
    peak_area_list = []
    peak_area_initial_1st = experimental_data(Initial_spectra_1st,x1,x2)[-1].mean(axis=0)
    timesweep_first = pd.read_csv(timesweepmodel_first,index_col=0)
    max_conversion = float(timesweep_first['conversion'].max())
else:
    print('Invalid response!')

#start of fine tuning experiment
print('Start of finetuning experiment')
timesweep_refined_first = conversion_fine_tuning(target_conversion,max_conversion,timesweep_first,peak_area_initial_1st)
print('end of finetuning experiment')

#Produce 20ml of macroRAFT agent before proceeding to second timesweep experiment
#Direct outlet from reactor 1 to macro-RAFT reservoir
switchvalve.toPositionB() 
a = timesweep_refined_first['residence time/min'].iloc[-1] #picking the latest residence time predicted from fine-tuning experiment
pump_stocksoln1.changeFlowrate(V_reactor1/a)
pump_stocksoln1.start()
print('It would take {}min to synthesize 20ml of macroRAFT'.format(20/(V_reactor1/a)))
sleep(20/(V_reactor1/a)*60)

#Timesweep experiment for diblock copolymerization
timesweep_second = timesweep_secondblock()










 
