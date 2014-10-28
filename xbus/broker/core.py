# -*- encoding: utf-8 -*-
__author__ = 'faide'

import asyncio
import aiozmq
from aiozmq import rpc

from xbus.broker.model import user


def prepare_event_loop():
    asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())


class XbusBrokerFront(rpc.AttrHandler):

    def __init__(self, dbengine):
        self.dbengine = dbengine
        super(rpc.AttrHandler, self).__init__()

    @rpc.method
    def remote_add(self, arg1: int, arg2: int) -> int:
        return arg1 + arg2

    @rpc.method
    @asyncio.coroutine
    def list_users(self) -> list:
        users = yield from find_users(self.dbengine)
        return users


@asyncio.coroutine
def find_users(dbengine):
    with (yield from dbengine) as conn:
        res = yield from conn.execute(user.select())
        users = []
        for row in res:
            users.append(("%.32x" % row.user_id, row.user_name))

        return users


@asyncio.coroutine
def frontserver(engine_callback, config, socket):
    dbengine = yield from engine_callback(config)
    zmqserver = yield from rpc.serve_rpc(
        XbusBrokerFront(dbengine),
        bind=socket
    )
    yield from zmqserver.wait_closed()
