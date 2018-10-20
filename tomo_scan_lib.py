'''
    Tomo Scan Lib for Sector 2-BM
    
'''
from __future__ import print_function

import sys
import json
import time
from epics import PV
import h5py
import shutil
import os
import imp
import traceback
import math
import signal

ShutterA_Open_Value = 1
ShutterA_Close_Value = 0
ShutterB_Open_Value = 1
ShutterB_Close_Value = 0

FrameTypeData = 0
FrameTypeDark = 1
FrameTypeWhite = 2

DetectorIdle = 0
DetectorAcquire = 1

UseShutterA = False
UseShutterB = True

STATION = '2-BM-B' # or '2-BM-A'

EPSILON = 0.1

TESTING_MODE = False

if TESTING_MODE == True:
    UseShutterA = False
    UseShutterB = False

Recursive_Filter_Type = 'RecursiveAve'

if UseShutterA is False and UseShutterB is False:
    print('### WARNING: shutters are deactivted during the scans !!!!')


def update_variable_dict(variableDict):
    argDic = {}
    if len(sys.argv) > 1:
        strArgv = sys.argv[1]
        argDic = json.loads(strArgv)
    ##print('orig variable dict', variableDict)
    for k,v in argDic.iteritems():
        variableDict[k] = v
    ##print('new variable dict', variableDict)


def wait_pv(pv, wait_val, max_timeout_sec=-1):
#wait on a pv to be a value until max_timeout (default forever)

    #print('wait_pv(', pv.pvname, wait_val, max_timeout_sec, ')')
    
    # delay for pv to change
    time.sleep(.01)
    startTime = time.time()
    while(True):
        pv_val = pv.get()
        if type(pv_val) == float:
            if abs(pv_val - wait_val) < EPSILON:
                return True
        if (pv_val != wait_val):
            if max_timeout_sec > -1:
                curTime = time.time()
                diffTime = curTime - startTime
                if diffTime >= max_timeout_sec:
                    #print('wait_pv(', pv.pvname, wait_val, max_timeout_sec, ') reached max timeout. Return False')
                    return False
            time.sleep(.01)
        else:
            return True


