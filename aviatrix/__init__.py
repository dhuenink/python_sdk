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

import datetime
import json
import logging
import urllib
import urllib2
import ssl

class Util(object):
    """
    Utilities class
    """

    EPOCH = datetime.datetime.utcfromtimestamp(0)
    @staticmethod
    def unix_time(date_to_convert):
        """
        Converts the given datetime object to unix time (seconds since epoch)
        """
        if not date_to_convert:
            return 0
        return long((date_to_convert - Util.EPOCH).total_seconds())

class Aviatrix(object):
    """
    This class connects to the Aviatrix Controller and provides an interface
    for provisioning and modifying configuration of your cloud networking.
    """

    class RESTException(Exception):
        """
        Base exception for REST API failures from aviatrix
        """
        def __init__(self, reason=None):
            """
            Constructor
            Arguments:
            reason - reason provided by the JSON response object
            """
            super(Aviatrix.RESTException, self).__init__('Aviatrix REST API: %s' % reason)
            self.reason = reason

    class CloudType(object):
        """
        Enum representation for the cloud_type argument
        """

        AWS = 1
        AZURE = 2
        GCP = 4
        ARM = 8
        AWS_GOVCLOUD = 256
        AZURE_CHINA = 512
        AWS_CHINA = 1024
        ARM_CHINA = 2048

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
        self.results = []
        self.result = None
        # Required for SSL Certificate no-verify
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def _avx_api_call(self, method, action, parameters, is_backend=False):
        """
        Internal function to handle the API call.
        Arguments:
        method - string - GET/POST
        action - string - the action name (see API docs for details)
        parameters - dict - parameters to send to controller for this action
        is_backend - bool - true is public API

        Side Effects:
        self.result - set to the JSON response object
        self.results - set to the reason or results object
        """
        url = 'https://%s/v1/%s' % (self.controller_ip, ('api' if not is_backend else 'backend1'))
        new_parameters = dict(parameters)
        new_parameters['action'] = action
        new_parameters['CID'] = self.customer_id
        data = urllib.urlencode(new_parameters)
        if method == 'GET':
            url = url + '?' + data
            response = urllib2.urlopen(url, context=self.ctx)
        elif method == 'POST':
            response = urllib2.urlopen(url, data=data, context=self.ctx)
        else:
            raise ValueError('Invalid method %s', method)

        json_response = response.read()
        logging.debug('[%s] HTTP Response: %s', url, json_response)
        self.result = json.loads(json_response)
        if 'return' in self.result:
            if not self.result['return']:
                self.results = None
                raise Aviatrix.RESTException(self.result['reason'])
            else:
                self.results = self.result['results']
        else:
            self.results = self.result

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

    CREATE_GW_ALLOWED = ['cloud_type', 'account_name', 'gw_name', 'vpc_reg',
                         'zone', 'vpc_net', 'vpc_size', 'vpc_id', 'enable_nat',
                         'vpn_access', 'cidr', 'otp_mode', 'duo_integration_key',
                         'duo_secret_key', 'duo_api_hostname', 'duo_push_mode',
                         'okta_url', 'okta_token', 'okta_username_suffix',
                         'enable_elb', 'elb_name', 'enable_client_cert_sharing',
                         'max_conn', 'split_tunnel', 'additional_cidrs',
                         'nameservers', 'search_domains', 'enable_pbr',
                         'pbr_subnet', 'pbr_default_gateway', 'pbr_logging',
                         'enable_ldap', 'ldap_server', 'ldap_bind_dn',
                         'ldap_password', 'ldap_base_dn', 'ldap_user_attr',
                         'ldap_additional_req', 'ldap_use_ssl',
                         'ldap_client_cert', 'ldap_ca_cert', 'save_template',
                         'allocate_new_eip']

    def create_gateway(self, account, cloud_type, gw_name, vpc_id, vpc_region,
                       vpc_size, vpc_net, **kwargs):
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
        kwargs - additional arguments supported:
             enable_nat - string - enable NAT for this gw ('yes' or 'no')
             vpn_access - string - enable VPN for this GW ('yes' or 'no')
             cidr - string - the VPN client CIDR block
             otp_mode - string - MFA configuration ('2': DUO, '3': Okta)
             duo_integration_key - string -
             duo_secret_key - string -
             duo_api_hostname - string -
             okta_url - string -
             okta_token - string -
             okta_username_suffix - string -
             enable_elb - string - enable ELB ('yes' or 'no')
             enable_client_cert_sharing - enable CCS ('yes' or 'no')
             max_conn - int - maximum number of connections
             split_tunnel - string - enable split tunnel?  ('yes' or 'no')
             additional_cidrs - string - additional CIDR blocks for split tunnel
             nameservers - string - name server(s) for split tunnel
             search_domains - string - search domains for split tunnel
             pbr_subnet - string - Policy Based Routing CIDR
             pbr_default_gateway - string - default gateway for policy based routing
             pbr_logging - string - enable logging ('yes' or 'no')
             enable_ldap - string - enable LDAP ('yes' or 'no')
             ldap_server - string -
             ldap_bind_dn - string -
             ldap_password - string -
             ldap_base_dn - string -
             ldap_user_attr - string -
             ldap_additional_req - string -
             ldap_use_ssl - string -
             ldap_client_cert - string -
             ldap_ca_cert - string -
             save_template - string -
             allocate_new_eip - string -
        """

        params = {'account_name': account,
                  'cloud_type': cloud_type,
                  'gw_name': gw_name,
                  'vpc_id': vpc_id,
                  'vpc_reg': vpc_region,
                  'vpc_size': vpc_size,
                  'vpc_net': vpc_net}
        for key, value in kwargs.iteritems():
            if key in Aviatrix.CREATE_GW_ALLOWED:
                params[key] = value
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
        left for backwards compatibility.
        See:
        list_peers()
        """
        return self.list_peers()

    def list_peers(self):
        """
        Lists the gateways that are peered.
        Returns:
        the list of peers
        """
        self._avx_api_call('GET', 'list_peer_vpc_pairs', {})
        return self.results['pair_list']

    def list_gateways(self, account_name):
        """
        Gets a list of gateways
        Arguments:
        account_name - string - the name of the cloud account
        Returns:
        the list of gateways
        """
        params = {'account_name': account_name}
        self._avx_api_call('GET', 'list_vpcs_summary', params)
        return self.results

    def add_vpn_user(self, lb_name, vpc_id, username, user_email, profile_name):
        """
        Add a new VPN user
        Arguments:
        lb_name - string - load balancer name
        vpc_id - string - the VPC ID where this user will be added
        username - string - the name of the user
        user_email - string - (optional) the email address where this user's
                              certificate and instructions should be emailed
        profile_name - string - (optional) the name of the profile that this
                                user should be assigned
        """

        params = {'lb_name': lb_name,
                  'vpc_id': vpc_id,
                  'username': username,
                  'user_email': user_email}
        if profile_name:
            params['profile_name'] = profile_name
        self._avx_api_call('GET', 'add_vpn_user', params)

    class StatName(object):
        """
        Enum representation for the statistic name field
        """

        DATA_AVG_TOTAL = 'data_avg_total'
        DATA_AVG_SENT = 'data_avg_sent'
        DATA_AVG_RECEIVED = 'data_avg_recvd'
        RATE_AVG_TOTAL = 'rate_avg_total'
        RATE_AVG_SENT = 'rate_avg_sent'
        RATE_AVG_RECEIVED = 'rate_avg_recvd'
        RATE_TOTAL = 'rate_total'
        RATE_SENT = 'rate_sent'
        RATE_RECEIVED = 'rate_received'
        RATE_PEAK_TOTAL = 'rate_peak_total'
        RATE_PEAK_SENT = 'rate_peak_sent'
        RATE_PEAK_RECEIVED = 'rate_peak_received'
        CUMULATIVE_SENT = 'cumulative_sent'
        CUMULATIVE_RECEIVED = 'cumulative_received'
        CUMULATIVE_TOTAL = 'cumulative_total'
        DISK_FREE = 'hdisk_free'
        DISK_TOTAL = 'hdisk_tot'
        MEMORY_CACHE = 'memory_cached'
        MEMORY_BUFFER = 'memory_buf'
        MEMORY_SWAPPED = 'memory_swpd'
        MEMORY_FREE = 'memory_free'
        CPU_IDLE = 'cpu_idle'
        CPU_WAIT = 'cpu_wait'
        CPU_USER_SPACE = 'cpu_us'
        CPU_KERNEL_SPACE = 'cpu_ks'
        CPU_STEAL = 'cpu_steal'
        SYSTEM_INTERRUPTS = 'system_int'
        SYSTEM_CONTEXT_SWITCHES = 'system_cs'
        MEMORY_SWAPS_TO_DISK = 'swap_to_disk'
        MEMORY_SWAPS_FROM_DISK = 'swap_from_disk'
        IO_BLOCKS_IN = 'io_blk_in'
        IO_BLOCKS_OUT = 'io_blk_out'
        PROCESSES_WAITING_TO_RUN = 'nproc_running'
        PROCESSES_UNINTERRUPTABLE_SLEEP = 'nproc_non_int_sleep'

    def get_gateway_statistic_over_time(self, gw_names, start, end, stat):
        """
        Gets statistics about one or more gateways during the given timeframe.
        Arguments:
        gw_names - array - array of gateway names
        start - datetime - start time to return statistic
        end - datetime - end time to return statistic
        stat - enum.StatName - the statistic to return

        Returns:
        list of gateways with the data in an array
        """

        if isinstance(gw_names, basestring):
            gw_name = gw_names
        else:
            gw_name = ','.join(gw_names)
        params = {'start_time': Util.unix_time(start),
                  'end_time': Util.unix_time(end),
                  'ds_name': stat,
                  'db_id': 0,
                  'gw_name': gw_name}
        self._avx_api_call('POST', 'get_statistics', params, True)
        return self.results

    def get_current_gateway_statistics(self, gw_name):
        """
        Gets current statistics about a single gateway.
        Arguments:
        gw_name - string - gateway name

        Returns:
        list of statistics
        """

        params = {'gw_name': gw_name}
        self._avx_api_call('POST', 'show_packets_stat_for_gw', params, True)
        return self.results
