"""
fattree.py: script to run Fat-Tree topology test

The tests performed are packet delay (ping), throughput (IPERF-TCP), jitter and packet loss (IPERF-UDP)

OVSBridgeSTP: STP-Enabled OVS switch class
FatTreeTopo: Fat Tree topology class for mininet

@author Victor Mehmeri (vime@fotonik.dtu.dk)
"""

from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, Controller, RemoteController, CPULimitedHost
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import Link, Intf, TCLink
from mininet.topo import Topo
from mininet.util import dumpNodeConnections, pmonitor
import time
import sys
import random
import logging
import os 
import argparse
 
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger( __name__ )

parser = argparse.ArgumentParser(description='Run Jellyfish topology evaluation test with mininet')
parser.add_argument('-k', type=int, nargs='?',
				   help='Number of PODs')
parser.add_argument('-d', type=int, nargs='?',
				   help='Duration of IPERF test')
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
FILE_PREFIX = "ft"
IPERF_TEST_DURATION = 40
kNUMBER = 4

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

 
class FatTreeTopo(Topo):
    coreSwitchList = []
    aggSwitchList = []
    edgeSwitchList = []
    hostList = []
    
    
    def __init__(self, kNUMBER=4):
		"""
		Instantiate Fat Tree topology with kNUMBER pods
		"""
		self.kNUMBER = kNUMBER
		self.coreLayerSwitchNumber = ( kNUMBER/2 ) ** 2
		self.aggLayerSwitchNumber = ( kNUMBER/2 ) * kNUMBER
		self.edgeLayerSwitchNumber = ( kNUMBER/2 ) * kNUMBER
		self.hostNumber = self.edgeLayerSwitchNumber * kNUMBER/2 

		#Init Topo
		Topo.__init__(self)

		logger.debug("Creating Core Layer Switches")
		self.createCoreLayerSwitch(self.coreLayerSwitchNumber)
		logger.debug("Creating Agg Layer Switches ")
		self.createAggLayerSwitch(self.aggLayerSwitchNumber)
		logger.debug("Creating Edge Layer Switches ")
		self.createEdgeLayerSwitch(self.edgeLayerSwitchNumber)
		logger.debug("Adding Hosts")
		self.createHost(self.hostNumber)
		logger.debug("Creating links")
		self.createLinks()
    
    
 
    def createCoreLayerSwitch(self, NUMBER):
        logger.debug("Create Core Layer")
        for x in range(1, NUMBER+1):
            PREFIX = "100"
            if x >= int(10):
                PREFIX = "10"
            self.coreSwitchList.append(self.addSwitch(PREFIX + str(x)))
 
    def createAggLayerSwitch(self, NUMBER):
        logger.debug( "Create Agg Layer")
        for x in range(1, NUMBER+1):
            PREFIX = "200"
            if x >= int(10):
                PREFIX = "20"
            self.aggSwitchList.append(self.addSwitch(PREFIX + str(x)))
 
    def createEdgeLayerSwitch(self, NUMBER):
        logger.debug("Create Edge Layer")
        for x in range(1, NUMBER+1):
            PREFIX = "300"
            if x >= int(10):
                PREFIX = "30"
            self.edgeSwitchList.append(self.addSwitch(PREFIX + str(x)))
    
    def createHost(self, NUMBER):
        logger.debug("Create Host")
        for x in range(1, NUMBER+1):
            PREFIX = "400"
            if x >= int(10):
                PREFIX = "40"
            self.hostList.append(self.addHost(PREFIX + str(x))) 
 
    def createLinks(self):
        logger.debug("Linking Core to Aggregate layer")
            
        pod = 0
        podOffset = 0
        
        for agg in self.aggSwitchList:
			for x in range(0, kNUMBER/2):
				self.addLink(agg, self.coreSwitchList[podOffset*kNUMBER/2 + x], bw=1000, delay='0.1ms')
			podOffset += 1
			if  podOffset >= kNUMBER/2:
				podOffset = 0
            
        logger.debug("Linking Aggregate to Edge layer")
        for pod in range(0, kNUMBER):
			for x in range(0, kNUMBER/2):
				for y in range(0,kNUMBER/2):
					self.addLink(self.aggSwitchList[pod*kNUMBER/2 + x], self.edgeSwitchList[pod*kNUMBER/2 + y], bw=1000, delay='0.1ms')
 
        logger.debug("Linking Edge switches to Hosts")
        for x in range(0, self.edgeLayerSwitchNumber):
			for port in range(0, kNUMBER/2):
				self.addLink(self.edgeSwitchList[x], self.hostList[x*kNUMBER/2+port], bw=1000)
    
    def hosts(self):
        return self.hostList

