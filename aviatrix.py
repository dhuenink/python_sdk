"""
Python SDK wrapper for Aviatrix REST APIs

See Also:
https://s3-us-west-2.amazonaws.com/avx-apidoc/index.htm

Usage:

from aviatrix import Aviatrix

controller_ip = 'x.x.x.x'
username = 'admin'
password = 'password'

controller = Aviatrix(controller_ip)
controller.login(username, password)
controller ...
"""

from urllib2 import urlopen, URLError
import json
import logging
import urllib
import ssl

class Aviatrix(object):
    """
    This class connects to the Aviatrix Controller and provides an interface
    for provisioning and modifying configuration of your cloud networking.
    """
    logging.basicConfig(filename='./aviatrix.log', level='INFO')

    def __init__(self, controller_ip):
        """
        Constructor for Aviatrix Controller class.  Controller IP is the
        host name or IP address of your controller.
        Arguments:
        controller_ip - string - host name or IP address of Aviatrix Controller
        """
        if not controller_ip:
            raise ValueError('Aviatrix Controller IP is required')
        self.controller_ip = controller_ip
        self.customer_id = ''
        self.url = ''
        self.results = []
        self.result = None
        # Required for SSL Certificate no-verify
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def _avx_api_call(self, method, action, parameters):
        """
        Internal function to handle the API call.
        Arguments:
        method - string - GET/POST
        action - string - the action name (see API docs for details)
        parameters - dict - parameters to send to controller for this action
        Side Effects:
        self.result - set to the JSON response object
        self.results - set to the reason or results object
        """
        url = 'https://%s/v1/api?action=%s' % (self.controller_ip, action)
        for key, value in parameters.iteritems():
            value = urllib.quote(value, safe='')
            url = url + '&%s=%s' % (key, value)
        self.url = url
        parameters['CID'] = self.customer_id
        logging.info('Executing API call: %s', self.url)
        try:
            if method == 'POST':
                data = urllib.urlencode(parameters)
                response = urlopen(self.url, data=data, context=self.ctx)
            else:
                response = urlopen(self.url, context=self.ctx)
            json_response = response.read()
            logging.debug('HTTP Response: %s', json_response)
            self.result = json.loads(json_response)
            if not self.result['return']:
                self.results = self.result['reason']
            else:
                self.results = self.result['results']

        except URLError, api_failed:
            logging.info('Failed request. URLError: %s', str(api_failed.reason))

    def login(self, username, password):
        """
        Login to the controller.
        Arguments:
        username - string - the username to login to the controller with
        password - string - the password for the given  username
        Side Effects:
        self.customer_id set to the CID in the response
        """
        if not username or not password:
            raise ValueError('Username and password are required')
        self._avx_api_call('GET', 'login', {'username': username,
                                            'password': password})
        try:
            if self.result['return']:
                self.customer_id = self.result['CID']
        except AttributeError, login_err:
            logging.info('Login Request Failed. AttributeError: %s', str(login_err))

    def admin_email(self, email):
        """
        Sets the Administrator email address.
        Arguments:
        email - string - email address
        """

        self._avx_api_call('GET', 'add_admin_email_addr', {'admin_email': email})

    def change_password(self, account, username, old_password, password):
        """
        Change the password for the given account and username
        Arguments:
        account - string - the name of the cloud account
        username - string - the name of the user to update the password for
        old_password - string - the current password
        password - string - the new password
        """
        params = {'account_name': account,
                  'user_name': username,
                  'old_password': old_password,
                  'password': password}
        self._avx_api_call('GET', 'change_password', params)

    def initial_setup(self, subaction):
        """
        Performs the initial setup action
        Arguments:
        subaction - string - one of 'run' or 'check'
        """
        self._avx_api_call('POST', 'initial_setup', {'subaction': subaction})

    def setup_account_profile(self, account, password, email, cloud_type,
                              aws_account_number, aws_role_arn, aws_role_ec2):
        """
        Onboard a new account.
        Arguments:
        account - string - the name of the account to be display in the Controller
        password - string - the password for the new admin user that will be
                            created for this account
        email - string - the email address associated with the new admin user
        cloud_type - int - 1 (AWS), 2 (Azure), 4 (GCP), 8 (ARM),
                           256 (AWS govcloud), 512 (Azure China),
                           1024 (AWS China), 2048 (ARM China);
                           can be OR'd together
        aws_account_number - string - the AWS account number
        aws_role_arn - string - the AWS ARN of the App role
        aws_role_ec2 - string - the AWS ARN of the EC2 role
        """
        params = {'account_name': account,
                  'account_password': password,
                  'account_email': email,
                  'cloud_type': cloud_type,
                  'aws_iam': 'true',
                  'aws_account_number': aws_account_number,
                  'aws_role_arn': aws_role_arn,
                  'aws_role_ec2': aws_role_ec2}
        self._avx_api_call('POST', 'setup_account_profile', params)

    def setup_customer_id(self, customer_id):
        """
        Set the customer ID on the Controller (only needed for BYOL installations)
        Arguments:
        customer_id - string - the customer ID provided by Aviatrix
        """

        params = {'customer_id': customer_id}
        self._avx_api_call('GET', 'setup_customer_id', params)

    def create_gateway(self, account, cloud_type, gw_name, vpc_id, vpc_region,
                       vpc_size, vpc_net):
        """
        Create a new Aviatrix Gateway.
        Arguments:
        account - string - the name of the cloud account where this gateway will be provisioned
        cloud_type - int - 1 (AWS), 2 (Azure), 4 (GCP), 8 (ARM),
                           256 (AWS govcloud), 512 (Azure China),
                           1024 (AWS China), 2048 (ARM China)
        gw_name - string - the name of the new gateway
        vpc_id - string - the VPC ID from AWS (see the AWS VPC Dashboard)
        vpc_region - string - the VPC region name
        vpc_size - string - the size of the instance
        vpc_net - string - the CIDR block of the subnet where this gateway will be deployed
        """

        params = {'account_name': account,
                  'cloud_type': cloud_type,
                  'gw_name': gw_name,
                  'vpc_id': vpc_id,
                  'vpc_reg': vpc_region,
                  'vpc_size': vpc_size,
                  'vpc_net': vpc_net}
        self._avx_api_call('POST', 'connect_container', params)

    def delete_gateway(self, cloud_type, gw_name):
        """
        Delete a gateway
        Arguments:
        cloud_type - int - 1 (AWS), 2 (Azure), 4 (GCP), 8 (ARM),
                           256 (AWS govcloud), 512 (Azure China),
                           1024 (AWS China), 2048 (ARM China)
        gw_name - string - the name of the gateway to delete
        """
        self._avx_api_call('GET', 'delete_container', {'cloud_type': cloud_type,
                                                       'gw_name': gw_name})
    def peering(self, vpc_name1, vpc_name2):
        """
        Connect 2 gateways together with Aviatrix Encrypted Peering
        Arguments:
        vpc_name1 - string - name of the gateway
        vpc_name2 - string - name of the second gateway
        """
        self._avx_api_call('GET', 'peer_vpc_pair', {'vpc_name1': vpc_name1,
                                                    'vpc_name2': vpc_name2})

    def unpeering(self, vpc_name1, vpc_name2):
        """
        Disconnect 2 gateways
        Arguments:
        vpc_name1 - string - name of the gateway
        vpc_name2 - string - name of the second gateway
        """
        self._avx_api_call('GET', 'unpeer_vpc_pair', {'vpc_name1': vpc_name1,
                                                      'vpc_name2': vpc_name2})

    def enable_vpc_ha(self, vpc_name, specific_subnet):
        """
        Enable HA for a GW
        Arguments:
        vpc_name - string - the name of the gateway
        specific_subnet - string -
        """
        params = {'vpc_name': vpc_name,
                  'specific_subnet': specific_subnet}
        self._avx_api_call('POST', 'enable_vpc_ha', params)

    def disable_vpc_ha(self, vpc_name, specific_subnet):
        """
        Disable HA for a gateway
        Arguments:
        vpc_name - string - the name of the gateway
        specific_subnet - string -
        """
        self._avx_api_call('POST', 'disable_vpc_ha', {'vpc_name': vpc_name,
                                                      'specific_subnet': specific_subnet})

    def extended_vpc_peer(self, source, nexthop, reachable_cidr):
        """
        Configure transitive peering
        Argument:
        source - the source gateway name
        nexthop - the name of the gateway that will be the "Next Hop"
        reachable_cidr - the CIDR of the destination
        """
        params = {'source': source,
                  'nexthop': nexthop,
                  'reachable_cidr': reachable_cidr}
        self._avx_api_call('POST', 'add_extended_vpc_peer', params)

    def list_peers_vpc_pairs(self):
        """
        Lists the gateways that are peered
        """
        self._avx_api_call('GET', 'list_peer_vpc_pairs', {})

    def list_gateways(self, account_name):
        """
        Gets a list of gateways
        Arguments:
        account_name - string - the name of the cloud account
        """
        self._avx_api_call('GET', 'list_vpcs_summary', {'account_name': account_name})

    def add_vpn_user(self, vpc_id, username, user_email, profile_name):
        """
        Add a new VPN user
        Arguments:
        vpc_id - string - the VPC ID where this user will be added
        username - string - the name of the user
        user_email - string - (optional) the email address where this user's
                              certificate and instructions should be emailed
        profile_name - string - (optional) the name of the profile that this
                                user should be assigned
        """

        params = {'vpc_id': vpc_id,
                  'username': username,
                  'user_email': user_email,
                  'profile_name': profile_name}
        self._avx_api_call('GET', 'add_vpn_user', params)
