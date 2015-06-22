SDN - Software Defined Networking experiments with mininet
==================================================================================

DEPENDS ON IPERF3

There are two pythons scripts, fattree.py and jellyfish.py, which run evaluation experiments for Fat-Tree and Jellyfish datacenter topologies, respectively.

The metrics analyzed are: Throughput (IPERF TCP), Packet Delay (PING), Jitter (IPERF UDP) and Packet Loss (IPERF UDP)

For usage, run:

python fattree.py -h
python jellyfish.py -h

The script run_test.sh will run both tests with default parameters