def generateUniformClientServerPairs(net, topo, numberOfPairs):
	clients = []
	servers = []
	
	hostSet = range(0, len(topo.hosts()))
	
	while (len(clients) < numberOfPairs):
		randomServer = random.choice(hostSet)
		randomClient = random.choice(hostSet)
		
		while (randomClient == randomServer):
			randomClient = random.choice(hostSet)
		
		clients.append(randomClient) 
		servers.append(randomServer)
		hostSet.remove(randomClient)
		hostSet.remove(randomServer)
	
	logger.debug( "Clients: " + " ".join(str(e) for e in clients) )
	logger.debug( "Servers: " + " ".join(str(e) for e in servers) )
	
	return (servers, clients)

def generateServerClientPairs(net, topo, kNUMBER):
	clients = []
	servers = []
	
	#Assign servers and clients pairs
	for pod in range(1, kNUMBER + 1):
		firstOfThePod = ( pod - 1 ) * (kNUMBER ** 2)/4
		lastOfThePod = pod * (kNUMBER ** 2)/4
		podSubset = range(firstOfThePod, lastOfThePod)
		dict = {}
		
		while len(podSubset) > 1:
			randomServer = random.choice(podSubset)
			randomClient = random.choice(podSubset)
			
			while (randomClient == randomServer):
				randomClient = random.choice(podSubset)
			
			dict[randomClient] = randomServer
			
			podSubset.remove(randomServer)
			podSubset.remove(randomClient)
		
		clientsFromPod = [(i) for i in dict.keys()] 
		serversFromPod = [(i) for i in dict.values()]
		
		logger.debug( "Clients from pod %d: " % (pod) + " ".join(str(e) for e in clientsFromPod) )
		logger.debug( "Servers from pod %d: " % (pod) + " ".join(str(e) for e in serversFromPod) )
		
		clients.extend(clientsFromPod)
		servers.extend(serversFromPod)
	
	logger.debug( "Clients: " + " ".join(str(e) for e in clients) )
	logger.debug( "Servers: " + " ".join(str(e) for e in servers) )
	
	return servers,clients

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
			
def runPingTest(net, topo, servers, clients):
	"""
	Rung concurrent ping tests for delay measurement
	:param net: mininet network
	:param topo: mininet topology
	:return:
	"""

	"""
	====================== CLIENTS AND SERVERS IN THE SAME POD ==========================
	"""
	
	logger.info(">>> Starting PING test for servers and clients in the same pod")

	popens = {}
	
	#Start PING 
	for index in range(0, len(clients)):
		clientHost = net.get(topo.hostList[clients[index]])
		serverHost = net.get(topo.hostList[servers[index]])
		logger.debug("%s --> %s" %(clientHost.IP(), serverHost.IP()))
		popens[index] = clientHost.popen('ping -q -n -c 6 %s >> results/%s_ping_results_same_pod ' %(serverHost.IP(), FILE_PREFIX), shell=True)
				
	logger.debug(">>> Waiting for PING test to finish...")
	
	for host, line in pmonitor( popens ):
		if host:
			logger.debug( "<%s>: %s" % ( host, line.strip() ) )
			
	"""
	====================== CLIENTS AND SERVERS IN DIFFERENT PODS ==========================
	"""
	
	# k must be even!
	logger.info(">>> Starting PING test for servers and clients in different pods")
	
	popens = {}
	
	#Start PING
	for index in range(0, len(clients)):
		clientHost = net.get(topo.hostList[clients[index]])
		serverHost = net.get(topo.hostList[servers[len(clients) - 1 - index]])
		logger.debug("%s --> %s" %(clientHost.IP(), serverHost.IP()))
		popens[index] = clientHost.popen('ping -q -n -c 6 %s >> results/%s_ping_results_different_pod ' %(serverHost.IP(), FILE_PREFIX), shell=True)
			
	logger.debug("Waiting for PING test to finish...")
	
	monitorOutput(popens, 300)
    	
