# python_sdk
Python script as a wrapper for Aviatrix API

## Installation

```
pip install aviatrix-sdk
```

## Usage examples:

#### Login to controller:
```
from aviatrix import Aviatrix

controller_ip = 'x.x.x.x'
username = 'admin'
password = 'password'

controller = Aviatrix(controller_ip)
controller.login(username,password)
```

#### Create an AWS account:
```
from aviatrix import Aviatrix

controller_ip = 'x.x.x.x'
username = 'admin'
password = 'password'
admin_email = 'test@acme.com'
aviatrixroleapp = 'arn:aws:iam::XXXXXXXXXXX:role/aviatrix-role-app'
aviatrixroleec2 = 'arn:aws:iam::XXXXXXXXXXX:role/aviatrix-role-ec2'

controller = Aviatrix(controller_ip)
controller.login(username,password)
controller.setup_account_profile("<<AWS Account Name>>",
                                 password,
                                 admin_email,
                                 "1",
                                 account,
                                 aviatrixroleapp,
                                 aviatrixroleec2)
```

#### Create a GW
```
from aviatrix import Aviatrix

controller_ip = 'x.x.x.x'
username = 'admin'
password = 'password'
gateway_name = 'GatewayName'
vpcid = 'vpc-XXXXXX'
region = 'us-east-1'
gwsize = 't2.micro'
subnet = '10.x.x.x/24'

controller = Aviatrix(controller_ip)
controller.login(username,password)
controller.create_gateway("AWSAccount",
                                "1",
                                gateway_name,
                                vpcid,
                                region_spoke,
                                gwsize_spoke,
                                subnet_spoke)
```

#### Getting the CID
```
from aviatrix import Aviatrix

controller_ip = 'x.x.x.x'
username = 'admin'
password = 'password'
gateway_name =

controller = Aviatrix(controller_ip)
controller.login(username,password)
controller.CID
```
