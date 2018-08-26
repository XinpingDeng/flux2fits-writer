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

def ConfigSectionMap(cfname, section):
    Config = ConfigParser.ConfigParser()
    Config.read(cfname)
    
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            if dict1[option] == -1:
                DebugPrint("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            dict1[option] = None
    return dict1

def capture(capture_key, capture_sod, capture_ndf, hdr, nic, capture_hfname, capture_efname, freq, length, directory, source_name, ra, dec):
    time.sleep(10) # Wait until the rest software ready
    os.system("/home/pulsar/xinping/flux2fits-writer/paf_capture -a {:s} -b {:s} -c {:d} -d {:d} -e {:d} -f {:s} -g {:s} -i {:f} -j {:f} -k {:s} -l {:s} -m {:s} -n {:s}".format(capture_key, capture_sod, capture_ndf, hdr, nic, capture_hfname, capture_efname, freq, length, directory, source_name, ra, dec))

def baseband2flux(baseband2flux_cpu, capture_key, baseband2flux_key, directory, numa, capture_ndf, baseband2flux_nchan, baseband2flux_sod, multi_gpu):
    if multi_gpu:
        print ('taskset -c {:d} /home/pulsar/xinping/flux2fits-writer/paf_baseband2flux -a {:s} -b {:s} -c {:s} -d {:d} -e {:d} -f {:d} -g {:d}'.format(baseband2flux_cpu, capture_key, baseband2flux_key, directory, numa, capture_ndf, baseband2flux_nchan, baseband2flux_sod))
        os.system('taskset -c {:d} /home/pulsar/xinping/flux2fits-writer/paf_baseband2flux -a {:s} -b {:s} -c {:s} -d {:d} -e {:d} -f {:d} -g {:d}'.format(baseband2flux_cpu, capture_key, baseband2flux_key, directory, numa, capture_ndf, baseband2flux_nchan, baseband2flux_sod))
    else:
        print ('taskset -c {:d} /home/pulsar/xinping/flux2fits-writer/paf_baseband2flux -a {:s} -b {:s} -c {:s} -d {:d} -e {:d} -f {:d} -g {:d}'.format(baseband2flux_cpu, capture_key, baseband2flux_key, directory, 0, capture_ndf, baseband2flux_nchan, baseband2flux_sod))
        os.system('taskset -c {:d} /home/pulsar/xinping/flux2fits-writer/paf_baseband2flux -a {:s} -b {:s} -c {:s} -d {:d} -e {:d} -f {:d} -g {:d}'.format(baseband2flux_cpu, capture_key, baseband2flux_key, directory, 0, capture_ndf, baseband2flux_nchan, baseband2flux_sod))
            
def flux2udp(flux2udp_cpu, baseband2flux_key, directory, ip_udp, port_udp, multicast_group, multicast_port):
    print "taskset -c {:d} /home/pulsar/xinping/flux2fits-writer/paf_flux2udp -a {:s} -b {:s} -c {:s} -d {:d} -e {:s} -f {:d} ".format(flux2udp_cpu, baseband2flux_key, directory, ip_udp, port_udp, multicast_group, multicast_port)
    os.system("taskset -c {:d} /home/pulsar/xinping/flux2fits-writer/paf_flux2udp -a {:s} -b {:s} -c {:s} -d {:d} -e {:s} -f {:d}  ".format(flux2udp_cpu, baseband2flux_key, directory, ip_udp, port_udp, multicast_group, multicast_port))
    
def dbdisk(dbdisk_cpu, baseband2flux_key, directory):
    print ('dada_dbdisk -b {:d} -k {:s} -D {:s} -W -s -d'.format(dbdisk_cpu, baseband2flux_key, directory))
    os.system('dada_dbdisk -b {:d} -k {:s} -D {:s} -W -s -d'.format(dbdisk_cpu, baseband2flux_key, directory))
    
def main(args):
    cfname           = args.cfname[0]
    numa             = args.numa[0]
    nic              = numa + 1
    visiblegpu       = args.visiblegpu[0]
    directory        = args.directory[0]
    length           = args.length[0]
    integration      = args.integration[0]
    interface        = args.interface[0]
    ip_udp, port_udp = interface.split(":")[0], int(interface.split(":")[1])

    multicast                        = args.multicast[0]
    multicast_group, multicast_port = multicast.split(":")[0], int(multicast.split(":")[1])
    
    # Bind to multicast
    #multicast_group = '224.1.1.1'
    #multicast_port = 5007
    server_address = ('', multicast_port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Create the socket

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(server_address) # Bind to the server address

    group = socket.inet_aton(multicast_group)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)  # Tell the operating system to add the socket to the multicast group on all interfaces.
    pkt, address = sock.recvfrom(1<<16)
    data = json.loads(pkt)

    hdr         = 0
    freq        = float(data['sky_frequency'])
    source_name = str(data['target_name'])
    ra          = str(ephem.hours(float(data['pk01']['actual_radec'][0])))
    dec         = str(ephem.degrees(float(data['pk01']['actual_radec'][1])))
        
    if(visiblegpu==''):
        multi_gpu = 1;
    elif(visiblegpu=='all'):
        multi_gpu = 1;
    else:
        multi_gpu = 0;
    
    # Basic configuration
    nsamp_df     = int(ConfigSectionMap(cfname, "BasicConf")['nsamp_df'])
    npol_samp    = int(ConfigSectionMap(cfname, "BasicConf")['npol_samp'])
    ndim_pol     = int(ConfigSectionMap(cfname, "BasicConf")['ndim_pol'])
    nchk_nic     = int(ConfigSectionMap(cfname, "BasicConf")['nchk_nic'])
    ncpu_numa    = int(ConfigSectionMap(cfname, "BasicConf")['ncpu_numa'])
    tdf_sec      = float(ConfigSectionMap(cfname, "BasicConf")['tdf_sec'])
    
    # Capture configuration
    capture_ncpu    = int(ConfigSectionMap(cfname, "CaptureConf")['ncpu'])
    capture_nbuf    = ConfigSectionMap(cfname, "CaptureConf")['nblk']
    capture_key     = ConfigSectionMap(cfname, "CaptureConf")['key']
    capture_key     = format(int("0x{:s}".format(capture_key), 0) + 2 * nic, 'x')
    capture_kfname  = "{:s}_nic{:d}.key".format(ConfigSectionMap(cfname, "CaptureConf")['kfname_prefix'], nic)
    capture_efname  = ConfigSectionMap(cfname, "CaptureConf")['efname']
    capture_hfname  = ConfigSectionMap(cfname, "CaptureConf")['hfname']
    capture_nreader = ConfigSectionMap(cfname, "CaptureConf")['nreader']
    capture_sod     = ConfigSectionMap(cfname, "CaptureConf")['sod']

    capture_ndf     = int(integration / tdf_sec) - int(integration / tdf_sec) % 32 # 32 = (4 * BLKSZ_SUM1) / NSAMP_DF, from the baseband2flux.cu
    capture_rbufsz  = capture_ndf *  nchk_nic * 7168
    
    # baseband2flux configuration
    baseband2flux_key        = ConfigSectionMap(cfname, "Baseband2fluxConf")['key']
    baseband2flux_kfname     = "{:s}.key".format(ConfigSectionMap(cfname, "Baseband2fluxConf")['kfname_prefix'])
    baseband2flux_key        = format(int("0x{:s}".format(baseband2flux_key), 0), 'x')
    baseband2flux_sod        = int(ConfigSectionMap(cfname, "Baseband2fluxConf")['sod'])
    baseband2flux_nreader    = ConfigSectionMap(cfname, "Baseband2fluxConf")['nreader']
    baseband2flux_nbuf       = ConfigSectionMap(cfname, "Baseband2fluxConf")['nblk']
    baseband2flux_nchan      = int(ConfigSectionMap(cfname, "Baseband2fluxConf")['nchan'])
    baseband2flux_nbyte      = int(ConfigSectionMap(cfname, "Baseband2fluxConf")['nbyte'])
    baseband2flux_rbufsz     = baseband2flux_nchan * baseband2flux_nbyte
    baseband2flux_cpu        = ncpu_numa * numa + capture_ncpu
    
    # Dbdisk configuration
    dbdisk_cpu = ncpu_numa * numa + capture_ncpu + 1

    # flux2udp configuration
    flux2udp_cpu = ncpu_numa * numa + capture_ncpu + 1
    
    # Create key files
    # and destroy share memory at the last time
    # this will save prepare time for the pipeline as well
    capture_key_file = open(capture_kfname, "w")
    capture_key_file.writelines("DADA INFO:\n")
    capture_key_file.writelines("key {:s}\n".format(capture_key))
    capture_key_file.close()

    # Create key files
    # and destroy share memory at the last time
    # this will save prepare time for the pipeline as well
    baseband2flux_key_file = open(baseband2flux_kfname, "w")
    baseband2flux_key_file.writelines("DADA INFO:\n")
    baseband2flux_key_file.writelines("key {:s}\n".format(baseband2flux_key))
    baseband2flux_key_file.close()

    os.system("dada_db -l -p -k {:s} -b {:d} -n {:s} -r {:s}".format(capture_key, capture_rbufsz, capture_nbuf, capture_nreader))
    os.system("dada_db -l -p -k {:s} -b {:d} -n {:s} -r {:s}".format(baseband2flux_key, baseband2flux_rbufsz, baseband2flux_nbuf, baseband2flux_nreader))

    t_capture       = threading.Thread(target = capture, args = (capture_key, capture_sod, capture_ndf, hdr, nic, capture_hfname, capture_efname, freq, length, directory, source_name, ra, dec,))
    t_baseband2flux = threading.Thread(target = baseband2flux, args = (baseband2flux_cpu, capture_key, baseband2flux_key, directory, numa, capture_ndf, baseband2flux_nchan, baseband2flux_sod, multi_gpu,))
    t_dbdisk         = threading.Thread(target = dbdisk, args = (dbdisk_cpu, baseband2flux_key, directory,))
    t_flux2udp      = threading.Thread(target = flux2udp, args = (flux2udp_cpu, baseband2flux_key, directory, ip_udp, port_udp, multicast_group, multicast_port, ))

    t_capture.start()
    t_baseband2flux.start()
    #t_dbdisk.start()
    t_flux2udp.start()

    t_capture.join()
    t_baseband2flux.join()
    #t_dbdisk.join()
    t_flux2udp.join()

    os.system("dada_db -d -k {:s}".format(capture_key))
    os.system("dada_db -d -k {:s}".format(baseband2flux_key))
    
if __name__ == "__main__":
    # Read in command line arguments
    parser = argparse.ArgumentParser(description='Convert baseband data into flux')
    parser.add_argument('-a', '--cfname', type=str, nargs='+',
                        help='The name of configuration file')
    parser.add_argument('-b', '--directory', type=str, nargs='+',
                        help='In which directory we record the data and read configuration files and parameter files')
    parser.add_argument('-c', '--numa', type=int, nargs='+',
                        help='On which numa node we do the work, 0 or 1')
    parser.add_argument('-d', '--visiblegpu', type=str, nargs='+',
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
    main(args)