def init_general_PVs(global_PVs, variableDict):

    # shutter pv's
    global_PVs['ShutterA_Open'] = PV('2bma:A_shutter:open.VAL')
    global_PVs['ShutterA_Close'] = PV('2bma:A_shutter:close.VAL')
    global_PVs['ShutterA_Move_Status'] = PV('PA:02BM:STA_A_FES_OPEN_PL')
    global_PVs['ShutterB_Open'] = PV('2bma:B_shutter:open.VAL')
    global_PVs['ShutterB_Close'] = PV('2bma:B_shutter:close.VAL')
    global_PVs['ShutterB_Move_Status'] = PV('PA:02BM:STA_B_SBS_OPEN_PL')

    if STATION == '2-BM-A':
            print('*** Running in station A:')
            # Set sample stack motor pv's:
            global_PVs['Motor_SampleX'] = PV('2bma:m49.VAL')
            global_PVs['Motor_SampleY'] = PV('2bma:m20.VAL')
            global_PVs['Motor_SampleRot'] = PV('2bma:m82.VAL')  
            global_PVs['Motor_SampleRot_Stop'] = PV('2bma:m82.STOP') # Aerotech ABR-250
            global_PVs['Motor_Sample_Top_X'] = PV('2bma:m50.VAL')
            global_PVs['Motor_Sample_Top_Z'] = PV('2bma:m51.VAL') 
            # Set FlyScan
            global_PVs['Fly_ScanDelta'] = PV('2bma:PSOFly2:scanDelta')
            global_PVs['Fly_StartPos'] = PV('2bma:PSOFly2:startPos')
            global_PVs['Fly_EndPos'] = PV('2bma:PSOFly2:endPos')
            global_PVs['Fly_SlewSpeed'] = PV('2bma:PSOFly2:slewSpeed')
            global_PVs['Fly_Taxi'] = PV('2bma:PSOFly2:taxi')
            global_PVs['Fly_Run'] = PV('2bma:PSOFly2:fly')
            global_PVs['Fly_ScanControl'] = PV('2bma:PSOFly2:scanControl')
            global_PVs['Fly_Calc_Projections'] = PV('2bma:PSOFly2:numTriggers')
            global_PVs['Theta_Array'] = PV('2bma:PSOFly2:motorPos.AVAL')
            
    else: # 2-BM-B
            print('*** Running in station B:')
            # Sample stack motor pv's:
            global_PVs['Motor_SampleX'] = PV('2bmb:m63.VAL')
            global_PVs['Motor_SampleY'] = PV('2bmb:m57.VAL') 
            global_PVs['Motor_SampleRot'] = PV('2bmb:m100.VAL') # Aerotech ABR-150
            global_PVs['Motor_SampleRot_Stop'] = PV('2bmb:m100.STOP') 
            global_PVs['Motor_Sample_Top_X'] = PV('2bmb:m76.VAL') 
            global_PVs['Motor_Sample_Top_Z'] = PV('2bmb:m77.VAL')

            # Set CCD stack motor PVs:
            global_PVs['Motor_CCD_Z'] = PV('2bmb:m31.VAL')

            # Set FlyScan
            global_PVs['Fly_ScanDelta'] = PV('2bmb:PSOFly:scanDelta')
            global_PVs['Fly_StartPos'] = PV('2bmb:PSOFly:startPos')
            global_PVs['Fly_EndPos'] = PV('2bmb:PSOFly:endPos')
            global_PVs['Fly_SlewSpeed'] = PV('2bmb:PSOFly:slewSpeed')
            global_PVs['Fly_Taxi'] = PV('2bmb:PSOFly:taxi')
            global_PVs['Fly_Run'] = PV('2bmb:PSOFly:fly')
            global_PVs['Fly_ScanControl'] = PV('2bmb:PSOFly:scanControl')
            global_PVs['Fly_Calc_Projections'] = PV('2bmb:PSOFly:numTriggers')
            global_PVs['Theta_Array'] = PV('2bmb:PSOFly:motorPos.AVAL')

    # detector pv's
    if ((variableDict['IOC_Prefix'] == '2bmbPG3:') or (variableDict['IOC_Prefix'] == '2bmbSP1:')): 
    
        # init Point Grey PV's
        # general PV's
        global_PVs['Cam1_SerialNumber'] = PV(variableDict['IOC_Prefix'] + 'cam1:SerialNumber_RBV')
        global_PVs['Cam1_ImageMode'] = PV(variableDict['IOC_Prefix'] + 'cam1:ImageMode')
        global_PVs['Cam1_ArrayCallbacks'] = PV(variableDict['IOC_Prefix'] + 'cam1:ArrayCallbacks')
        global_PVs['Cam1_AcquirePeriod'] = PV(variableDict['IOC_Prefix'] + 'cam1:AcquirePeriod')
        global_PVs['Cam1_TriggerMode'] = PV(variableDict['IOC_Prefix'] + 'cam1:TriggerMode')
        global_PVs['Cam1_SoftwareTrigger'] = PV(variableDict['IOC_Prefix'] + 'cam1:SoftwareTrigger')
        global_PVs['Cam1_AcquireTime'] = PV(variableDict['IOC_Prefix'] + 'cam1:AcquireTime')
        global_PVs['Cam1_FrameType'] = PV(variableDict['IOC_Prefix'] + 'cam1:FrameType')
        global_PVs['Cam1_NumImages'] = PV(variableDict['IOC_Prefix'] + 'cam1:NumImages')
        global_PVs['Cam1_Acquire'] = PV(variableDict['IOC_Prefix'] + 'cam1:Acquire')
        global_PVs['Cam1_AttributeFile'] = PV(variableDict['IOC_Prefix'] + 'cam1:NDAttributesFile')
        global_PVs['Cam1_FrameTypeZRST'] = PV(variableDict['IOC_Prefix'] + 'cam1:FrameType.ZRST')
        global_PVs['Cam1_FrameTypeONST'] = PV(variableDict['IOC_Prefix'] + 'cam1:FrameType.ONST')
        global_PVs['Cam1_FrameTypeTWST'] = PV(variableDict['IOC_Prefix'] + 'cam1:FrameType.TWST')
        global_PVs['Cam1_Display'] = PV(variableDict['IOC_Prefix'] + 'image1:EnableCallbacks')


        # hdf5 writer PV's
        global_PVs['HDF1_AutoSave'] = PV(variableDict['IOC_Prefix'] + 'HDF1:AutoSave')
        global_PVs['HDF1_DeleteDriverFile'] = PV(variableDict['IOC_Prefix'] + 'HDF1:DeleteDriverFile')
        global_PVs['HDF1_EnableCallbacks'] = PV(variableDict['IOC_Prefix'] + 'HDF1:EnableCallbacks')
        global_PVs['HDF1_BlockingCallbacks'] = PV(variableDict['IOC_Prefix'] + 'HDF1:BlockingCallbacks')
        global_PVs['HDF1_FileWriteMode'] = PV(variableDict['IOC_Prefix'] + 'HDF1:FileWriteMode')
        global_PVs['HDF1_NumCapture'] = PV(variableDict['IOC_Prefix'] + 'HDF1:NumCapture')
        global_PVs['HDF1_Capture'] = PV(variableDict['IOC_Prefix'] + 'HDF1:Capture')
        global_PVs['HDF1_Capture_RBV'] = PV(variableDict['IOC_Prefix'] + 'HDF1:Capture_RBV')
        global_PVs['HDF1_FileName'] = PV(variableDict['IOC_Prefix'] + 'HDF1:FileName')
        global_PVs['HDF1_FullFileName_RBV'] = PV(variableDict['IOC_Prefix'] + 'HDF1:FullFileName_RBV')
        global_PVs['HDF1_FileTemplate'] = PV(variableDict['IOC_Prefix'] + 'HDF1:FileTemplate')
        global_PVs['HDF1_ArrayPort'] = PV(variableDict['IOC_Prefix'] + 'HDF1:NDArrayPort')
        global_PVs['HDF1_NextFile'] = PV(variableDict['IOC_Prefix'] + 'HDF1:FileNumber')
        global_PVs['HDF1_XMLFileName'] = PV(variableDict['IOC_Prefix'] + 'HDF1:XMLFileName')
                                                                      
        # proc1 PV's
        global_PVs['Image1_Callbacks'] = PV(variableDict['IOC_Prefix'] + 'image1:EnableCallbacks')
        global_PVs['Proc1_Callbacks'] = PV(variableDict['IOC_Prefix'] + 'Proc1:EnableCallbacks')
        global_PVs['Proc1_ArrayPort'] = PV(variableDict['IOC_Prefix'] + 'Proc1:NDArrayPort')
        global_PVs['Proc1_Filter_Enable'] = PV(variableDict['IOC_Prefix'] + 'Proc1:EnableFilter')
        global_PVs['Proc1_Filter_Type'] = PV(variableDict['IOC_Prefix'] + 'Proc1:FilterType')
        global_PVs['Proc1_Num_Filter'] = PV(variableDict['IOC_Prefix'] + 'Proc1:NumFilter')
        global_PVs['Proc1_Reset_Filter'] = PV(variableDict['IOC_Prefix'] + 'Proc1:ResetFilter')
        global_PVs['Proc1_AutoReset_Filter'] = PV(variableDict['IOC_Prefix'] + 'Proc1:AutoResetFilter')
        global_PVs['Proc1_Filter_Callbacks'] = PV(variableDict['IOC_Prefix'] + 'Proc1:FilterCallbacks')

    elif (variableDict['IOC_Prefix'] == 'PCOIOC3:'):
        global_PVs['Cam1_Acquire'] = PV(variableDict['IOC_Prefix'] + 'cam1:Acquire')   
        global_PVs['Cam1_AcquireTime'] = PV(variableDict['IOC_Prefix'] + 'cam1:AcquireTime')
        global_PVs['Cam1_AcquirePeriod'] = PV(variableDict['IOC_Prefix'] + 'cam1:AcquirePeriod')
        global_PVs['Cam1_NumImages'] = PV(variableDict['IOC_Prefix'] + 'cam1:NumImages')                              
        global_PVs['Cam1_ImageMode'] = PV(variableDict['IOC_Prefix'] + 'cam1:ImageMode')   
        global_PVs['Cam1_PCOTriggerMode'] = PV(variableDict['IOC_Prefix'] + 'cam1:pco_trigger_mode')
        global_PVs['Cam1_PCOReady2Acquire'] = PV(variableDict['IOC_Prefix'] + 'cam1:pco_ready2acquire')
        global_PVs['Cam1_PCOSetFrameRate'] = PV(variableDict['IOC_Prefix'] + 'cam1:pco_set_frame_rate')
        global_PVs['Cam1_PCOIsFrameRateMode'] = PV(variableDict['IOC_Prefix'] + 'cam1:pco_is_frame_rate_mode')
        
    
    if (variableDict['IOC_Prefix'] == '2bmbPG3:'):
        global_PVs['Cam1_FrameRateOnOff'] = PV(variableDict['IOC_Prefix'] + 'cam1:FrameRateOnOff')

    elif (variableDict['IOC_Prefix'] == '2bmbSP1:'):
        global_PVs['Cam1_FrameRateOnOff'] = PV(variableDict['IOC_Prefix'] + 'cam1:FrameRateEnable')
        global_PVs['Cam1_TriggerSource'] = PV(variableDict['IOC_Prefix'] + 'cam1:TriggerSource')
        global_PVs['Cam1_TriggerOverlap'] = PV(variableDict['IOC_Prefix'] + 'cam1:TriggerOverlap')

    elif (variableDict['IOC_Prefix'] == 'PCOIOC3:'):
        print('do nothing ...')
    
    else:
        print ('Detector %s is not defined' % variableDict['IOC_Prefix'])
        return            


