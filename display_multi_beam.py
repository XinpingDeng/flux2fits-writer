#!/usr/bin/env python

from scipy.interpolate import griddata
import matplotlib.pyplot as plt
import numpy as np
import ephem

def keyword_value(data_file, nline_header, key_word):
    data_file.seek(0)  # Go to the beginning of DADA file
    for iline in range(nline_header):
        line = data_file.readline()
        if key_word in line and line[0] != '#':
            mjd_start = float(line.split()[1])
            return mjd_start
    print "Can not find the keyword \"{:s}\" in header ...".format(key_word)
    exit(1)

def power_cal(beam, time_stamp, ddir):
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
    power = np.array(np.fromstring(power_file.read(nsamp * nchan * nbit / 8), dtype='float32'))
    power = np.reshape(power, (nsamp, nchan))
    time  = mjd_start + tsamp * np.arange(nsamp)/86400.0 + 3.5 / 86400.0
    
    power_file.close()
    return time, power

def direction_cal(beam, time_stamp, ddir, time):
    direction_fname = "{:s}/{:s}.direction".format(ddir, time_stamp)
    direction_data = np.loadtxt(direction_fname)
    #plt.figure()
    #plt.subplot(2,1,1)
    #plt.plot(direction_data[:,1])
    #plt.subplot(2,1,2)
    #plt.plot(direction_data[:,2])
    #plt.show()
    
    direction_interp = []
    direction_interp.append(np.interp(time, direction_data[:,0], direction_data[:, 2 * beam + 1]))
    direction_interp.append(np.interp(time, direction_data[:,0], direction_data[:, 2 * beam + 2]))
    direction_interp = np.array(direction_interp).T

    return direction_interp

def coord_conv(src, point, direction, time):
    ndata = len(time)
    direction_convert = []
    for i in range(ndata):
        eff.date = time[i] - 15019.5
        point._ra, point._dec = direction[i,0], direction[i,1]

        point.compute(eff)
        src.compute(eff)

        direction_convert.append([point.az - src.az, point.alt - src.alt])
    return np.array(direction_convert)

def del_outliner(time, direction, power, limit):
    ndata = len(time)
    direction_array = np.asarray(direction)
    print direction_array

    #plt.figure()
    #plt.subplot(2,1,1)
    #plt.plot(direction_array[:,0])
    #plt.ylim(-limit, limit)
    #plt.subplot(2,1,2)
    #plt.plot(direction_array[:,1])
    #plt.ylim(-limit, limit)
    #plt.show()

    remove = 0
    for i in range(ndata):
        if (abs(direction_array[i,0]) > limit) or (abs(direction_array[i,1]) > limit):
            del time[i - remove]
            del direction[i - remove]
            del power[i -remove]
            remove = remove + 1
    return time, direction, power

def main(time_stamps, base_dir, src, point, coord, limit, freq):
    beam          = 0
    time_all      = []
    power_all     = []
    direction_all = []
    
    for time_stamp in time_stamps:
        ddir        = "{:s}/beam{:d}".format(base_dir, beam)
        time, power = power_cal(beam, time_stamp, ddir)
        direction   = direction_cal(beam, time_stamp, ddir, time)
        print "Working on {:s}".format(ddir)
        
        #plt.figure()
        #plt.subplot(2,1,1)
        #plt.plot(direction[:,0])
        #plt.subplot(2,1,2)
        #plt.plot(direction[:,1])
        #plt.show()
        
        if coord == 1:
            direction = coord_conv(src, point, direction, time)
            print direction
            
        beam  = beam + 1

        time_all.extend(time)
        direction_all.extend(direction  * 180 / np.pi)
        power_all.extend(power)
        
    time_all, direction_all, power_all = del_outliner(time_all, direction_all, power_all, limit)    
    time_all      = np.asarray(time_all)
    direction_all = np.asarray(direction_all)
    power_all     = np.asarray(power_all)

    nsamp = len(time_all)/len(time_stamps)
    x     = direction_all[:,0]
    y     = direction_all[:,1]
    z     = power_all[:, freq]

    #plt.figure()
    #plt.subplot(2,1,1)
    #plt.plot(x, z)
    #plt.subplot(2,1,2)
    #plt.plot(y, z)
    #plt.show()
    
    xinterval = max(x)-min(x)
    maxx = max(x) - xinterval * 0.1
    minx = min(x) + xinterval * 0.1
    yinterval = max(y) - min(y)
    maxy = max(y) - yinterval * 0.1
    miny = min(y) + yinterval * 0.1
    xi = np.linspace(minx, maxx, nsamp)
    yi = np.linspace(miny, maxy, nsamp)

    X,Y= np.meshgrid(xi,yi)

    zi = griddata((x, y), z, (X,Y), method='linear')
    
    plt.figure()
    plt.imshow(zi, interpolation = 'hanning')#, extent=[-35, 35, -35, 35])
    plt.xlabel("Azimuth offset (arcmin)")
    plt.ylabel("Elevation offset (arcmin)")
    plt.show()

if __name__ == "__main__":
    #time_stamps=['2018-06-26-20:01:17',
                 #'2018-06-26-20:01:12',
                 #'2018-06-26-20:01:03',
                 #'2018-06-26-20:01:05',
                 #'2018-06-26-20:01:06',
                 #'2018-06-26-20:01:06',
                 #'2018-06-26-20:01:02',
                 #'2018-06-26-20:00:59',
                 #'2018-06-26-20:00:57'
    #]
    
    time_stamps = ["2018-06-29-17:44:40"]
    
    time_stamps = ['2018-06-26-19:30:02',
    #               '2018-06-26-19:30:02',
    #               '2018-06-26-19:29:59',
    #               '2018-06-26-19:29:58',
    #               '2018-06-26-19:29:53',
    #               '2018-06-26-19:29:53',
    #               '2018-06-26-19:29:35',
    #               '2018-06-26-19:29:35',
    #               '2018-06-26-19:29:29'
    ]

    base_dir = '/beegfs/DENG/docker'
    limit = 36.0/60.0
    #limit = 1
    freq = 200
    
    # Source and tracking point
    point = ephem.FixedBody()
    src   = ephem.FixedBody()
    src._ra, src._dec = "13:31:08.28556", "+30:30:32.4990" # 3C286
    coord = 1   # coord = 1 means we need to do coordinate conversion
    
    # Effelsberg
    eff = ephem.Observer()
    eff.long, eff.lat = '6.883611111', '50.52483333'
    
    main(time_stamps, base_dir, src, point, coord, limit, freq)
