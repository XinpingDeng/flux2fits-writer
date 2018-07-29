#!/usr/bin/env python

import os
import numpy as np
import matplotlib.pyplot as plt

fdir  = "/beegfs/DENG/JULY"
fname = "flux2udp.bin35"

fname = os.path.join(fdir, fname)
f = open(fname, "r")

nchan = np.fromstring(f.read(4), dtype='int32')
flux = np.fromstring(f.read(nchan[0] * 4), dtype='float32')
tsamp = np.fromstring(f.read(4), dtype='float32')
utc_time = np.fromstring(f.read(28), dtype='c')
beam = np.fromstring(f.read(4), dtype='int32')

ra = np.fromstring(f.read(4), dtype='float32')
dec = np.fromstring(f.read(4), dtype='float32')
mjd_i = np.fromstring(f.read(4), dtype='int32')
mjd_f = np.fromstring(f.read(4), dtype='float32')
az = np.fromstring(f.read(4), dtype='float32')
el = np.fromstring(f.read(4), dtype='float32')

print tsamp, utc_time, beam, ra, dec, mjd_i, mjd_f, az, el

plt.figure()
plt.plot(flux)
plt.show()

f.close()
