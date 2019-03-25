import os
from subprocess import CalledProcessError
from awrapperlib import aw, logger as log, resource
from services import vpc as vpc_service, dms as dms_service


class Migration:
    DEFAULT_SOURCE_TYPE = 'oracle'
    DEFAULT_TARGET_TYPE = 'mariadb'
    DEFAULT_DATA = 'no'
    DEFAULT_LOG = 'sqldata.log'

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.db_name = self.get_db_name()
        self.source = self.get_source()
        self.s_port = self.get_port()
        self.service_name = self.get_service_name()
        self.s_user = self.get_user()
        self.s_password = self.get_password()
        self.target = self.get_target()
        self.t_user = self.get_user('t')
        self.t_password = self.get_password('t')
        self.t_port = self.get_port('t')
        self.data = self.get_data()

    def get_db_name(self):
        return self.kwargs['db_name'] if 'db_name' in self.kwargs else aw.exit_with_error('DB Name must be specified')

    def get_source(self):
        return self.kwargs['source'] if 'source' in self.kwargs else aw.exit_with_error('Source must be specified')

    def get_port(self, _type='s'):
        if 's' == _type:
            return self.kwargs['s_port'] if 's_port' in self.kwargs else None
        else:
            return self.kwargs['t_port'] if 't_port' in self.kwargs else None

    def get_service_name(self):
        return self.kwargs['service_name'] if 'service_name' in self.kwargs else aw.exit_with_error(
            'Service Name must be specified')

    def get_user(self, _type='s'):
        if 's' == _type:
            return self.kwargs['s_user'] if 's_user' in self.kwargs else aw.exit_with_error(
                'Source User must be specified')
        else:
            return self.kwargs['t_user'] if 't_user' in self.kwargs else aw.exit_with_error(
                'Target User must be specified')

    def get_password(self, _type='s'):
        if 's' == _type:
            return self.kwargs['s_password'] if 's_password' in self.kwargs else aw.exit_with_error(
                'Source Password must be specified')
        else:
            return self.kwargs['t_password'] if 't_password' in self.kwargs else aw.exit_with_error(
                'Target Password must be specified')

    def get_target(self):
        return self.kwargs['target'] if 'target' in self.kwargs else aw.exit_with_error(
            'Target must be specified')

    def get_data(self):
        return self.kwargs['data'] if 'data' in self.kwargs else self.DEFAULT_DATA

    def __construct_oracle_maria_command(self):
        sql_data = aw.find_a_file(os.environ['HOME'], 'sqldata')
        if sql_data is None:
            aw.exit_with_error('Migration can proceed, one package missing need to download and install sqldata')
        data = '-data=' + self.data
        t = '-t=*'
        sd = '-sd=' + self.DEFAULT_SOURCE_TYPE + ','
        if self.s_port:
            port = ':' + self.s_port
            source = self.s_user + '/' + self.s_password + '@' + self.source + port + '/' + self.service_name
        else:
            source = self.s_user + '/' + self.s_password + '@' + self.source + '/' + self.service_name
        sd = sd + source
        td = '-td=' + self.DEFAULT_TARGET_TYPE + ','
        if self.t_port:
            port = ':' + self.t_port
            target = self.t_user + '/' + self.t_password + '@' + self.target + port + ',' + self.db_name
        else:
            target = self.t_user + '/' + self.t_password + '@' + self.target + ',' + self.db_name
        td = td + target
        return [sql_data, data, t, sd, td]

    def run_migration(self):
        cmd = self.__construct_oracle_maria_command()
        log.echo_info('Running command %s' % cmd)
        try:
            aw.check_call(cmd, stdout=aw.dev_null(), close_fds=True)
        except CalledProcessError as error:
            aw.exit_with_error('Error: [%s]' % error)

    def parse_execution_summary(self):
        aw.set_resource_env_cwd()
        sqldata_log = resource.get_resource(self.DEFAULT_LOG)
        log.echo_info('Schema Convertion Results:')
        tables = aw.grep(sqldata_log, 'Tables:')[0].rstrip().replace(' ', '', 5)
        log.echo_info(tables)
        ddl = aw.grep(sqldata_log, 'Target DDL:')[0].rstrip().replace(' ', '', 5)
        log.echo_info(ddl)
        table_errors = int(tables.split(',')[1].replace(' ', '').replace('failed)', ''))
        ddl_errors = int(ddl.split(',')[1].replace(' ', '').replace('failed)', ''))
        if table_errors > 0:
            log.echo_warning('Found [%s] errors Converting Tables check logs for more information' % table_errors)
        if ddl_errors > 0:
            log.echo_warning(
                'Found [%s] errors Converting the Structure of the tables, check logs for more information' %
                ddl_errors)
        if table_errors > 0 or ddl_errors > 0:
            log.echo_warning('Will require manual intervention to solve this errors')
            log.echo_info('Continuing with data migration since this are minor failures')
        aw.clear_resource_env()

    def run_dms_process(self):
        log.echo_info('Beginning Data Migration')
        self.kwargs['subnet_number'] = 2
        log.echo_info('Creating VPC for Data Migration Service')
        vpc = vpc_service.VPCCreation(**self.kwargs)
        vpc.create_vpc()
        log.echo_info('Creating VPC Subnet')
        vpc.create_subnet()
        log.echo_info('Creating Internet Gateway')
        vpc.create_internet_gateway()
        log.echo_info('Attaching Internet Gateway to VPC')
        vpc.attach_igw()
        log.echo_info('Creating Route Table')
        vpc.create_route_table()
        log.echo_info('Associating Subnet to Route Table')
        vpc.associate_route_table()
        log.echo_info('Creating Route to Internet Gateway')
        vpc.create_igw_route()
        self.kwargs['vpc_security_groups'] = vpc.get_vpc_default_security_group()
        self.kwargs['subnet'] = vpc.get_subnet_id()
        dms = dms_service.DMSCreation(**self.kwargs)
        log.echo_info('Creating Data Migration Instance')
        dms.create_dms_instance()
        log.echo_info('Creating Source Endpoint')
        dms.create_source_endpoint()
        log.echo_info('Creating Target Endpoint')
        dms.create_target_endpoint()
        log.echo_info('Wait for Data Migration Instance to be Ready')
        dms.wait_replication_instance()
        log.echo_info('Creating Replication Task')
        dms.create_replication_task()
        log.echo_info('Wait for Replication Task to be Ready')
        dms.wait_replication_task_ready()
        log.echo_info('Wait for Endpoints test connection')
        dms.wait_test_connection()
        log.echo_info('Starting Data Migration')
        dms.start_replication_task()
        log.echo_info('Wait for Data Migration to start')
        dms.wait_replication_task_starts()
