#!/usr/bin/env python
#-------------------------------------------------------------------------
# This is a simple external script to be executed by services like Zabbix
# to retrieve the number of peered connections that are currently DOWN.
#
# INPUTS:
#   $1 - HOST - string - host/ip of the controller
#   $2 - USER - string - the username used to authenticate with controller
#   $3 - PASSWORD - string - the password of the given USER
#
# OUTPUTS:
#   count - int - number of peers that are not UP
#-------------------------------------------------------------------------
from aviatrix import Aviatrix
import logging
import sys

if len(sys.argv) != 4:
    print ('usage: %s <HOST> <USER> <PASSWORD>\n'
           '  where\n'
           '    HOST Aviatrix Controller hostname or IP\n'
           '    USER Aviatrix Controller login username\n'
           '    PASSWORD Aviatrix Controller login password\n' % sys.argv[0])
    sys.exit(1)

controller_ip = sys.argv[1]
username = sys.argv[2]
password = sys.argv[3]

controller = Aviatrix(controller_ip)
controller.login(username, password)
peers = controller.list_peers_vpc_pairs()

# count all peers that are not UP
count = 0
for peer in peers:
    if peer['peering_state'].lower() != 'up':
        count = count + 1

# print out the total count of gateways found to be DOWN
print count
