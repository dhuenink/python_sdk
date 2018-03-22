#!/usr/bin/env python
"""
 This script provides an example of how to connect to an Aviatrix Controller
 and create a user ssl vpn gateway.

 INPUTS:
   $1 - HOST - string - host/ip of the controller
   $2 - USER - string - the username used to authenticate with controller
   $3 - PASSWORD - string - the password of the given USER

 EXAMPLE OUTPUT:
    gw-sample-app-dev:
    	CPU Load: 0%
    	CPU Idle: 100%
    	Free Memory: 938780 kb
    	Free Diskspace: 4236684 kb
    	Bytes in: 232.46MB
    	Bytes out: 126.07MB

    gw-transit-hub:
    	CPU Load: 0%
    	CPU Idle: 99%
    	Free Memory: 944088 kb
    	Free Diskspace: 4236508 kb
    	Bytes in: 248.13MB
    	Bytes out: 143.03MB

    gw-sample-app-dev <==> gw-transit-hub UP
"""
#import logging
#logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
import sys

from aviatrix import Aviatrix

def main():
    """
    main() interface to this script
    """
    if len(sys.argv) != 4:
        print ('usage: %s <HOST> <USER> <PASSWORD>\n'
               '  where\n'
               '    HOST Aviatrix Controller hostname or IP\n'
               '    USER Aviatrix Controller login username\n'
               '    PASSWORD Aviatrix Controller login password\n' % sys.argv[0])
        sys.exit(1)

    print_stats(sys.argv[1], sys.argv[2], sys.argv[3])

def print_stats(controller_ip, username, password):
    """
    Prints the statistics to stdout
    Arguments:
    controller_ip - string - the controller host or IP
    username - string - the controller login username
    password - string - the controller login password
    """
    controller = Aviatrix(controller_ip)
    controller.login(username, password)

    gws = controller.list_gateways('admin')
    for gateway in gws:
        data = controller.get_current_gateway_statistics(gateway['vpc_name'])
        for gw_data in data:
            current = gw_data['mpstats']['stats_current']
            cpu = current['cpu']
            cpu_load = cpu['ks'] + cpu['us']
            cpu_idle = cpu['idle']
            memory = current['memory']
            memory_free = memory['free']
            disk_free = long(gw_data['hdisk_free'])
            network = gw_data['ifstats']
            total_bytes_in = network['Cumulative (sent/received/total)'][1]
            total_bytes_out = network['Cumulative (sent/received/total)'][0]

            print ('%s:\n\tCPU Load: %d%%\n\tCPU Idle: %d%%\n\tFree Memory: %d kb\n\t'
                   'Free Diskspace: %d kb\n\tBytes in: %s\n\tBytes out: %s\n\t' %
                   (gw_data['gw_name'],
                    cpu_load,
                    cpu_idle,
                    memory_free,
                    disk_free,
                    total_bytes_in,
                    total_bytes_out,
                   ))

    peers = controller.list_peers()
    for pair in peers:
        is_down = (pair['peering_state'].lower() != 'up')
        print '%s%s <==> %s %s' % ('!!!!! ' if is_down else '',
                                   pair['vpc_name1'],
                                   pair['vpc_name2'],
                                   pair['peering_state'].upper())

if __name__ == "__main__":
    main()
