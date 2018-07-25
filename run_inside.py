#!/usr/bin/env python

import os

stream = 1
dir_name    = "/beegfs/DENG/JUNE/"
numa        = 1
visiblegpu  = 1
nvprof      = 1
memcheck    = 0
length      = 100
nbeam       = 9
dfname      = "2018-04-17-19:22:11.56868_0000000000000000.000000.dada"

if stream:
    script_name = "paf-baseband2power-stream.py"
    conf_fname  = "paf-baseband2power-stream.conf"
else:
    script_name = "paf-baseband2power-file.py"
    conf_fname  = "paf-baseband2power-file.conf"    

if nvprof == 1:
    if stream:
        com_line = "nvprof --profile-child-processes ./{:s} -a {:s} -b {:s} -c {:d} -d {:s} -e {:d} -f {:f} -g {:d}".format(script_name, conf_fname, dir_name, numa, str(visiblegpu), memcheck, length, nbeam)
    else:
        com_line = "nvprof --profile-child-processes ./{:s} -a {:s} -b {:s} -c {:d} -d {:s} -e {:d} -f {:s}".format(script_name, conf_fname, dir_name, numa, str(visiblegpu), memcheck, dfname)
else:
    if stream:
        com_line = "./{:s} -a {:s} -b {:s} -c {:d} -d {:s} -e {:d} -f {:f} -g {:d}".format(script_name, conf_fname, dir_name, numa, str(visiblegpu), memcheck, length, nbeam)
    else:
        com_line = "./{:s} -a {:s} -b {:s} -c {:d} -d {:s} -e {:d} -f {:s}".format(script_name, conf_fname, dir_name, numa, str(visiblegpu), memcheck, dfname)

print com_line
os.system(com_line)
