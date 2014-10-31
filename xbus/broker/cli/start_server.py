# -*- encoding: utf-8 -*-
__author__ = 'faide'

import asyncio
from aiopg.sa import create_engine

from xbus.broker.cli import get_config
from xbus.broker.core import get_frontserver
from xbus.broker.core import get_backserver
from xbus.broker.core import prepare_event_loop
import signal
import sys


def signal_handler(_signal, frame):
        print('')
        print('received signal {} during frame {}'.format(_signal, frame))
        print('User initiated shutdown by Ctrl+C')
        sys.exit(0)


@asyncio.coroutine
def get_engine(config):
    dbengine = yield from create_engine(
        dsn=config.get('database', 'sqlalchemy.dburi')
    )
    return dbengine


@asyncio.coroutine
def start_all() -> None:
    """the real coroutine that will spawn all the coroutines

    :return: None
    """
    signal.signal(signal.SIGINT, signal_handler)
    config = get_config()
    front_socket_name = config.get('zmq', 'frontsocket')
    back_socket_name = config.get('zmq', 'backsocket')
    b2f_socket_name = config.get('zmq', 'b2fsocket')
    prepare_event_loop()

    coroutines = [
        get_frontserver(get_engine, config, front_socket_name, b2f_socket_name),
        get_backserver(get_engine, config, back_socket_name, b2f_socket_name),
    ]

    yield from asyncio.gather(*coroutines)


def start_server() -> None:
    """A helper function that is used to start the broker server
    """
    asyncio.get_event_loop().run_until_complete(start_all())
