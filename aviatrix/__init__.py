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
import urllib.request, urllib.parse, urllib.error
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
        return int((date_to_convert - Util.EPOCH).total_seconds())


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
            super(Aviatrix.RESTException, self).__init__('Aviatrix REST API: {}'.format(reason))
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
        url = 'https://{0}/v1/{1}'.format(self.controller_ip, ('api' if not is_backend else 'backend1'))
        new_parameters = dict(parameters)
        new_parameters['action'] = action
        new_parameters['CID'] = self.customer_id
        data = urllib.parse.urlencode(new_parameters)
        if method == 'GET':
            url = url + '?' + data
            req = urllib.request.Request(url)
        elif method == 'POST':
            data = data.encode()
            req = urllib.request.Request(url, data)
        else:
            raise ValueError('Invalid method {}'.format(method))
        with urllib.request.urlopen(req, context=self.ctx) as response:
            json_response = response.read()
            logging.debug('[{0}] HTTP Response: {1}'.format(url, json_response))

        if json_response[0:6] == 'Error:':
            raise ValueError(json_response)
        try:
            self.result = json.loads(json_response)
            if 'return' in self.result:
                if not self.result['return']:
                    self.results = None
                    raise Aviatrix.RESTException(self.result['reason'])
                else:
                    self.results = self.result['results']
            else:
                self.results = self.result
        except ValueError as nojson:
            if str(nojson) == 'No JSON object could be decoded':
                self.results = json_response
            else:
                raise nojson

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
        except AttributeError as login_err:
            logging.info('Login Request Failed. AttributeError: {}'.format(str(login_err)))

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

    def setup_account_profile(self, account, cloud_type, aws_account_number, aws_role_arn, aws_role_ec2):
        """
        Onboard a new account.
        Arguments:
        account - string - the name of the account to be display in the Controller
        cloud_type - int - 1 (AWS), 2 (Azure), 4 (GCP), 8 (ARM),
                           256 (AWS govcloud), 512 (Azure China),
                           1024 (AWS China), 2048 (ARM China);
                           can be OR'd together
        aws_account_number - string - the AWS account number
        aws_role_arn - string - the AWS ARN of the App role
        aws_role_ec2 - string - the AWS ARN of the EC2 role
        """
        params = {'account_name': account,
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

    def get_controller_public_ip(self):
        """
        Gets the Aviatrix Controller public IP address
        Returns:
        The Public IP address
        """

        params = {'public': 'yes'}
        self._avx_api_call('POST', 'show_controller_ip', params, True)
        return self.results['public_ip']

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
        for key, value in kwargs.items():
            if key in Aviatrix.CREATE_GW_ALLOWED:
                params[key] = value
        self._avx_api_call('POST', 'connect_container', params)

    CREATE_SPOKE_GW_ALLOWED=['account_name', 'cloud_type', 'region', 'vpc_id', 'public_subnet', 'gw_name',
                             'gw_size', 'dns_server', 'nat_enabled', 'tags']

    def create_spoke_gateway(self, account_name, cloud_type, region, vpc_id, public_subnet, gw_name,
                             gw_size, **kwargs):
        """
                Create a new Aviatrix Spoke Gateway.
                Arguments:
                account_name - string - the name of the cloud account where this gateway will be provisioned
                cloud_type - int - 1 (AWS), 2 (Azure), 4 (GCP), 8 (ARM),
                                   256 (AWS govcloud), 512 (Azure China),
                                   1024 (AWS China), 2048 (ARM China)
                region - string - the VPC region name
                vpc_id - string - the VPC ID from AWS (see the AWS VPC Dashboard)
                public_subnet - string - The public subnet info example: AWS: "CIDR~~ZONE~~SubnetName"
                gw_name - string - the name of the new gateway
                gw_size - string - the size of the gateway instance
                kwargs - additional arguments supported:
                    dns_server - string - specify the DNS IP
                    nat_enabled - string - specify whether enabling NAT feature on the gateway or not
                    tags - string - Instance tag of cloud provider
        """

        params = {'account_name': account_name,
                  'cloud_type': cloud_type,
                  'region': region,
                  'vpc_id': vpc_id,
                  'public_subnet': public_subnet,
                  'gw_name': gw_name,
                  'gw_size': gw_size}
        for key, value in kwargs.items():
            if key in Aviatrix.CREATE_SPOKE_GW_ALLOWED:
                params[key] = value
        self._avx_api_call('POST', 'create_spoke_gw', params)

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

    def get_gateway_by_name(self, account_name, gw_name):
        """
        Gets a gateway by name
        Arguments:
        account_name - string - the name of the cloud account
        gw_name - string - the name of the gateway name
        Returns:
        matching gateway object or None if not found
        """
        gws = self.list_gateways(account_name)
        if not gws:
            return None

        for gwy in gws:
            if gwy['vpc_name'] == gw_name:
                return gwy

        return None

    def list_vpn_users(self):
        """
        Lists all VPN users
        Returns:
        Array of VPN user objects
        """

        self._avx_api_call('GET', 'list_vpn_users', {})
        return self.results

    def delete_vpn_user(self, vpc_id, username):
        """
        Delete a VPN user
        Arguments:
        vpc_id - string - the VPC ID from where the user will be deleted
        username - string - the username to delete
        """

        params = {'vpc_id': vpc_id,
                  'username': username}
        self._avx_api_call('GET', 'delete_vpn_user', params)

    def add_vpn_user(self, lb_name, vpc_id, username,
                     user_email=None,
                     profile_name=None,
                     saml_endpoint=None):
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
        saml_endpoint - string - (optional) the saml endpoint for this user
        """

        params = {'lb_name': lb_name,
                  'vpc_id': vpc_id,
                  'username': username,
                  'dns': 'false',
                  'external_user': 'false'}
        if user_email:
            params['user_email'] = user_email
        if profile_name:
            params['profile_name'] = profile_name
        if saml_endpoint:
            params['saml_endpoint'] = saml_endpoint
        self._avx_api_call('POST', 'add_vpn_user', params, True)

    def detach_vpn_user(self, vpc_id, username):
        """
        Detaches an existing VPN user from the VPC.
        Arguments:
        vpc_id - string - the VPC ID that the user is currently attached
        username - string - the username to detach
        """

        params = {'vpc_id_or_dns_name': vpc_id,
                  'username': username,
                  'dns': 'false'}
        self._avx_api_call('POST', 'detach_vpn_user', params)

    def attach_vpn_user(self, lb_name, vpc_id, username,
                        user_email=None,
                        profile_name=None,
                        saml_endpoint=None):
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
        saml_endpoint - string - (optional) the saml endpoint for this user
        """

        params = {'lb_name': lb_name,
                  'vpc_id_or_dns_name': vpc_id,
                  'username': username,
                  'dns': 'false',
                  'external_user': 'false',
                  'use_profile': 'false'}
        if user_email:
            params['user_email'] = user_email
        if profile_name:
            params['use_profile'] = 'true'
            params['profile_name'] = profile_name
        if saml_endpoint:
            params['saml_endpoint'] = saml_endpoint
        self._avx_api_call('POST', 'attach_vpn_user', params)

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

        if isinstance(gw_names, str):
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

    def enable_nat(self, gw_name):
        """
        Enables NAT on the given gateway
        Arguments:
        gw_name - string - gateway name

        """

        params = {'gw_name': gw_name}
        self._avx_api_call('POST', 'enable_nat', params)

    def disable_nat(self, gw_name):
        """
        Disables NAT on the given gateway
        Arguments:
        gw_name - string - gateway name

        """

        params = {'gw_name': gw_name}
        self._avx_api_call('POST', 'disable_nat', params)

    def add_fqdn_filter_tag(self, tag_name):
        """
        Adds FQDN Filter Tag
        Arguments:
        tag_name - name of the filter tag to create
        """

        params = {'tag_name': tag_name}
        self._avx_api_call('POST', 'add_fqdn_filter_tag', params)

    def delete_fqdn_filter_tag(self, tag_name):
        """
        Deletes FQDN Filter Tag
        Arguments:
        tag_name - name of the filter tag to delete
        """

        params = {'tag_name': tag_name}
        self._avx_api_call('POST', 'del_fqdn_filter_tag', params)

    def set_fqdn_filter_domain_list(self, tag_name, domains):
        """
        Sets the domain definitions for the given FQDN filter
        Arguments:
        tag_name - the name of the tag to update
        domains - list of domain definitions
                  for example: ["*.google.com", "cnn.com"]
        """

        params = {'tag_name': tag_name, 'domain_names[]': domains}
        self._avx_api_call('POST', 'set_fqdn_filter_tag_domain_names', params)

    def get_fqdn_filter_domain_list(self, tag_name):
        """
        Gets the domain definitions for the given FQDN filter
        Arguments:
        tag_name - the name of the tag to get
        """

        params = {'tag_name': tag_name}
        self._avx_api_call('GET', 'list_fqdn_filter_tag_domain_names', params)
        return self.results

    def set_fqdn_filter_black_list(self, tag_name):
        """
        Sets the FQDN filter to be a black list (rather than a white list)
        Arguments:
        tag_name - name of the filter tag to change
        """

        params = {'tag_name': tag_name, 'color': 'black'}
        self._avx_api_call('POST', 'set_fqdn_filter_tag_color', params)

    def set_fqdn_filter_white_list(self, tag_name):
        """
        Sets the FQDN filter to be a black list (rather than a white list)
        Arguments:
        tag_name - name of the filter tag to change
        """

        params = {'tag_name': tag_name, 'color': 'white'}
        self._avx_api_call('POST', 'set_fqdn_filter_tag_color', params)

    def enable_fqdn_filter(self, tag_name):
        """
        Enables the given FQDN filter
        Arguments:
        tag_name - name of the filter tag to change
        """

        params = {'tag_name': tag_name, 'status': 'enabled'}
        self._avx_api_call('POST', 'set_fqdn_filter_tag_state', params)

    def disable_fqdn_filter(self, tag_name):
        """
        Disables the given FQDN filter
        Arguments:
        tag_name - name of the filter tag to change
        """

        params = {'tag_name': tag_name, 'status': 'disabled'}
        self._avx_api_call('POST', 'set_fqdn_filter_tag_state', params)

    def attach_fqdn_filter_to_gateway(self, tag_name, gw_name):
        """
        Attaches the given gateway to the given FQDN Filter
        Arguments:
        tag_name - the FQDN tag name to attach
        gw_name - the gateway name that this tag will be attached to
        """

        params = {'tag_name': tag_name, 'gw_name': gw_name}
        self._avx_api_call('POST', 'attach_fqdn_filter_tag_to_gw', params)

    def detach_fqdn_filter_from_gateway(self, tag_name, gw_name):
        """
        Detaches the given gateway from the given FQDN Filter
        Arguments:
        tag_name - the FQDN tag name to detach
        gw_name - the gateway name that this tag will be detached to
        """

        params = {'tag_name': tag_name, 'gw_name': gw_name}
        self._avx_api_call('POST', 'detach_fqdn_filter_tag_from_gw', params)

    def list_fqdn_filter_gateways(self, tag_name):
        """
        Lists the gateways attached to the specified FQDN filter
        Arguments:
        tag_name - the FQDN filter name
        Returns:
        List of gateway(s) attached to this tag
        """

        params = {'tag_name': tag_name}
        self._avx_api_call('GET', 'list_fqdn_filter_tag_attached_gws', params)
        return self.results

    def list_fqdn_filters(self):
        """
        Lists all FQDN filter tags defined
        """

        params = {}
        self._avx_api_call('GET', 'list_fqdn_filter_tags', params)
        return self.results

    def list_fw_tags(self):
        """
        Lists all policy tags defined
        Arguments:
        None
        """

        params = {}
        self._avx_api_call('POST', 'list_policy_tags', params, True)
        return self.results

    def add_fw_tag(self, tag_name):
        """
        Adds a new FW policy tag
        Arguments:
        tag_name - the name of the FW policy tag
        """

        params = {'tag_name': tag_name}
        self._avx_api_call('POST', 'add_policy_tag', params)

    def delete_fw_tag(self, tag_name):
        """
        Removes a FW policy tag
        Arguments:
        tag_name - string - the name of the FW policy tag to remove
        """

        params = {'tag_name': tag_name}
        self._avx_api_call('POST', 'del_policy_tag', params)

    def get_fw_tag_members(self, tag_name):
        """
        Lists all policy tag members (name + CIDR)
        Arguments:
        tag_name - string - the name of the FW policy tag to retrieve
        """

        params = {'tag_name': tag_name}
        self._avx_api_call('GET', 'list_policy_members', params)
        return self.results['members']

    def set_fw_tag_members(self, tag_name, members):
        """
        Sets the policies associated with the given tag.
        Arguments:
        tag_name - string - the name of the FW policy tag
        members - list[dict] - dict should include 'name', 'cidr'
        """

        params = {'tag_name': tag_name}
        current = 0
        for member in members:
            params['new_policies[%d][name]' % (current)] = member['name']
            params['new_policies[%d][cidr]' % (current)] = member['cidr']
            current = current + 1

        self._avx_api_call('POST', 'update_policy_members', params)

    def get_fw_policy_full(self, gw_name):
        """
        Gets the firewall policy defined for a single VPC/GW.
        Arguments:
        gw_name - string - the name of the gateway to return policies
        Returns:
        dict with base_policy, base_policy_log_enable, _and_ security_rules
           NOTE: security_rules corresponds to what you set in set_fw_policy()
        """

        params = {'vpc_name': gw_name}
        self._avx_api_call('GET', 'vpc_access_policy', params)
        return self.results

    def set_fw_policy_security_rules(self, gw_name, rules):
        """
        Sets the firewall policy rules for the given gateway
        Arguments:
        gw_name - string - the name of the gateway to return policies
        rules - list[dict] - list of dictionary with keys
                ('protocol', 's_ip', 'log_enable', 'd_ip', 'deny_allow', 'port')
               all keys are required and all values are strings
               deny_allow is one of ('allow', 'deny')
               protocol is one of ('all', 'tcp', 'udp', 'icmp', 'sctp', 'rdp', 'dccp')
               s_ip/d_ip - valid CIDR or tag name
               port - single port or range ('25', '25:1024', etc.)
               log_enable is one of ('on', 'off')
        """

        params = {'vpc_name': gw_name, 'new_policy': json.dumps(rules)}
        self._avx_api_call('GET', 'update_access_policy', params)

    def list_accounts(self):

        """
        Lists all Accounts
        """

        params = {}
        self._avx_api_call('GET', 'list_accounts', params)
        return self.results

    def list_spoke_gws(self):
        """
        Lists spoke gateways
        """

        params = {}
        self._avx_api_call('GET', 'list_spoke_gws', params)
        return self.results

    def list_public_subnets(self, account_name, region, vpc_id, cloud_type):
        """
                Gets a list of gateways
                Arguments:
                account_name - string - the name of the cloud account
                region - string - Region of the resource in cloud provider
                vpc_id - string - the VPC ID of the cloud provider
                Returns:
                the list of public subnets
                """
        params = {'account_name': account_name,
                  'region': region,
                  'vpc_id': vpc_id,
                  'cloud_type': cloud_type
                  }
        self._avx_api_call('GET', 'list_public_subnets', params)
        return self.results

    def list_spoke_gw_supported_sizes(self):
        """
                Gets a list of supported gateway sizes
                Arguments:
                Returns:
                the list of supported gateway sizes
                """
        params = {}
        self._avx_api_call('GET', 'list_spoke_gw_supported_sizes', params)
        return self.results

    def list_transit_gws(self):
        """
                Gets a list of supported gateway sizes
                Arguments:
                Returns:
                the list of supported gateway sizes
                """
        params = {}
        self._avx_api_call('GET', 'list_transit_gws', params)
        return self.results

    def enable_single_az_ha(self, gw_name):
        """
        Enables single AZ HA on the gateway
        Arguments:
        gw_name - the gateway name that will have single AZ HA enabled
        """

        params = {'gw_name': gw_name}
        self._avx_api_call('POST', 'enable_single_az_ha', params)

    def enable_spoke_ha(self, gw_name, public_subnet):
        """
        Enables spoke HA on the gateway
        Arguments:
        gw_name - the gateway name that will have HA enabled
        public_subnet - The public subnet to deploy the ha gateway to
        """

        params = {'gw_name': gw_name, 'public_subnet': public_subnet}
        self._avx_api_call('POST', 'enable_spoke_ha', params)

    def attach_spoke_to_transit_gw(self, spoke_gw, transit_gw):
        """
        Enables spoke HA on the gateway
        Arguments:
        gw_name - the gateway name that will have HA enabled
        public_subnet - The public subnet to deploy the ha gateway to
        """

        params = {'spoke_gw': spoke_gw, 'transit_gw': transit_gw}
        self._avx_api_call('POST', 'attach_spoke_to_transit_gw', params)