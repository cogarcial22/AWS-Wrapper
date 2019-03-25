"""
Implement common behaviors and often-used procedures.

- Console output and logging TBD
- OS-dependent procedures that are worth sharing among scripts
- Load properties file TBD
"""

import os
import tempfile
import shutil
import re
import subprocess
import io
from urllib.request import urlopen
from awrapperlib import logger as log, resource

DEFAULT_TOMCAT_PATH = '/opt/tomcat/latest/webapps'
DEFAULT_SECURITY_GROUP_NAME = 'AWS-Wrapper'
DEFAULT_REGION = 'us-east-2'

#############
# OS Utilities
#############


def is_windows():
    """
    Check if os is windows
    :return: True when Windows, else False
    """
    return os.name == 'nt'


def is_linux():
    """
    Check if os is Linux
    :return: True when Linux, else False
    """
    return not is_windows()


def os_switch(lin='linux', win='windows'):
    """
    Get the string representing th os
    :param lin: Linux string (optional)
    :param win: Windows string (optional)
    :return: String representing the OS
    """
    if is_windows():
        return win
    elif is_linux():
        return lin
    else:
        assert False, 'Unsupported operating system. Neither Linux nor Windows.'

#############
# Utilities
#############


def escape_path(full_path):
    """
    Converts a Python path to an escaped path
    :param full_path: Full path string
    :return: Escaped path
    """
    if is_windows():
        full_path = full_path.replace("\\", "\\\\")
    return full_path


def file_to_string(file_name):
    """
    Converts the file output to string
    :param file_name: The file name to read
    :return: String with the entire file
    """
    with open(file_name, 'r') as _file:
        data = _file.read()
    return data


def check_file_exists(path):
    """
    Check if file exists
    :param path: Full path of the file
    :return: True if file exists, else return False
    """
    assert path, 'path must not be empty'
    if os.path.isfile(path):
        return True
    else:
        return False


def get_cwd():
    """
    Get current working directory
    :return: Current working directory
    """
    return os.getcwd()


def path_join(fragment, *path):
    """
    Appends fragment to path to make a complete path
    :param fragment: First argument of the path
    :param path: One or more fragments to join to the path
    :return: The full path, normalized to specific OS
    """
    result = os.path.join(fragment, *path)
    return os.path.normpath(result)


def basename(path):
    """
    Get path base name
    :param path: Full path
    :return: Base name
    """
    return os.path.basename(path)


def get_tomcat_path():
    """
    Get Tomcat working directory
    :return: The path to Tomcat installation
    """
    return DEFAULT_TOMCAT_PATH


def get_public_ip():
    """
    Get public IP
    :return: String public IP
    """
    my_ip = urlopen('http://ip.42.pl/raw').read()
    log.echo_info('Public IP: %s' % my_ip.decode("utf-8"))
    return my_ip.decode("utf-8") + '/32'


def dir_name(path):
    """
    Get directory name of path
    :param path: Path
    :return: Directory name of path
    """
    return os.path.dirname(path)


def move_file(source, target):
    """
    Move file from specific source file to target
    :param source: Full path to the file to be moved
    :param target: Full path to the moved file
    """
    log.echo_info('move [%s] to [%s]' % (source, target))
    check_file_exists(source)
    shutil.move(source, target)
    log.echo_info('moving...')
    check_file_exists(target)


# noinspection SpellCheckingInspection
def chown(path, user, group=None):
    """
    Change owner for the file/folder defined by path
    :param path: the file/folder name
    :param user: User name or id
    :param group: Group name or id
    """
    __chown(path, user, group, False)


# noinspection SpellCheckingInspection
def __chown(path, user, group=None, recursive_flag=False):
    """
    Change owner for the file/folder defined by path
    :param path: The file/folder name including the path
    :param user: User name or id
    :param group: Group name or id
    :param recursive_flag: True if recursive enable, else False
    """
    if os.path.isdir(path) or os.path.isfile(path):
        if not isinstance(user, str):
            user = str(user)
        assert user, "user [%s] not defined!" % user
        if group:
            if not isinstance(group, str):
                group = str(group)
            assert group, "group [%s] not defined!" % group

        if is_linux():
            if group:
                chown_string = user + ":" + group
            else:
                chown_string = user
            if recursive_flag:
                log.echo_info('recursively update [%s] chown [%s]' % (path, chown_string))
                check_call(['chown', '-R', chown_string, path])
            else:
                log.echo_info('update [%s] chown [%s]' % (path, chown_string))
                check_call(['chown', chown_string, path])
            check_call(['ls', '-la', path])
        else:
            log.echo_error('Not supported')
            return
    else:
        log.echo_error("path [%s] does not refer to an existing file or folder" % path)
        exit(1)


