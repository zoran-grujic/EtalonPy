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

import class_centralWidget

import class_MySerial

from PyQt5 import QtCore  # conda install pyqt
# from PyQt5.QtCore import Qt
from PyQt5 import QtGui
from PyQt5 import QtWidgets


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        logging.basicConfig(filename='log/app.log', filemode='a',
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=20)

        self.setWindowIcon(QtGui.QIcon('images/S-Speach-Bubble-256x256-icon.png'))

        self.setMinimumSize(QtCore.QSize(1000, 600))  # Set sizes
        self.setWindowTitle("Etalon kontroler")  # Set the window title

        # -----------------------------------------------------
        #
        #                  Status bar - bottom of the window
        #
        # -----------------------------------------------------
        self.status = self.statusBar()
        self.status.showMessage('Ready')

        # -----------------------------------------------------
        #
        #                  Central widget
        #
        # -----------------------------------------------------
        self.centralWidget = class_centralWidget.MainForm(self)  # give reference of the parent
        self.setCentralWidget(self.centralWidget)

        self.show()


##############################################################################################
#
#                    Start main code
#
##############################################################################################


def main():

    app = QtWidgets.QApplication(sys.argv)
    # import BreezeStyleSheets.breeze_resources  #  https://github.com/Alexhuszagh/BreezeStyleSheets
    # app.setStyle(QtWidgets.QStyleFactory.create('WindowsXP'))
    # print(QtWidgets.QStyleFactory.keys())  # ['Windows', 'WindowsXP', 'WindowsVista', 'Fusion']
    # app.exec_()  # execute connectingForm until closed
    # file = QtCore.QFile(":/light.qss")
    # file.open(QtCore.QFile.ReadOnly | QtCore.QFile.Text)
    # stream = QtCore.QTextStream(file)
    # app.setStyleSheet(stream.readAll())
    MainWindow()
    sys.exit(app.exec_())
    # del mf


if __name__.endswith('__main__'):
    main()
