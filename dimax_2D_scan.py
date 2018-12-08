import time
import numpy as np
import os
import Tkinter
import tkMessageBox as mbox

from pco_lib import *

global variableDict

variableDict = {
        'ExposureTime': 0.01,
        'Projections': 300,
        'SampleYIn': 0.0,
        'SampleYOut': -3,
        'roiSizeX': 2016, 
        'roiSizeY': 900,        
        'PostWhiteImages': 20,
        'PostDarkImages': 25,
        'ShutterOpenDelay': 0.00,
        'IOC_Prefix': 'PCOIOC2:', # options: 1. DIMAX: 'PCOIOC2:', 2. EDGE: 'PCOIOC3:'
        'FileWriteMode': 'Stream',
        'CCD_Readout': 0.0001,
        'EnergyPink': 2.657, 
        'EnergyMono': 24.9,
        'Station': '2-BM-A',
        'StartSleep_min': 0,
        'SlewSpeed': 37.5, # to use this as default value comment the calc_blur_pixel(global_PVs, variableDict) function below
        'AcclRot': 90.0,
        'SampleRotStart': 0.0,
        'SampleRotEnd': 180.0,
        'SampleXIn': 0.0,
        'SampleXOut': 14,
        }

global_PVs = {}

def getVariableDict():
    global variableDict
    return variableDict

def main():

    tic =  time.time()
    update_variable_dict(variableDict)
    init_general_PVs(global_PVs, variableDict)
    
    try: 
        model = global_PVs['Cam1_Model'].get()
        if model == None:
            print('*** The PCO Camera with EPICS IOC prefix %s is down' % variableDict['IOC_Prefix'])
            print('  *** Failed!')
        else:
            print ('*** The %s is on' % (model))            # get sample file name

            dimaxInit(global_PVs, variableDict)            
            dimaxTest(global_PVs, variableDict)
            
            fname = global_PVs['HDF1_FileName'].get(as_string=True)
            print(' ')
            print('  *** File name prefix: %s' % fname)
            
            dimaxSet2D(global_PVs, variableDict, fname)

            dimaxAcquisition2D(global_PVs, variableDict)

            proj_time = variableDict['ExposureTime'] * variableDict['Projections']
            print('  *** Total projection time: %s s' % str(proj_time))            
            print('  *** Total memory dump time: %s s' % str((time.time() - tic) - proj_time))
            time.sleep(2)

            dimaxAcquireFlat2D(global_PVs, variableDict)  

            close_shutters(global_PVs, variableDict)
            dimaxAcquireDark2D(global_PVs, variableDict)

            print(' ')
            print('  *** Total scan time: %s minutes' % str((time.time() - tic)/60.))
            print('  *** Data file: %s' % global_PVs['HDF1_FullFileName_RBV'].get(as_string=True))
            print('  *** Done!')

    except  KeyError:
        print('  *** Some PV assignment failed!')
        pass

     
if __name__ == '__main__':
    main()











