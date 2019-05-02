#  Copyright (c) 2019.
#  This code has been produced by Zoran D. Grujic and by the knowledge found on The Internet.
#  Please feel free to ask me for permission to use my code in your own projects. It is for your own well fare!

import sys
import os
import glob
import serial  # conda install pyserial
import h5py  # conda install h5py
import sip  # pip install sip
import time
import numpy as np
import threading
import logging

import class_matplotlibWidget
import class_signal
from class_circularBuffer import CircularBuffer

import class_MySerial

from PyQt5 import QtCore  # conda install pyqt
# from PyQt5.QtCore import Qt
from PyQt5 import QtGui
from PyQt5 import QtWidgets


class MainForm(QtWidgets.QWidget):  # QMainWindow # QWidget
    name = "Etalon"
    due = False  # connection to Arduino DUE
    timer = False  # timer to read ports
    timerDisplayTime_ms = 1000
    data = False
    thread_readDue = False
    R_data = CircularBuffer(100)
    fi_data = CircularBuffer(100)
    X_data = CircularBuffer(100)
    Y_data = CircularBuffer(100)
    pos_data = CircularBuffer(100)
    time_ms_data = CircularBuffer(100)

    mode = "scan"  # scan ili lock

    # scan
    scanPoints = 50         # pts
    scanStart = 0           # 0-4095
    scanStop = 4095         # 0-4095
    scanIntegration_ms = 500   # ms
    scanPositions_int = []
    scanPosGen = None
    scanData = []

    def __init__(self, parent):
        super(MainForm, self).__init__()
        self.parent = parent  # parent je glavni okvir, odavde može da se utiče na njega
        self.scanPositions()

        # ------------------------------------------
        # Timers
        # ------------------------------------------

        # odložena promena parametara scan-a
        self.timerScanChange = QtCore.QTimer(self)  # make timer to belong to the MainForm class
        self.timerScanChange.setInterval(2000)
        self.timerScanChange.timeout.connect(self.scanChanged)
        self.timerScanChange.setSingleShot(True)

        # Timer za plot grafika
        self.timer = QtCore.QTimer(self)  # make timer to belong to the MainForm class
        self.timer.setInterval(self.timerDisplayTime_ms)
        self.timer.timeout.connect(self.displayNewData)

        # Timer za scan
        self.timerScan = QtCore.QTimer(self)  # make timer to belong to the MainForm class
        self.timerScan.setInterval(self.scanIntegration_ms)
        self.timerScan.timeout.connect(self.nextScanPoint)

        # ------------------------------------------
        # make controls
        # ------------------------------------------

        """
        self.serialPortLineEdit = QtWidgets.QLineEdit('', self)  # Serial port preview
        self.serialPortLineEdit.setReadOnly(True)        
        self.serialInputTextEdit = QtWidgets.QTextEdit()  # Serial port preview
        self.serialInputTextEdit.setReadOnly(True)
        self.serialInputTextEdit.setMinimumHeight(150)
        """

        self.portLabel = QtWidgets.QLabel("Port: ", self)
        self.portLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # self.portLabel.setFixedWidth(80)





        # -------------------------------------------
        # make tabs
        # -------------------------------------------
        self.tabs = QtWidgets.QTabWidget(self)
        self.tabScan = QtWidgets.QWidget()
        self.tabLock = QtWidgets.QWidget()

        # tab scan plots
        self.plotScanR = class_matplotlibWidget.MatplotlibWidget(20, 2, self.tabScan)
        self.plotScanR.xLabel = "pozicija (#)"
        self.plotScanR.yLabel = 'R (arb. u.)'
        self.plotScanR.line = 'o'

        self.plotScanfi = class_matplotlibWidget.MatplotlibWidget(20, 2, self.tabScan)
        self.plotScanfi.xLabel = "pozicija (#)"
        self.plotScanfi.yLabel = '$\phi$ ($^\circ$)'
        self.plotScanfi.line = 'o'

        # tab lock plots
        self.plotR = class_matplotlibWidget.MatplotlibWidget(20, 2, self.tabLock)
        # x = range(0, 100, 10)
        # y = [np.sin(xx / 10) for xx in x]
        self.plotR.xLabel = 'vreme (s)'
        self.plotR.yLabel = 'R (arb. u.)'
        self.plotR.line = '-'
        # self.plotR.plot(x, y)

        self.plotfi = class_matplotlibWidget.MatplotlibWidget(20, 2, self.tabLock)
        self.plotfi.xLabel = 'vreme (s)'
        self.plotfi.yLabel = '$\phi$ ($^\circ$)'
        self.plotfi.line = '-'

        # tab buttons
        self.startScanButton = QtWidgets.QPushButton("Počni scan", self.tabScan)
        self.startScanButton.clicked.connect(self.scanRun)
        self.startLockButton = QtWidgets.QPushButton("Zaključaj na rezonanci", self.tabLock)
        self.startLockButton.clicked.connect(self.stabilizacija)
        tt = "Pokreće algoritam zaključavanja rezonatora na izabranoj rezonanci..."
        self.startLockButton.setToolTip('<span style="color:#555555;">'+tt+'</span>')

        # tab inputs

        self.scanPointsLineEdit = QtWidgets.QLineEdit(str(self.scanPoints), self.tabScan)  # Koliko tačaka u scan-u
        self.scanPointsLineEdit.setValidator(QtGui.QIntValidator(10, 4096))
        self.scanPointsLineEdit.textChanged.connect(self.delayChange)
        tt = "Koliko tačaka će biti u snimljenom spektru?"
        self.scanPointsLineEdit.setToolTip('<span style="color:#555555;">' + tt + '</span>')

        self.scanStartQDoubleSpinBox = QtWidgets.QDoubleSpinBox(self.tabScan)  # Serial port preview
        self.scanStartQDoubleSpinBox.name = "ScanStart"
        self.scanStartQDoubleSpinBox.setValue(100 * self.scanStart/4095)
        self.scanStartQDoubleSpinBox.setRange(0, 100)
        self.scanStartQDoubleSpinBox.setSingleStep(100 / 4095)
        self.scanStartQDoubleSpinBox.setSuffix(" %")
        self.scanStartQDoubleSpinBox.setDecimals(3)
        self.scanStartQDoubleSpinBox.valueChanged.connect(self.delayChange)
        tt = "Od koje tačke počinje snimanje spektra?"
        self.scanStartQDoubleSpinBox.setToolTip('<span style="color:#555555;">' + tt + '</span>')

        self.scanStopQDoubleSpinBox = QtWidgets.QDoubleSpinBox(self.tabScan)  # Serial port preview
        self.scanStopQDoubleSpinBox.name = "ScanStop"
        self.scanStopQDoubleSpinBox.setRange(0, 100)
        self.scanStopQDoubleSpinBox.setSingleStep(100 / 4095)
        self.scanStopQDoubleSpinBox.setValue(100 * self.scanStop/4095)
        self.scanStopQDoubleSpinBox.setSuffix(" %")
        self.scanStopQDoubleSpinBox.setDecimals(3)
        self.scanStopQDoubleSpinBox.valueChanged.connect(self.delayChange)
        tt = "Gde stati sa snimanjem spektra? Start i Stop definišu prozor u kome se snima spektar."
        self.scanStopQDoubleSpinBox.setToolTip('<span style="color:#555555;">' + tt + '</span>')

        self.scanIntegrationQDoubleSpinBox = QtWidgets.QSpinBox(self.tabScan)  # Serial port preview
        self.scanIntegrationQDoubleSpinBox.name = "ScanStop"
        self.scanIntegrationQDoubleSpinBox.setRange(200, 5000)
        self.scanIntegrationQDoubleSpinBox.setSingleStep(10)
        self.scanIntegrationQDoubleSpinBox.setValue(self.scanIntegration_ms)
        self.scanIntegrationQDoubleSpinBox.setSuffix(" ms")
        self.scanIntegrationQDoubleSpinBox.valueChanged.connect(self.delayChange)
        tt = "Koliko dugo snimati svaku tačku?"
        self.scanIntegrationQDoubleSpinBox.setToolTip('<span style="color:#555555;">' + tt + '</span>')

        # ------------------------------------------
        # set layout
        # ------------------------------------------
        self.setUIlayout()

        time.sleep(.2)

        while not self.connectDUE():
            pass

        self.portLabel.setText("Port: " + self.due.port)
        self.thread_readDue = threading.Thread(name='ReadDue', target=self.readDUE)
        self.thread_readDue.setDaemon(True)
        self.thread_readDue.start()

        self.timer.start()

    def scanChanged(self):
        """
        Update scan parameters
        """
        print("scanParametersChanged")
        # print(sender)
        # print("scanStartChanged: " + str(sender.value()))
        # print(str(self.percentTo4095(sender.value())))
        # return MainForm.percentTo4095(sender.value())

        if self.scanIntegrationQDoubleSpinBox.value() != self.scanIntegration_ms:
            self.scanIntegration_ms = self.scanIntegrationQDoubleSpinBox.value()

        newStart = self.percentTo4095(self.scanStartQDoubleSpinBox.value())
        newStop = self.percentTo4095(self.scanStopQDoubleSpinBox.value())
        newPoints = int(self.scanPointsLineEdit.text())
        if newStart != self.scanStart or newStop != self.scanStop or newPoints != self.scanPoints:
            # ima promena
            if newStop - newStart < newPoints:
                # ne može, vrati stare vrednosti!
                self.scanStartQDoubleSpinBox.setValue((self.scanStart * 100)/4095)
                self.scanStopQDoubleSpinBox.setValue((self.scanStop * 100) / 4095)
                self.self.scanPointsLineEdit.setText(str(self.scanPoints))
            else:
                # usvoji nove vrednosti
                self.scanStart = newStart
                self.scanStop = newStop
                self.scanPoints = newPoints

                # generiši novi niz za scan
                pass

    def delayChange(self):
        print("delayChange")
        # sender = self.sender()
        if self.timerScanChange.isActive():
            # dok timer ne završi nove promene se ignorišu
            print("Timer Active")
            # self.timerScanChange.stop()
            self.timerScanChange.start()
            return
        else:
            # print("delayChange connect")
            # self.timerScanChange.timeout.connect(lambda: func(sender))
            print("Start timer timerScanChange")
            self.timerScanChange.start()
        pass


    @staticmethod
    def percentTo4095(val):
        return int(val*4095/100)

    def readDUE(self):
        while True:
            try:
                if self.due.box.in_waiting > 0:
                    line = self.due.readLine()
                    #  print(line)

                    pos, x, y, time_ms = [float(s) for s in line.split(", ")]
                    pos = int(pos)
                    self.data = [pos, x, y, int(time_ms)]  # share data with app
                    self.pos_data.append(int(pos))
                    self.X_data.append(x)
                    self.Y_data.append(y)
                    r = np.sqrt(x ** 2 + y ** 2)
                    self.R_data.append(r)
                    fi = np.degrees(np.arctan2(y, x))
                    self.fi_data.append(fi)
                    self.time_ms_data.append(int(time_ms))

                    if self.mode == 'scan':
                        if pos in self.scanPositions_int:
                            try:
                                li = [l[0] for l in self.scanData]
                                index = li.index(pos)
                            except Exception as e:
                                index = -1
                                # print(e)
                            # print(index)
                            if index == -1:
                                self.scanData.append([pos, r, fi])
                            else:
                                # pregaziti staru vrednost

                                self.scanData[index] = [pos, r, fi]
                                # print("pregazi")


            except Exception as e:
                # ili je odgovor na komandu ili polomljeni podaci
                parts = line.split(': ')
                if parts[0] == 'scan':
                    self.mode = parts[0]
                else:
                    print("readDUE: "+str(e))

            time.sleep(0.02)  # save processor time

    def displayNewData(self):

        if self.mode == "lock":
            """
            pos, x, y, time_ms = self.data
            r = np.sqrt(x ** 2 + y ** 2)
            fi = np.arctan2(y, x)
            self.serialInputTextEdit.setText(str(r) + ", " + str(fi) + ", " + str(time_ms))
            """
            # print(list(self.R_data))
            # print(list(self.pos_data))
            t = list(self.time_ms_data)
            t = [(v - t[-1])/1000 for v in t]
            r = list(self.R_data)
            fi = list(self.fi_data)
            # t = (timear - timear[-1])/1000
            #print(len(t))
            #print(len(np.array(self.R_data)))
            #print(len(np.array(self.fi_data)))
            self.plotR.plot(t, r)
            self.plotfi.plot(t, fi)
        elif self.mode == "scan":
            # print(self.scanData)
            if len(self.scanData) > 3:
                pos = [l[0] for l in self.scanData]
                r = [l[1] for l in self.scanData]
                fi = [l[2] for l in self.scanData]

                self.plotScanR.plot(pos, r)
                self.plotScanfi.plot(pos, fi)
                # print("scan tab plots")

        else:
            pass

    def setUIlayout(self):

        tabScanPlotLayout = QtWidgets.QVBoxLayout()
        tabScanPlotLayout.addWidget(self.plotScanR)
        tabScanPlotLayout.addWidget(self.plotScanfi)

        tabScanControlsLayout = QtWidgets.QGridLayout()
        tabScanControlsLayout.addWidget(QtWidgets.QLabel("Tačaka u scan-u"), 0, 0)
        tabScanControlsLayout.addWidget(self.scanPointsLineEdit, 0, 1)
        tabScanControlsLayout.addWidget(QtWidgets.QLabel("Scan start"), 1, 0)
        tabScanControlsLayout.addWidget(self.scanStartQDoubleSpinBox, 1, 1)
        tabScanControlsLayout.addWidget(QtWidgets.QLabel("Scan stop"), 2, 0)
        tabScanControlsLayout.addWidget(self.scanStopQDoubleSpinBox, 2, 1)
        tabScanControlsLayout.addWidget(QtWidgets.QLabel("Vreme po tački"), 3, 0)
        tabScanControlsLayout.addWidget(self.scanIntegrationQDoubleSpinBox, 3, 1)

        tabScanControlsLayout.addWidget(self.startScanButton, 4, 0, 1, 2)  # sta, row, col, rowspan, colspan
        scanLabel = QtWidgets.QLabel("Neki text za laku noć koji ljudi vole da čitaju i uživaju dok mogu")
        scanLabel.setWordWrap(True)
        tabScanControlsLayout.addWidget(scanLabel, 5, 0, 2, 2)  # text

        tabScanLayout = QtWidgets.QGridLayout(self.tabScan)
        tabScanLayout.addLayout(tabScanControlsLayout, 0, 0)
        tabScanLayout.addLayout(tabScanPlotLayout, 0, 1)
        tabScanLayout.setColumnMinimumWidth(0, 250)
        tabScanLayout.setColumnStretch(0, 1)
        tabScanLayout.setColumnStretch(1, 30)

        self.tabScan.setLayout(tabScanLayout)

        tabLockPlotLayout = QtWidgets.QVBoxLayout()
        tabLockPlotLayout.addWidget(self.plotR)
        tabLockPlotLayout.addWidget(self.plotfi)

        tabLockLayout = QtWidgets.QVBoxLayout(self)
        tabLockLayout.addLayout(tabLockPlotLayout)
        tabLockLayout.addWidget(self.startLockButton)
        self.tabLock.setLayout(tabLockLayout)

        self.tabs.addTab(self.tabScan, "Scan")
        self.tabs.addTab(self.tabLock, "Lock")
        # self.tabs.resize(300, 200)

        self.tabs.adjustSize()
        # self.tabs.resize(300, 200)

        # ------------------------------------------
        #    define layout, arrange widgets
        # ------------------------------------------

        # top HBox
        topHBox = QtWidgets.QHBoxLayout()
        topHBox.addWidget(self.portLabel)
        topHBox.addStretch(1)

        # serial input HBox
        #serialHBox = QtWidgets.QHBoxLayout()
        #serialHBox.addWidget(self.serialInputTextEdit)

        # Tabs
        tabsHBox = QtWidgets.QHBoxLayout()
        tabsHBox.addWidget(self.tabs)
        # tabsHBox.addStretch(1)



        # ------------------------------------------
        #    Add HBoxes into VBox
        # ------------------------------------------

        mainVBox = QtWidgets.QVBoxLayout()
        mainVBox.addLayout(topHBox)
        # mainVBox.addLayout(serialHBox)
        mainVBox.addLayout(tabsHBox)

        # mainVBox.addStretch(1)

        self.setLayout(mainVBox)

        # self.setWindowTitle('Etalon kontroler')
        # self.setWindowIcon(QIcon('web.png'))    #put icon

        #  window position x, y and size x, y
        # x position 100 i width of my taskbar on left
        # y position 35 to have top of the window visible
        self.setGeometry(100, 35, 1000, 800)

        self.show()

    def connectDUE(self):

        msgBox = QtWidgets.QMessageBox()
        msgBox.setWindowTitle("Lock-in modul nije pronađen")
        msgBox.setText("Digitalni modul za detekciju trećeg izvoda nije pronađen. Proverite USB kabl.")
        msgBox.setIcon(QtWidgets.QMessageBox.Warning)
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Retry | QtWidgets.QMessageBox.Abort)

        self.due = class_MySerial.MySerial()
        #print(self.due.serial_ports())

        while not self.due.connect():
            retval = msgBox.exec_()
            if retval == QtWidgets.QMessageBox.Abort:
                exit()
        self.due.sendToBox("mode?")

        return True

    def scanRun(self):
        print("Počinje scan")
        self.due.sendToBox("scan 0") # da prekine lock ako nije već

        self.scanPositions()
        self.timerScan.start()

    def scanPositions(self):
        dif = self.scanStop - self.scanStart
        delta = dif/self.scanPoints

        scanPositions = np.linspace(self.scanStart, self.scanStop, self.scanPoints)
        self.scanPositions_int = np.random.permutation(scanPositions.astype(np.int64))
        print(self.scanPositions_int)
        self.scanPosGen = self.nsp(self.scanPositions_int)
        self.scanData=[]

    def nextScanPoint(self):
        try:
            command = "scan " + str(self.scanPosGen.__next__())
            self.due.sendToBox(command)
            #print(command)
        except Exception as e:
            self.scanPosGen = self.nsp(self.scanPositions_int)
            print(e)

    def nsp(self, poss):
        for p in poss:
            yield p

    def stabilizacija(self):
        print("Stabilizacija počinje")

##############################################################################################
#
#                    Start main code
#
##############################################################################################


def main():
    print("Počinje...")
    # print(config.sections())
    # print("Last port: ", config.get('General','port'))

    app = QtWidgets.QApplication(sys.argv)
    # app.exec_()  # execute connectingForm until closed
    mf = MainForm()
    sys.exit(app.exec_())
    del mf


if __name__.endswith('__main__'):
    main()
