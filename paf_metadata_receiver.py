#!/usr/bin/env /usr/bin/python

import socket
import json
import logging
from logging import handlers
from optparse import OptionParser

UNICAST_UDP = ("134.104.74.36", 26666)
MULTICAST_UDP = ("224.1.1.1", 5007)

class UnicastToMulticast(object):
    def __init__(self, unicast_addr, multicast_addr):
        self._log = logging.getLogger('UnicastToMulticast')
        self._unicast_addr = unicast_addr
        self._multicast_addr = multicast_addr
        self._log.info("Setting up packet forwarding from {0[0]}:{0[1]} to {1[0]}:{1[1]}".format(
                self._unicast_addr,self._multicast_addr))
        self._usock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._usock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #self._usock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        self._msock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._msock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        self._log.debug("Binding to {}:{}".format(*self._unicast_addr))
        self._usock.bind(self._unicast_addr)
        
    def recv(self):
        packet = self._usock.recvfrom(1<<16)[0]
        self._log.debug("Received {} byte packet on {}:{}".format(len(packet),*self._unicast_addr))
        #print "Received {} byte packet on {}:{}".format(len(packet),*self._unicast_addr)
        try:
            self._log.debug("Packet contents: {}".format(json.loads(packet)))
        except:
            self._log.debug("Packet contents: {}".format(packet))
        self._log.debug("Sending packet to {}:{}".format(*self._multicast_addr))
        self._msock.sendto(packet, self._multicast_addr)

    def listen(self):
        while True:
            try:
                self.recv()
            except Exception as error:
                self._log.exception("Error on receive call")
            
if __name__ == "__main__":
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option(
        '-g', '--group', dest='group', type=str,
        help='Hostname to setup on', default=MULTICAST_UDP[0])
    parser.add_option(
        '-p', '--port', dest='port', type=long,
        help='Port number to bind to',default=MULTICAST_UDP[1])
    parser.add_option(
        '', '--log-level', dest='log_level', type=str,
        help='Port number of status server instance', default="INFO")
    (opts, args) = parser.parse_args()

    logging.basicConfig(level=opts.log_level.upper(), 
                        format='[paf_metadata_receiver.py] - %(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        handlers=[handlers.SysLogHandler(address='/dev/log')])
    converter = UnicastToMulticast(UNICAST_UDP, (opts.group,opts.port))
    converter.listen()