def sed_in_place(source_file, replacement_list):
    """
    Perform a unix-like sed -i on a source file
    :param source_file: File to be modified
    :param replacement_list: List of replacements in tuple (pattern, replacement)
    :return: Number of replaced lines
    """
    source_file = os.path.normpath(source_file)
    replaced = 0
    with tempfile.NamedTemporaryFile(mode='w+t', delete=False) as tmp_sources:
        with open(source_file) as source_file:
            for line in source_file:
                line_replaced = False
                for replacement in replacement_list:
                    if re.findall(replacement[0], line):
                        line_r = re.sub(replacement[0], replacement[1], line)
                        replaced += 1
                        line_replaced = True
                        line = line_r
                if not line_replaced or line:
                    tmp_sources.write(line)
    if not replaced:
        pass
    else:
        if is_linux():
            shutil.copymode(getattr(source_file, 'name'), getattr(tmp_sources, 'name'))
            file_st = os.stat(getattr(source_file, 'name'))

            user = getattr(file_st, 'st_uid')
            group = getattr(file_st, 'st_gid')
            chown(tmp_sources.name, user, group)

        move_file(getattr(tmp_sources, 'name'), getattr(source_file, 'name'))
    return replaced


def grep(source_file, pattern, ignore_case=False):
    """
    Perform a unix-like grep on a source file
    :param source_file: File to apply grep
    :param pattern: Pattern to look for
    :param ignore_case: True if case should be ignored, else False
    :return: Lines from the source_file that match the pattern
    """
    source_file = os.path.normpath(source_file)
    pattern_compiled = re.compile(pattern, flags=(re.IGNORECASE if ignore_case else 0))
    with open(source_file) as file_handle:
        return [line for line in file_handle if pattern_compiled.findall(line)]


def exit_with_error(msg, return_code=1):
    """
    Exit with an error
    :param msg: The error message to display
    :param return_code: Return code, default 1
    """
    log.echo_error(msg)
    exit(return_code)


def find_a_file(searching_dir, file_name):
    """
    Search a file

    :param searching_dir: the start search point of the directory
    :param file_name: The file name to be searched
    :return The file path name if find, otherwise None
    """
    for root, _, files in os.walk(searching_dir):
        for name in files:
            if name == file_name:
                return path_join(root, name)
    return None


def set_resource_env_cwd():
    os.environ[resource.RESOURCES_DIRECTORY_ENV_VAR] = get_cwd()


def clear_resource_env():
    del os.environ[resource.RESOURCES_DIRECTORY_ENV_VAR]


#############
# Utilities for subprocess
#############
# noinspection SpellCheckingInspection
def __call_fixup_stdin_arg(kwargs):
    """
    Cleanup keyword arguments
    :param kwargs: Keyword arguments to be fixed
    :return: kwargs cleaned up
    """
    if 'dump' in kwargs:
        del kwargs['dump']
    if 'stdin' in kwargs and isinstance(kwargs.get('stdin'), (str, io.StringIO)):
        input_ = kwargs.get('stdin')
        input_ = input_.getvalue() if isinstance(input_, io.StringIO) else input_
        del kwargs['stdin']
        return kwargs, input_
    return kwargs, None


def call(cmd, **kwargs):
    """
    Run a OS command
    :param cmd: Command to be run
    :param kwargs: Keyword arguments for command
    :return: Return code of the command
    """
    __dump_commands(cmd, **kwargs)
    kwargs, input_ = __call_fixup_stdin_arg(kwargs)
    if input_:
        log.echo_debug('Running command using STDIN pipe...')
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, **kwargs)
        _, _ = process.communicate(input_)
        log.echo_debug('Return code [%d]' % process.returncode)
        return process.returncode
    else:
        return_code = subprocess.call(cmd, **kwargs)
        log.echo_debug('Return code [%d]' % return_code)
        return return_code


def check_call(cmd, **kwargs):
    """
    Run a OS command with check
    :param cmd: command to be run
    :param kwargs: Keyword arguments for command
    :return: Return code of the command
    """
    __dump_commands(cmd, **kwargs)
    if 'stdin' in kwargs:
        return_code = call(cmd, **kwargs)
        assert return_code == 0
        return return_code
    else:
        return_code = subprocess.check_call(cmd, **kwargs)
        log.echo_debug('Return code [%d]' % return_code)
        return return_code


def __dump_commands(cmd, **kwargs):
    """
    Output command and arguments
    :param cmd: Command to output, if 'dump' one of the arguments
    :param kwargs: Keyword arguments for command
    """
    if 'dump' in kwargs:
        cmd = kwargs['dump']
    log.echo_debug('Calling command-line: <<<%s>>>' % str(cmd))
    log.echo_debug('kwargs: <<<%s>>>' % str(kwargs))


def check_output(cmd, **kwargs):
    """
    Run a command and check output.
    :param cmd: command to be run
    :param kwargs: keyword arguments for command
    :return: output of command
    """
    __dump_commands(cmd, **kwargs)
    kwargs, input_ = __call_fixup_stdin_arg(kwargs)
    if input_:
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, **kwargs)
        out, err = process.communicate(input_)
    else:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
        out, err = process.communicate()
    log.echo_debug('tempOut [%s]' % out)
    log.echo_debug('tempErr [%s]' % err)
    log.echo_debug('return code [%d]' % process.returncode)
    assert process.returncode == 0
    return out


def dev_null():
    return open(os.devnull, 'w')
