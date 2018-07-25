#!/usr/bin/env python

import numpy as np
import matplotlib.pyplot as plt
import ephem
import matplotlib.cm as cm
from matplotlib.colors import LogNorm
from mpl_toolkits.mplot3d import axes3d
from mpl_toolkits.mplot3d import Axes3D
from scipy.interpolate import interp2d
from scipy.interpolate import BivariateSpline
#RectBivariateSpline
from scipy.interpolate import griddata

def keyword_value(data_file, nline_header, key_word):
    data_file.seek(0)  # Go to the beginning of DADA file
    for iline in range(nline_header):
        line = data_file.readline()
        if key_word in line and line[0] != '#':
            mjd_start = float(line.split()[1])
            return mjd_start
    print "Can not find the keyword \"{:s}\" in header ...".format(key_word)
    exit(1)

def power(beam, time_stamp, ddir):
    # Some special case for file name
    if time_stamp == "2018-06-26-18:31:15":
        time_stamp = "2018-06-26-18:31:16"
    if time_stamp == "2018-06-26-20:59:41":
        time_stamp = "2018-06-26-20:59:42"
    if time_stamp == "2018-06-27-15:30:43":
        time_stamp = "2018-06-27-15:30:44"
    if time_stamp == "2018-06-27-16:21:04":
        time_stamp = "2018-06-27-16:21:05"

    power_fname     = "{:s}/{:s}_0000000000000000.000000.dada".format(ddir, time_stamp)
    
    hdr_size     = 4096
    power_file   = open(power_fname, "r")
    
    # To get the essential values from DADA header
    nline_header = 50  # Slightly larger than real lines
    key_word     = "MJD_START"
    mjd_start    = float(keyword_value(power_file, nline_header, key_word))
    key_word     = "TSAMP"
    tsamp        = float(keyword_value(power_file, nline_header, key_word))/1E6 # Convert to second
    key_word     = "FILE_SIZE"
    file_size    = int(keyword_value(power_file, nline_header, key_word))
    key_word     = "NCHAN"
    nchan        = int(keyword_value(power_file, nline_header, key_word))
    key_word     = "NBIT"
    nbit         = int(keyword_value(power_file, nline_header, key_word))
    nsamp        = 8 * file_size / (nchan * nbit)
    
    # Read data sample from DADA file
    power_file.seek(hdr_size)
    power_sample = np.array(np.fromstring(power_file.read(nsamp * nchan * nbit / 8), dtype='float32'))
    power_sample = np.reshape(power_sample, (nsamp, nchan))
    #time_sample  = mjd_start + tsamp * np.arange(nsamp)/86400.0 + 2*tsamp/86400.0
    time_sample  = mjd_start + tsamp * np.arange(nsamp)/86400.0 + 3.5 / 86400.0
    
    power_file.close()
    return time_sample, power_sample

def direction(beam, time_stamp, ddir, time_sample):
    direction_fname = "{:s}/{:s}.direction".format(ddir, time_stamp)
    direction_data = np.loadtxt(direction_fname)
    direction_interp = []
    direction_interp.append(np.interp(time_sample, direction_data[:,0], direction_data[:, 2 * beam + 1]))
    direction_interp.append(np.interp(time_sample, direction_data[:,0], direction_data[:, 2 * beam + 2]))
    direction_interp = np.array(direction_interp).T

    return direction_interp

