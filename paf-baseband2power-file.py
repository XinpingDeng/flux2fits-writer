#!/usr/bin/env python

# ./paf-baseband2power.py -a paf-baseband2power.conf -b /beegfs/DENG/docker/ -c 0 -d 0 -e 0 -f 2018-04-17-19:22:11.56868_0000000000000000.000000.dada

import os, time, threading, ConfigParser, argparse, socket, json, struct, sys

def ConfigSectionMap(section):
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

# Read in command line arguments
parser = argparse.ArgumentParser(description='Convert baseband data into power')
parser.add_argument('-a', '--cfname', type=str, nargs='+',
                    help='The name of configuration file')
parser.add_argument('-b', '--directory', type=str, nargs='+',
                    help='In which directory we record the data and read configuration files and parameter files')
parser.add_argument('-c', '--gpu', type=int, nargs='+',
                    help='The index of GPU')
parser.add_argument('-d', '--visiblegpu', type=str, nargs='+',
                    help='Visible GPU, the parameter is for the usage inside docker container.')
parser.add_argument('-e', '--memcheck', type=int, nargs='+',
                    help='To run cuda-memcheck or not.')
parser.add_argument('-f', '--dfname', type=str, nargs='+',
                    help='Data file to check.')

args         = parser.parse_args()
cfname       = args.cfname[0]
gpu          = args.gpu[0]
visiblegpu   = args.visiblegpu[0]
directory    = args.directory[0]
memcheck     = args.memcheck[0]
dfname       = args.dfname[0]

if(args.visiblegpu[0]==''):
    multi_gpu = 1;
if(args.visiblegpu[0]=='all'):
    multi_gpu = 1;
else:
    multi_gpu = 0;
    
# Play with configuration file
Config = ConfigParser.ConfigParser()
Config.read(cfname)

# Basic configuration
nsamp_df     = int(ConfigSectionMap("BasicConf")['nsamp_df'])
npol_samp    = int(ConfigSectionMap("BasicConf")['npol_samp'])
ndim_pol     = int(ConfigSectionMap("BasicConf")['ndim_pol'])
nchk_nic     = int(ConfigSectionMap("BasicConf")['nchk_nic'])

# Diskdb configuration
diskdb_ndf     = int(ConfigSectionMap("DiskdbConf")['ndf'])
diskdb_nbuf    = ConfigSectionMap("DiskdbConf")['nblk']
diskdb_key     = ConfigSectionMap("DiskdbConf")['key']
diskdb_key     = format(int("0x{:s}".format(diskdb_key), 0), 'x')
diskdb_kfname  = "{:s}.key".format(ConfigSectionMap("DiskdbConf")['kfname_prefix'])
diskdb_hfname  = ConfigSectionMap("DiskdbConf")['hfname']
diskdb_nreader = ConfigSectionMap("DiskdbConf")['nreader']
diskdb_sod     = ConfigSectionMap("DiskdbConf")['sod']
diskdb_rbufsz  = diskdb_ndf *  nchk_nic * 7168
diskdb_cpu     = 10

# baseband2power configuration
baseband2power_key        = ConfigSectionMap("Baseband2powerConf")['key']
baseband2power_kfname     = "{:s}.key".format(ConfigSectionMap("Baseband2powerConf")['kfname_prefix'])
baseband2power_key        = format(int("0x{:s}".format(baseband2power_key), 0), 'x')
baseband2power_sod        = int(ConfigSectionMap("Baseband2powerConf")['sod'])
baseband2power_nreader    = ConfigSectionMap("Baseband2powerConf")['nreader']
baseband2power_nbuf       = ConfigSectionMap("Baseband2powerConf")['nblk']
baseband2power_nchan      = int(ConfigSectionMap("Baseband2powerConf")['nchan'])
baseband2power_nbyte      = int(ConfigSectionMap("Baseband2powerConf")['nbyte'])
baseband2power_rbufsz     = baseband2power_nchan * baseband2power_nbyte
baseband2power_cpu        = 11 