def stop_scan(global_PVs, variableDict):
        print(' ')
        print('  *** Stop scan called!')
        global_PVs['Motor_SampleRot_Stop'].put(1)
        global_PVs['HDF1_Capture'].put(0)
        wait_pv(global_PVs['HDF1_Capture'], 0)
        reset_CCD(global_PVs, variableDict)
        reset_CCD(global_PVs, variableDict)


def reset_CCD(global_PVs, variableDict):
    if (variableDict['IOC_Prefix'] == '2bmbPG3:'):   
        global_PVs['Cam1_TriggerMode'].put('Internal', wait=True)    # 
        global_PVs['Cam1_TriggerMode'].put('Overlapped', wait=True)  # sequence Internal / Overlapped / internal because of CCD bug!!
        global_PVs['Cam1_TriggerMode'].put('Internal', wait=True)    #
        global_PVs['Proc1_Filter_Callbacks'].put( 'Every array' )
        global_PVs['Cam1_ImageMode'].put('Single', wait=True)
        global_PVs['Cam1_Display'].put(1)
        global_PVs['Cam1_Acquire'].put(DetectorAcquire); wait_pv(global_PVs['Cam1_Acquire'], DetectorAcquire, 2)
    elif (variableDict['IOC_Prefix'] == '2bmbSP1:'):   
        global_PVs['Cam1_TriggerMode'].put('Off', wait=True)    # 
        global_PVs['Proc1_Filter_Callbacks'].put( 'Every array' )
        global_PVs['Cam1_ImageMode'].put('Single', wait=True)
        global_PVs['Cam1_Display'].put(1)
        global_PVs['Cam1_Acquire'].put(DetectorAcquire); wait_pv(global_PVs['Cam1_Acquire'], DetectorAcquire, 2)
    elif (variableDict['IOC_Prefix'] == 'PCOIOC3:'):
        print("not done yet #####")   


