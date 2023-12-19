 # -*- coding: utf-8 -*-
# !/usr/bin/python

import sys
import os.path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import xlsxwriter


COLUMN_NAME_LIST = ["周期号", "速传1速度", "速传2速度", "加速度速度", "对端速度", "表决速度",
                    "速传1速度-速传2速度", "速传1速度-加速度速度", "速传1速度-对端速度",
                    "速传2速度-加速度速度", "速传2速度-对端速度",
                    "加速度速度-对端速度"]

class SpeedInfo:
    name = None   #名称
    cycNum = 0    #周期号
    speedSym = 0  #加速或减速
    speedVal = 0  #速度值
    accSym   = 0  #加速度加速或减速
    accVal   = 0  #加速度值
    impactSym = 0 #冲击率
    impactVal = 0 #冲击率

    def __init__(self, name, cycNum, speedSym, speedVal, accSym, accVal, impactSym, impactVal):
        self.name = name
        self.cycNum = cycNum
        self.speedSym = speedSym
        self.speedVal = speedVal
        self.accSym = accSym
        self.accVal = accVal
        self.impactSym = impactSym
        self.impactVal = impactVal


'''
读取文件
'''       
def get_info_from_text(filePath:str):
    allValidInfoList = []  # 整个文件每周期的有效数据
    onePeriodLogList = []  # 一周期的有效数据
    featureStrList = ["SpdAvPc2", "AccelerBa", "OppSpdInfo", "SpeedDirValidCheck"]

    if os.path.exists(filePath):
        with open(filePath, "r") as fp:
            isFindStartFlag = False
            while True:
                line = None
                line = fp.readline()

                if line:
                    if "End(" in line and ")" in line and isFindStartFlag == False:
                        isFindStartFlag = True
                        onePeriodLogList = []  # 需要
                        continue

                    if isFindStartFlag:
                        for featureStr in featureStrList:
                            if featureStr in line:
                                onePeriodLogList.append(line)

                        if "End(" in line and ")" in line:
                            onePeriodLogList.append(line)
                            allValidInfoList.append(onePeriodLogList)           
                            isFindStartFlag = False
                            #print(onePeriodLogList)            
                else:
                    break
    else:
        print("file not exist %s" % filePath)

    return allValidInfoList


"""
抓取SDU数据
"""
def seize_sdu_info(lineStr:str):
    spdVal = int(lineStr[lineStr.index("V:") + len("V:"): lineStr.index("Acc:")])

    accInfo = lineStr[lineStr.index("Acc:") + len("Acc:"): lineStr.index("Impact:")].split(" ")
    accSym = int(accInfo[0], 16)
    accVal = int(accInfo[1])
    
    impactInfo = lineStr[lineStr.index("Impact:") + len("Impact:"): lineStr.index("Err:")].split(" ")
    impactSym = int(impactInfo[0], 16)
    impactVal = int(impactInfo[1])

    #print("%d %d %d %d %d" % (spdVal, accSym, accVal, impactSym, impactVal))
    return spdVal, accSym, accVal, impactSym, impactVal


'''
抓取加速度计数据
'''
def seize_acc_info(lineStr:str):
    spdInfo = lineStr[lineStr.index("AccelerBa:S:") + len("AccelerBa:S:"): lineStr.index("Tag:")].split(" ")

    spdVal = int(spdInfo[1])  # 速度
    accVal = int(spdInfo[3])  # 加速度

    return spdVal, accVal


"""
抓取对端速度
"""
def seize_opp_info(lineStr:str):
    spdInfo = lineStr[lineStr.index("OppSpdInfo:") + len("OppSpdInfo:"): -1].split(",")

    spdVal = int(spdInfo[1])    # 速度
    accVal = int(spdInfo[4])    # 加速度
    impactVal = int(spdInfo[6]) # 冲击率

    return spdVal, accVal, impactVal
    

"""
抓取表决速度
"""
def seize_vote_info(lineStr:str):
    spdInfo = lineStr[lineStr.index("v:") + len("v:"): -1].split(" ")

    spdVal = int(spdInfo[0])    # 速度

    return spdVal

'''
获取一周内的速度信息
'''
def get_spd_info(periodInfos:list):
    existNum = 0
    periodNum = 0  # 周期号
    for line in periodInfos:
        try:
            if "SpdAvPc2" in line:
                existNum = existNum + 1
            if "End(" in line and ")--" in line:
                periodNum = int(line[line.index("End(")+len("End(") :line.index(')--')])
        except:
            print(line)
    
    sdu1, sdu2, acc, opp, vote = None, None, None, None, None

    # 确保速传信息出现2次
    if 2 == existNum:
        isSdu1 = False
        for line in periodInfos:
            if "SpdAvPc2" in line and False == isSdu1:
                # 速传1
                spdVal, accSym, accVal, impactSym, impactVal = seize_sdu_info(line)
                sdu1 = SpeedInfo("SDU1", periodNum, 0, spdVal, accSym, accVal, impactSym, impactVal)
                isSdu1 = True

                continue

            if "SpdAvPc2" in line and True == isSdu1:
                # 速传2
                spdVal, accSym, accVal, impactSym, impactVal = seize_sdu_info(line)
                sdu2 = SpeedInfo("SDU2", periodNum, 0, spdVal, accSym, accVal, impactSym, impactVal)
                isSdu1 = False

                continue

            if "AccelerBa" in line:
                # 加速度计
                spdVal, accVal = seize_acc_info(line)
                acc = SpeedInfo("ACC", periodNum, 0, spdVal, 0, accVal, 0, 0)

                continue

            if "OppSpdInfo" in line:
                # 等待端发至对端的速度
                spdVal, accVal, impactVal = seize_opp_info(line)
                opp = SpeedInfo("OPP", periodNum, 0, spdVal, 0, accVal, 0, impactVal)

                continue

            if "SpeedDirValidCheck:" in line:
                spdVal = seize_vote_info(line)
                vote = SpeedInfo("VOTE", periodNum, 0, spdVal, 0, 0, 0, 0)

                continue

    return sdu1, sdu2, acc, opp, vote
    

