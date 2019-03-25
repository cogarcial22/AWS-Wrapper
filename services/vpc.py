import boto3
from awrapperlib import aw, logger as log


class VPCFactory:
    DEFAULT_VPC_NAME = 'dms-vpc-AWS-Wrapper'
    DEFAULT_SUBNET_NAME = 'dms-subnet@-AWS-Wrapper'
    DEFAULT_SUBNET_NUMBER = 1
    DEFAULT_IGW_NAME = 'dms-igw-AWS-Wrapper'
    DEFAULT_ROUTE_NAME = 'dms-route-AWS-Wrapper'
    DEFAULT_CIDR = '10.10.0.0/16'
    DEFAULT_SUBNET = '10.10.@.0/24'
    DEFAULT_DESTINATION_CIDR = '0.0.0.0/0'

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.region = self.get_region()
        self.subnet_number = self.get_subnet_number()
        self.vpc_name = self.get_vpc_name()
        self.subnet_names = self.get_subnet_names()
        self.igw_name = self.get_igw_name()
        self.route_name = self.get_route_name()
        self.cidr_block = self.get_cidr_block()
        self.subnet_cidr = self.get_subnet_cidr()
        self.vpc_client = boto3.client('ec2', region_name=self.region)

    def get_region(self):
        return self.kwargs['region'] if 'region' in self.kwargs else aw.DEFAULT_REGION

    def get_subnet_number(self):
        return self.kwargs['subnet_number'] if 'subnet_number' in self.kwargs else self.DEFAULT_SUBNET_NUMBER

    def get_vpc_name(self):
        return self.kwargs['vpc_name'] if 'vpc_name' in self.kwargs else self.DEFAULT_VPC_NAME

    def get_subnet_names(self):
        subnet = []
        for i in range(self.subnet_number):
            if 'subnet_name' in self.kwargs:
                subnet.append(self.kwargs['subnet_name'] + str(i))
            else:
                subnet.append(self.DEFAULT_SUBNET_NAME.replace('@', str(i)))
        return subnet

    def get_igw_name(self):
        return self.kwargs['igw_name'] if 'igw_name' in self.kwargs else self.DEFAULT_IGW_NAME

    def get_route_name(self):
        return self.kwargs['route_name'] if 'route_name' in self.kwargs else self.DEFAULT_ROUTE_NAME

    def get_cidr_block(self):
        return self.kwargs['cidr_block'] if 'cidr_block' in self.kwargs else self.DEFAULT_CIDR

    def get_subnet_cidr(self):
        return self.kwargs['subnet_cidr'] if 'subnet_cidr' in self.kwargs else self.DEFAULT_SUBNET


class VPCCreation(VPCFactory):
    """
    VPC creation class, create instance
    """
    # TODO get existing AWS-WRAPPER VPC if exists

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def create_vpc(self):
        response = self.vpc_client.create_vpc(CidrBlock=self.cidr_block, AmazonProvidedIpv6CidrBlock=False,
                                              InstanceTenancy='default')
        setattr(self, 'vpc_id', response['Vpc']['VpcId'])
        self.__create_name_tag(getattr(self, 'vpc_id'), self.vpc_name)
        log.echo_info('Created VPC %s' % self.__get_vpc_id())

    def create_subnet(self):
        # TODO figure out subnet cidr from vpc_cidr
        for i in range(self.subnet_number):
            if '@' in self.subnet_cidr:
                letter = 97 + i
                self.__create_sub_net(self.subnet_cidr.replace('@', str(i)), self.subnet_names[i],
                                      self.region + str(chr(letter)))
            else:
                self.__create_sub_net(self.subnet_cidr, self.subnet_names)

    def __create_sub_net(self, cidr_block, name, az=None):
        if az:
            response = self.vpc_client.create_subnet(CidrBlock=cidr_block, VpcId=self.__get_vpc_id(),
                                                     AvailabilityZone=az)
        else:
            response = self.vpc_client.create_subnet(CidrBlock=cidr_block, VpcId=self.__get_vpc_id())
        self.__create_name_tag(response['Subnet']['SubnetId'], name)
        self.__set_subnet_id(response['Subnet']['SubnetId'])
        log.echo_info('Created Subnet %s' % response['Subnet']['SubnetId'])

    def __create_name_tag(self, resource_id, name):
        self.vpc_client.create_tags(Resources=[resource_id], Tags=[{'Key': 'Name', 'Value': name}])

    def __get_vpc_id(self):
        return getattr(self, 'vpc_id')

    def __get_subnet_id(self):
        return getattr(self, 'subnet_id', None)

    def get_subnet_id(self):
        return getattr(self, 'subnet_id', None)

    def __set_subnet_id(self, subnet):
        if self.__get_subnet_id():
            subnet_list = self.__get_subnet_id().split()
            subnet_list.append(subnet)
            setattr(self, 'subnet_id', subnet_list)
        else:
            setattr(self, 'subnet_id', subnet)

    def create_route_table(self):
        response = self.vpc_client.create_route_table(VpcId=self.__get_vpc_id())
        self.__set_route_table(response['RouteTable']['RouteTableId'])
        log.echo_info('Created Route Table %s' % self.__get_route_table())

    def __set_route_table(self, route_table_id):
        setattr(self, 'route_table_id', route_table_id)
        self.__create_name_tag(route_table_id, self.route_name)

    def __get_route_table(self):
        return getattr(self, 'route_table_id')

    def create_internet_gateway(self):
        response = self.vpc_client.create_internet_gateway()
        self.__set_igw(response['InternetGateway']['InternetGatewayId'])
        log.echo_info('Created Internet Gateway %s' % self.__get_igw())

    def __set_igw(self, igw_id):
        setattr(self, 'igw_id', igw_id)
        self.__create_name_tag(igw_id, self.igw_name)

    def __get_igw(self):
        return getattr(self, 'igw_id')

    def attach_igw(self):
        self.vpc_client.attach_internet_gateway(InternetGatewayId=self.__get_igw(), VpcId=self.__get_vpc_id())
        log.echo_info('Attached Internet Gateway %s to VPC %s' % (self.__get_igw(), self.__get_vpc_id()))

    def associate_route_table(self):
        subnets = self.__get_subnet_id()
        if isinstance(subnets, list):
            for subnet in subnets:
                self.__associate_route_table(subnet)
        else:
            self.__associate_route_table(subnets)

    def __associate_route_table(self, subnet_id):
        self.vpc_client.associate_route_table(RouteTableId=self.__get_route_table(), SubnetId=subnet_id)
        log.echo_info('Associating Route Table %s to Subnet %s' % (self.__get_route_table(), subnet_id))

    def create_igw_route(self):
        self.vpc_client.create_route(DestinationCidrBlock=self.DEFAULT_DESTINATION_CIDR, GatewayId=self.__get_igw(),
                                     RouteTableId=self.__get_route_table())
        log.echo_info('Creating Route on Route Table %s = Traffic from %s to Internet Gateway %s' %
                      (self.__get_route_table(), self.DEFAULT_DESTINATION_CIDR, self.__get_igw()))

    def get_vpc_default_security_group(self):
        response = self.vpc_client.describe_security_groups(
            Filters=[{'Name': 'vpc-id', 'Values': [self.__get_vpc_id()]}])
        return next(iter(response.items()))[1][0]['GroupId']
