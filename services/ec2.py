"""
EC2 handler
"""

import boto3
import os
import time
from prettytable import PrettyTable
from awrapperlib import aw, resource, logger as log
from multipledispatch import dispatch
from botocore.exceptions import ClientError
import paramiko as ssh
from paramiko.ssh_exception import NoValidConnectionsError
from urllib3.exceptions import NewConnectionError
import socket

DEFAULT_SECURITY_GROUP_NAME = 'AWS-Wrapper'
DEFAULT_REGION = aw.DEFAULT_REGION


class EC2Factory:
    """
    EC2 Factory generate an object that contain the EC2 valid options
    """
    DEFAULT_IMAGE_ID = 'ami-0cd3dfa4e37921605'  # Amazon Linux
    DEFAULT_KEY_PAIR_SUFFIX = 'ec2-keypair'
    DEFAULT_TYPE = 't2.micro'
    TOMCAT_IP_PERMISSIONS = {'FromPort': 8080, 'IpProtocol': 'tcp',
                             'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'TomcatConnection'}], 'ToPort': 8080}
    DEFAULT_IP_PERMISSIONS = {'FromPort': 22, 'IpProtocol': 'tcp',
                              'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'SSH Connection'}], 'ToPort': 22}

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.name = self.get_name()
        self.region = self.get_region()
        self.ec2 = boto3.resource('ec2', region_name=self.region)
        self.type = self.get_type()
        self.user_data = self.get_user_data()
        self.key_pair_name = self.get_key_pair_name()
        self.image = self.get_image()
        self.security_group = self.get_security_group()

    def __create_key_pair(self):
        log.echo_info('Creating Key Pair')
        key_pair_file_name = self.name + self.DEFAULT_KEY_PAIR_SUFFIX + '.pem'
        key_pair_name = self.name + self.DEFAULT_KEY_PAIR_SUFFIX
        output_file = open(key_pair_file_name, 'w')
        key_pair = self.ec2.create_key_pair(KeyName=key_pair_name)
        key_pair_out = str(key_pair.key_material)
        output_file.write(key_pair_out)
        os.chmod(key_pair_file_name, 0o400)
        return key_pair_name

    def __create_security_group(self):
        log.echo_info('Creating Security Group')
        create_security_group = self.ec2.create_security_group(Description=DEFAULT_SECURITY_GROUP_NAME + ' SG',
                                                               GroupName=DEFAULT_SECURITY_GROUP_NAME)
        security_group_id = create_security_group.id
        security_group = self.ec2.SecurityGroup(security_group_id)
        security_group.create_tags(Tags=[{'Key': 'Name', 'Value': DEFAULT_SECURITY_GROUP_NAME}])
        security_group.authorize_ingress(GroupId=security_group_id, IpPermissions=[self.__get_ip_permissions()])
        return security_group_id

    def __get_ip_permissions(self):
        permissions = []
        if self.user_data == 'tomcat':
            permissions.append(self.TOMCAT_IP_PERMISSIONS)
        permissions.append(self.__get_ssh_permissions())
        return permissions

    def __add_ssh_inbound_rule(self, security_group_id):
        try:
            security_group = self.ec2.SecurityGroup(security_group_id)
            security_group.authorize_ingress(GroupId=security_group_id, IpPermissions=[self.__get_ssh_permissions()])
        except ClientError:
            pass

    def __get_ssh_permissions(self):
        ip_permissions = self.DEFAULT_IP_PERMISSIONS
        ip_permissions['IpRanges'][0]['CidrIp'] = aw.get_public_ip()
        return ip_permissions

    def __set_security_group(self):
        self.__add_ssh_inbound_rule(self.kwargs['security_group'])
        return self.kwargs['security_group']

    def get_name(self):
        """
        Get instance name
        :return: Deploy instance name
        """
        return self.kwargs['name'] if 'name' in self.kwargs else aw.exit_with_error('Name must be specified')

    def get_region(self):
        """
        Get current region to work on
        :return: Region name
        """
        return self.kwargs['region'] if 'region' in self.kwargs else DEFAULT_REGION

    def get_type(self):
        """
        Get instance type to be deployed
        :return: Type name
        """
        return self.kwargs['type'] if 'type' in self.kwargs else self.DEFAULT_TYPE

    def get_user_data(self):
        """
        Get user data to deploy on instance
        :return:
        """
        return self.kwargs['user_data'] if 'user_data' in self.kwargs else None

    def get_key_pair_name(self):
        """
        Get key pair name to use on the instance
        :return: Key pair name
        """
        return self.kwargs['key_pair'] if 'key_pair' in self.kwargs else self.__create_key_pair()

    def get_image(self):
        """
        Get image Id to use in instance
        :return: Image id
        """
        return self.kwargs['image'] if 'image' in self.kwargs else self.DEFAULT_IMAGE_ID

    def get_security_group(self):
        """
        Get security group to use on instance
        :return: Security group id
        """
        return self.__set_security_group() if 'security_group' in self.kwargs else self.__create_security_group()

    def get_valid_properties(self):
        """
        Get all valid properties
        :return: Dictionary containing all the properties
        """
        object_list = {}
        for attr, value in self.__dict__.items():
            if not isinstance(value, dict) and not isinstance(value, type(self.ec2)):
                object_list[attr] = value
        return object_list


class Ec2Creation(EC2Factory):
    """
    EC2 creation class, create instance
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def create_instance(self):
        """
        Create instance method
        :return: Instance Id
        """
        tag = [{'ResourceType': 'instance', 'Tags': [{'Key': 'Name', 'Value': self.name}]},
               {'ResourceType': 'volume', 'Tags': [{'Key': 'Name', 'Value': self.name}]}]
        instance_options = dict(ImageId=self.image, MinCount=1, MaxCount=1, InstanceType=self.type,
                                KeyName=self.key_pair_name, TagSpecifications=tag)
        instance_options.update(self.__add_extra_options())
        instance = self.ec2.create_instances(**instance_options)
        return instance

    def __add_extra_options(self):
        extra_options = dict()
        if self.user_data:
            self.user_data = self.__read_script_file()
            extra_options.update(dict(UserData=self.user_data))
        if self.security_group:
            extra_options.update(dict(SecurityGroupIds=[self.security_group]))
        return extra_options

    def __read_script_file(self):
        if self.user_data == 'tomcat':
            script_file = resource.get_resource('Tomcat/tomcat.sh')
            return aw.file_to_string(script_file)
        else:
            aw.exit_with_error('Init Script not supported')


class Ec2Helper:
    """
    Ec2 help method, get instance information
    """
    DEFAULT_STATUS = 'does-not-exist'
    DEFAULT_IP_PERMISSIONS = {'FromPort': 0, 'IpProtocol': 'tcp',
                              'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': ''}], 'ToPort': 0}

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.region = self.get_region()
        self.ec2 = boto3.client('ec2', region_name=self.region)
        self.response = []

    def get_region(self):
        """
        Get current region to work on
        :return: Region name
        """
        return self.kwargs['region'] if 'region' in self.kwargs else DEFAULT_REGION

    def print_key_pairs(self):
        """
        Print available key pairs from AWS
        """
        t = PrettyTable(['KeyName'])
        response = self.get_key_pairs()
        for data in response:
            t.add_row([data])
        log.echo_info(t)

    def print_security_groups(self):
        """
        Print available security groups from AWS
        """
        response = self.get_security_groups()
        t = PrettyTable(['GroupName', 'Description'])
        for data in response:
            t.add_row([data[0], data[1]])
        log.echo_info(t)

    def get_key_pairs(self):
        """
        Get available key pairs from AWS
        :return: List with key pairs [KeyName]
        """
        new_response = []
        response = self.ec2.describe_key_pairs()
        for data in response['KeyPairs']:
            new_response.append(data['KeyName'])
        return new_response

    @dispatch()
    def get_security_groups(self):
        """
        Get available security groups on AWS by GroupId and Description
        :return: List with security groups [[GroupId, Description]]
        """
        response = self.ec2.describe_security_groups()
        for data in response['SecurityGroups']:
            self.response.append([data['GroupId'], data['Description']])
        return self.response

    @dispatch(str)
    def get_security_groups(self, _):
        """
         Get available security groups on AWS by GroupId
        :param _: Overload method to get GroupId
        :return: List with security groups [GroupId]
        """
        response = self.ec2.describe_security_groups()
        for data in response['SecurityGroups']:
            self.response.append(data['GroupId'])
        return self.response

    def get_security_groups_by_name(self):
        """
        Get available security groups on AWS by GroupId and GroupName
        :return: List with security groups [[GroupId, GroupName]]
        """
        response = self.ec2.describe_security_groups()
        for data in response['SecurityGroups']:
            self.response.append([data['GroupId'], data['GroupName']])
        return self.response

    def get_instance_status(self, instance_id):
        """
        Get instance status
        :param instance_id: Instance Id
        :return: Instance status
        """
        if self.instance_exists(instance_id):
            status = self.ec2.describe_instance_status(InstanceIds=[instance_id], IncludeAllInstances=True)
            status = next(iter(status.items()))[1][0]['SystemStatus']['Status']
        else:
            status = self.DEFAULT_STATUS
        return status

    def get_instance_public_ip(self, instance_id):
        """
        Get instance public IP
        :param instance_id: Instance Id
        :return: Instance public IP
        """
        instance = self.get_instance_description(instance_id)
        if self.get_instance_status(instance_id) == 'ok':
            return next(iter(instance.items()))[1][0]['Instances'][0]['PublicIpAddress']
        else:
            aw.exit_with_error('Instance Not Running')

    def get_instance_public_dns(self, instance_id):
        """
        Get instance public DNS
        :param instance_id: Instance Id
        :return: Instance public DNS
        """
        instance = self.get_instance_description(instance_id)
        if self.get_instance_status(instance_id) == 'ok':
            return next(iter(instance.items()))[1][0]['Instances'][0]['PublicDnsName']
        else:
            aw.exit_with_error('Instance Not Running')

    def get_instance_description(self, instance_id):
        """
        Get instance description
        :param instance_id: Instance Id
        :return: Instance description
        """
        return self.ec2.describe_instances(InstanceIds=[instance_id])

    def instance_exists(self, instance_id):
        """
        Check if instance exists
        :param instance_id: Instance Id
        :return: True if the instance exists, else return False
        """
        try:
            self.ec2.describe_instances(InstanceIds=[instance_id])
        except ClientError:
            return False
        return True

    def get_image_id(self, instance_id):
        """
        Get image id from running instance
        :param instance_id: Instance Id
        :return: Image Id
        """
        instance = self.get_instance_description(instance_id)
        return next(iter(instance.items()))[1][0]['Instances'][0]['ImageId']

    def get_image_description(self, image_id):
        """
        Get image description, from existing image
        :param image_id: Image Id
        :return: Image description
        """
        image = self.ec2.describe_images(ImageIds=[image_id])
        return image

    def get_image_distribution(self, instance_id):
        """
        Get Image distribution from existing image
        :param instance_id: Instance Id
        :return: Image distribution (Amazon, Ubuntu, etc)
        """
        image_id = self.get_image_id(instance_id)
        image = self.get_image_description(image_id)
        return next(iter(image.items()))[1][0]['Description']

    def get_image_user(self, instance_id):
        """
        Get image user, from instance
        :param instance_id: Instance Id
        :return: Image user to use (ec2-user, ubuntu, etc)
        """
        image_distribution = self.get_image_distribution(instance_id)
        if 'Ubuntu' in image_distribution or 'Canonical' in image_distribution:
            return 'ubuntu'
        else:
            return 'ec2-user'

    def check_security_group_exists(self):
        """
        Check if default security group exists
        :return: Security Group if security group exist, else return None
        """
        security_groups = self.get_security_groups_by_name()
        for security_group in security_groups:
            if security_group[1] == DEFAULT_SECURITY_GROUP_NAME:
                return security_group[0]
        return None

    def get_security_group_id(self, security_group_name):
        security_groups = self.get_security_groups_by_name()
        for security_group in security_groups:
            if security_group[1] == security_group_name:
                return security_group[0]
        return None

    def add_inbound_rule(self, security_group_name, port, description='Default'):
        ip_permission = self.DEFAULT_IP_PERMISSIONS
        ip_permission['IpRanges'][0]['CidrIp'] = aw.get_public_ip()
        ip_permission['FromPort'] = port
        ip_permission['ToPort'] = port
        ip_permission['IpRanges'][0]['Description'] = description
        security_group_id = self.get_security_group_id(security_group_name)
        try:
            security_group = self.ec2.SecurityGroup(security_group_id)
            security_group.authorize_ingress(GroupId=security_group_id, IpPermissions=[ip_permission])
        except ClientError:
            pass


class Ec2Process(Ec2Helper):
    DEFAULT_SLEEP = 10
    DEFAULT_TIMEOUT = 600

    def __init__(self, instance_id, **kwargs):
        self.kwargs = kwargs
        self.instance_id = instance_id
        self.key_pair_name = kwargs['key_pair']
        self.deploy = self.get_deploy_value()
        self.key_path = self.get_key_path()
        super().__init__(**kwargs)

    def get_key_pair(self):
        """
        Get key pair from properties
        :return: Key pair from properties file
        """
        return self.kwargs['key_pair'] if 'key_pair' in self.kwargs else aw.exit_with_error('Key Pair was not defined')

    def get_deploy_value(self):
        """
        Get deploy value from properties file
        :return: Deploy value from properties file
        """
        return self.kwargs['deploy'] if 'deploy' in self.kwargs else None

    def get_key_path(self):
        """
        Get the key pair path location
        :return: Key pair path pointing to the key pair location
        """
        return self.kwargs['key_path'] if 'key_path' in self.kwargs else aw.get_cwd()

    def wait_for_instance(self):
        """
        Wait for the instance to be running
        :return: Instance state
        """
        log.echo_info('Wait %s seconds for EC2 instance (%s) to be ready' % (self.instance_id, self.DEFAULT_TIMEOUT))
        running = False
        timeout = time.time() + self.DEFAULT_TIMEOUT
        while not running:
            status = self.get_instance_status(self.instance_id)
            if status == 'ok':
                running = True
                break
            if time.time() > timeout:
                break
            time.sleep(self.DEFAULT_SLEEP)
        return running

    def copy_to_instance(self):
        """
        Copy files to the instance. Only Tomcat supported
        """
        log.echo_info('Copy file to EC2 Instance')
        ssh_client = self.get_instance_connection()
        ftp_client = ssh_client.open_sftp()
        ftp_client.put(self.deploy, aw.path_join(aw.get_tomcat_path(), aw.basename(self.deploy)))
        log.echo_info('File Copied successfully')
        ftp_client.close()
        ssh_client.close()

    def get_instance_connection(self):
        """
        Get ssh connection to the instance
        :return: SSHClient object instance
        """
        log.echo_info('Get SSH connection info')
        log.echo_info('Using key file (%s) located on %s' % (self.key_pair_name + '.pem', self.key_path))
        p_key = ssh.RSAKey.from_private_key_file(aw.path_join(self.key_path, self.key_pair_name + '.pem'))
        ssh_client = ssh.SSHClient()
        ssh_client.set_missing_host_key_policy(ssh.AutoAddPolicy())
        self.wait_ssh_connection(p_key, ssh_client)
        return ssh_client

    def wait_ssh_connection(self, p_key, ssh_client):
        """
        Wait to ssh connection to be established
        :param p_key: Private Key pair
        :param ssh_client: SSH connection instance
        :return:
        """
        log.echo_info('Wait %s seconds for SSH connection to be established' % self.DEFAULT_TIMEOUT)
        running = False
        timeout = time.time() + self.DEFAULT_TIMEOUT
        instance_user = self.get_image_user(self.instance_id)
        log.echo_info("Using User: %s to connect to instance" % instance_user)
        while not running:
            try:
                ssh_client.connect(hostname=self.get_instance_public_ip(self.instance_id), username=instance_user,
                                   pkey=p_key)
            except (NoValidConnectionsError or NewConnectionError or TimeoutError or socket.timeout):
                continue
            if ssh_client.get_transport().is_active():
                time.sleep(10)
                return ssh_client
            if time.time() > timeout:
                aw.exit_with_error("Timeout Can't connect to instance")
            time.sleep(self.DEFAULT_SLEEP)
        aw.exit_with_error("Can't connect to instance")
