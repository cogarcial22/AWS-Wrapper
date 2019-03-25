import logging
import os
import sys
import math
import time
import inspect

SCRIPT_NAME = os.path.basename(sys.argv[0])
LOG_DEFAULT_LEVEL = logging.INFO
LOG_DEFAULT_FORMAT = '%(asctime)s %(message)s'
LOG_DEFAULT_DATE_FORMAT = '%b-%d %H:%M:%S'
LOG_INDENT = 58


def get_logger(name):
    """
    Get logger instance
    :param name: Name of the logger
    :return: Logger instance
    """
    base_logger = logging.getLogger(name)
    return _AWLoggerAdapter(base_logger)


class _AWLoggerAdapter(logging.LoggerAdapter):
    """
    Log adapter
    """
    def __init__(self, logger):
        super(_AWLoggerAdapter, self).__init__(logger, {})

    def process(self, msg, kwargs):
        """
        Process message to log
        :param msg: Message to be processed
        :param kwargs: Keyword arguments
        :return: Message and keyword
        """
        msg, kwargs = logging.LoggerAdapter.process(self, msg, kwargs)
        return msg, kwargs


def __get_echo_msg(msg, log_level):
    """
    Get message with keywords replaced
    :param msg: Message to be output to log
    :param log_level: Log level
    :return: Message to be logged
    """
    if isinstance(msg, str):
        if r'{timestamp}' in msg.lower():
            timestamp = math.floor(time.time())
            msg = msg.replace('{timestamp}', '%d' % timestamp)
        if r'{scriptname}' in msg.lower():
            msg = msg.replace('{scriptname}', SCRIPT_NAME)
    caller_name, caller_line = __get_echo_caller()
    msg = '%-27s %-5s %-7s %s' % (caller_name, caller_line, log_level, msg)
    return msg


def __get_echo_caller():
    """
    Uses the stack to determine frame immediately before a qd.echo_* call.  When called during
    the output of an echo statement, provides the calling module/line in order to make resulting
    log more useful.
    :return Tuple (module_name, module_line):
    """
    try:
        stack_level = 1
        frame = inspect.stack()[stack_level]
        frame_module = frame[1]
        frame_method = frame[3]
        while not (str(frame_module).endswith('aw.py') and
                   str(frame_method).startswith('echo_')) and stack_level < 10:
            try:
                stack_level += 1
                frame = inspect.stack()[stack_level]
                frame_module = frame[1]
                frame_method = frame[3]
            except IndexError:
                raise IndexError
        frame = inspect.stack()[stack_level + 1]
        frame_module = frame[1]
        frame_line = frame[2]
    except Exception or BaseException:
        frame_module = SCRIPT_NAME
        frame_line = '---'
    index_start = str(frame_module).rfind(os.path.sep)
    index_end = str(frame_module).rfind('.')
    return frame_module[index_start + 1:index_end], frame_line


LOGGER = get_logger(__name__)


def echo_debug(msg):
    """
    Echo DEBUG message
    :param msg: message to be logged
    """
    LOGGER.debug(__get_echo_msg(wrap_long_lines(msg), 'DEBUG'))


def echo_info(msg):
    """
    Echo INFO message
    :param msg: message to be logged
    """
    LOGGER.info(__get_echo_msg(wrap_long_lines(msg), 'INFO'))


def echo_error(msg):
    """
    Echo ERROR message
    :param msg: message to be logged
    """
    LOGGER.error(__get_echo_msg(wrap_long_lines(msg), 'ERROR'))


def echo_warning(msg):
    """
    Echo WARNING message
    :param msg: message to be logged
    """
    LOGGER.warning(__get_echo_msg(wrap_long_lines(msg), 'WARNING'))


def wrap_long_lines(msg):
    """
    Get a string representing the message
    :param msg: Message to wrapped
    :return: Message wrapped
    """
    return_msg = msg
    if '\n' in msg or '\r' in msg or '\r\n' in msg:
        if '\r\n' in return_msg:
            return_msg = return_msg.replace('\r\n', '~!@#$%^&*' + ' ' * LOG_INDENT)
        if '\n' in return_msg:
            return_msg = return_msg.replace('\n', '~!@#$%^&*' + ' ' * LOG_INDENT)
        if '\r' in return_msg:
            return_msg = return_msg.replace('\r', '~!@#$%^&*' + ' ' * LOG_INDENT)
        return return_msg.replace('~!@#$%^&*', '\n')
    else:
        return msg
