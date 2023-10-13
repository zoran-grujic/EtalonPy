#  Copyright (c) 2019.
#  This code has been produced by Zoran D. Grujic and by the knowledge found on The Internet.
#  Please feel free to ask me for permission to use my code in your own projects. It is for your own well fare!
#  pyinstaller --onefile -w app.pyw

import sys
import logging
from PyQt5 import QtCore  # conda install pyqt
# from PyQt5.QtCore import Qt
from PyQt5 import QtGui
from PyQt5 import QtWidgets
import qdarkgraystyle  #  https://pypi.org/project/qdarkgraystyle/

import class_centralWidget
# import class_signal


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        logging.basicConfig(filename='log/app.log', filemode='a',
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=20)

        self.setWindowIcon(QtGui.QIcon('images/S-Speach-Bubble-256x256-icon.png'))

        self.setMinimumSize(QtCore.QSize(1000, 600))  # Set sizes
        self.setWindowTitle("HeNe standard controller")  # Set the window title

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
        self.centralWidget.setMouseTracking(True)

        self.show()


##############################################################################################
#
#                    Start main code
#
##############################################################################################


def main():

    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkgraystyle.load_stylesheet())

    MainWindow()
    sys.exit(app.exec_())
    # del mf


if __name__.endswith('__main__'):
    main()