def setup_detector(global_PVs, variableDict):

    # Set detectors
    if (variableDict['IOC_Prefix'] == '2bmbPG3:'):   
        # setup Point Grey PV's
        print(' ')
        print('  *** setup Point Grey')

        if STATION == '2-BM-A':
            global_PVs['Cam1_AttributeFile'].put('fastDetectorAttributes.xml')
            global_PVs['HDF1_XMLFileName'].put('fastHDFLayout.xml')           
        else: # Mona (B-station)
            global_PVs['Cam1_AttributeFile'].put('monaDetectorAttributes.xml', wait=True) 
            global_PVs['HDF1_XMLFileName'].put('monaLayout.xml', wait=True) 

        if variableDict.has_key('Display_live'):
            print('** disable live display')
            global_PVs['Cam1_Display'].put( int( variableDict['Display_live'] ) )
        global_PVs['Cam1_ImageMode'].put('Multiple')
        global_PVs['Cam1_ArrayCallbacks'].put('Enable')
        #global_PVs['Image1_Callbacks'].put('Enable')
        global_PVs['Cam1_AcquirePeriod'].put(float(variableDict['ExposureTime']))
        global_PVs['Cam1_AcquireTime'].put(float(variableDict['ExposureTime']))
        # if we are using external shutter then set the exposure time
        global_PVs['Cam1_FrameRateOnOff'].put(0)

        wait_time_sec = int(variableDict['ExposureTime']) + 5
        global_PVs['Cam1_TriggerMode'].put('Overlapped', wait=True) #Ext. Standard
        global_PVs['Cam1_NumImages'].put(1, wait=True)
        global_PVs['Cam1_Acquire'].put(DetectorAcquire)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorAcquire, 2)
        global_PVs['Cam1_SoftwareTrigger'].put(1)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle, wait_time_sec)
        global_PVs['Cam1_Acquire'].put(DetectorAcquire)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorAcquire, 2)
        global_PVs['Cam1_SoftwareTrigger'].put(1)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle, wait_time_sec)
        print('  *** setup Point Grey: Done!')

    elif (variableDict['IOC_Prefix'] == '2bmbSP1:'):
        # setup Point Grey PV's
        print(' ')
        print('  *** setup FLIR camera')

        if STATION == '2-BM-A':
            global_PVs['Cam1_AttributeFile'].put('fastDetectorAttributes.xml')
            global_PVs['HDF1_XMLFileName'].put('fastHDFLayout.xml')           
        else: # Mona (B-station)
            global_PVs['Cam1_AttributeFile'].put('monaDetectorAttributes.xml', wait=True) 
            global_PVs['HDF1_XMLFileName'].put('monaLayout.xml', wait=True) 

        if variableDict.has_key('Display_live'):
            print('** disable live display')
            global_PVs['Cam1_Display'].put( int( variableDict['Display_live'] ) )
        global_PVs['Cam1_ImageMode'].put('Multiple')
        global_PVs['Cam1_ArrayCallbacks'].put('Enable')
        #global_PVs['Image1_Callbacks'].put('Enable')
        global_PVs['Cam1_AcquirePeriod'].put(float(variableDict['ExposureTime']))
        global_PVs['Cam1_AcquireTime'].put(float(variableDict['ExposureTime']))
        # if we are using external shutter then set the exposure time
        global_PVs['Cam1_FrameRateOnOff'].put(0)

        wait_time_sec = int(variableDict['ExposureTime']) + 5
        global_PVs['Cam1_TriggerMode'].put('On', wait=True)
        global_PVs['Cam1_TriggerSource'].put('Line2', wait=True)
        global_PVs['Cam1_TriggerOverlap'].put('ReadOut', wait=True) 
        global_PVs['Cam1_NumImages'].put(1, wait=True)
        global_PVs['Cam1_Acquire'].put(DetectorAcquire)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorAcquire, 2)
        global_PVs['Cam1_SoftwareTrigger'].put(1)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle, wait_time_sec)
        global_PVs['Cam1_Acquire'].put(DetectorAcquire)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorAcquire, 2)
        global_PVs['Cam1_SoftwareTrigger'].put(1)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle, wait_time_sec)
        print('  *** setup FLIR camera: Done!')
    
    elif (variableDict['IOC_Prefix'] == 'PCOIOC3:'):
        # setup Point PCO Edge PV's
        print(' ')
        print('  *** setup POC Edge camera')
        if STATION == '2-BM-A':
            global_PVs['Cam1_AttributeFile'].put('DynaMCTDetectorAttributes.xml')
            global_PVs['HDF1_XMLFileName'].put('DynaMCTHDFLayout.xml')           
        else: # Space holder for now, next time PCO runs in 2-BM-B create a set of new xml files
            global_PVs['Cam1_AttributeFile'].put('DynaMCTDetectorAttributes.xml')
            global_PVs['HDF1_XMLFileName'].put('DynaMCTHDFLayout.xml')           

        wait_time_sec = int(variableDict['ExposureTime']) + 5
        global_PVs['Cam1_ImageMode'].put("Multiple", wait=True)  
        #global_PVs['Cam1_ArrayCallbacks'].put('Enable')
        global_PVs['Cam1_AcquirePeriod'].put(float(variableDict['ExposureTime']))
        global_PVs['Cam1_AcquireTime'].put(float(variableDict['ExposureTime']))
        global_PVs['Cam1_NumImages'].put(1, wait=True)
        global_PVs['Cam1_Acquire'].put(DetectorAcquire)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorAcquire, 2)
        global_PVs['Cam1_PCOTriggerMode'].put("Soft/Ext", wait=True)
        global_PVs['Cam1_PCOReady2Acquire'].put(0, wait=True)
        global_PVs['Cam1_PCOIsFrameRateMode'].put("DelayExp", wait=True)
        print('  *** setup PCO Edge: Done!')

    
    else:
        print ('Detector %s is not defined' % variableDict['IOC_Prefix'])
        return


