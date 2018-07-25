#!/usr/bin/env python

import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
from scipy.interpolate import interp2d

time_stamps = ["2018-06-27-13:40:30",
               "2018-06-27-13:40:26",
               "2018-06-27-13:39:39",
               "2018-06-27-13:39:38",
               "2018-06-27-13:39:38",
               "2018-06-27-13:39:36",
               "2018-06-27-13:39:44",
               "2018-06-27-13:39:42",
               "2018-06-27-13:39:41"]

nbeam = 9

direction = []
data = []
for i in range(nbeam):
    data_single = np.loadtxt("{:s}.beam{:d}".format(time_stamps[i], i))
    data.append(data_single)
    direction.extend(data_single[:,0:2])

nintep = np.shape(data)[1]

data      = np.asarray(data)
direction = np.asarray(direction)

maxx, minx = max(direction[:,0]), min(direction[:,0])
maxy, miny = max(direction[:,1]), min(direction[:,1])

print minx, maxx
print miny, maxy

xi = np.linspace(minx, maxx, nintep)
yi = np.linspace(miny, maxy, nintep)
#X, Y = np.meshgrid(xi,yi)

freq = 210
nbeam = np.shape(data)[0]
result = np.zeros(np.shape(X))
for i in range(nbeam):
    print i
    #result = result + griddata((data[:, 0], data[:, 1]), data[:, freq + 2], (X,Y), method='linear')
    f = interp2d(data[:, 0], data[:, 1], data[:, freq + 2], kind='cubic')
    result = result + f(xi , yi)
    
print np.shape(data)
print np.shape(direction)

plt.figure()
plt.plot(result)
plt.show()
