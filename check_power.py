#!/usr/bin/env python

import os
import numpy as np
import matplotlib.pyplot as plt

fdir    = "/beegfs/DENG/JUNE"
fname   = "2018-04-17-19:22:11_0000000000000000.000000.dada"
#fname   = "2018-06-07-13:30:48_0000000000026880.000000.dada"
#fname   = "2018-06-08-10:07:53_0000000000000000.000000.dada"

nchan   = 336
dsize   = 4
hdrsize = 4096

fname = os.path.join(fdir, fname)
f = open(fname, "r")

plt.figure()
f.seek(hdrsize)
#while True:
for i in range(20):
    sample = np.array(np.fromstring(f.read(nchan * dsize), dtype='float32'))
    plt.plot(sample)
plt.show()
#sample = np.array(np.fromstring(f.read(nchan * dsize), dtype='float32'))
#plt.plot(sample)
f.close()