def setup_frame_type(global_PVs, variableDict):
    global_PVs['Cam1_FrameTypeZRST'].put('/exchange/data')
    global_PVs['Cam1_FrameTypeONST'].put('/exchange/data_dark')
    global_PVs['Cam1_FrameTypeTWST'].put('/exchange/data_white')


def setup_hdf_writer(global_PVs, variableDict, fname=None):

    if (variableDict['IOC_Prefix'] == '2bmbPG3:') or (variableDict['IOC_Prefix'] == '2bmbSP1:'):   
        # setup Point Grey hdf writer PV's
        print('  ')
        print('  *** setup hdf_writer')
        setup_frame_type(global_PVs, variableDict)
        if variableDict.has_key('Recursive_Filter_Enabled'):
            if variableDict['Recursive_Filter_Enabled'] == 1:
                global_PVs['Proc1_Callbacks'].put('Enable')
                global_PVs['Proc1_Filter_Enable'].put('Disable')
                global_PVs['HDF1_ArrayPort'].put('PROC1')
                global_PVs['Proc1_Filter_Type'].put( Recursive_Filter_Type )
                global_PVs['Proc1_Num_Filter'].put( int( variableDict['Recursive_Filter_N_Images'] ) )
                global_PVs['Proc1_Reset_Filter'].put( 1 )
                global_PVs['Proc1_AutoReset_Filter'].put( 'Yes' )
                global_PVs['Proc1_Filter_Callbacks'].put( 'Array N only' )
            else:
                global_PVs['Proc1_Filter_Enable'].put('Disable')
                global_PVs['HDF1_ArrayPort'].put(global_PVs['Proc1_ArrayPort'].get())
        else:
            global_PVs['Proc1_Filter_Enable'].put('Disable')
            global_PVs['HDF1_ArrayPort'].put(global_PVs['Proc1_ArrayPort'].get())
        global_PVs['HDF1_AutoSave'].put('Yes')
        global_PVs['HDF1_DeleteDriverFile'].put('No')
        global_PVs['HDF1_EnableCallbacks'].put('Enable')
        global_PVs['HDF1_BlockingCallbacks'].put('No')

        if variableDict.has_key('ProjectionsPerRot'):
            totalProj = int(variableDict['PreDarkImages']) + int(variableDict['PreWhiteImages']) + \
                       (int(variableDict['Projections']) * int(variableDict['ProjectionsPerRot'])) + \
                        int(variableDict['PostDarkImages']) + int(variableDict['PostWhiteImages'])
        else:
            totalProj = int(variableDict['PreDarkImages']) + int(variableDict['PreWhiteImages']) + \
                        int(variableDict['Projections']) + int(variableDict['PostDarkImages']) + \
                        int(variableDict['PostWhiteImages'])

        global_PVs['HDF1_NumCapture'].put(totalProj)
        global_PVs['HDF1_FileWriteMode'].put(str(variableDict['FileWriteMode']), wait=True)
        if fname is not None:
            global_PVs['HDF1_FileName'].put(fname)
        global_PVs['HDF1_Capture'].put(1)
        wait_pv(global_PVs['HDF1_Capture'], 1)
        print('  *** setup Point Grey hdf_writer: Done!')
    elif (variableDict['IOC_Prefix'] == 'PCOIOC3:'):
        print('######')
    else:
        print ('Detector %s is not defined' % variableDict['IOC_Prefix'])
        return