# Dbdisk configuration
dbdisk_cpu = 12

def diskdb():
    print ('taskset -c {:d} ./paf_diskdb -a {:s} -b {:s} -c {:s} -d {:s} -e {:s}'.format(diskdb_cpu, diskdb_key, directory, dfname, diskdb_hfname, diskdb_sod))
    os.system('taskset -c {:d} ./paf_diskdb -a {:s} -b {:s} -c {:s} -d {:s} -e {:s}'.format(diskdb_cpu, diskdb_key, directory, dfname, diskdb_hfname, diskdb_sod))

def baseband2power():
    if memcheck:
        print ('taskset -c {:d} cuda-memcheck ./paf_baseband2power -a {:s} -b {:s} -c {:s} -d {:d} -e {:d} -f {:d} -g {:d}'.format(baseband2power_cpu, diskdb_key, baseband2power_key, directory, gpu, diskdb_ndf, baseband2power_nchan, baseband2power_sod))
        os.system('taskset -c {:d} cuda-memcheck ./paf_baseband2power -a {:s} -b {:s} -c {:s} -d {:d} -e {:d} -f {:d} -g {:d}'.format(baseband2power_cpu, diskdb_key, baseband2power_key, directory, gpu, diskdb_ndf, baseband2power_nchan, baseband2power_sod))
    else:
        print ('taskset -c {:d} ./paf_baseband2power -a {:s} -b {:s} -c {:s} -d {:d} -e {:d} -f {:d} -g {:d}'.format(baseband2power_cpu, diskdb_key, baseband2power_key, directory, gpu, diskdb_ndf, baseband2power_nchan, baseband2power_sod))
        os.system('taskset -c {:d} ./paf_baseband2power -a {:s} -b {:s} -c {:s} -d {:d} -e {:d} -f {:d} -g {:d}'.format(baseband2power_cpu, diskdb_key, baseband2power_key, directory, gpu, diskdb_ndf, baseband2power_nchan, baseband2power_sod))

def dbdisk():
    print ('dada_dbdisk -b {:d} -k {:s} -D {:s} -W -s -d'.format(dbdisk_cpu, baseband2power_key, directory))
    os.system('dada_dbdisk -b {:d} -k {:s} -D {:s} -W -s -d'.format(dbdisk_cpu, baseband2power_key, directory))

def main():
    # Create key files
    # and destroy share memory at the last time
    # this will save prepare time for the pipeline as well
    diskdb_key_file = open(diskdb_kfname, "w")
    diskdb_key_file.writelines("DADA INFO:\n")
    diskdb_key_file.writelines("key {:s}\n".format(diskdb_key))
    diskdb_key_file.close()

    # Create key files
    # and destroy share memory at the last time
    # this will save prepare time for the pipeline as well
    baseband2power_key_file = open(baseband2power_kfname, "w")
    baseband2power_key_file.writelines("DADA INFO:\n")
    baseband2power_key_file.writelines("key {:s}\n".format(baseband2power_key))
    baseband2power_key_file.close()

    os.system("dada_db -l -p -k {:s} -b {:d} -n {:s} -r {:s}".format(diskdb_key, diskdb_rbufsz, diskdb_nbuf, diskdb_nreader))
    os.system("dada_db -l -p -k {:s} -b {:d} -n {:s} -r {:s}".format(baseband2power_key, baseband2power_rbufsz, baseband2power_nbuf, baseband2power_nreader))
    
    t_diskdb  = threading.Thread(target = diskdb)
    t_baseband2power = threading.Thread(target = baseband2power)
    t_dbdisk    = threading.Thread(target = dbdisk)
    
    t_diskdb.start()
    t_baseband2power.start()
    t_dbdisk.start()
    
    t_diskdb.join()
    t_baseband2power.join()
    t_dbdisk.join()

    os.system("dada_db -d -k {:s}".format(diskdb_key))
    os.system("dada_db -d -k {:s}".format(baseband2power_key))
    
if __name__ == "__main__":
    main()
