# Automated-Flow-Synthesizer-for-Diblock-Copolymer-Material Library Construction 

**Python files for contronlling instruments:**
1. SF10 pumps --> SF10.py 
2. switch valve --> switchValve.py
3. liquid-handling autosampler -->Autosampler.py
4. GSIOC instrument cimmunication --> GSIOC_Online.py

Note: to establish communication with the liquid-handling autosampler, 

**Wavenumber range screening for quantitative analysis of residual monomer conversion**
--> Optimal Wavenumber Range.py 

This script is used in tandem with NMR conversion values of all the samples collected during a polymerization experiment.
1. It will generate a csv file in the form of heatmaps, which show all the %error between the monomer conversion calculated
across each range of wavenumber (Beer-Lambert Law) and that of NMR.

2. A heatmap visualization function also included in the script which can be used with the dataframe generated.

**Experiment execution code **
-->Automated Diblock Copolymer Synthesis (Publication).py
This script contains all the functions needed to run a complete experiment, including Python libraries and modules needed for the operation.
Before initiating the program for an experiment: 
1. users need to input all the parameters before running an experiment.
2. input directories to extract raw IR data from and export final results.
3. prepare all the stock solutions.
4. make sure all the instrument is turned on.
