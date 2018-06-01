#!/usr/bin/env python
#-------------------------------------------------------------------------
# This script provides an example of how to connect to an Aviatrix Controller
# and detach existing VPN users from their current VPN gateway and then
# attach them to a new VPN gateway
#
# INPUTS:
#   $1 - HOST - string - host/ip of the controller
#   $2 - USER - string - the username used to authenticate with controller
#   $3 - PASSWORD - string - the password of the given USER
#
#-------------------------------------------------------------------------

import logging
import sys

from aviatrix import Aviatrix

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

#logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

controller = Aviatrix(controller_ip)
controller.login(username, password)

users = controller.list_vpn_users()
for user in users:
    if user['attached']:
        controller.detach_vpn_user(user['vpc_id'], user['_id'])
    controller.attach_vpn_user('Aviatrix-vpc', # TODO: ELB (from controller UI)
                               'vpc-abcd0000', # TODO: VPC ID
                               user['_id'], # username
                               user['email'], # email
                               None,
                               'TODO') # TODO
