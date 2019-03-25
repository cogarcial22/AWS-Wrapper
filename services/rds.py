import boto3
import time
from awrapperlib import aw, logger as log

DEFAULT_SECURITY_GROUP_NAME = 'rds-AWS-Wrapper'
DEFAULT_REGION = aw.DEFAULT_REGION


class RDSFactory:
    """
    RDS Factory generate an object that contain RDS valid options
    """
    DEFAULT_LICENSE_MODEL = 'general-public-license'
    DEFAULT_IOPS = 1000
    DEFAULT_PUBLIC_ACCESS = True
    DEFAULT_SECURITY_GROUP = 'rds-launch-wizard-2'
    DEFAULT_STORAGE_TYPE = 'io1'
    DEFAULT_INSTANCE_CLASS = 'db.r4.xlarge'

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.name = self.get_name()
        self.db_name = self.get_db_name()
        self.region = self.get_region()
        self.rds = boto3.client('rds', region_name=self.region)
        self.instance_class = self.get_instance_class()
        self.engine = self.get_engine()
        self.alloc_storage = self.get_alloc_storage()
        self.multi_az = self.get_multi_az()
        self.version = self.get_version()
        self.source = self.get_source()
        self.user = self.get_user()
        self.password = self.get_password()
        self.license_model = self.get_license_model()
        self.iops = self.get_iops()
        self.public_access = self.get_public_access()
        self.security_group = self.get_security_group()
        self.storage_type = self.get_storage_type()
        self.port = self.get_port()

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

    def get_instance_class(self):
        """
        Get instance class to be deployed
        :return: Type name
        """
        return self.kwargs['instance_class'] if 'instance_class' in self.kwargs else self.DEFAULT_INSTANCE_CLASS

    def get_db_name(self):
        """
        Get database name
        :return: Database name
        """
        return self.kwargs['db_name'] if 'db_name' in self.kwargs else aw.exit_with_error(
            'Database name must be specified')

    def get_engine(self):
        """
        Get database engine
        :return: Database engine
        """
        return self.kwargs['engine'] if 'engine' in self.kwargs else aw.exit_with_error("Engine must be specified")

    def get_alloc_storage(self):
        """
        Get Allocated Storage
        :return: Allocated Storage
        """
        return self.kwargs['alloc_storage'] if 'alloc_storage' in self.kwargs else aw.exit_with_error(
            "Allocated storage must be specified")

    def get_multi_az(self):
        """
        Get multi availability zone property
        :return: Multi availability zone
        """
        return self.kwargs['multi_az'] if 'multi_az' in self.kwargs else aw.exit_with_error("MultiAZ must be specified")

    def get_version(self):
        """
        Get database engine version property
        :return: Database engine version
        """
        return self.kwargs['version'] if 'version' in self.kwargs else aw.exit_with_error("Version must be specified")

    def get_source(self):
        """
        Get database source
        :return: Database source
        """
        return self.kwargs['source'] if 'source' in self.kwargs else aw.exit_with_error("Source must be specified")

    def get_user(self):
        return self.kwargs['s_user'] if 's_user' in self.kwargs else aw.exit_with_error("User must be specified")

    def get_password(self):
        return self.kwargs['s_password'] if 's_password' in self.kwargs else aw.exit_with_error(
            "Password must be specified")

    def get_license_model(self):
        return self.kwargs['license_model'] if 'license_model' in self.kwargs else self.DEFAULT_LICENSE_MODEL

    def get_iops(self):
        return self.kwargs['iops'] if 'iops' in self.kwargs else self.DEFAULT_IOPS

    def get_public_access(self):
        return self.kwargs['public_access'] if 'public_access' in self.kwargs else self.DEFAULT_PUBLIC_ACCESS

    def get_security_group(self):
        return self.kwargs['security_group'] if 'security_group' in self.kwargs else self.DEFAULT_SECURITY_GROUP

    def get_storage_type(self):
        return self.kwargs['storage_type'] if 'storage_type' in self.kwargs else self.DEFAULT_STORAGE_TYPE

    def get_port(self):
        return self.kwargs['s_port'] if 's_port' in self.kwargs else aw.exit_with_error("Port must be specified")


class RDS(RDSFactory):
    """
    RDS creation class, create instance
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def create_instance(self):
        """
        Create rds instance method
        :return: Instance Id
        """
        instance_options = dict(DBName=self.db_name, DBInstanceIdentifier=self.name,
                                AllocatedStorage=self.alloc_storage, DBInstanceClass=self.instance_class,
                                Engine=self.engine, MasterUsername=self.user, MasterUserPassword=self.password,
                                DBSecurityGroups=[self.security_group], Port=self.port, MultiAZ=self.multi_az,
                                EngineVersion=self.version, LicenseModel=self.version, Iops=self.iops,
                                PubliclyAccessible=self.public_access)
        instance = self.rds.create_db_instance(**instance_options)
        return instance


class RDSHelper:
    DEFAULT_SLEEP = 10
    DEFAULT_TIMEOUT = 600

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.region = self.get_region()
        self.rds = boto3.client('rds', region_name=self.region)
        self.response = []

    def get_region(self):
        """
        Get current region to work on
        :return: Region name
        """
        return self.kwargs['region'] if 'region' in self.kwargs else DEFAULT_REGION

    def get_instance_status(self, instance_id):
        response = self.rds.describe_db_instances(Filters=[dict(Name='db-instance-id', Values=[instance_id])])
        return next(iter(response.items()))[1][0]['DBInstanceStatus']

    def get_db_endpoint(self, instance_id):
        response = self.rds.describe_db_instances(Filters=[dict(Name='db-instance-id', Values=[instance_id])])
        return next(iter(response.items()))[1][0]['Endpoint']['Address']

    def wait_for_instance(self, instance_id):
        log.echo_info('Wait %s seconds for RDS instance (%s) to be ready' % (instance_id, self.DEFAULT_TIMEOUT))
        running = False
        timeout = time.time() + self.DEFAULT_TIMEOUT
        while not running:
            status = self.get_instance_status(instance_id)
            if status == 'available':
                running = True
                break
            if time.time() > timeout:
                break
            time.sleep(self.DEFAULT_SLEEP)
        return running