def startIPERFServers(net, topo, servers):
	"""
	Start IPERF server daemons
	"""
    
	#Start IPERF servers
	logger.info( ">>> Starting IPERF servers..." )
	for serverHostIndex in servers:
		net.get(topo.hostList[serverHostIndex]).popen('iptables -A INPUT -p tcp --dport 5001 -j ACCEPT', shell=True)
		net.get(topo.hostList[serverHostIndex]).popen('iptables -A INPUT -p tcp --dport 5201 -j ACCEPT', shell=True)
		net.get(topo.hostList[serverHostIndex]).popen('iperf3 -sD', shell=True)
		time.sleep(1)
    	
def runTCPTest(net, topo, servers, clients):
	"""
	Run IPERF test, TCP for bandwidth measurement, and UDP for jitter and packet loss
	:param net: mininet network
	:param topo: mininet topology
	:return:
	"""
	
	#Limiting TCP's bandwidth will simulate different oversubscription values
	bwLimit = [100, 1000]
	
	"""
	====================== CLIENTS AND SERVERS IN THE SAME POD ==========================
	"""
	
	#Start IPERF TCP clients
	for bwLim in bwLimit:
		logger.info( ">>> Starting IPERF TCP Clients in the SAME POD..." )
		popens = {}
	
		for index in range(0, len(clients)):
			clientHost = net.get(topo.hostList[clients[index]])
			serverHost = net.get(topo.hostList[servers[index]])
			logger.debug("%s --> %s" %(clientHost.IP(), serverHost.IP()))
			#popens[index] = clientHost.popen('iperf3 -O 10 -f m -b %dM -i 10 -t %d -Z -c %s >> results/%s_tcp_results_same_pod_%dM 2>&1' %(bwLim, IPERF_TEST_DURATION, serverHost.IP(), FILE_PREFIX, bwLim), shell=True)
			popens[index] = clientHost.popen('iperf3 -O 10 -f m -i 10 -t %d -Z -c %s >> results/%s_tcp_results_same_pod_%dM 2>&1' %(IPERF_TEST_DURATION, serverHost.IP(), FILE_PREFIX, bwLim), shell=True)
					
		logger.debug(">>> Waiting for TCP test to finish...")
	
		monitorOutput(popens, 1200)
			
	
			
	"""
	====================== CLIENTS AND SERVERS IN DIFFERENT PODS ==========================
	"""
	
	# k must be even!
	for bwLim in bwLimit:
		logger.info( ">>> Starting IPERF TCP Clients in DIFFERENT PODs..." )
		
		popens = {}
		#Start IPERF TCP clients
		
		for index in range(0, len(clients)):
			duration = IPERF_TEST_DURATION + len(clients) - index
			clientHost = net.get(topo.hostList[clients[index]])
			serverHost = net.get(topo.hostList[servers[len(clients) - 1 - index]])
			logger.debug("%s --> %s" %(clientHost.IP(), serverHost.IP()))
			#popens[index] = clientHost.popen('iperf3 -O 10 -f m -b %dM -i 10 -t %d -Z -c %s >> results/%s_tcp_results_different_pod_%dM 2>&1' %(bwLim, duration, serverHost.IP(), FILE_PREFIX, bwLim), shell=True)
			popens[index] = clientHost.popen('iperf3 -O 10 -f m -i 10 -t %d -Z -c %s >> results/%s_tcp_results_different_pod_%dM 2>&1' %(duration, serverHost.IP(), FILE_PREFIX, bwLim), shell=True)
			time.sleep(1)
				
		logger.debug("Waiting for TCP test to finish...")
		
		monitorOutput(popens, 1200)

