#!/usr/bin/env python
"""
 This script provides an example of how to connect to an Aviatrix Controller
 and get the public IP address

 INPUTS:
   $1 - HOST - string - host/ip of the controller
   $2 - USER - string - the username used to authenticate with controller
   $3 - PASSWORD - string - the password of the given USER

"""
import logging
import sys
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


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

    test(sys.argv[1], sys.argv[2], sys.argv[3])

def test(controller_ip, username, password):
    """
    Arguments:
    controller_ip - string - the controller host or IP
    username - string - the controller login username
    password - string - the controller login password
    """

    print 'Connecting to %s' % controller_ip
    controller = Aviatrix(controller_ip)
    controller.login(username, password)

    print controller.get_controller_public_ip()

if __name__ == "__main__":
    main()