####
def capture_multiple_projections(global_PVs, variableDict, num_proj, frame_type):
    wait_time_sec = int(variableDict['ExposureTime']) + 5
    global_PVs['Cam1_ImageMode'].put('Multiple')
    global_PVs['Cam1_FrameType'].put(frame_type)

    if (variableDict['IOC_Prefix'] == '2bmbPG3:'):
        global_PVs['Cam1_TriggerMode'].put('Overlapped')
    elif (variableDict['IOC_Prefix'] == 'PCOIOC3:'):
        global_PVs['Cam1_TriggerMode'].put('Soft/Ext')
        
    global_PVs['Cam1_NumImages'].put(1)
    for i in range(int(num_proj)):
        global_PVs['Cam1_Acquire'].put(DetectorAcquire)
        time.sleep(0.1)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorAcquire, 2)
        time.sleep(0.1)
        global_PVs['Cam1_SoftwareTrigger'].put(1, wait=True)
        time.sleep(0.1)
        wait_pv(global_PVs['Cam1_Acquire'], DetectorIdle, wait_time_sec)
        time.sleep(0.1)


def move_sample_in(global_PVs, variableDict):
    print(' ')
    print('  *** horizontal move_sample_in')
    global_PVs['Motor_SampleX'].put(float(variableDict['SampleXIn']), wait=True)
    if wait_pv(global_PVs['Motor_SampleX'], float(variableDict['SampleXIn']), 60) == False:
        print('Motor_SampleX did not move in properly')
        print (global_PVs['Motor_SampleX'].get())
        print('\r\n\r\n')
    print('  *** horizontal move_sample_in: Done!')


