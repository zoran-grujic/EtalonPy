#  Copyright (c) 2019.
#  This code has been produced by Zoran D. Grujic and by the knowledge found on The Internet.
#  Please feel free to ask me for permission to use my code in your own projects. It is for your own well fare!

import sys
#from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
#from matplotlib.figure import Figure
#import matplotlib
#import matplotlib.pyplot as pyplot
import numpy as np
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QSizePolicy


class MatplotlibWidget(QtWidgets.QWidget):
    """
    Simple class to make PyQT5 widget from the matplotlib plot.
    Variable 'self.plt' is accessible from parent to set additional properties if needed.
    """
    colors = ['blue', 'green', 'red', 'cyan']
    line = "-"
    xLabel = False
    yLabel = False
    hLines = []
    vLines = []

    def __init__(self, width=4, height=4, parent=None):
        super(MatplotlibWidget, self).__init__(parent)
        pyplot.style.use('dark_background')  # set dark theme # pip install qdarkgraystyle
        pyplot.subplots(constrained_layout=False)

        # self.figure = Figure(figsize=(width, height))
        self.figure = Figure(constrained_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.mpl_connect('pick_event', self.onpick)

        self.plt = self.figure.add_subplot(111)

        self.layout = QtWidgets.QHBoxLayout(self)#QVBoxLayout
        self.layout.addWidget(self.canvas)
        self.setLayout(self.layout)


    def set(self):
        if self.xLabel is not False:
            self.plt.set_xlabel(self.xLabel)
        if self.yLabel is not False:
            self.plt.set_ylabel(self.yLabel)
        if len(self.hLines) > 0:
            for h in self.hLines:
                self.plt.axhline(h)
        if len(self.vLines) > 0:
            for v in self.vLines:
                self.plt.axvline(v)

    def plot(self, x, y=[], line='o', clear=True):
        # print("on_threadPlot_plotNowSignal: enter")
        if clear:
            self.plt.clear()
        if line != 'o':
            self.line = line
        self.set()
        if len(y) == 0:
            self.plt.plot(x, self.line, picker=500)
        else:
            self.plt.plot(x, y, self.line, picker=500)

        #self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        #self.canvas.updateGeometry()
        self.canvas.draw()

    def plot_date(self, x, y, line = 'o'):
        #print("on_threadPlot_plotNowSignal: enter")
        self.plt.clear()
        self.set()
        x=matplotlib.dates.num2date(np.divide(x, 3600*24)+1)
        #print(x)
        self.plt.plot_date(x, y, line)
        self.canvas.draw()

    def plotHistogram(self, *argv):
        #print("on_threadPlot_plotNowSignal: enter")
        self.plt.clear()
        self.set()

        i = 0
        for sample in argv:
            n, bins, patches = self.plt.hist(sample, 20, normed=1, facecolor=self.colors[i], alpha=0.75)
            i += 1
            """
            print(n )
            print(bins)
            print(patches)"""

        self.canvas.draw()

    """
    Detektuje poziciju klika miša na grafiku
    """
    def onpick(self, event):

        mouseevent = event.mouseevent
        artist = event.artist

        print(mouseevent)
        print(artist)


if __name__ == "__main__":
    #run the script

    app = QApplication(sys.argv)
    mw = MatplotlibWidget(10,2)
    mu, sigma = 100, 15
    x = mu + sigma*np.random.randn(10000)
    #mw.plot(x)
    mw.plotHistogram(x)
    mw.show()
    sys.exit(app.exec())
