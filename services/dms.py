import boto3
from awrapperlib import aw, logger as log, resource


class DMSFactory:
    DEFAULT_NAME = 'dms-AWS-Wrapper'
    DEFAULT_INSTANCE_CLASS = 'dms.t2.medium'
    DEFAULT_ALLOCATION_STORAGE = 50
    DEFAULT_ENGINE_VERSION = '3.1.3'
    DEFAULT_PUBLIC = True
    DEFAULT_MULTIAZ = False
    DEFAULT_SUBNET_GROUP_NAME = 'replication-subnet-group-AWS-Wrapper'
    DEFAULT_MIGRATION_TYPE = 'full-load'
    DEFAULT_MARIADB_CON_ARGS = 'targetDbType=SPECIFIC_DATABASE;initstmt=SET FOREIGN_KEY_CHECKS=0;parallelLoadThreads=1'
    DEFAULT_ORACLE_CON_ARGS = 'addSupplementalLogging=Y;useLogminerReader=N'
    DEFAULT_REPLICATION_TASK = 'replication-task-aws-wrapper'

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.name = self.get_name()
        self.region = self.get_region()
        self.instance_class = self.get_instance_class()
        self.allocation_storage = self.get_allocation_storage()
        self.engine = self.get_engine()
        self.public = self.get_public()
        self.vpc_security_groups = self.get_vpc_security_groups()
        self.multi_az = self.get_multi_az()
        self.subnet_group_name = self.get_subnet_group_name()
        self.subnet = self.get_subnet()
        self.migration_type = self.get_migration_type()
        self.dms_client = boto3.client('dms', region_name=self.region)

    def get_region(self):
        return self.kwargs['region'] if 'region' in self.kwargs else aw.DEFAULT_REGION

    def get_name(self):
        return self.kwargs['name'] if 'name' in self.kwargs else self.DEFAULT_NAME

    def get_instance_class(self):
        return self.kwargs['instance_class'] if 'instance_class' in self.kwargs else self.DEFAULT_INSTANCE_CLASS

    def get_allocation_storage(self):
        return self.kwargs[
            'allocation_storage'] if 'allocation_storage' in self.kwargs else self.DEFAULT_ALLOCATION_STORAGE

    def get_engine(self):
        return self.kwargs['engine'] if 'engine' in self.kwargs else self.DEFAULT_ENGINE_VERSION

    def get_public(self):
        return self.kwargs['public'] if 'public' in self.kwargs else self.DEFAULT_PUBLIC

    def get_multi_az(self):
        return self.kwargs['multi_az'] if 'multi_az' in self.kwargs else self.DEFAULT_MULTIAZ

    def get_vpc_security_groups(self):
        return self.kwargs['vpc_security_groups'] if 'vpc_security_groups' in self.kwargs else aw.exit_with_error(
            'VPC Security Group must be specified')

    def get_subnet(self):
        return self.kwargs['subnet'] if 'subnet' in self.kwargs else aw.exit_with_error(
            'Subnets must be specified')

    def get_subnet_group_name(self):
        return self.kwargs[
            'subnet_group_name'] if 'subnet_group_name' in self.kwargs else self.DEFAULT_SUBNET_GROUP_NAME

    def get_migration_type(self):
        return self.kwargs['migration_type'] if 'migration_type' in self.kwargs else self.DEFAULT_MIGRATION_TYPE


