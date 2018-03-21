#!/usr/bin/env python
#-------------------------------------------------------------------------
# This script provides an example of how to connect to an Aviatrix Controller
# and create a user ssl vpn gateway.
#
# INPUTS:
#   $1 - HOST - string - host/ip of the controller
#   $2 - USER - string - the username used to authenticate with controller
#   $3 - PASSWORD - string - the password of the given USER
#
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

#logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

controller = Aviatrix(controller_ip)
controller.login(username, password)
controller.create_gateway('demoteam', # account_name
                          Aviatrix.CloudType.AWS, # cloud_type
                          'vpn', # gateway name
                          'vpc-abcd0000', # VPC ID
                          'us-east-1', # region
                          't2.micro', # size
                          '172.16.44.0/28', # public subnet
                          vpn_access='yes',
                          enable_elb='yes',
                          cidr='192.168.43.0/24',
                          max_conn=100,
                          split_tunnel='yes',
                          enable_ldap='no')

controller.add_vpn_user('Aviatrix-vpc', # ELB name
                        'vpc-abcd0000', # VPC ID
                        'jdoe', # username
                        'johndoe@example.com', # email
                        None) # profile
