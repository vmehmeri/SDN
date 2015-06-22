"""
jellyfish.py: script to run Jellyfish topology test

The tests performed are packet delay (ping), throughput (IPERF-TCP), jitter and packet loss (IPERF-UDP)

OVSBridgeSTP: STP-Enabled OVS switch class

@author Victor Mehmeri (vime@fotonik.dtu.dk)
"""

from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, Controller, RemoteController, CPULimitedHost
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import Link, Intf, TCLink
from mininet.topo import Topo
from mininet.util import dumpNodeConnections, pmonitor
from ripl.ripl.dctopo import JellyfishTopo
from signal import SIGINT
import time
import sys
import random
import logging
import os 
import argparse
 
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger( __name__ )

parser = argparse.ArgumentParser(description='Run Jellyfish topology evaluation test with mininet')
parser.add_argument('-H', type=int, nargs='?',
				   help='Number of servers (hosts)')
parser.add_argument('-s', type=int, nargs='?',
				   help='Number of switches')
parser.add_argument('-p', type=int, nargs='?',
				   help='Number of switch ports')
parser.add_argument('-d', type=int, nargs='?',
				   help='Duration of IPERF test')
parser.add_argument('-r', type=int, nargs='?',
				   help='Number of test runs')
parser.add_argument('--controller', action='store_true',
				   help='use SDN controller')
parser.add_argument('--ip', type=str, nargs='?',
				   help='Controller IP address')
parser.add_argument('--port', type=int, nargs='?',
				   help='Controller Port')

args = parser.parse_args()

global IPERF_TEST_DURATION, kNUMBER, CONTROLLER, CONTROLLER_IP, CONTROLLER_PORT, FILE_PREFIX
	
#Set defaults
CONTROLLER = 0
CONTROLLER_IP = "127.0.0.1"
CONTROLLER_PORT = 6633 
FILE_PREFIX = "jf"
IPERF_TEST_DURATION = 40


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
            

def monitorOutput(popens, duration):
	endTime = time.time() + duration
	for host, line in pmonitor( popens ):
		if host:
			logger.debug( "<%s>: %s" % ( host, line.strip() ) )
		if time.time() >= endTime:
			logger.debug("*** One or more connections timed out ***")
			for p in popens.values():
				p.send_signal( SIGINT )
			break
    	
def startIperfServers(net, topo, servers):
	#Start IPERF servers
	logger.info( ">>> Starting IPERF servers..." )
	for serverHostIndex in servers:
		net.get(serverHostIndex).popen('iptables -A INPUT -p tcp --dport 5001 -j ACCEPT', shell=True)
		net.get(serverHostIndex).popen('iptables -A INPUT -p tcp --dport 5201 -j ACCEPT', shell=True)
		net.get(serverHostIndex).popen('iperf3 -sD', shell=True)
		time.sleep(1)
	time.sleep(60)

def generateServerClientPairs(net, topo):
	clients = []
	servers = []
	
	hosts = topo.hosts()
	
	while (len(hosts) > 1):
		randomServer = random.choice(hosts)
		randomClient = random.choice(hosts)
		
		while (randomClient == randomServer):
			randomClient = random.choice(hosts)
		
		clients.append(randomClient) 
		servers.append(randomServer)
		hosts.remove(randomClient)
		hosts.remove(randomServer)
	
	logger.debug( "Clients: " + " ".join(str(e) for e in clients) )
	logger.debug( "Servers: " + " ".join(str(e) for e in servers) )
	
	return (servers, clients)
 

def runPingTest(net, topo, servers, clients):
	"""
	Run PING test, for delay measurement,
	:param net: mininet network
	:param topo: mininet topology
	:return:
	"""
	
	"""
	====================== START PING TEST ==========================
	"""
	
	#Number of test runs
	runs = 1
	
	if args.r:
		runs = args.r
	
	for run in range(1, runs+1):
		popens = {}
		
		logger.info( ">>> Starting PING test..." )
		for index in range(0, len(clients)):
			clientHost = net.get(clients[index])
			serverHost = net.get(servers[index])
			logger.debug("[PING] %s --> %s" %(clientHost.IP(), serverHost.IP()))
			#discard first ping
			clientHost.popen('ping -q -n -c 1 %s' %(serverHost.IP()), shell=True).wait()
			popens[index] = clientHost.popen('ping -q -n -c 8 %s >> results/%s_ping_results_%d 2>&1' %(serverHost.IP(), FILE_PREFIX, run), shell=True)
					
		logger.debug(">>> Waiting for PING test to finish...")
		
		monitorOutput(popens, 60)
 
