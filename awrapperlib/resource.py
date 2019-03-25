"""
Provides functions to simplify finding non-Python resources.
"""
import os
import errno
from awrapperlib import aw

RESOURCES_DIRECTORY_ENV_VAR = "AW_RESOURCES_DIR"

DEFAULT_RESOURCES_DIR_NAME = 'resources'


def get_resources_directory():
    """
    Get base resource directory, default is the project resource directory
    :return: Resource base directory
    """
    resources_dir = os.environ.get(RESOURCES_DIRECTORY_ENV_VAR, None)

    if not resources_dir:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        resources_dir = os.path.join(script_dir, '..',  DEFAULT_RESOURCES_DIR_NAME)
        resources_dir = os.path.abspath(resources_dir)

    if not os.path.isdir(resources_dir):
        raise IOError(errno.ENOENT, os.strerror(errno.ENOENT), resources_dir)

    return resources_dir


def get_resource(resource_path):
    """
    Get resource full path
    :param resource_path: Resource base directory
    :return: Resource full path
    """
    full_path = os.path.abspath(os.path.join(get_resources_directory(), resource_path))

    parent_path = os.path.abspath(os.path.join(full_path, os.pardir))
    file_name = os.path.basename(full_path)
    os_dir_name = "windows" if aw.is_windows() else "linux"

    os_full_path = os.path.abspath(os.path.join(parent_path, os_dir_name, file_name))

    if os.path.isfile(os_full_path):
        return os_full_path

    if not os.path.exists(full_path):
        raise IOError(errno.ENOENT, os.strerror(errno.ENOENT), full_path)

    return full_path
