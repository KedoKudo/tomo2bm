import time
import epics
import numpy as np
import os
import Tkinter
import tkMessageBox as mbox

from pco_lib import *


global variableDict

variableDict = {
        'ExposureTime': 0.040,
        'SlewSpeed': 1.0,           # to use this as default value comment the calc_blur_pixel(global_PVs, variableDict) function below
        'AcclRot': 1.0,
        'SampleRotStart': 0.0,
        'SampleRotEnd': 180.0,
        'Projections': 750,
        'SampleXIn': -0.404,        # to use X change the sampleInOutVertical = False in PCO_lib.py
        'SampleXOut': 0.7,
        # 'SampleYIn': 0,             # default white field is taken moving the Y
        # 'SampleYOut': -4,
        'FurnaceYIn': 0.0,          # to use X change the sampleInOutVertical = False in PCO_lib.py
        'FurnaceYOut': 48.0,
        'StartSleep_s': 180,        # wait time (s) before starting data collection; usefull to stabilize sample environment 
        'roiSizeX': 1280, 
        'roiSizeY': 2160,       
        'NumWhiteImages': 20,
        'NumDarkImages': 20,
        'ShutterOpenDelay': 0.00,
        'IOC_Prefix': 'PCOIOC3:',   # options: 1. DIMAX: 'PCOIOC2:', 2. EDGE: 'PCOIOC3:'
        'FileWriteMode': 'Stream',
        'CCD_Readout': 0.05,
        'Station': '2-BM-A',
        'SampleMoveEnabled': False, # False to freeze sample motion during white field data collection
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
            print('*** The Point Grey Camera with EPICS IOC prefix %s is down' % variableDict['IOC_Prefix'])
            print('  *** Failed!')
        else:
            print ('*** The %s is on' % (model))            # get sample file name
            start = 0
            end = 41
            number_of_steps = 1

            # calling calc_blur_pixel() to replace the default 'SlewSpeed' with its optinal value 
            blur_pixel, rot_speed, scan_time = calc_blur_pixel(global_PVs, variableDict)
            variableDict['SlewSpeed'] = rot_speed
           
            print ('*** First data set ***')
            variableDict['SampleMoveEnabled'] = True
            print('*** Sample Move Enabled: %s ' % variableDict['SampleMoveEnabled'])                
            time.sleep(.5)
            edgeInit(global_PVs, variableDict)     
            edgeTest(global_PVs, variableDict)
            setPSO(global_PVs, variableDict)

            fname = global_PVs['HDF1_FileName'].get(as_string=True)
            print('  *** File name: %s' % fname)
            edgeSet(global_PVs, variableDict, fname)

            open_shutters(global_PVs, variableDict)
            edgeAcquireFlat(global_PVs, variableDict) 
            edgeAcquisition(global_PVs, variableDict)
            close_shutters(global_PVs, variableDict)
            edgeAcquireDark(global_PVs, variableDict) 

            print('          *** Wait (s): %s ' % str(variableDict['StartSleep_s']))
            time.sleep(variableDict['StartSleep_s']) 
            
            variableDict['SampleMoveEnabled'] = False
            for i in np.arange(start, end, number_of_steps):
                print('*** Sample Move Enabled: %s ' % variableDict['SampleMoveEnabled'])                
                print ('*** Data set number: %s of %s ' % (i, number_of_steps))
                time.sleep(.5)
                edgeInit(global_PVs, variableDict)     
                edgeTest(global_PVs, variableDict)
                setPSO(global_PVs, variableDict)

                fname = global_PVs['HDF1_FileName'].get(as_string=True)
                print('  *** File name: %s' % fname)
                edgeSet(global_PVs, variableDict, fname)

                open_shutters(global_PVs, variableDict)
                edgeAcquisition(global_PVs, variableDict)
                edgeAcquireFlat(global_PVs, variableDict) 
                close_shutters(global_PVs, variableDict)
                edgeAcquireDark(global_PVs, variableDict) 

                print('          *** Wait (s): %s ' % str(variableDict['StartSleep_s']))
                time.sleep(variableDict['StartSleep_s']) 

            global_PVs['Motor_FurnaceY'].put(str(variableDict['FurnaceYOut']), wait=True, timeout=1000.0)

            print(' ')
            print('  *** Total scan time: %s minutes' % str((time.time() - tic)/60.))
            print('  *** Data file: %s' % global_PVs['HDF1_FullFileName_RBV'].get(as_string=True))
            print('  *** Done!')

    except  KeyError:
        print('  *** Some PV assignment failed!')
        pass

   
    
    
if __name__ == '__main__':
    main()
