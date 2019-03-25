import os
import configparser
import re
from awrapperlib import aw, resource, logger as log
DEFAULT_ENV_PROPS_LOCATION = 'Properties/aw.properties'


def get_default_props():
    """
    Get properties instance using default properties file
    :return: AWEnv instance object
    """
    properties_file = resource.get_resource(DEFAULT_ENV_PROPS_LOCATION)
    return AWEnv(properties_file)


def get_props(path):
    """
    Get properties instance using the provisioned path location
    :param path: Path to properties file location
    :return: AWEnv instance object
    """
    dir_name = aw.dir_name(path)
    os.environ[resource.RESOURCES_DIRECTORY_ENV_VAR] = dir_name
    properties_file = resource.get_resource(aw.basename(path))
    return AWEnv(properties_file)


class AWEnv:
    """
    Properties file handler
    """

    def __init__(self, filename=None, error_if_not_exist=True):
        self.default_section = 'DEFAULT_SECTION'
        self.parser = configparser.ConfigParser()
        if filename:
            if not os.path.isfile(filename) and not error_if_not_exist:
                self.filename = filename
            else:
                self.read(filename)

    def read(self, filename):
        """
        Read properties file
        :param filename: File name of the properties file
        """
        self.parser.optionxform = lambda x: x
        default_section = '[' + self.default_section + ']'
        self.parser.read_string(default_section + os.linesep + open(filename).read())
        log.echo_info(
            'loaded [%s] and %d properties are defined.' % (filename, len(self.parser.options(self.default_section))))
        self.filename = filename

    def set_value(self, prop, value):
        """
        Set value to properties file
        :param prop: Property to save
        :param value: Value of the property
        """
        self.parser.set(self.default_section, prop, value)
        if os.path.exists(self.filename) and aw.grep(self.filename, r'^%s=' % re.escape(prop)):
            if value is None:
                aw.sed_in_place(self.filename, [(r'^%s=.*$' % re.escape(prop), '')])
            else:
                aw.sed_in_place(self.filename, [(r'^%s=.*$' % re.escape(prop),
                                                 ('%s=%s' % (prop, value)).replace('\\', '\\\\'))])
        else:
            with open(self.filename, 'at') as file_handle:
                file_handle.write(os.linesep + '%s=%s' % (prop, value))

    def update_value(self, prop, value):
        """
        Update property file
        :param prop: Property to save
        :param value: Value of the property
        """
        self.set_value(prop, value)

    def get_values_as_dict(self, *props, **defaults):
        """
        Get properties and values as dictionary
        :param props: List of property to get
        :param defaults: List of defaults values for properties in case doesn't exists
        :return: Dictionary of properties
        """
        items = {}
        for prop in props:
            try:
                items[prop] = self.parser.get(self.default_section, prop)
            except configparser.NoOptionError:
                if prop in defaults:
                    items[prop] = defaults[prop]
                    self.update_value(prop, defaults[prop])
                else:
                    items[prop] = None
                continue
        return items

    def __clean_value_output(self, value):
        """
        TBD remove special characters form properties
        :param value:
        :return:
        """
        return True

    def get_values(self, *props, **defaults):
        """
        Get values from properties
        :param props: Properties to get
        :param defaults: Defaults values of properties
        :return: List of values if exists else will return defaults
        """
        items = [[prop, None] for prop in props]
        for item in items:
            try:
                item[1] = self.parser.get(self.default_section, item[0])
            except configparser.NoOptionError:
                if item[0] in defaults:
                    item[1] = defaults[item[0]]
                    self.update_value(item[0], defaults[item[1]])
                else:
                    item[0] = None
                continue
        if len(items) == 1:
            return items[0][1]
        else:
            return tuple((v[1]) for v in items)

    def get_all_values(self):
        """
        Get all property values as dictionary
        :return: Dictionary of properties with values
        """
        items = {}
        options = self.parser.options(self.default_section)
        for option in options:
            items[option] = self.parser.get(self.default_section, option)
        return items
