#  Copyright (c) 2019.
#  This code has been produced by Dr Zoran D. Grujic and by the knowledge found on The Internet.
#  Please feel free to ask me for permission to use my code in your own projects. It is for your own well fare!

import serial
import class_signal
import sys
import glob
import logging
import time


class MySerial:
    # define start values, constants
    baud = 250000
    time_out = .5
    port = ""
    boxNamePrefix = "Etalon lock-in"
    name = ""
    boxSettings = False  # have settings from box
    box = False  # serial port object
    status = ""
    connected = False

    sig = class_signal.signal()

    def __init__(self):
        pass

    def connect(self):
        """Connect to sanity box"""
        if self.connected:
            return

        ports = self.serial_ports()

        for port in ports:
            try:
                # dsrdtr=True  # no auto reset of the controller!!!
                self.box = serial.Serial(port, self.baud, timeout=self.time_out, dsrdtr=True)  # connect to port
                # print("Port name:", port)
                self.sendToBox("")  # prvi mačići se u vodu bacaju. Prva komanda "nestane", ne bude primljena.
                time.sleep(.01)
                self.box.reset_input_buffer()
                self.sendToBox("ko?")  # Pitamo COM port ko je tamo
                for i in range(10):
                    line = self.readLine()
                    logging.info('%i: PORT: %s : %s', i, port, line)
                    print(i, ": PORT: ", port, ": ", line)
                    # print(line[:len(self.boxName)])
                    if line[:len(self.boxNamePrefix)] == self.boxNamePrefix:
                        self.name = line
                        # print("Yes, connected to the Sanity box!")
                        self.port = port

                        self.status = "connected"
                        self.connected = True
                        return True

                self.box.close()
            except Exception as e:
                logging.error(str(e))

        return False
        # end findAndConnect

    def readLine(self):
        """Remove \r\n from the end of line """
        return self.box.readline().decode("ascii")[:-2]  # "utf-8"

    def sendToBox(self, stri):
        """Prepare string to be sent to the box,
           add \n at the end or box will wait 1s to get it before continuing...
        """
        # print("sendToBox")
        stri = stri.encode("utf-8")
        # print("Send to box: ",str)
        self.box.write(stri + b'\n')  # + b'\r'

    @staticmethod
    def serial_ports():
        """ Lists serial port names

        :raises: EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
        """
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []
        for port in ports:
            try:
                s = serial.Serial(port, dsrdtr=True)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result
    # end serial_ports()

