#  Copyright (c) 2019.
#  This code has been produced by Zoran D. Grujic and by the knowledge found on The Internet.
#  Please feel free to ask me for permission to use my code in your own projects. It is for your own well fare!

# -*- coding: utf-8 -*-
"""
Created on Fri Dec  2 18:49:30 2016

@author: GrujicZ
"""
from PyQt5 import QtCore


class signal(QtCore.QObject):
    addADCsignal = QtCore.pyqtSignal()
    pinComboADCsignal = QtCore.pyqtSignal()
    addDIGsignal = QtCore.pyqtSignal()
    pinComboDIGsignal = QtCore.pyqtSignal()
    enableEEPROMsignal = QtCore.pyqtSignal()