def move_sample_out(global_PVs, variableDict):
    print(' ')
    print('  *** horizontal move_sample_out')
    global_PVs['Motor_SampleX'].put(float(variableDict['SampleXOut']), wait=True)
    if False == wait_pv(global_PVs['Motor_SampleX'], float(variableDict['SampleXOut']), 60):
        print('Motor_SampleX did not move out properly')
        print (global_PVs['Motor_SampleX'].get())
        print('\r\n\r\n')
    print('  *** horizontal move_sample_out: Done!')


def open_shutters(global_PVs, variableDict):
    print(' ')
    print('  *** open_shutters')
    if UseShutterA is True:
        global_PVs['ShutterA_Open'].put(1, wait=True)
        wait_pv(global_PVs['ShutterA_Move_Status'], ShutterA_Open_Value)
        time.sleep(3)
    if UseShutterB is True:
        global_PVs['ShutterB_Open'].put(1, wait=True)
        wait_pv(global_PVs['ShutterB_Move_Status'], ShutterB_Open_Value)
    print('  *** open_shutters: Done!')


def close_shutters(global_PVs, variableDict):
    print(' ')
    print('  *** close_shutters')
    if UseShutterA is True:
        global_PVs['ShutterA_Close'].put(1, wait=True)
        wait_pv(global_PVs['ShutterA_Move_Status'], ShutterA_Close_Value)
    if UseShutterB is True:
        global_PVs['ShutterB_Close'].put(1, wait=True)
        wait_pv(global_PVs['ShutterB_Move_Status'], ShutterB_Close_Value)
    print('  *** close_shutters: Done!')


def add_theta(global_PVs, variableDict, theta_arr):
    print(' ')
    print('  *** add_theta')
    fullname = global_PVs['HDF1_FullFileName_RBV'].get(as_string=True)
    try:
        hdf_f = h5py.File(fullname, mode='a')
        if theta_arr is not None:
            theta_ds = hdf_f.create_dataset('/exchange/theta', (len(theta_arr),))
            theta_ds[:] = theta_arr[:]
        hdf_f.close()
        print('  *** add_theta: Done!')
    except:
        traceback.print_exc(file=sys.stdout)
        print('  *** add_theta: Failed accessing:', fullname)
