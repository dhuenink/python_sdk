from aviatrix import Aviatrix
import logging
import sys

controller_ip = 'controller.example.com'
username = 'admin'
password = 'password'

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
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
