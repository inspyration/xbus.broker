# -*- encoding: utf-8 -*-
__author__ = 'faide'

import optparse
import os
import sys
from configparser import ConfigParser

import logging
import logging.config
logger = logging.getLogger(__name__)


def get_config():  # pragma: nocover
    """Create a Config object from config file gave as an argument
    and instantiate the MiniConnector passing the config
    """
    optparser = optparse.OptionParser()
    optparser.add_option(
        "-c", "--config",
        dest="config_file",
        help="Read the configuration from FILE",
        metavar="FILE",
        default="/etc/xbus.ini"
    )

    (options, args) = optparser.parse_args()

    config = ConfigParser()
    if not os.path.exists(options.config_file):
        # can't log when logging system is not yet ready
        print('Config file: %s not found !' % options.config_file)
        sys.exit(1)

    config.read(options.config_file)

    logging_configfile = os.path.abspath(config.get('logging', 'configfile'))
    if not os.path.exists(logging_configfile):
        # can log when logging system is not started
        print(
            'Logging config file "{0}" not found'.format(logging_configfile)
        )
        sys.exit(1)
    logging.config.fileConfig(logging_configfile)
    logger.info('Logging system initialized')

    return config
