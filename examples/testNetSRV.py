#!/usr/bin/python
import random
import time
from subprocess import Popen, PIPE


def difer(x, y, a):
 cnt = 0
 for j in range(0, a):
  if (x%2 != y%2):
   cnt += 1
  x = x//2
  y = y//2
 return cnt
 
def Test():

 n = 2**a
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
 clients = [(i) for i in dict.keys()] 
 servers = [(i) for i in dict.values()]
 print clients
 print servers
 IP = []
 for i in range(0, n/2):
#  cmd = """ssh mininet-vm /home/mininet/mininet/uil/m h$i "/sbin/ifconfig h$i-eth0" | grep 'inet addr:' | cut -d: -f2 | awk '{ print $1}'"""
  cmd = "ssh mininetSRV /home/mininet/mininet/util/m h%d 'ifconfig h%d-eth0 | grep inet.add | cut -d: -f2 '" %(servers[i], servers[i])
  (p,e) = Popen(cmd , shell=True, stdout=PIPE, stderr=PIPE).communicate()
#  print p.split()[0]
  IP.append(p.split()[0])
 
#print clients and servers//////////////////////////////////////////////////////////
 for i in range (0, n/2):
  print '%d    %s' %(clients[i], IP[i])  
#ping network clients-servers///////////////////////////////////////////////////
 time.sleep(10)

 for i in range(0, n/2):
  time.sleep(3)
  cmd = "ssh mininetSRV /home/mininet/mininet/util/m h%d 'ping -n -c 3 %s >> ping1 &'" %(clients[i], IP[i])
  p = Popen(cmd , shell=True, stdout=PIPE, stderr=PIPE)
 cmd = "ssh mininetSRV /home/mininet/mininet/util/m h1 'ping -n -c 1 h1 >> killc &'"
 print 'kill//////////////////////////////////////////////////////////////////////////////////////////////'
 time.sleep(60)

#install iperf3 servers///////////////////////////////////////////////////////// 
 for i in range(0, n/2):
  time.sleep(1)
  cmd = "ssh mininetSRV /home/mininet/mininet/util/m h%d 'iperf3 -sD'" %servers[i]
  p = Popen(cmd , shell=True, stdout=PIPE, stderr=PIPE)

 
#start iperf3 clients///////////////////////////////////////////////////////////
#banda de testat
 list_BW = [1, 2, 5]
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////
#BATERIE DE TESTE///////////////////////////////////////////////////////////BATERIE DE TESTE
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////

 for j in list_BW:
#///////////////////////TCP////////////////////////////////////TCP//////////////TCP//////////TCP/////////////// 
  for i in range(0, n/2):
   cmd = "ssh mininetSRV /home/mininet/mininet/util/m h%d 'iperf3 -O 10  -b %dM -i 10 -t 40 -Z -c %s --logfile lapTCP%d'" %(clients[i], j, IP[i], j)
   p = Popen(cmd , shell=True, stdout=PIPE, stderr=PIPE)  
  time.sleep (60)
  
#////////////////UDP///////////////////////////////////////////UDP//////////////UDP//////////UDP//////////////   
  for i in range(0, n/2):
   cmd = "ssh mininetSRV /home/mininet/mininet/util/m h%d 'iperf3 -O 10 -u  -b %dM -i 10 -t 40 -Z -c %s --logfile lapUDP%d'" %(clients[i], j, IP[i], j)
   p = Popen(cmd , shell=True, stdout=PIPE, stderr=PIPE)  
  time.sleep (60)
  
#////////////////PING///////////////////////////////////////////PING//////////////PING//////////PING//////////////  
 for i in range(0, n/2):
  cmd = "ssh mininetSRV /home/mininet/mininet/util/m h%d 'ping -n -c 3 %s >> pingConcurent &'" %(clients[i], IP[i])
  p = Popen(cmd , shell=True, stdout=PIPE, stderr=PIPE) 
 time.sleep (10)  
 '''
 backup test//////////////////////////////////////////////////////////////////////////////////////////////////////////////
   for i in range(0, n/2):
 #  time.sleep(0.05)
   cmd = "ssh mininetSRV /home/mininet/mininet/util/m h%d 'iperf3 -O 10  -b 5M -i 10 -t 40 -Z -c %s --logfile lap'" %(clients[i], IP[i])
   p = Popen(cmd , shell=True, stdout=PIPE, stderr=PIPE)
 '''
#killall iperfsss//////////////////////////////////////////////////////////////
# cmd="killall -9 iperf3"
 p=Popen(cmd , shell=True, stdout=PIPE, stderr=PIPE)
if __name__ == '__main__':
#    setLogLevel( 'info' )
    a = 9#dimension/////////////////////////////////////////////
    Test()
    
#ssh mininet-vm /home/mininet/mininet/uil/m h$i "iperf3 -u -c $IP >> file &"