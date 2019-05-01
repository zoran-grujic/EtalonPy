#  Copyright (c) 2019.
#  This code has been produced by Zoran D. Grujic and by the knowledge found on The Internet.
#  Please feel free to ask me for permission to use my code in your own projects. It is for your own well fare!

from collections import deque
import numpy as np
# from collections import Counter


class CircularBuffer(deque):
    def __init__(self, size=0):
        super(CircularBuffer, self).__init__(maxlen=size)

    # @property
    def average(self):  # TODO: Make type check for integer or floats
        try:
            return np.average(list(self))

        except Exception as e:
            print("CB:average error" + str(e))
            return 1

    def std(self):
        # print(self)
        return np.std(list(self))