def runTCPTest(net, topo, servers, clients):
	"""
	Run IPERF TCP test, for bandwidth measurement,
	:param net: mininet network
	:param topo: mininet topology
	:return:
	"""

	"""
	====================== START TCP TEST ==========================
	"""
	
	#Number of test runs
	runs = 1
	
	if args.r:
		runs = args.r
	
	for run in range(1, runs+1):
		popens = {}
		
		#First, ping everyone to add the flows/paths
		for index in range(0, len(clients)):
			clientHost = net.get(clients[index])
			serverHost = net.get(servers[index])
			clientHost.popen('ping -n -c 1 -W 10 %s ' %(serverHost.IP()), shell=True)
		
		time.sleep(15)
		
		#Start IPERF TCP clients	
		logger.info( ">>> Starting IPERF TCP Clients..." )
		for index in range(0, len(clients)):
			duration = IPERF_TEST_DURATION
			#if IPERF tests start to fail, try uncommenting the following lines
			#duration = IPERF_TEST_DURATION + len(clients) - index
			#time.sleep(1)
			clientHost = net.get(clients[index])
			serverHost = net.get(servers[index])
			logger.debug("%s --> %s" %(clientHost.IP(), serverHost.IP()))
			popens[index] = clientHost.popen('iperf3 -O 10 -f k -i 10 -t %d -Z -c %s >> results/%s_tcp_results_%d 2>&1' %(duration, serverHost.IP(), FILE_PREFIX, run), shell=True)
			
					
		logger.debug(">>> Waiting for TCP test to finish...")
		
		monitorOutput(popens, 300)
	
	
def runUDPTest(net, topo, servers, clients, bwList = [1]):
	"""
	Run IPERF UDP test, for jitter and packet loss measurement,
	:param net: mininet network
	:param topo: mininet topology
	:return:
	"""

	"""
	====================== START UDP TEST ==========================
	"""

	#Number of test runs
	runs = 1

	if args.r:
		runs = args.r

	for run in range(1, runs+1):
		popens = {}

		for index in range(0, len(clients)):
			clientHost = net.get(clients[index])
			serverHost = net.get(servers[index])
			clientHost.popen('ping -n -c 1 %s -W 5 ' %(serverHost.IP()), shell=True)

		time.sleep(5)

		for bw in bwList:
			#Start IPERF UDP clients
			logger.info( ">>> Starting IPERF UDP Clients..." )
			for index in range(0, len(clients)):
				#duration = IPERF_TEST_DURATION
				#if IPERF tests start to fail, try uncommenting the following lines
				duration = IPERF_TEST_DURATION + len(clients) - index
				time.sleep(1)
				clientHost = net.get(clients[index])
				serverHost = net.get(servers[index])
				logger.debug("%s --> %s" %(clientHost.IP(), serverHost.IP()))
				popens[index] = clientHost.popen('iperf3 -O 10 -f k -u -b %.1fM -i 10 -t %d -Z -c %s >> results/%s_udp_results_%.1fM_%d 2>&1' %(bw, duration, serverHost.IP(), FILE_PREFIX, bw, run), shell=True)
				

			logger.debug(">>> Waiting for UDP test to finish...")

			monitorOutput(popens, 300)



def netTest(net):
    logger.debug("Testing network...")
    net.pingAll()
 
def run():
	logging.debug("Creating Jellyfish Topology")
	
	if (args.H and args.s and args.p):
		topo = JellyfishTopo(args.H, args.s, args.p)
	elif args.H and args.p:
		topo = JellyfishTopo(args.H, args.H, args.p)
	else:
		topo = JellyfishTopo() #run with defaults
	
	if CONTROLLER:
		net = Mininet(topo=topo, link=TCLink, host=CPULimitedHost, controller=None)
		net.addController('controller',controller=RemoteController,ip=CONTROLLER_IP,port=CONTROLLER_PORT)
	else:
		net = Mininet(switch=OVSBridgeSTP, topo=topo, host=CPULimitedHost, link=TCLink, controller=None)
 
	net.start()
	servers, clients = generateServerClientPairs(net, topo)
	
	#netTest(net)
	
	#allow some time for the controller to initialize all the links
	time.sleep(30)
	
	runPingTest(net, topo, servers, clients)
	startIperfServers(net, topo, servers)
	runTCPTest(net, topo, servers, clients)
	runUDPTest(net, topo, servers, clients)
 
	#CLI(net)
	net.stop()

def cleanUp():
	os.system("mn -c")
	os.system("killall iperf3")
 
if __name__ == '__main__':
	setLogLevel('info')
	
	if args.d:
		IPERF_TEST_DURATION = args.d
		
	if args.controller:
		CONTROLLER = 1
		FILE_PREFIX = "%s_sdn" % FILE_PREFIX
		if args.ip:
			CONTROLLER_IP = args.ip
		if args.port:
			CONTROLLER_PORT = args.port
	else:
		FILE_PREFIX = "%s_stp" % FILE_PREFIX

	if args.H:
		FILE_PREFIX = "%s_%d" % (FILE_PREFIX, args.H)
	
	logger.info( ">> Iniating Jellyfish topology test"  )
	logger.info( ">> IPERF tests will run for %d seconds " % (IPERF_TEST_DURATION) )
	
	
	if os.getuid() != 0:
		logger.debug("You are NOT root")
	elif os.getuid() == 0:
		try:
			run()
		finally:
			cleanUp()
	