def runUDPTest(net, topo, servers, clients):
	"""
	Run IPERF test, TCP for bandwidth measurement, and UDP for jitter and packet loss
	:param net: mininet network
	:param topo: mininet topology
	:return:
	"""

	
	bwLimit = [1000]
	
	"""
	====================== CLIENTS AND SERVERS IN THE SAME POD ==========================
	"""

	
	for bwLim in bwLimit:
		logger.info( ">>> Starting IPERF UDP Clients in the SAME POD..." )
		popens = {}
		
		for index in range(0, len(clients)):
			clientHost = net.get(topo.hostList[clients[index]])
			serverHost = net.get(topo.hostList[servers[index]])
			logger.debug("%s --> %s" %(clientHost.IP(), serverHost.IP()))
			popens[index] = clientHost.popen('iperf3 -O 10 -f k -u -b %dM -i 10 -t %d -Z -c %s >> results/%s_udp_results_same_pod_%dM 2>&1' %(bwLim, IPERF_TEST_DURATION, serverHost.IP(), FILE_PREFIX, bwLim), shell=True)
					
		logger.debug(">>> Waiting for UDP test to finish...")
		
		monitorOutput(popens, 1200)
		
			
	"""
	====================== CLIENTS AND SERVERS IN DIFFERENT PODS ==========================
	"""
	
	# k must be even!
	for bwLim in bwLimit:
		logger.info( ">>> Starting IPERF UDP Clients in DIFFERENT PODs..." )
		popens = {}
		
		for index in range(0, len(clients)):
			duration = IPERF_TEST_DURATION + len(clients) - index
			clientHost = net.get(topo.hostList[clients[index]])
			serverHost = net.get(topo.hostList[servers[len(clients) - 1 - index]])
			logger.debug("%s --> %s" %(clientHost.IP(), serverHost.IP()))
			popens[index] = clientHost.popen('iperf3 -O 10 -f m -b %dM -i 10 -t %d -Z -c %s >> results/%s_udp_results_different_pod_%dM 2>&1' %(bwLim, duration, serverHost.IP(), FILE_PREFIX, bwLim), shell=True)
			time.sleep(1)
				
		logger.debug("Waiting for UDP test to finish...")
		
		monitorOutput(popens, 1200)
	
	

def netTest(net):
    logger.debug("Testing network...")
    net.pingAll()
 
def run():
	logging.debug("Creating Fat Tree Topology")
    
	topo = FatTreeTopo(kNUMBER)
    
	if CONTROLLER:
		net = Mininet(topo=topo, link=TCLink, host=CPULimitedHost, controller=None)
		net.addController('controller',controller=RemoteController,ip=CONTROLLER_IP,port=CONTROLLER_PORT)
	else:
		net = Mininet(switch=OVSBridgeSTP, topo=topo, host=CPULimitedHost, link=TCLink, controller=None)

	net.start()
	servers, clients = generateServerClientPairs(net, topo, kNUMBER)

	#netTest(net)
	#netTest(net)

	#allow some time for the controller to initialize all the links
	time.sleep(60)

	#runPingTest(net, topo, servers, clients)
	startIPERFServers(net, topo, servers)
	runTCPTest(net, topo, servers, clients)
	runUDPTest(net, topo, servers, clients)
	
	CLI(net)
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
	
	if args.k:
		FILE_PREFIX = "%s_k%d" % (FILE_PREFIX, args.k)
		kNUMBER = args.k
	
	logger.info( "Iniating Fat Tree topology test with k = %d" % (kNUMBER) )
	logger.info( "IPERF test will run for %d seconds " % (IPERF_TEST_DURATION) )

	if os.getuid() != 0:
		logger.debug("You are NOT root")
	elif os.getuid() == 0:
		try:
			run()
		finally:
			cleanUp()
