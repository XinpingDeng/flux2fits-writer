#!/usr/bin/env python

import re 
import numpy as np
import matplotlib.pyplot as plt
import ephem
import matplotlib.cm as cm
from matplotlib.colors import LogNorm
from mpl_toolkits.mplot3d import axes3d
from mpl_toolkits.mplot3d import Axes3D
from scipy.interpolate import interp2d
from scipy.interpolate import BivariateSpline
import json
import codecs

#RectBivariateSpline

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
    #time_stamp = "2018-06-26-18:31:16"
    #time_stamp = "2018-06-26-20:59:42"
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

    #time_sample  = mjd_start + tsamp * np.arange(nsamp)/86400.0 + 3.5 / 86400.0
    time_sample  = mjd_start + tsamp * np.arange(nsamp)/86400.0 
    print 0.5 * tsamp
    
    power_file.close()
    return time_sample, power_sample

def direction(beam, time_stamp, ddir, time_sample):
    direction_fname = "{:s}/{:s}.direction".format(ddir, time_stamp)

    #direction_fname = "2018-06-28-00:22:10.azel"
    #direction_fname = "2018-06-28-00:22:10.radec"
    #direction_fname = "2018-06-28-00:22:10.radec_new"
    direction_fname = "2018-06-28-22:30:25.azel"
    #direction_fname = "2018-06-28-14:16:53.azel"
    #direction_fname = "2018-06-28-14:42:12.azel"

    direction_data = np.loadtxt(direction_fname)
    #print direction_data
    direction_interp = []
    direction_interp.append(np.interp(time_sample, direction_data[:,0], direction_data[:, 2 * beam + 1]))
    direction_interp.append(np.interp(time_sample, direction_data[:,0], direction_data[:, 2 * beam + 2]))
    direction_interp = np.array(direction_interp).T

    return direction_interp

def metadata_azel(beam, time_stamp, ddir):
    metadata_fname = "{:s}/{:s}.metadata".format(ddir, time_stamp)
    
    lines = codecs.open(metadata_fname, encoding='utf-8').readlines()
    for line in lines:
        #print (line.split(":")[49].split(']')[0].split('[')[1].split(',')[0].encode("ascii","ignore")), (line.split(":")[49].split(']')[0].split('[')[1].split(',')[1].split(' ')[1].encode("ascii","ignore"))
        print (line.split(":")[50].split(']')[0].split('[')[1].split(',')[0].encode("ascii","ignore")), (line.split(":")[50].split(']')[0].split('[')[1].split(',')[1].split(' ')[1].encode("ascii","ignore"))        
        
    ##print line
    ###print line['target_name']
    ##
    ##exit()
    #
    ##lines = open(metadata_fname).readlines()
    ##for line in lines:
    ##    #print line.split(':')#.index('target_name')
    ##    print dict(lines)
    ##    exit()
    ##    
    ##data = json.loads(dict(json_data[0]))
    #
    ##print json_data
    ##exit()
    #
    ###json.load()
    ##with open(metadata_fname) as json_data:
    #with codecs.open(metadata_fname, encoding='utf-8') as json_data:
    #    commands = dict(re.findall(r'(\S+)\s+(.+)', json_data.read()))
    #    print commands['target_name']
    #    #print json.loads(json.dumps(commands))['target_name']
    #    
    ##    
    ##    #data = 
    ##    #print json.dumps(commands, indent=2, sort_keys=True)
    ##    #print commands.keys()#['target_name']
    ##    
    ##    #print commands['target_name']
        
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
    beam       = 0

    #time_stamp = "2018-06-28-00:22:10"   
    time_stamp = "2018-06-28-22:30:25"
    #time_stamp = "2018-06-28-14:16:53"
    #time_stamp = "2018-06-28-14:42:12"
    
    #ddir       = "/beegfs/DENG/JUNE/beam{:d}".format(beam)
    ddir       = "/beegfs/DENG/docker/beam{:d}".format(beam)
    
    time_sample, direction_sample, direction_delta, power_sample = main(beam, time_stamp, ddir)
    
    freq = 210
    plt.figure()
    plt.subplot(2,1,1)
    plt.plot(direction_sample[:,0] * 180.0/np.pi * 60.0, power_sample[:,freq])
    #plt.plot(direction_delta[:,0] * 180.0/np.pi * 60.0, power_sample[:,freq])
    plt.subplot(2,1,2)
    plt.plot(direction_sample[:,1] * 180.0/np.pi * 60.0, power_sample[:,freq])
    #plt.plot(direction_delta[:,1] * 180.0/np.pi * 60.0, power_sample[:,freq])
    plt.show()

    plt.figure()
    plt.plot(direction_sample[:,0], direction_sample[:,1])
    plt.show()
    
    #metadata_azel(beam, time_stamp, ddir)

    #data = np.loadtxt("2018-06-28-00:22:10.azel")
    #plt.figure()
    #plt.plot(data[:,0], data[:,1])
    #plt.plot(data[:,0], data[:,2])
    #plt.plot(data[:,1], data[:,2])
    #plt.show()
