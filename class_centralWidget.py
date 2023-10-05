#  Copyright (c) 2019.
#  This code has been produced by Zoran D. Grujic and by the knowledge found on The Internet.
#  Please feel free to ask me for permission to use my code in your own projects. It is for your own well fare!

import sys
import os
import glob
import serial  # conda install pyserial
# import h5py  # conda install h5py
import sip  # pip install sip
import time
import numpy as np
import threading
import logging

from typing import List, Any, Union

import class_matplotlibWidget
import class_signal
from class_circularBuffer import CircularBuffer

import class_MySerial

from PyQt5 import QtCore  # conda install pyqt
# from PyQt5.QtCore import Qt
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication
import pyqtgraph as pg  # Fast plot package
# import pyqtgraph.examples
# pyqtgraph.examples.run()



class MainForm(QtWidgets.QWidget):  # QMainWindow # QWidget
    plotScanX = None  # type: object
    name = "Etalon"
    due = False  # connection to Arduino DUE
    timer = False  # timer to read ports
    timerDisplayTime_ms = 100
    data = False  # type: List[Union[Union[int, float], Any]]
    lockCenter = 0
    thread_readDue = False
    R_data = CircularBuffer(200)
    fi_data = CircularBuffer(200)
    X_data = CircularBuffer(200)
    Y_data = CircularBuffer(200)
    pos_data = CircularBuffer(200)
    pos_dataF = CircularBuffer(200)
    time_ms_data = CircularBuffer(200)
    dataAll = CircularBuffer(200)
    temperature = 0
    laserDCPower = 0
    mousePoint = False


    mode = "scan"  # scan ili lock

    # scan
    scanCalibrationVrms =  0.707/636  # 636 => 0.707 Vrms
    scanPoints = 1000       # pts
    scanStart = 5000           # 0-65535
    scanStop = 65535         # 0-65535
    scanIntegration_ms = 10   # ms
    scanPositions_int = []
    scanPosGen = None
    scanPhase_deg = -20.0
    scanData = []
    lastMouseClick = ''

    """
    PI  parametri

    int integralPI = 1000; // Integralna konstanta PI u Vrms / s
    int propPI = 1000; // Prop konstanta PI
    int fineHVratio = 100; // Odnos finog i HV koraka
    int lockPointX = 0;
    float integral = 0; // trenutna vrednost integrala greske, integral += integralPI * greska * dt
    """
    integralPI = 3
    propPI = 3
    lockPoint = 0
    fineHVratio = 90  # ratio is 17 (fine) : 10 (HV)

    def __init__(self, parent):
        super(MainForm, self).__init__()
        self.parent = parent  # parent je glavni okvir, odavde može da se utiče na njega
        self.scanPositions()



        # ------------------------------------------
        # Timers
        # ------------------------------------------

        # odložena promena parametara scan-a
        self.timerScanChange = QtCore.QTimer(self)  # make timer to belong to the MainForm class
        self.timerScanChange.setInterval(500)
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
        self.olovkaScanX = pg.mkPen((100, 200, 250), width=2, style=QtCore.Qt.SolidLine)
        # symbol = 'o'
        self.plotScanX = pg.PlotWidget()  # class_matplotlibWidget.MatplotlibWidget(20, 2, self.tabScan)
        self.plotScanX.scene().sigMouseMoved.connect(self.mouseMoved)
        self.plotScanX.scene().sigMouseClicked.connect(self.mouseClick)

        #  self.plotScanX.xLabel = "pozicija (#)"
        #  self.plotScanX.yLabel = 'R (Vrms)'
        #  self.plotScanX.line = 'o'

        self.plotScanX.setLabel('left', '<font>X</font>', units='<font>Vrms</font>', color='white', **{'font-size': '10pt'})
        self.plotScanX.setLabel('bottom', '<font>pozicija</font>', units='<font>V</font>', color='white', **{'font-size': '10pt'})
        # cross hair
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.vLineCenter = pg.InfiniteLine(angle=90, movable=False)

        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        self.plotScanX.addItem(self.vLine, ignoreBounds=True)
        self.plotScanX.addItem(self.hLine, ignoreBounds=True)

        self.olovkaScanY = pg.mkPen((100, 250, 200), width=2, style=QtCore.Qt.SolidLine)
        self.plotScanY = pg.PlotWidget()
        # self.plotScanY = class_matplotlibWidget.MatplotlibWidget(20, 2, self.tabScan)
        # self.plotScanY.xLabel = "pozicija (#)"
        # self.plotScanY.yLabel = '$\phi$ ($^\circ$)'
        # self.plotScanY.line = 'o'
        self.plotScanY.setLabel('left', '<font>Y</font>', units='<font>Vrms</font>', color='white',
                                **{'font-size': '10pt'})
        self.plotScanY.setLabel('bottom', '<font>pozicija</font>', units='<font>V</font>', color='white',
                                **{'font-size': '10pt'})

        self.olovkaX = pg.mkPen((100, 200, 250), width=2, style=QtCore.Qt.SolidLine)
        self.plotX = pg.PlotWidget()
        self.plotX.setLabel('left', '<font>X</font>', units='<font>Vrms</font>', color='white', **{'font-size': '10pt'})
        self.plotX.setLabel('bottom', '<font>vreme</font>', units='<font>s</font>', color='white', **{'font-size': '10pt'})

        self.olovkaY = pg.mkPen((100, 200, 250), width=2, style=QtCore.Qt.SolidLine)
        self.plotPosHV = pg.PlotWidget()
        self.plotPosHV.setLabel('left', '<font>pos HV PZT</font>', units='<font>V</font>', color='white', **{'font-size': '10pt'})
        self.plotPosHV.setLabel('bottom', '<font>vreme</font>', units='<font>s</font>', color='white', **{'font-size': '10pt'})

        self.plotPosF = pg.PlotWidget()
        self.plotPosF.setLabel('left', '<font>pos fine PZT</font>', units='<font>V</font>', color='white',
                                **{'font-size': '10pt'})
        self.plotPosF.setLabel('bottom', '<font>vreme</font>', units='<font>s</font>', color='white',
                                **{'font-size': '10pt'})

        # tab buttons
        self.startScanButton = QtWidgets.QPushButton("Počni scan", self.tabScan)
        self.startScanButton.clicked.connect(self.scanRun)

        """
        self.startLockButton = QtWidgets.QPushButton("Zaključaj na rezonanci", self.tabLock)
        self.startLockButton.clicked.connect(self.stabilizacija)
        tt = "Pokreće algoritam zaključavanja rezonatora na izabranoj rezonanci..."
        self.startLockButton.setToolTip('<span style="color:#555555;">'+tt+'</span>')
        """

        # tab buttons
        self.startFullScanButton = QtWidgets.QPushButton("Full scan", self.tabScan)
        self.startFullScanButton.clicked.connect(self.scanFullRun)
        tt = "Pokreće scan u punom opsegu radi potrage za rezonancama..."
        self.startFullScanButton.setToolTip('<span style="color:#555555;">' + tt + '</span>')

        # tab buttons
        self.sendPIButton = QtWidgets.QPushButton("Submit", self.tabLock)
        self.sendPIButton.clicked.connect(self.sendPI)
        tt = "Šalje PI parametre na kontroler"
        self.sendPIButton.setToolTip('<span style="color:#555555;">' + tt + '</span>')

        # tab buttons
        self.centrirajButton = QtWidgets.QPushButton("Centriraj", self.tabLock)
        self.centrirajButton.clicked.connect(self.centrirajLok)
        tt = "Šalje komandu da se fini PZT dovede u osnovnu poziciju."
        self.centrirajButton.setToolTip('<span style="color:#555555;">' + tt + '</span>')

        # tab buttons
        self.stopLockButton = QtWidgets.QPushButton("STOP lock", self.tabLock)
        self.stopLockButton.clicked.connect(self.stopLock)
        tt = "Zaustavlja lock i vraća na scan."
        self.stopLockButton.setToolTip('<span style="color:#555555;">' + tt + '</span>')

        # tab inputs

        self.scanPointsLineEdit = QtWidgets.QLineEdit(str(self.scanPoints), self.tabScan)  # Koliko tačaka u scan-u
        self.scanPointsLineEdit.setValidator(QtGui.QIntValidator(10, 10000))
        self.scanPointsLineEdit.textChanged.connect(self.delayChange)
        tt = "Koliko tačaka će biti u snimljenom spektru?"
        self.scanPointsLineEdit.setToolTip('<span style="color:#555555;">' + tt + '</span>')

        self.scanStartQDoubleSpinBox = QtWidgets.QDoubleSpinBox(self.tabScan)  # Serial port preview
        self.scanStartQDoubleSpinBox.name = "ScanStart"
        self.scanStartQDoubleSpinBox.setValue(100 * self.scanStart/4095)
        self.scanStartQDoubleSpinBox.setRange(0, 4.096)
        self.scanStartQDoubleSpinBox.setSingleStep(0.05)
        self.scanStartQDoubleSpinBox.setSuffix(" V")
        self.scanStartQDoubleSpinBox.setDecimals(3)
        self.scanStartQDoubleSpinBox.valueChanged.connect(self.delayChange)
        tt = "Od koje tačke počinje snimanje spektra?"
        self.scanStartQDoubleSpinBox.setToolTip('<span style="color:#555555;">' + tt + '</span>')

        self.scanStopQDoubleSpinBox = QtWidgets.QDoubleSpinBox(self.tabScan)  # Serial port preview
        self.scanStopQDoubleSpinBox.name = "ScanStop"
        self.scanStopQDoubleSpinBox.setRange(0, 4.096)
        self.scanStopQDoubleSpinBox.setSingleStep(0.04)
        self.scanStopQDoubleSpinBox.setValue(4.096)
        self.scanStopQDoubleSpinBox.setSuffix(" V")
        self.scanStopQDoubleSpinBox.setDecimals(3)
        self.scanStopQDoubleSpinBox.valueChanged.connect(self.delayChange)
        tt = "Gde stati sa snimanjem spektra? Start i Stop definišu prozor u kome se snima spektar."
        self.scanStopQDoubleSpinBox.setToolTip('<span style="color:#555555;">' + tt + '</span>')

        self.scanIntegrationQDoubleSpinBox = QtWidgets.QSpinBox(self.tabScan)  # Serial port preview
        self.scanIntegrationQDoubleSpinBox.name = "ScanStop"
        self.scanIntegrationQDoubleSpinBox.setRange(10, 5000)
        self.scanIntegrationQDoubleSpinBox.setSingleStep(10)
        self.scanIntegrationQDoubleSpinBox.setValue(self.scanIntegration_ms)
        self.scanIntegrationQDoubleSpinBox.setSuffix(" ms")
        self.scanIntegrationQDoubleSpinBox.valueChanged.connect(self.delayChange)
        tt = "Koliko dugo snimati svaku tačku?"
        self.scanIntegrationQDoubleSpinBox.setToolTip('<span style="color:#555555;">' + tt + '</span>')

        self.scanPhaseQDoubleSpinBox = QtWidgets.QDoubleSpinBox(self.tabScan)  # Podešavanje faze demodulatora
        self.scanPhaseQDoubleSpinBox.name = "ScanStop"
        self.scanPhaseQDoubleSpinBox.setRange(-360.0, 360.0)
        self.scanPhaseQDoubleSpinBox.setSingleStep(0.01)
        self.scanStopQDoubleSpinBox.setDecimals(2)
        self.scanPhaseQDoubleSpinBox.setValue(self.scanPhase_deg)
        self.scanPhaseQDoubleSpinBox.setSuffix(" deg")
        self.scanPhaseQDoubleSpinBox.valueChanged.connect(self.delayChange)
        tt = "Treba li pomeriti fazu reference?"
        self.scanPhaseQDoubleSpinBox.setToolTip('<span style="color:#555555;">' + tt + '</span>')

        self.scanStopEndCheckBox = QtWidgets.QCheckBox("Zaustavi scan na kraju", self.tabScan)
        self.scanStopEndCheckBox.setCheckState(False)
        self.scanStopEndCheckBox.stateChanged.connect(self.delayChange)
        tt = "Zaustavi skeniranje na kraju scan-a?"
        self.scanStopEndCheckBox.setToolTip('<span style="color:#555555;">' + tt + '</span>')

        self.hideYgraphCheckBox = QtWidgets.QCheckBox("Sakrij Y grafik", self.tabScan)
        self.hideYgraphCheckBox.setCheckState(False)
        self.hideYgraphCheckBox.stateChanged.connect(self.hideY)
        tt = "Da li želite da sakrijete Y grafik?"
        self.hideYgraphCheckBox.setToolTip('<span style="color:#555555;">' + tt + '</span>')

        self.integralPIQDoubleSpinBox = QtWidgets.QDoubleSpinBox(self.tabLock)  # Podešavanje faze demodulatora
        self.integralPIQDoubleSpinBox.name = "integralPI"
        self.integralPIQDoubleSpinBox.setRange(-1000, 1000)
        self.integralPIQDoubleSpinBox.setSingleStep(.1)
        self.integralPIQDoubleSpinBox.setDecimals(3)
        self.integralPIQDoubleSpinBox.setValue(self.integralPI)
        self.integralPIQDoubleSpinBox.setSuffix("")
        # self.scanPhaseQDoubleSpinBox.valueChanged.connect(self.delayChange)
        tt = "Integraciona konstanta PI-ja"
        self.integralPIQDoubleSpinBox.setToolTip('<span style="color:#555555;">' + tt + '</span>')


        self.propPIQDoubleSpinBox = QtWidgets.QDoubleSpinBox(self.tabLock)  # Podešavanje faze demodulatora
        self.propPIQDoubleSpinBox.name = "propPI"
        self.propPIQDoubleSpinBox.setRange(-1000, 1000)
        self.propPIQDoubleSpinBox.setSingleStep(1)
        self.propPIQDoubleSpinBox.setDecimals(3)
        self.propPIQDoubleSpinBox.setValue(self.propPI)
        self.propPIQDoubleSpinBox.setSuffix("")
        # self.scanPhaseQDoubleSpinBox.valueChanged.connect(self.delayChange)
        tt = "Proporcionalna konstanta PI-ja"
        self.propPIQDoubleSpinBox.setToolTip('<span style="color:#555555;">' + tt + '</span>')

        #lockPointPIQDoubleSpinBox
        self.lockPointPIQDoubleSpinBox = QtWidgets.QDoubleSpinBox(self.tabLock)  # Podešavanje lock point
        self.lockPointPIQDoubleSpinBox.name = "lockPointPI"
        self.lockPointPIQDoubleSpinBox.setRange(-1000, 1000)
        self.lockPointPIQDoubleSpinBox.setSingleStep(1)
        self.lockPointPIQDoubleSpinBox.setDecimals(3)
        self.lockPointPIQDoubleSpinBox.setValue(self.lockPoint)
        self.lockPointPIQDoubleSpinBox.setSuffix("")
        # self.scanPhaseQDoubleSpinBox.valueChanged.connect(self.delayChange)
        tt = "Lock point PI-ja"
        self.lockPointPIQDoubleSpinBox.setToolTip('<span style="color:#555555;">' + tt + '</span>')

        self.fineHVratioLineEdit = QtWidgets.QLineEdit(str(self.fineHVratio), self.tabLock)  # Koliko tačaka u scan-u
        self.fineHVratioLineEdit.setValidator(QtGui.QIntValidator(-100000, 10000))
        #self.scanPointsLineEdit.textChanged.connect(self.delayChange)
        tt = "Odnos koraka HV i finog PZT-a"
        self.fineHVratioLineEdit.setToolTip('<span style="color:#555555;">' + tt + '</span>')

        # tab buttons
        self.moveHVButton = QtWidgets.QPushButton("Move HV", self.tabLock)
        self.moveHVButton.clicked.connect(self.moveHV)
        tt = "Pomeri HV PZT radi provere lokovanja"
        self.moveHVButton.setToolTip('<span style="color:#555555;">' + tt + '</span>')

        self.moveHVLineEdit = QtWidgets.QLineEdit(str(100), self.tabLock)  # Koliko tačaka u scan-u
        self.moveHVLineEdit.setValidator(QtGui.QIntValidator(-1000, 1000))
        # self.scanPointsLineEdit.textChanged.connect(self.delayChange)
        tt = "Za koliko da pomeri HV PZT"
        self.moveHVLineEdit.setToolTip('<span style="color:#555555;">' + tt + '</span>')

        self.sigmaLabel = QtWidgets.QLabel("Sigma: ", self.tabLock)
        # self.sigmaLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.meanLabel = QtWidgets.QLabel("Srednja  vrednost: ", self.tabLock)

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

        command = "phase " + str(self.scanPhase_deg*100) + " " + str(self.scanPhase_deg*100)
        print(command)
        self.due.sendToBox(command)
        self.due.sendToBox(command)

        self.timer.start()
        self.showMaximized()

    def stopLock(self):
        self.centrirajLok()
        time.sleep(0.01)

        self.mode = 'scan'

        self.vLineCenter.setPos(self.lockCenter)
        print("Lock center = ", self.lockCenter)

        self.scanPointsLineEdit.setText(str(200))
        self.scanStartQDoubleSpinBox.setValue(self.lockCenter - 0.031)
        self.scanStopQDoubleSpinBox.setValue(self.lockCenter + 0.031)
        self.scanIntegrationQDoubleSpinBox.setValue(10)
        self.scanChanged()
        self.scanRun()


        self.tabs.setCurrentIndex(0)

    def centrirajLok(self):
        self.due.sendToBox("center")

        """
        PI 587 654
        -------------------------
        Postavlja integralni (587) i proporcionalni deo (654)
        
        FHVratio 1000 1000
        -----------------------------------
        Postavlja odnos HV i običnog PZT-ako
        
        Odgovor: Ako brojevi nisu isti prijavljuje grešku
        """
    def sendPI(self):
        #command = "PI "+str(self.integralPIQDoubleSpinBox.value())+" "
        #command += str(self.propPIQDoubleSpinBox.value())
        command = "PI {0:d} {1:d}".format(int(1000*self.integralPIQDoubleSpinBox.value()), int(1000*self.propPIQDoubleSpinBox.value()))
        self.due.sendToBox(command)
        print(command)

        command = "FHVratio " + self.fineHVratioLineEdit.text() + " " + self.fineHVratioLineEdit.text()
        self.due.sendToBox(command)
        print(command)

        # lock point
        val = int(1000.0 * self.lockPointPIQDoubleSpinBox.value())
        command = "lockpoint {0:d} {1:d}".format(val, val)
        self.due.sendToBox(command)
        print(command)

    def moveHV(self):
        command = "moveHV " + self.moveHVLineEdit.text() + " " + self.moveHVLineEdit.text()
        self.due.sendToBox(command)
        print (command)

    def hideY(self, state):
        if state > 0:
            # checked
            self.plotScanY.setHidden(True)
        else:
            self.plotScanY.setHidden(False)


    """Pomera crosshair da grafik lepše izgleda"""
    def mouseMoved(self, qpoint):
        # print("Mouse moved here!")
        #pos = [qpoint.x(), qpoint.y()]
        #print(pos)
        self.mousePoint = self.plotScanX.plotItem.vb.mapSceneToView(qpoint)
        self.vLine.setPos(self.mousePoint.x())
        self.hLine.setPos(0)
        # print([mousePoint.x(), mousePoint.y()])

    """
    Detektuje sve klikove
    Ako je jedan klik zumira na oblast od +/- 150mV oko klika 
    Koristi poziciju miša od self.ouseMoved event-a.
    """
    def mouseClick(self, evt):
        print("Klik!")

        if evt.button() == 1:  # levi klik

            if evt.double():
                print("     Doubleclick: ", self.mousePoint)
                self.lastMouseClick = "DoubleClick"
                self.lockNow(self.mousePoint.x())
            else:
                """
                if self.lastMouseClick == "DoubleClick":
                    return
                """
                #print(QApplication.instance().doubleClickInterval())
                print("     Levo dugme ", self.mousePoint)
                # print("     Klik: ", mousePoint.x())
                self.lastMouseClick = "Click"
                self.scanPointsLineEdit.setText(str(200))
                self.scanStartQDoubleSpinBox.setValue(self.mousePoint.x()-0.1)
                self.scanStopQDoubleSpinBox.setValue(self.mousePoint.x()+0.1)
                self.scanIntegrationQDoubleSpinBox.setValue(10)
                self.scanChanged()
                self.scanRun()
                print("Scan center: ", self.mousePoint.x())


        else:
            print("     NIJE Levo dugme ", evt)

    def lockNow(self, x):

        self.sendPI()
        x = int(x * 65535/4.096)
        command = "lock " + str(x) + " " + str(x)
        print(command)

        self.due.sendToBox(command)
        self.timerScan.stop()  # zaustavi scan
        self.tabs.setCurrentIndex(1)
        self.dataAll = CircularBuffer(200)
        self.scanData = CircularBuffer(200)
        time.sleep(.2)
        self.dataAll = CircularBuffer(200)
        self.scanData = CircularBuffer(200)

        pass

    def scanChanged(self):
        """
        Update scan parameters
        """
        print("scanParametersChanged")
        # print(sender)
        # print("scanStartChanged: " + str(sender.value()))
        # print(str(self.percentTo4095(sender.value())))
        # return MainForm.percentTo4095(sender.value())

        if int(self.scanPhaseQDoubleSpinBox.value()) != self.scanPhase_deg:
            self.scanPhase_deg = int(self.scanPhaseQDoubleSpinBox.value()*100)  # puta 100 za 0.01 stepen rezolucije
            command = "phase " + str(self.scanPhase_deg) + " " + str(self.scanPhase_deg)
            self.due.sendToBox(command)
            #self.due.sendToBox(command)

        if self.scanIntegrationQDoubleSpinBox.value() != self.scanIntegration_ms:
            self.scanIntegration_ms = self.scanIntegrationQDoubleSpinBox.value()
            self.timerScan.setInterval(self.scanIntegration_ms)

        newStart = self.vTo65535(self.scanStartQDoubleSpinBox.value())
        newStop = self.vTo65535(self.scanStopQDoubleSpinBox.value())
        newPoints = int(self.scanPointsLineEdit.text())
        if newStart != self.scanStart or newStop != self.scanStop or newPoints != self.scanPoints:
            # ima promena
            if newStop - newStart < newPoints:
                # ne može, vrati stare vrednosti!
                self.scanStartQDoubleSpinBox.setValue((self.scanStart * 4.096)/65535)
                self.scanStopQDoubleSpinBox.setValue((self.scanStop * 4.096) / 65535)
                self.scanPointsLineEdit.setText(str(self.scanPoints))
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

    def scanFullRun(self):
        self.scanPointsLineEdit.setText(str(1000))
        self.scanStartQDoubleSpinBox.setValue(0.5)
        self.scanStopQDoubleSpinBox.setValue(4.096)
        self.scanIntegrationQDoubleSpinBox.setValue(10)
        self.scanChanged()
        self.scanRun()

    @staticmethod
    def percentTo4095(val):
        return int(val*4095/100)

    @staticmethod
    def percentTo65535(val):
        return int(val * 65535 / 100)

    @staticmethod
    def vTo65535(val):
        return int(val * 65535 / 4.096)

    def readDUE(self):
        while True:
            try:
                while self.due.box.in_waiting > 0:
                    line = self.due.readLine()
                    #  print(line)
                    #  print(line.split()[0])

                    pos, posF, x, y, time_ms = [float(s) for s in line.split(", ")]
                    pos = int(pos)
                    posF = int(posF)
                    x = x * self.scanCalibrationVrms
                    y = y * self.scanCalibrationVrms
                    self.data = [pos, posF, x, y, int(time_ms)]  # share data with app
                    self.dataAll.append(self.data)
                    # self.pos_data.append(pos)
                    # self.pos_dataF.append(posF)
                    # self.X_data.append(x)
                    # self.Y_data.append(y)
                    # r = np.sqrt(x ** 2 + y ** 2)
                    # self.R_data.append(r)
                    # fi = np.degrees(np.arctan2(y, x))
                    # self.fi_data.append(fi)
                    # self.time_ms_data.append(int(time_ms))

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
                                self.scanData.append([pos, x, y])
                            else:
                                # pregaziti staru vrednost

                                self.scanData[index] = [pos, x, y]
                                # print("pregazi")


            except Exception as e:
                # ili je odgovor na komandu ili polomljeni podaci
                parts = line.split(': ')
                # print(line)
                if parts[0] == 'scan':
                    self.mode = parts[0]
                    print("DUE mode: ", self.mode)
                elif parts[0] == 'mode':
                    self.mode = parts[1]
                elif parts[0] == 'temp':
                    self.temperature = int(parts[1])
                elif parts[0] == 'power':
                    self.laserDCPower = int(parts[1])
                    self.updateTP()
                elif parts[0] == 'lockcenter':
                    self.lockCenter = 4.096 * int(parts[1]) / 65535
                elif parts[0] == 'Lock point offset':
                    print(f"Lok point offset: {parts[1]}")
                elif parts[0] == 'Phase':
                    print(f"Phase: {parts[1]}")


                else:
                    if parts[0] == 'Error':  # Error reported from ADB
                        print("readDUE: " + line)
                    else:
                        print("readDUE: "+str(e) + " - " + line)

            time.sleep(0.005)  # save processor time


    def updateTP(self):
        #print("temp: ", self.temperature)
        #print("power: ", self.laserDCPower)
        tempstr=str(self.temperatureConvert(self.temperature))
        m = "Temperatura: {0:0.1f} ˚C, Snaga lasera: {1:0.2f} µW, buffer size: {2:d}"
        m = m.format(self.temperatureConvert(self.temperature)-0.2, 0.0253*self.laserDCPower, self.due.box.in_waiting)
        #self.parent.status.showMessage(m)
        self.portLabel.setText("Port: " + self.due.port + ", " + m)
        pass


    def displayNewData(self):


        #print(posHV.size )
        """
        if posHV.size > 200:
            self.timer.stop()
            self.timer.setInterval(10*self.timerDisplayTime_ms)
            self.timer.start()
            print("duzio interval:", self.timer.interval())
        elif self.timer.interval()!=self.timerDisplayTime_ms:
            self.timer.stop()
            self.timer.setInterval(self.timerDisplayTime_ms)
            self.timer.start()
            """
        if self.mode == "lock":
            """
            pos, x, y, time_ms = self.data
            r = np.sqrt(x ** 2 + y ** 2)
            fi = np.arctan2(y, x)
            self.serialInputTextEdit.setText(str(r) + ", " + str(fi) + ", " + str(time_ms))
            """
            # print(list(self.R_data))
            # print(list(self.pos_data))
            t = [v[4] for v in self.dataAll]  # list(self.dataAll[:4])
            t = [(v - t[-1])/1000 for v in t]
            x = [v[2] for v in self.dataAll]  # self.dataAll[:2]
            posHV = np.array([v[0] for v in self.dataAll]) * 4.096 / 65535
            posF = 0.55 + np.array([v[1] for v in self.dataAll]) * 2.2 / 4095
            # y = [l[2] for l in self.scanData]
            # t = (timear - timear[-1])/1000
            #print(len(t))
            #print(len(np.array(self.R_data)))
            #print(len(np.array(self.fi_data)))
            std=np.std(x)*1000
            mean = np.mean(x)*1000
            msg = "Stand. devijacija: {0:0.2f} mVrms".format(std)
            self.sigmaLabel.setText(msg)
            msg = "Srednja  vrednost: {0:0.2f} mVrms".format(mean)
            self.meanLabel.setText(msg)

            self.plotX.clear()  # očisti graph
            self.plotX.plot(t, x, symbol='o', pen=self.olovkaX)  #  m, y, k, w
            self.plotPosHV.clear()  # očisti graph
            self.plotPosHV.plot(t, posHV, symbol='o', pen=self.olovkaY)
            self.plotPosF.clear()  # očisti graph
            self.plotPosF.plot(t, posF, symbol='o', pen=self.olovkaY)
        elif self.mode == "scan":
            # print(self.scanData)
            if len(self.scanData) > 3:
                posHV = np.array([v[0] for v in self.scanData]) * 4.096 / 65535
                x = [l[1] for l in self.scanData]
                y = [l[2] for l in self.scanData]

                d = np.transpose([posHV, x])
                d = d[d[:, 0].argsort()]
                if len(x) == len(posHV):
                    self.plotScanX.clear()
                    self.plotScanX.addItem(self.vLine, ignoreBounds=True)
                    self.plotScanX.addItem(self.vLineCenter, ignoreBounds=True)
                    self.plotScanX.addItem(self.hLine, ignoreBounds=True)
                    self.plotScanX.plot(d, symbol='o', pen=self.olovkaScanX)
                if self.hideYgraphCheckBox.checkState():
                    #print(len(x), len(posHV))
                    pass
                else:
                    dy = np.transpose([posHV, y])
                    dy = dy[dy[:, 0].argsort()]
                    if len(x) == len(posHV):
                        self.plotScanY.clear()
                        self.plotScanY.plot(dy, symbol='o', pen=self.olovkaScanY)
                # print("scan tab plots")

        else:
            pass

    def setUIlayout(self):

        self.tabScanPlotLayout = QtWidgets.QVBoxLayout()
        self.tabScanPlotLayout.addWidget(self.plotScanX)
        self.tabScanPlotLayout.addWidget(self.plotScanY)

        tabScanControlsLayout = QtWidgets.QGridLayout()
        tabScanControlsLayout.addWidget(QtWidgets.QLabel("Tačaka u scan-u"), 0, 0)
        tabScanControlsLayout.addWidget(self.scanPointsLineEdit, 0, 1)
        tabScanControlsLayout.addWidget(QtWidgets.QLabel("Scan start"), 1, 0)
        tabScanControlsLayout.addWidget(self.scanStartQDoubleSpinBox, 1, 1)
        tabScanControlsLayout.addWidget(QtWidgets.QLabel("Scan stop"), 2, 0)
        tabScanControlsLayout.addWidget(self.scanStopQDoubleSpinBox, 2, 1)
        tabScanControlsLayout.addWidget(QtWidgets.QLabel("Vreme po tački"), 3, 0)
        tabScanControlsLayout.addWidget(self.scanIntegrationQDoubleSpinBox, 3, 1)
        tabScanControlsLayout.addWidget(QtWidgets.QLabel("Faza reference"), 4, 0)
        tabScanControlsLayout.addWidget(self.scanPhaseQDoubleSpinBox, 4, 1)

        # tabScanControlsLayout.addWidget(QtWidgets.QLabel("Zaustavi scan"), 5, 0)
        tabScanControlsLayout.addWidget(self.scanStopEndCheckBox, 5, 0, 1, 2)

        tabScanControlsLayout.addWidget(self.startScanButton, 6, 0, 1, 2)  # sta, row, col, rowspan, colspan

        tabScanControlsLayout.addWidget(self.hideYgraphCheckBox, 7, 0, 1, 2)
        tabScanControlsLayout.addWidget(self.startFullScanButton, 9, 0, 1, 2)

        scanLabel = QtWidgets.QLabel("Uputstvo: <br>1. Kliknuti 'Full scan' za prikaz rezonanci.<br>2. Kliknuti izabranu rezonancu.<br>3. Dupli klik na mesto gde treba lokovati laser!")
        scanLabel.setWordWrap(True)
        tabScanControlsLayout.addWidget(scanLabel, 100, 0, 2, 2)  # text

        tabScanLayout = QtWidgets.QGridLayout(self.tabScan)
        tabScanLayout.addLayout(tabScanControlsLayout, 0, 0)
        tabScanLayout.addLayout(self.tabScanPlotLayout, 0, 1)
        tabScanLayout.setColumnMinimumWidth(0, 250)
        tabScanLayout.setColumnStretch(0, 1)
        tabScanLayout.setColumnStretch(1, 30)

        self.tabScan.setLayout(tabScanLayout)


        tabLockControlsLayout = QtWidgets.QGridLayout()
        #tabLockControlsLayout.addWidget(QtWidgets.QLabel("PI parametri"), 0, 0, 1, 2)
        tabLockControlsLayout.addWidget(QtWidgets.QLabel("Integrator"), 2, 0)
        tabLockControlsLayout.addWidget(self.integralPIQDoubleSpinBox, 2, 1)
        tabLockControlsLayout.addWidget(QtWidgets.QLabel("Proporcionalni"), 1, 0)
        tabLockControlsLayout.addWidget(self.propPIQDoubleSpinBox, 1, 1)
        tabLockControlsLayout.addWidget(QtWidgets.QLabel("Odnos HV fini"), 3, 0)
        tabLockControlsLayout.addWidget(self.fineHVratioLineEdit, 3, 1)

        tabLockControlsLayout.addWidget(QtWidgets.QLabel("Lock point"), 4, 0)
        tabLockControlsLayout.addWidget(self.lockPointPIQDoubleSpinBox, 4, 1)

        tabLockControlsLayout.addWidget(self.sendPIButton, 5, 0, 1, 2)

        tabLockControlsLayout.addWidget(self.moveHVLineEdit, 7, 0)
        tabLockControlsLayout.addWidget(self.moveHVButton, 7, 1)

        tabLockControlsLayout.addWidget(self.centrirajButton, 8, 0, 1, 2)

        tabLockControlsLayout.addWidget(self.stopLockButton, 9, 0, 1, 2)

        tabLockControlsLayout.addWidget(self.sigmaLabel, 10, 0, 1, 2)
        tabLockControlsLayout.addWidget(self.meanLabel, 11, 0, 1, 2)




        tabLockControlsLayout.addWidget(QtWidgets.QLabel("Uputstvo:"), 100, 0, 1, 2)




        tabLockPlotLayout = QtWidgets.QVBoxLayout()
        tabLockPlotLayout.addWidget(self.plotX)
        tabLockPlotLayout.addWidget(self.plotPosHV)
        tabLockPlotLayout.addWidget(self.plotPosF)

        tabLockLayout = QtWidgets.QGridLayout(self.tabLock)

        tabLockLayout.addLayout(tabLockControlsLayout, 0, 0)
        tabLockLayout.addLayout(tabLockPlotLayout, 0, 1)
        tabLockLayout.setColumnMinimumWidth(0, 250)
        tabLockLayout.setColumnStretch(0, 1)
        tabLockLayout.setColumnStretch(1, 30)

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
        # serialHBox = QtWidgets.QHBoxLayout()
        # serialHBox.addWidget(self.serialInputTextEdit)

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

        #self.show()
        self.showMaximized()

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
                sys.exit()
        self.due.sendToBox("mode?")

        return True

    def scanRun(self):
        print("Počinje scan")
        self.mode = 'scan'
        self.scanPositions()
        command = "scan " + str(self.scanPositions_int[0])+" " + str(self.scanPositions_int[0])
        self.due.sendToBox(command)  # da prekine lock ako nije već
        self.due.sendToBox(command)  # da pošalje ponovo za slučaj lošeg prijema
        time.sleep(0.1)
        self.scanData = []
        if self.scanPoints > 200:
            self.timer.setInterval(5*self.timerDisplayTime_ms)
        else:
            self.timer.setInterval(self.timerDisplayTime_ms)
        self.timerScan.start()

    def scanPositions(self):
        dif = self.scanStop - self.scanStart
        delta = dif/self.scanPoints

        scanPositions = np.linspace(self.scanStart, self.scanStop, self.scanPoints)
        #self.scanPositions_int = np.random.permutation(scanPositions.astype(np.int64))
        self.scanPositions_int = scanPositions.astype(np.int64)
        # print(self.scanPositions_int)
        self.scanPosGen = self.nsp(self.scanPositions_int)
        self.scanData = []

    def nextScanPoint(self):
        try:
            int_string = str(self.scanPosGen.__next__())
            command = "scan " + int_string + " " + int_string
            self.due.sendToBox(command)
            #self.due.sendToBox(command)
            #print(command)
        except Exception as e:
            # scan gotov, počni novi
            if self.scanStopEndCheckBox.checkState():
                self.mode = ''
                self.timerScan.stop()
            self.scanPosGen = self.nsp(self.scanPositions_int)
            # print(e)

    def nsp(self, poss):
        for p in poss:
            yield p

    def stabilizacija(self):
        print("Stabilizacija počinje")
        self.mode = 'lock'


    @staticmethod
    def temperatureConvert(b):
        # b 12 bit ADC value
        if b < 1:
            b = 1
        """
        float R1 = 10000;
        float logR2, R2, T, Tc ;
        float c1 = 1.009249522e-03, c2 = 2.378405444e-04, c3 = 2.019202697e-07;
        V = analogRead(ThermistorPin);

        R2 = R1 * (1023.0 / (float)V - 1.0);
        logR2 = log(R2);
        T = (1.0 / (c1 + c2*logR2 + c3*logR2*logR2*logR2));
        Tc = T - 273.15;
        """
        c1 = 1.009249522e-03
        c2 = 2.378405444e-04
        c3 = 2.019202697e-07
        R1 = 10000
        R2 = R1 * ((5/3.3)* 4095 / b - 1.0)
        logR2 = np.log(R2)

        return (1.0 / (c1 + c2*logR2 + c3*logR2**3))-273.15


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
