# -*- encoding: utf-8 -*-
__author__ = 'faide'

import aioredis
import json
import asyncio

from aiozmq import rpc


class XbusBrokerBase(rpc.AttrHandler):
    """The XbusBrokerBase is the boilerplate code we need for both our
    broker front and broker back (ie: initialize redis etc...)
    """

    def __init__(self, dbengine):
        self.dbengine = dbengine
        self.redis_connection = None
        super(rpc.AttrHandler, self).__init__()

    def prepare_redis(self, redis_host, redis_port):
        self.redis_connection = yield from aioredis.create_connection(
            (redis_host, redis_port)
        )

    @asyncio.coroutine
    def create_token(self, token: bytes, info: dict):
        yield from self.redis_connection.execute(
            'set', 'tok:' + token, json.dumps(info)
        )

    @asyncio.coroutine
    def get_token_info(self, token: bytes) -> dict:

        info = yield from self.redis_connection.execute(
            'get', 'tok:' + token
        )
        if info:
            return json.loads(info)

    @asyncio.coroutine
    def destroy_token(self, token: bytes):