def main(beam, time_stamp, ddir):
    time_sample, power_sample = power(beam, time_stamp, ddir)
    direction_sample = direction(beam, time_stamp, ddir, time_sample)

    # 3C286
    beam = ephem.FixedBody()
    src = ephem.FixedBody()
    #src._ra, src._dec = "13:31:08.3", "+30:30:33"
    #src._ra, src._dec = "13:28:49.66", "+30:45:58.3"
    src._ra, src._dec = "13:31:08.28556", "+30:30:32.4990"
    
    # Effelsberg
    eff = ephem.Observer()
    eff.long, eff.lat = '6.883611111', '50.52483333'

    direction_delta = []
    len_direction = len(direction_sample)
    for i in range(len_direction):
        beam_direction = []
        eff.date = time_sample[i] - 15019.5
        beam._ra, beam._dec = direction_sample[i,0], direction_sample[i,1]
        #beam._ra, beam._dec = "13:31:08.3", "+30:30:33"
        
        beam.compute(eff)
        src.compute(eff)

        #beam_direction.append(beam.az - src.az)
        #beam_direction.append(beam.az)
        #beam_direction.append(beam.alt * np.cos(beam.az))
        #beam_direction.append(beam.alt)
        #beam_direction.append(beam.az * np.cos(beam.alt))
        #beam_direction.append((beam.az - src.az) * np.cos(src.alt))

        beam_direction.append(beam.ra - src.ra)
        #beam_direction.append(beam.az*np.cos(beam.alt))
        beam_direction.append((beam.dec - src.dec))
        direction_delta.append(beam_direction)
    direction_delta = np.array(direction_delta)
    
    return time_sample, direction_sample, direction_delta, power_sample

