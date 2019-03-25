import csv
from awrapperlib import aw, resource, logger as log
from services import ec2 as ec2_service

VALID_OPTIONS = ['ec2', 'list']
VALID_LIST_OPTIONS = ['types', 'key_pairs', 'security_groups', 'regions']
VALID_EC2_OPTIONS = ['name', 'type', 'region', 'user_data', 'security_group', 'key_pair', 'key_path', 'deploy']
VALID_INIT_SCRIPT = ['tomcat']


def validate_options(arg, **kwargs):
    """
    Check if option is valid
    :param arg: Option to check if valid, see valid options in $VALID_OPTIONS
    :param kwargs: Dictionary containing the properties file options
    :return: True if validation was successful else return False
    """
    _valid = False
    if arg[0] in VALID_OPTIONS:
        if 'ec2' == arg[0]:
            _valid = validate_ec2(**kwargs)
        elif 'list' == arg[0]:
            _valid = validate_list(arg, dict(region=kwargs['region']))
    if _valid:
        return
    else:
        aw.exit_with_error('Invalid Parameter %s' % arg[0])


def validate_list(arg, args):
    """
    Check list options are valid, see valid options in $VALID_LIST_OPTIONS
    :param arg: List option to validate
    :param args: Keyword arguments to validate (Region)
    :return: True if validation was successful else return False
    """
    _valid = True
    if arg[1] not in VALID_LIST_OPTIONS:
        _valid = False
        log.echo_error("'%s' is not a valid option" % arg[1])
    if len(args) > 1:
        log.echo_error('Too many arguments: %s' % len(args))
        _valid = False
    elif len(args) == 1:
        for key in args:
            if key == 'region':
                if not valid_instance_region(args['region']):
                    _valid = False
                    log.echo_error("Invalid Region '" + args['region'] + "' , run 'list regions' to see valid options")
            else:
                _valid = False
    return _valid


def validate_ec2(args):
    """
    Check ec2 options are valid, see valid options in $VALID_EC2_OPTIONS
    :param args: Dictionary containing the properties file options
    :return: True if validation was successful else return False
    """
    _valid = True
    ec2 = ec2_service.Ec2Helper()
    for key in args:
        if key not in VALID_EC2_OPTIONS:
            log.echo_error('Invalid Parameter ' + key)
            _valid = False
            break
        if key == 'user_data':
            if args[key] not in VALID_INIT_SCRIPT:
                _valid = False
                log.echo_error('Invalid user data parameter valid parameters are: ' + str(VALID_INIT_SCRIPT))
        if key == 'type':
            if not valid_instance_type(args[key]):
                _valid = False
                log.echo_error("Invalid Type '" + args[key] + "' , run 'list types' to see valid options")
        if key == 'region':
            if not valid_instance_region(args[key]):
                _valid = False
                log.echo_error("Invalid Region '" + args[key] + "' , run 'list regions' to see valid options")
        if key == 'security_group':
            if args[key] not in ec2.get_security_groups(''):
                _valid = False
                log.echo_error(
                    "Invalid Security Group '" + args[key] + "' , run 'list security_groups' to see valid options")
        if key == 'key_pair':
            if args[key] not in ec2.get_key_pairs():
                _valid = False
                log.echo_error("Invalid Key Pair '" + args[key] + "' , run 'list key_pairs' to see valid options")
            try:
                if not aw.check_file_exists(aw.path_join(args['key_path'], args[key]) + '.pem'):
                    _valid = False
                    log.echo_error("Key file doesn't exist '" + aw.path_join(args['key_path'], args[
                        key]) + '.pem' + "' , check the file exist or the path is correct")
            except KeyError:
                if not aw.check_file_exists(aw.path_join(aw.get_cwd(), args[key]) + '.pem'):
                    _valid = False
                    log.echo_error("Key file doesn't exist '" + aw.path_join(aw.get_cwd(), args[
                        key]) + '.pem' + "' , check the file exist or use 'key_path=' to specify the path")
        if key == 'deploy':
            if not aw.check_file_exists(args[key]):
                _valid = False
                log.echo_error(
                    "File to deploy doesn't exist '" + args[key] + "' , check the file exist or the path is correct")
    return _valid


def valid_instance_type(name):
    """
    Check instance type csv file to verify if option is valid
    :param name: Type name to check if valid
    :return: True if validation was successful else return False
    """
    _valid = False
    file_name = resource.get_resource('Extra/Amazon EC2 Instance Comparison.csv')
    with open(file_name, mode='r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                line_count += 1
            if name == row['API Name']:
                _valid = True
                break
            line_count += 1
    return _valid


def valid_instance_region(name):
    """
    Check instance regions csv file to verify if the option is valid
    :param name: Region name to check if valid
    :return: True if validation was successful else return False
    """
    _valid = False
    file_name = resource.get_resource('Extra/regions.csv')
    with open(file_name, mode='r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                line_count += 1
            if name == row['Name']:
                _valid = True
                break
            line_count += 1
    return _valid