"""
创建文件夹和文件
"""
def create_folder_file(fileAbsPath:str):
    if not os.path.exists(fileAbsPath):
        foldPath = os.path.dirname(fileAbsPath)
        if not os.path.exists(foldPath):
            os.makedirs(foldPath, mode=0o777)  # 递归创建文件夹
        
        if os.access(foldPath, os.W_OK):
            #os.path.basename(fileAbsPath)
            writer = pd.ExcelWriter(fileAbsPath, engine='xlsxwriter')
            writer.close()
            os.chmod(fileAbsPath, 0o777)
        else:
            print("当前用户没有目录创建权限:%s" % (fileAbsPath))
"""
处理日志
["周期号", "速传1速度", "速传2速度", "加速度速度", "对端速度", "表决速度",
                    "速传1速度-速传2速度", "速传1速度-加速度速度", "速传1速度-对端速度",
                    "速传2速度-加速度速度", "速传2速度-对端速度",
                    "加速度速度-对端速度"]
"""
def handle_log(logName:str):
    cur_py_dir = os.path.dirname(os.path.abspath(__file__))
    cur_log_dir = cur_py_dir + "\\" + logName

    allValidInfoList = get_info_from_text(cur_log_dir)
    
    sdu1sList = []
    for periodInfo in allValidInfoList:
        if len(periodInfo) == 6:  # 挑选正确的周期日志数据，用行数过滤
            rowDataList = []
            sdu1, sdu2, acc, opp, vote = None, None, None, None, None
            sdu1, sdu2, acc, opp, vote = get_spd_info(periodInfo)

            rowDataList = [sdu1.cycNum, sdu1.speedVal, sdu2.speedVal, acc.speedVal, opp.speedVal, vote.speedVal,
                           sdu1.speedVal - sdu2.speedVal, sdu1.speedVal - acc.speedVal, sdu1.speedVal - opp.speedVal,
                           sdu2.speedVal - acc.speedVal, sdu2.speedVal - opp.speedVal, 
                           acc.speedVal - opp.speedVal]
            
            sdu1sList.append(rowDataList)


    # 写文件
    df_out = pd.DataFrame(sdu1sList, columns = COLUMN_NAME_LIST)
    if not df_out.empty:
        outXlsxPath = cur_py_dir + "\\" + "Out" + "\\result.xlsx"
        create_folder_file(outXlsxPath) 

        if os.path.exists(outXlsxPath):
            with pd.ExcelWriter(outXlsxPath, mode = 'w') as writer:
                df_out.to_excel(writer, sheet_name = logName, header=True, index=False, index_label=None)

    #plot_figure(sdu1sList)

def plot_figure(spdValList:list):
    xs = np.arange(len(spdValList))
    series1 = np.array(spdValList).astype(np.double)
    s1mask = np.isfinite(series1)

    plt.plot(xs[s1mask], series1[s1mask], linestyle='-')
    plt.show()


def main():

    handle_log("Info-2023-11-05-15.log")

    testList = ['SpdAvPc2:55 Dir:55 55 55 V:590 Acc:55 0 Impact:55 0 Err:0000\n', 
                'SpdAvPc2:55 Dir:55 55 55 V:590 Acc:55 0 Impact:55 0 Err:0000\n', 
                'AccelerBa:S:1 590 590 0 Tag:55 55 Out:1,55,590\n', 
                'OppSpdInfo:55,591,55,55,0,55,0,0.200000\n',
                'SpeedDirValidCheck:111 55 55 v:590 55 118\n', 
                '2023-11-05 15:44:49.6501 INFO: -----------------------------End(1971)--1.1.10\n']

    #seize_sdu_info(testList[0])
    #seize_acc_info(testList[2])
    #seize_opp_info(testList[3])
    #sdu1, sdu2, acc, opp = get_spd_info(testList)

    
    xs = np.arange(8)
    series1 = np.array([1, 3, 3, None, None, 5, 8, 9]).astype(np.double)
    s1mask = np.isfinite(series1)
    series2 = np.array([2, None, 5, None, 4, None, 3, 2]).astype(np.double)
    s2mask = np.isfinite(series2)

    plt.plot(xs[s1mask], series1[s1mask], linestyle='-')
    plt.plot(xs[s2mask], series2[s2mask], linestyle='-', marker='o')

    plt.show()
    

if __name__ == "__main__":
    main()
