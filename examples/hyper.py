#!/usr/bin/python
"""Custom topology example

Two directly connected switches plus a host for each switch:

   host --- switch --- switch --- host
                  |               |
                  |               |
   host --- switch --- switch --- host

Adding the 'topos' dict with a key/value pair to generate our newly defined
topology enables one to pass in '--topo=mytopo' from the command line.
"""
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import ( OVSKernelSwitch, Node, RemoteController )
from mininet.log import setLogLevel
from mininet.util import dumpNodeConnections, pmonitor
from mininet.cli import CLI
from functools import partial
from mininet.link import TCIntf
from mininet.util import custom
import random
import time

import datetime 

def difer(x, y, a):
 cnt = 0
 for j in range(0, a):
  if (x%2 != y%2):
   cnt += 1
  x = x//2
  y = y//2
 return cnt

class OVSBridgeSTP( OVSKernelSwitch ):
    """Open vSwitch Ethernet bridge with Spanning Tree Protocol
       rooted at the first bridge that is created"""
    prio = 1000
    def start( self, *args, **kwargs ):
        OVSKernelSwitch.start( self, *args, **kwargs )
        OVSBridgeSTP.prio += 1
        self.cmd( 'ovs-vsctl set-fail-mode', self, 'standalone' )
        self.cmd( 'ovs-vsctl set-controller', self )
        self.cmd( 'ovs-vsctl set Bridge', self,
                  'stp_enable=true',
                  'other_config:stp-priority=%d' % OVSBridgeSTP.prio )
 
switches = { 'ovs-stp': OVSBridgeSTP }

class MyTopo( Topo ):
    "Simple topology example."

    def __init__( self ):
        "Create custom topo."

        # Initialize topology
        Topo.__init__( self )

        # Add hosts and switches
        leftHost = self.addHost( "h1" )
        rightHost = self.addHost( 'h2' )
        downHost = self.addHost( 'h3' )
        upHost = self.addHost( 'h4' )
        leftSwitch = self.addSwitch( 's1' )
        rightSwitch = self.addSwitch( 's2' )
        downSwitch = self.addSwitch('s3' )
        upSwitch = self.addSwitch( 's4' )
        
        # Add links
        self.addLink( leftHost, leftSwitch )
        self.addLink( leftSwitch, rightSwitch )
        self.addLink( upSwitch, upHost )
        self.addLink( rightSwitch, rightHost )
        self.addLink( upSwitch, downSwitch )
        self.addLink( rightSwitch, downSwitch )
        self.addLink( downSwitch, downHost )
        self.addLink( upSwitch, leftSwitch )

topos = { 'mytopo': ( lambda: MyTopo() ) }
#import subprocess
#for i in range (1, 5):
# bashCommand = "ovs-ofctl add-flow s1 action=normal" 
# process = subprocess.Popen(bashCommand.split(), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
# output = process.communicate()[0]


 

class Hypercube( Topo ):
    "Simple topology example."
 
    def __init__( self):
        "Create custom topo."
#        a = 3#dimension/////////////////////////////////////////////
        n = 2**a #numer of switches///////////////////////////////////
        
        # Initialize topology
        Topo.__init__( self )

        # Add hosts and switches
        switch = []
        host = []
        for i in range(0, n):
         switch.append(self.addSwitch('s%d' %i))
         host.append(self.addHost('h%d' %i))

         print switch[i]

        # Add links Host--Switch
        for i in range(0, n):
         self.addLink(switch[i], host[i])
         
        # Add links Switch--Switch
        for i in range(0, n-1):
         for j in range(i+1, n):
          if (difer(i, j, a) == 1):
           self.addLink(switch[i], switch[j])
           
topos = { 'hypercube': ( lambda: Hypercube() ) }

def simpleTest():
 "create a test"
# a = 7
 n = 2**a
 topo = Hypercube()
# c = RemoteController('c1', ip='192.168.56.101')
# opts = (switch=OVSKernelSwitch, topo=topo)
 cpu=.1/n
 intf = custom( TCIntf,  bw=10, delay=2 )
# host = custom(CPULimitedHost, cpu=cpu )
 net = Mininet(switch=OVSKernelSwitch, intf=intf, topo=topo, controller=partial( RemoteController,ip='10.51.42.117', port=6633 ))
 net.start()#///////////////////////////////////////////////////////////////////////////////////////
 print "Dumping node connections"
 dumpNodeConnections(net.switches)
 seq = range(0, n)
 print seq
 dict = {}
 while seq:
  x = random.choice(seq)
  y = random.choice(seq)
  while (x == y):
   y = random.choice(seq)
  dict[x] = y
  seq.remove(x)
  seq.remove(y)
 print dict
 
 
 #///////////////////////////////////////////////////////////////////////////////////////
# h4, h1, h2, h3 = net.getNodeByName('h4', 'h1', 'h2', 'h3')
# net.iperf((h4, h3), (h1, h2))
# net.iperf((h1, h2))
# net.pingAll()
# hosts = [h1, h2, h3, h4]
# last = hosts[-1]
 
 clients = [net.getNodeByName('h%d' % (i)) for i in dict.keys()]
 servers = [net.getNodeByName('h%d' % (i)) for i in dict.values()]

 popens = {}

 #start servers and ping all pairs 
 time.sleep(2) 
 for i in range(0, n/2):
  popens[ servers[i] ] = servers[i].popen( "iperf3 -sD")
  popens[ servers[i] ] = servers[i].popen( "ping -c1 %s" %clients[i].IP()) 
 for i in range(0, n/2):
  time.sleep(0.3)
  popens[ servers[i] ] = servers[i].popen( "ping -c1 %s" %clients[i].IP())
 time.sleep(2) 
 #start client traffci iperf3
 for i in range(0, n/2):
  popens[ clients[i] ] = clients[i].popen( "iperf3 -b 100Mb -t 10 -c %s" % servers[i].IP() )
#print server--client pairs
  print 'server %s  '% servers[i], 'client  %s' % clients[i] 
  print 'server IP %s  '% servers[i].IP(), 'client IP  %s' % clients[i].IP()
 # print process output with pmonitor
 f = open('rez', 'w')
 for host, line in pmonitor( popens ):
  print host
  if host:
   f.write("<%s>: %s\n" % (host.name, line.strip() ))
   timp = time.time()
   print "%s <%s>: %s" % (timp, host.name, line.strip() )
 f.closed
 CLI(net)
 #///////////////////////////////////////////////////////////////////////////////////////
 
# net.stop() #///////////////////////////////////////////////////////////////////////////////////////

if __name__ == '__main__':
    setLogLevel( 'info' )
    a = 10#dimension/////////////////////////////////////////////
    simpleTest()
 
















