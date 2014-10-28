# -*- encoding: utf-8 -*-
__author__ = 'faide'

from xbus.broker.cli import get_config
from xbus.broker.model import setup_app


def setup_xbusbroker():
    """ a simple cmd line that will create a default db
    """
    # just run the setup script by passing it a config instance
    setup_app(get_config())