if __name__ == "__main__":
    ### The first nine beams scan with small area, the focus is 430mm (SB00172_201806261745_FILT_1450_9beam.pk01.wt.hdf5)
    #beam       = 0
    #time_stamp = "2018-06-26-19:30:02"
    #beam       = 1
    #time_stamp = "2018-06-26-19:30:02"
    #beam       = 2
    #time_stamp = "2018-06-26-19:29:59"
    #beam       = 3
    #time_stamp = "2018-06-26-19:29:58"
    #beam       = 4
    #time_stamp = "2018-06-26-19:29:53"
    #beam       = 5
    #time_stamp = "2018-06-26-19:29:53"
    #beam       = 6
    #time_stamp = "2018-06-26-19:29:35"
    #beam       = 7
    #time_stamp = "2018-06-26-19:29:35"
    #beam       = 8
    #time_stamp = "2018-06-26-19:29:29"

    # The second nine beam scan with a god area, focus is 430 mm (SB00172_201806261745_FILT_1450_9beam.pk01.wt.hdf5)
    #beam       = 0
    #time_stamp = "2018-06-26-20:01:17"
    #beam       = 1
    #time_stamp = "2018-06-26-20:01:12"
    #beam       = 2
    #time_stamp = "2018-06-26-20:01:03"
    #beam       = 3
    #time_stamp = "2018-06-26-20:01:05"
    #beam       = 4
    #time_stamp = "2018-06-26-20:01:06"
    #beam       = 5
    #time_stamp = "2018-06-26-20:01:06"
    #beam       = 6
    #time_stamp = "2018-06-26-20:01:02"
    #beam       = 7
    #time_stamp = "2018-06-26-20:00:59"
    #beam       = 8
    #time_stamp = "2018-06-26-20:00:57"

    # The third nine beam scan with a good area, focus is 474mm, with the same beamweights for the first and second scan (SB00172_201806261745_FILT_1450_9beam.pk01.wt.hdf5)
    #beam       = 0
    #time_stamp = "2018-06-27-13:40:30"
    #beam       = 1
    #time_stamp = "2018-06-27-13:40:26"
    #beam       = 2
    #time_stamp = "2018-06-27-13:39:39"
    #beam       = 3
    #time_stamp = "2018-06-27-13:39:38"
    #beam       = 4
    #time_stamp = "2018-06-27-13:39:38"
    #beam       = 5
    #time_stamp = "2018-06-27-13:39:36"
    #beam       = 6
    #time_stamp = "2018-06-27-13:39:44"
    #beam       = 7
    #time_stamp = "2018-06-27-13:39:42"
    #beam       = 8
    #time_stamp = "2018-06-27-13:39:41"

    ## The forth nine beam scan with a good area, focus is 474mm, with the a new beamweights (SB00186_201806271433_FILT_1450_9beam.pk01.wt.hdf5)
    #beam       = 0
    #time_stamp = "2018-06-27-14:36:37"
    #beam       = 1
    #time_stamp = "2018-06-27-14:36:40"
    #beam       = 2
    #time_stamp = "2018-06-27-14:36:41"
    #beam       = 3
    #time_stamp = "2018-06-27-14:36:44"
    #beam       = 4
    #time_stamp = "2018-06-27-14:36:45"
    #beam       = 5
    #time_stamp = "2018-06-27-14:36:44"
    #beam       = 6
    #time_stamp = "2018-06-27-14:36:54"
    #beam       = 7
    #time_stamp = "2018-06-27-14:36:47"
    ##beam       = 8
    ##time_stamp = "2018-06-27-14:36:54"

    ### The fifth nine beam scan with a good area, focus is 335mm, with the a new beamweights (SB00187_201806271523_FILT_1450_9beam.pk01.wt.hdf5)
    #beam       = 0
    #time_stamp = "2018-06-27-15:30:28"
    #beam       = 1
    #time_stamp = "2018-06-27-15:30:30"
    #beam       = 2
    #time_stamp = "2018-06-27-15:30:31"
    #beam       = 3
    #time_stamp = "2018-06-27-15:30:34"
    #beam       = 4
    #time_stamp = "2018-06-27-15:30:38"
    #beam       = 5
    #time_stamp = "2018-06-27-15:30:37"
    #beam       = 6
    #time_stamp = "2018-06-27-15:30:43"
    #beam       = 7
    #time_stamp = "2018-06-27-15:30:42"
    #beam       = 8
    #time_stamp = "2018-06-27-15:30:44"
    
    # The sixth nine beam scan with a good area, focus is 234mm, with the a new beamweights (SB00188_201806271618_FILT_1450_9beam.pk01.wt.hdf5)
    #beam       = 0
    #time_stamp = "2018-06-27-16:21:04"
    #beam       = 1
    #time_stamp = "2018-06-27-16:21:07"
    #beam       = 2
    #time_stamp = "2018-06-27-16:21:04"
    #beam       = 3
    #time_stamp = "2018-06-27-16:21:08"
    #beam       = 4
    #time_stamp = "2018-06-27-16:21:07"
    #beam       = 5
    #time_stamp = "2018-06-27-16:21:13"
    #beam       = 6
    #time_stamp = "2018-06-27-16:21:23"
    #beam       = 7
    #time_stamp = "2018-06-27-16:21:21"
    #beam       = 8
    #time_stamp = "2018-06-27-16:21:17"

    ### The seventh nine beam scan with a good area, focus is 594mm, with the a new beamweights (SB00189_201806271729_FILT_1450_9beam.pk01.wt.hdf5)
    #beam       = 0
    #time_stamp = "2018-06-27-17:34:33"
    #beam       = 1
    #time_stamp = "2018-06-27-17:34:35"
    #beam       = 2
    #time_stamp = "2018-06-27-17:34:37"
    #beam       = 3
    #time_stamp = "2018-06-27-17:34:36"
    #beam       = 4
    #time_stamp = "2018-06-27-17:34:38"
    #beam       = 5
    #time_stamp = "2018-06-27-17:34:39"
    #beam       = 6
    #time_stamp = "2018-06-27-17:34:48"
    #beam       = 7
    #time_stamp = "2018-06-27-17:34:48"
    #beam       = 8
    #time_stamp = "2018-06-27-17:34:42"
    
    ## The eigth nine beam scan with a good area, focus is 430mm, but with a offset -66mm, the previous tests are with a offset -119mm, with the a new beamweights (SB00193_201806271920_FILT_1450_9beam)
    #beam       = 0
    #time_stamp = "2018-06-27-19:23:03"
    #beam       = 1
    #time_stamp = "2018-06-27-19:22:58"
    #beam       = 2
    #time_stamp = "2018-06-27-19:23:01"
    #beam       = 3
    #time_stamp = "2018-06-27-19:23:00"
    #beam       = 4
    #time_stamp = "2018-06-27-19:23:08"
    #beam       = 5
    #time_stamp = "2018-06-27-19:23:07"
    #beam       = 6
    #time_stamp = "2018-06-27-19:23:14"
    #beam       = 7
    #time_stamp = "2018-06-27-19:23:14"
    #beam       = 8
    #time_stamp = "2018-06-27-19:23:08"
    
    ## The ninth nine beam scan with a good area, focus is 430mm, but with a offset -167mm, with the a new beamweights (SB00194_201806272013_FILT_1450_9beam.pk01.wt.hdf5)
    #beam       = 1
    #time_stamp = "2018-06-27-20:23:04"
    #beam       = 2
    #time_stamp = "2018-06-27-20:23:05"
    #beam       = 3
    #time_stamp = "2018-06-27-20:23:02"
    #beam       = 4
    #time_stamp = "2018-06-27-20:23:10"
    #beam       = 5
    #time_stamp = "2018-06-27-20:23:07"
    #beam       = 6
    #time_stamp = "2018-06-27-20:23:15"
    #beam       = 7
    #time_stamp = "2018-06-27-20:23:18"
    #beam       = 8
    #time_stamp = "2018-06-27-20:23:13"
    
    ## The tenth nine beam scan with a good area, focus is 430mm, with the a new beamweights(SB00212_201806281948_FILT_1800_9beam)
    #beam       = 0
    #time_stamp = "2018-06-28-20:15:20"
    #beam       = 1
    #time_stamp = "2018-06-28-20:15:19"
    #beam       = 2
    #time_stamp = "2018-06-28-20:15:21"
    #beam       = 3
    #time_stamp = "2018-06-28-20:15:24"
    #beam       = 4
    #time_stamp = "2018-06-28-20:15:24"
    #beam       = 5
    #time_stamp = "2018-06-28-20:15:24"
    #beam       = 6
    #time_stamp = "2018-06-28-20:15:27"
    #beam       = 7
    #time_stamp = "2018-06-28-20:15:27"
    #beam       = 8
    #time_stamp = "2018-06-28-20:15:25"
    
    #beam       = 0
    #time_stamp = "2018-06-09-07:37:10"
    #time_stamp = "2018-06-25-20:12:41"
    #time_stamp = "2018-06-26-17:52:22"
    #time_stamp = "2018-06-26-17:59:52"
    #time_stamp = "2018-06-26-18:31:15"
    #time_stamp = "2018-06-26-18:44:48"
    #time_stamp = "2018-06-26-19:08:34"
    #time_stamp = "2018-06-26-20:59:41"
    #time_stamp = "2018-06-26-21:24:46"
    #time_stamp = "2018-06-27-22:00:58"
    #time_stamp = "2018-06-27-22:11:21"
    #time_stamp = "2018-06-27-22:45:40"
    #time_stamp = "2018-06-27-23:03:3"
    #time_stamp = "2018-06-28-00:22:10"
    #time_stamp = "2018-06-28-13:37:12"
    #time_stamp = "2018-06-28-14:00:22"
    #time_stamp = "2018-06-28-14:09:58"
    #time_stamp = "2018-06-28-14:16:53"
    #time_stamp = "2018-06-28-14:42:12"
    #time_stamp = "2018-06-28-15:22:46"
    #time_stamp = "2018-06-28-16:02:36"
    #time_stamp = "2018-06-28-16:31:30"
    #time_stamp = "2018-06-28-16:54:09"
    #time_stamp = "2018-06-28-20:06:46"
    #time_stamp = "2018-06-28-20:15:20"
    #time_stamp = "2018-06-28-22:30:25"
    #time_stamp = "2018-06-29-10:56:51"
    #time_stamp = "2018-06-29-10:56:51"
    #time_stamp = "2018-06-29-12:05:23"
    #time_stamp = "2018-06-29-12:20:17"
    #time_stamp = "2018-06-29-12:52:20"
    #time_stamp = "2018-06-29-13:07:10"
    #time_stamp = "2018-06-29-13:12:45"
    #time_stamp = "2018-06-29-13:35:38"
    #time_stamp = "2018-06-29-14:07:23"
    #time_stamp = "2018-06-29-14:26:37"
    #time_stamp = "2018-06-29-14:32:59"
    #time_stamp = "2018-06-29-14:48:04"
    #time_stamp = "2018-06-29-14:55:29"
    #time_stamp = "2018-06-29-15:04:38"
    #time_stamp = "2018-06-29-15:17:57"
    #time_stamp = "2018-06-29-15:49:37"
    #time_stamp = "2018-06-29-16:26:14"
    #time_stamp = "2018-06-29-17:44:40"
    time_stamp = "2018-06-29-19:04:15"
    time_stamp = "2018-06-29-19:11:05"
    time_stamp = "2018-06-29-20:47:34"
    time_stamp = "2018-06-29-21:17:36"
    time_stamp = "2018-06-29-21:28:56"
    time_stamp = "2018-06-30-12:58:45"
    time_stamp = "2018-06-30-13:32:19"
    time_stamp = "2018-06-30-13:57:18"
    time_stamp = "2018-06-30-17:59:09"
    time_stamp = "2018-06-30-18:05:07"
    time_stamp = "2018-06-30-18:30:50"
    
    beam = 0
    #ddir       = "/beegfs/DENG/JUNE/beam{:d}".format(beam)
    ddir       = "/beegfs/DENG/docker/beam{:d}".format(beam)
    
    time_sample, direction_sample, direction_delta, power_sample = main(beam, time_stamp, ddir)

    #time_stamp = "2018-06-29-18:13:02"
    time_sample1, direction_sample1, direction_delta1, power_sample1 = main(beam, time_stamp, ddir)
    
    freq = 200
    freq = 269
    plt.figure()
    plt.subplot(2,1,1)
    plt.plot(direction_sample[:,0] * 180/np.pi, power_sample[:,freq])
    #plt.plot(direction_sample1[:,0] * 180/np.pi, power_sample1[:,freq])
    plt.subplot(2,1,2)
    plt.plot(direction_sample[:,1] * 180/np.pi, power_sample[:,freq])
    #plt.plot(direction_sample1[:,1] * 180/np.pi, power_sample1[:,freq])
    plt.show()

    #freq = 200
    #plt.figure()
    ##plt.plot(direction_sample[:,0] * 180/np.pi, direction_sample[:,1] * 180/np.pi)
    #plt.scatter(direction_sample[:,0] * 180/np.pi, direction_sample[:,1] * 180/np.pi, c=power_sample[:, freq])#, s=500, cmap='gray')
    #plt.show()
    
    #freq = 200
    #x = direction_sample[:,0]
    #xmin = min(x)
    #xmax = max(x)
    #y = direction_sample[:,1]
    #ymin = min(y)
    #ymax = max(y)
    #z = power_sample[:,freq]

    #freq = 200
    #x = direction_sample[:,0] * 180/np.pi
    #xinterval = max(x)-min(x)
    #maxx = max(x) + xinterval * 0.1
    #minx = min(x) - xinterval * 0.1
    #y = direction_sample[:,1] * 180/np.pi
    #yinterval = max(y) - min(y)
    #maxy = max(y) + yinterval * 0.1
    #miny = min(y) - yinterval * 0.1    
    #
    #z = power_sample[:, freq]
    #
    #
    #xi = np.linspace(minx, maxx,100)
    #yi = np.linspace(miny, maxy,100)
    #X,Y= np.meshgrid(xi,yi)
    #
    ##zi = griddata((x, y), z, (xi[None,:], yi[:,None]), method='nearest')
    #zi = griddata((x, y), z, (X,Y), method='cubic')
    #
    #print zi
    #
    #plt.figure()
    #plt.imshow(zi)
    #plt.show()
