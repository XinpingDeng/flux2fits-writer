#!/usr/bin/env python

# ./flux2fits-writer.py -a flux2fits-writer.conf -b /beegfs/DENG/AUG/ -c 0 -d 0 -e 10 -f 0.064 -g 134.104.70.90:17106 -i 224.1.1.1:5007

import os
import time
import threading
import ConfigParser
import argparse
import socket
import json
import struct
import sys
import datetime
import pytz
import ephem

if __name__ == "__main__":
    # Read in command line arguments
    parser = argparse.ArgumentParser(description='Convert baseband data into flux')
    parser.add_argument('-a', '--config_fname', type=str, nargs='+',
                        help='The name of configuration file')
    parser.add_argument('-b', '--directory', type=str, nargs='+',
                        help='In which directory we record the data and read configuration files and parameter files')
    parser.add_argument('-c', '--numa', type=int, nargs='+',
                        help='On which numa node we do the work, 0 or 1')
    parser.add_argument('-d', '--visible_gpu', type=str, nargs='+',
                        help='Visible GPU, the parameter is for the usage inside docker container.')
    parser.add_argument('-e', '--length', type=float, nargs='+',
                        help='Length of data capture.')
    parser.add_argument('-f', '--integration', type=float, nargs='+',
                        help='Integration time for flux in seconds.')    
    parser.add_argument('-g', '--interface', type=str, nargs='+',
                        help='Interface to send the data (IP and port number, ip:port).')
    parser.add_argument('-i', '--multicast', type=str, nargs='+',
                        help='Multicast interface to receive metadata from TOS (IP and port number, ip:port).')
    
    args = parser.parse_args()

    config_fname   = args.config_fname[0]
    directory      = args.directory[0]
    numa           = args.numa[0]
    visible_gpu    = args.visible_gpu[0]
    length         = args.length[0]
    integration    = args.integration[0]
    interface      = args.interface[0]
    multicast      = args.multicast[0]
    
    image_name     = "phased-array-feed"
    container_name = "flux2fits-writer"
    script_name    = "/home/pulsar/xinping/flux2fits-writer/flux2fits-writer-entry.py"
    config_fname   = "/home/pulsar/xinping/flux2fits-writer/{:s}".format(config_fname)
    
    uid = 50000
    gid = 50000
    hdir = "/home/pulsar"
    dvolume = '{:s}:{:s}'.format(directory, directory)
    hvolume = '{:s}:{:s}'.format(hdir, hdir)

    command_line = "docker run --rm -it --net=host -v {:s} -v {:s} -u {:d}:{:d} --cap-add=IPC_LOCK --ulimit memlock=-1:-1 --name {:s} xinpingdeng/{:s} \"{:s} -a {:s} -b {:s} -c {:d} -d {:s} -e {:f} -f {:f} -g {:s} -i {:s}\"".format(dvolume, hvolume, uid, gid, container_name, image_name, script_name, config_fname, directory, numa, visible_gpu, length, integration, interface, multicast)
    print command_line
    os.system(command_line)

    print "\n\n\nDONE!!!\n"
