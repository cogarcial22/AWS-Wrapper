import sys
from services import ec2 as ec2_service
from services import rds as rds_service
from services import migration
from services import vpc as vpc_service
from services import dms as dms_service
from helper import help
from awrapperlib import aw, validator, logger as log, properties as props


def main(argv):
    """
    Main
    1- Get properties
    2- Validate the properties
    3- Run the valid option
    :param argv: Sys argument, valid options list, ec2
    """
    log.echo_info('Validating parameters')
    aw_props = props.get_default_props()
    values = aw_props.get_all_values()
    log.echo_info('Working with current values: %s' % values)
    argv.pop(0)
    # validator.validate_options(argv, **values)
    switch = Switcher(argv, **values)
    switch.switcher()


class Switcher:
    """
    Switcher class will get the method name and execute it according to the option
    """
    def __init__(self, argv, **kwargs):
        self.argv = argv
        self.kwargs = kwargs

    def switcher(self):
        """
        Get the method name and execute it
        :return: The method to execute
        """
        method_name = self.argv[0]
        method = getattr(self, method_name, lambda: log.echo_error('Invalid option %s' % method_name))
        return method()

    def list(self):
        """
        List options, output the available options for types, key_pairs, security_groups and regions
        """
        ec2_helper = ec2_service.Ec2Helper(**self.kwargs)
        if self.argv[1] == 'types':
            help.get_instance_type()
        elif self.argv[1] == 'key_pairs':
            ec2_helper.print_key_pairs()
        elif self.argv[1] == 'security_groups':
            ec2_helper.print_security_groups()
        elif self.argv[1] == 'regions':
            help.get_regions()

    def ec2(self):
        """
        EC2 instance creation method
        """
        log.echo_info('Creating EC2 Instance')
        ec2_helper = ec2_service.Ec2Helper(**self.kwargs)
        if 'security_group' not in self.kwargs:
            security_group_id = ec2_helper.check_security_group_exists()
            if security_group_id:
                self.kwargs['security_group'] = security_group_id
        ec2 = ec2_service.Ec2Creation(**self.kwargs)
        self.kwargs.update(ec2.get_valid_properties())
        ec2_instance = ec2.create_instance()
        if 'deploy' in self.kwargs:
            instance_id = ec2_instance[0].id
            ec2_process = ec2_service.Ec2Process(instance_id, **self.kwargs)
            if ec2_process.wait_for_instance():
                ec2_process.copy_to_instance()
                log.echo_info(ec2_process.get_instance_public_dns(ec2_process.instance_id))

    def migration(self):
        """
        Migration method
        """
        log.echo_info('Running RDS Migration')
        if 'target' not in self.kwargs:
            log.echo_info('Creating RDS Instance')
            rds = rds_service.RDS(**self.kwargs)
            rds_instance = rds.create_instance()
            log.echo_info('RDS instance created: %s' % rds_instance[0].id)
            ec2_helper = ec2_service.Ec2Helper(**self.kwargs)
            log.echo_info('Add inbound rule to security group')
            ec2_helper.add_inbound_rule(rds.security_group, 3306)
            rds_helper = rds_service.RDSHelper(**self.kwargs)
            if rds_helper.wait_for_instance(rds_instance):
                endpoint = rds_helper.get_db_endpoint('mariadb-migration')
                self.kwargs['target'] = endpoint
        else:
            try:
                log.echo_info(
                    'Migrating from Source: %s to Target: %s' % (self.kwargs['source'], self.kwargs['target']))
            except KeyError as key:
                aw.exit_with_error('Missing property: %s' % key)
        log.echo_info('Starting Schema Convertion')
        data = migration.Migration(**self.kwargs)
        data.run_migration()
        data.parse_execution_summary()
        log.echo_info('Finish Schema Convertion')
        log.echo_info('See log for more information')
        data.run_dms_process()
        log.echo_info('Data Migration Running Check AWS for more information')


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=log.LOG_DEFAULT_LEVEL, format=log.LOG_DEFAULT_FORMAT, datefmt=log.LOG_DEFAULT_DATE_FORMAT)
    log.echo_info("=== AWS WRAPPER ===")
    if len(sys.argv) - 1 == 0:
        help.get_help()
        exit(1)
    elif len(sys.argv) == 1:
        main(sys.argv[1])
    else:
        main(sys.argv[0:])
    exit(0)
