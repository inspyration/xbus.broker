# -*- encoding: utf-8 -*-
__author__ = 'faide'

import asyncio
import aiozmq
from xbus.broker.core.base import XbusBrokerBase
from xbus.broker.core.front import get_frontserver
from xbus.broker.core.back import get_backserver
from xbus.broker.core.event import Event


def prepare_event_loop():
    asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())
