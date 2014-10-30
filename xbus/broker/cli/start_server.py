# -*- encoding: utf-8 -*-
__author__ = 'faide'

import asyncio
from aiopg.sa import create_engine

from xbus.broker.cli import get_config
from xbus.broker.core import get_frontserver
from xbus.broker.core import prepare_event_loop
import signal
import sys


def signal_handler(signal, frame):
        print('')
        print('User initiated shutdown by Ctrl+C')
        sys.exit(0)


@asyncio.coroutine
def get_engine(config):
    dbengine = yield from create_engine(
        dsn=config.get('database', 'sqlalchemy.dburi')
    )
    return dbengine


def start_server() -> None:
    """A helper function that is used to start the broker server
    :return: None
    """
    signal.signal(signal.SIGINT, signal_handler)
    config = get_config()
    socket_name = config.get('zmq', 'frontsocket')
    prepare_event_loop()

    asyncio.get_event_loop().run_until_complete(
        get_frontserver(get_engine, config, socket_name))
