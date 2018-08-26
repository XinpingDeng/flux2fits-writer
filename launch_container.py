#!/usr/bin/env python

import os

length  = 20
numa    = 1

hdir    = '/home/pulsar/'
ddir    = '/beegfs/DENG/AUG'
uid     = 50000
gid     = 50000
dname   = 'paf-base'

os.system('./do_launch.py -a {:f} -b {:d} -c {:s} -d {:s} -e {:d} -f {:d} -g {:s}'.format(length, numa, ddir, hdir, uid, gid, dname))
