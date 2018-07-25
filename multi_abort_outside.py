#!/usr/bin/env python

import subprocess
import sys
import threading
import time
import socket
import os
import commands

def ssh(host, command):
    #FNULL = open(os.devnull, 'w')
    ssh = subprocess.Popen(["ssh", "%s" % host, command],
                           shell=False,
                           stdout=subprocess.PIPE,
                           #stdout=FNULL,
                           stderr=subprocess.PIPE)
    result = ssh.stdout.readlines()
    if result == []:
        error = ssh.stderr.readlines()
        print >>sys.stderr, "ERROR: %s" % error, host
    else:
        print result
    #FNULL.close()

#def ssh(host, command):
#    commands.getstatusoutput("ssh {:s} {:s}".format(host, command))
    
def main():
    nbeam = 9
    length = 10
    threads = []
    ddir = "/beegfs/DENG/JUNE"
    
    for beam in range(0,4):
        numa = beam % 2
        node = beam / 2
        print numa, node
    
        command = "docker kill paf-baseband2power0 paf-baseband2power1"
        host = "pacifix{:d}".format(node)
        print host, command
        threads.append(threading.Thread(target = ssh, args = (host, command,)))
    
    for beam in range(4, nbeam):
        numa = beam % 2
        node = beam / 2 + 1
        print numa, node
        command = "docker kill paf-baseband2power0 paf-baseband2power1"
        host = "pacifix{:d}".format(node)
        print host, command
        threads.append(threading.Thread(target = ssh, args = (host, command,)))

    
    #for beam in range(4, 6):
    #    numa = beam % 2
    #    node = beam / 2 + 2
    #    print numa, node
    #
    #    command = "docker kill paf-baseband2power0 paf-baseband2power1"
    #    host = "pacifix{:d}".format(node)
    #    print host, command
    #    threads.append(threading.Thread(target = ssh, args = (host, command,)))
    #
    #for beam in range(6, nbeam):
    #    numa = beam % 2
    #    node = beam / 2 + 3
    #    print numa, node
    #
    #    command = "docker kill paf-baseband2power0 paf-baseband2power1"
    #    host = "pacifix{:d}".format(node)
    #    print host, command
    #    threads.append(threading.Thread(target = ssh, args = (host, command,)))
    
    for beam in range(nbeam):
        threads[beam].start()
    
    for beam in range(nbeam):
        threads[beam].join()
    
if __name__ == "__main__":
    main()