class DMSCreation(DMSFactory):
    # TODO get existing DMS bits if exists and re-use them
    # TODO make the script smarter to figure out engines source an target
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__create_subnet_group()

    def create_dms_instance(self):
        response = self.dms_client.create_replication_instance(ReplicationInstanceIdentifier=self.name,
                                                               AllocatedStorage=self.allocation_storage,
                                                               ReplicationInstanceClass=self.instance_class,
                                                               VpcSecurityGroupIds=[self.vpc_security_groups],
                                                               ReplicationSubnetGroupIdentifier=self.subnet_group_name,
                                                               MultiAZ=self.multi_az,
                                                               EngineVersion=self.engine,
                                                               PubliclyAccessible=self.public)
        self.__set_dms_instance(response)

    def __set_dms_instance(self, dms_instance):
        setattr(self, 'dms_instance', dms_instance)

    def __get_dms_arn(self):
        return getattr(self, 'dms_instance')['ReplicationInstance']['ReplicationInstanceArn']

    def __create_subnet_group(self):
        log.echo_info('Creating Replication Subnet Groups')
        response = self.dms_client.create_replication_subnet_group(
            ReplicationSubnetGroupIdentifier=self.subnet_group_name, ReplicationSubnetGroupDescription='default',
            SubnetIds=self.subnet)
        self.subnet_group_name = response['ReplicationSubnetGroup']['ReplicationSubnetGroupIdentifier']

    def create_source_endpoint(self):
        response = self.dms_client.create_endpoint(EndpointIdentifier='oracle-source-AWS-Wrapper',
                                                   EndpointType='source', EngineName='oracle',
                                                   Username=self.kwargs['s_user'], Password=self.kwargs['s_password'],
                                                   ServerName=self.kwargs['source'], Port=int(self.kwargs['s_port']),
                                                   DatabaseName=self.kwargs['service_name'],
                                                   ExtraConnectionAttributes=self.DEFAULT_ORACLE_CON_ARGS)
        self.__set_source_endpoint_arn(response['Endpoint']['EndpointArn'])

    def __set_source_endpoint_arn(self, arn):
        setattr(self, 'source_arn', arn)

    def __get_source_endpoint_arn(self):
        return getattr(self, 'source_arn')

    def create_target_endpoint(self):
        response = self.dms_client.create_endpoint(EndpointIdentifier='mariadb-target-AWS-Wrapper',
                                                   EndpointType='target', EngineName='mariadb',
                                                   Username=self.kwargs['t_user'],
                                                   Password=self.kwargs['t_password'], ServerName=self.kwargs['target'],
                                                   Port=int(self.kwargs['t_port']), DatabaseName=self.kwargs['db_name'],
                                                   ExtraConnectionAttributes=self.DEFAULT_MARIADB_CON_ARGS)

        self.__set_target_endpoint_arn(response['Endpoint']['EndpointArn'])

    def __set_target_endpoint_arn(self, arn):
        setattr(self, 'target_arn', arn)

    def __get_target_endpoint_arn(self):
        return getattr(self, 'target_arn')

    def create_replication_task(self):
        json_file = resource.get_resource('DMS/table_mappings.json')
        table_mappings = aw.file_to_string(json_file)
        table_mappings = table_mappings.replace('__SCHEMA__', self.kwargs['db_name'])
        json_file = resource.get_resource('DMS/task_settings.json')
        task_settings = aw.file_to_string(json_file)
        response = self.dms_client.create_replication_task(ReplicationTaskIdentifier=self.DEFAULT_REPLICATION_TASK,
                                                           SourceEndpointArn=self.__get_source_endpoint_arn(),
                                                           TargetEndpointArn=self.__get_target_endpoint_arn(),
                                                           ReplicationInstanceArn=self.__get_dms_arn(),
                                                           MigrationType=self.migration_type,
                                                           TableMappings=table_mappings,
                                                           ReplicationTaskSettings=task_settings)
        self.__set_replication_task_arn(response['ReplicationTask']['ReplicationTaskArn'])

    def __set_replication_task_arn(self, arn):
            setattr(self, 'replication_task_arn', arn)

    def __get_replication_task_arn(self):
            return getattr(self, 'replication_task_arn')

    def wait_replication_instance(self):
        waiter = self.dms_client.get_waiter('replication_instance_available')
        waiter.wait(Filters=[{'Name': 'replication-instance-arn', 'Values': [self.__get_dms_arn()]}])

    def start_replication_task(self):
        response = self.dms_client.start_replication_task(ReplicationTaskArn=self.__get_replication_task_arn(),
                                                          StartReplicationTaskType='start-replication')
        self.__set_start_replication_task_arn(response['ReplicationTask']['ReplicationInstanceArn'])

    def __set_start_replication_task_arn(self, arn):
            setattr(self, 'replication_instance_arn', arn)

    def __get_start_replication_task_arn(self):
            return getattr(self, 'replication_instance_arn')

    def wait_replication_task_starts(self):
        waiter = self.dms_client.get_waiter('replication_task_running')
        waiter.wait(Filters=[{'Name': 'replication-task-arn', 'Values': [self.__get_replication_task_arn()]}])

    def wait_replication_task_ready(self):
        waiter = self.dms_client.get_waiter('replication_task_ready')
        waiter.wait(Filters=[{'Name': 'replication-task-arn', 'Values': [self.__get_replication_task_arn()]}])

    def wait_test_connection(self):
        waiter = self.dms_client.get_waiter('test_connection_succeeds')
        waiter.wait(Filters=[{'Name': 'replication-instance-arn', 'Values': [self.__get_dms_arn()]}])
