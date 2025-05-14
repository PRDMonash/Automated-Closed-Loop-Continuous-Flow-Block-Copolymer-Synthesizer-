import numpy as np
import os
import pandas as pd
import scipy.integrate as intg
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.cross_decomposition import PLSRegression
from sklearn.metrics import mean_absolute_error,mean_squared_error
import seaborn as sns

exp_data = ''

def peak_area(df,i,a,b):
    '''

    peak integration function with baseline drawn between <a to b> cm-1

    '''
    y_data = df.loc[i,a:b]
   
    x_data = np.arange(a,b-4,-4)

    #baseline
    y_base1 = y_data.iloc[0]
    y_base2 = y_data.iloc[-1]

    #Peak integration with Trapezoidal rule
    #Total Area
    peak_area1 = abs(intg.trapezoid(x=x_data,y=y_data)) #multiply by -1 because the wavenumber is in descending order
    #Area of baseline
    peak_area2 = abs(intg.trapezoid(x=[a,b],y=[y_base1,y_base2]))
    peak_area = peak_area1-peak_area2
    return peak_area

def optimization_wavenumber(x1,x2,x_NMR,exp_data):
    '''
    function to calculate % error between conversion calculated across each range of wavenumber and values given by NMR analysis

    '''


    #importing and compiling all the IR spectral data in a dataframe for processing
    df = pd.DataFrame({},columns=[x for x in range(4000,644,-4)]) 
    col = []
    for file in os.scandir(exp_data):
        #Extract name from each data file
        name = os.path.basename(file).split('.')[0]
        col.append(name)

        #read all the spectra and organize into a single dataframe
        with open(file)as i:
            x = pd.read_csv(i,index_col=0)
            x = x.loc[4000:648]
            df.loc[len(df)]=x.iloc[:,0].to_list()
    
    a_list = b_list = np.arange(x1,x2,-4)
    error = pd.DataFrame({},index=b_list,columns=a_list)

    dict = {}
    for i in range(len(df)):
        dict[i]=pd.DataFrame({},index=b_list,columns=a_list)

    #wavenumber screening across the specified range of wavenumber
    for a in a_list:
        for b in b_list:
            if a>b+4:
                error_list = []
                alpha = peak_area(df,0,a,b)
        
                for i in range(1,len(df)):
                    omega = peak_area(df,i,a,b)
                    conversion = 1-(omega/alpha)
                    
                    er = abs(conversion-x_NMR[i-1])/x_NMR[i-1]*100
                    dict[i-1].loc[a,b]=er
                    error_list.append(er)

                mean_error = sum(error_list)/len(error_list)
                error.loc[a,b] = mean_error
            elif a==b:
                error.loc[a,b]=None
            
            else:
                error.loc[a,b]=None
    
    os.chdir('S:\Sci-Chem\PRD\IR 112\WeiNian\Data\Processed Data')
    name = 'Optimized WV {}.xlsx'.format(os.path.basename(exp_data))

    #exporting the data file
    with pd.ExcelWriter(name) as writer:
        error.to_excel(writer,sheet_name='Average')
        for i in range(len(df)-1):
            dict[i].to_excel(writer,str(i))
    return error

def heatmap(error,name):
    i_list = []
    j_list = []
    error_list = []

    df = pd.DataFrame({},columns=['wavenumber 1','wavenumber 2','error'])
    for i in error.index:
        for j in error.index:
            if i>j:
                i_list.append(i)
                j_list.append(j)

                error_list.append(error.loc[i,j])
                
    df['wavenumber 1']=i_list
    df['wavenumber 2']=j_list
    df['error']=error_list

    sns.heatmap(df.pivot(index='wavenumber 1',columns='wavenumber 2',values='error'),cmap="coolwarm",vmin=0,vmax=100)
    plt.xlabel('$\it{Wavenumber}$ 1 / $cm^{-1}$')
    plt.ylabel('$\it{Wavenumber}$ 2 / $cm^{-1}$')
    return plt.savefig(name,dpi=200)


#Example
#conversion according to NMR analysis of each samples
x_NMR = [0.271,0.342,0.586,0.734,0.823,0.873]

#directory of the folders storing all the IR spectra in csv format
exp_data = r'S:\Sci-Chem\PRD\IR 112\WeiNian\Data\Timesweep PEGMEA DP30'

error = optimization_wavenumber(1700,1600,x_NMR,exp_data)

#directroy to store the heatmap figures
name = r'\\ad.monash.edu\home\User007\wwon0072\Documents\Automated Block Copolymer Synthesizer\Publication\Optimal WV for IR\PEGMEA in Butyl Acetate'

#generating heatmap from the analysis
heatmap(error,name)