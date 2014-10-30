# -*- encoding: utf-8 -*-
__author__ = 'faide'

import aioredis
import uuid
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

    @staticmethod
    def new_token() -> str:
        return uuid.uuid4().hex

    @staticmethod
    def new_envelope() -> str:
        return uuid.uuid4().hex

    @staticmethod
    def new_event() -> str:
        return uuid.uuid4().hex

    @asyncio.coroutine
    def save_key(self, key: str, info: str) -> bool:
        try:
            yield from self.redis_connection.execute(
                'set', key, info
            )
        except (aioredis.ReplyError, aioredis.ProtocolError):
            return False
        return True

    @asyncio.coroutine
    def get_key_info(self, key: str) -> str:
        try:
            info = yield from self.redis_connection.execute(
                'get', key
            )
        except (aioredis.ReplyError, aioredis.ProtocolError):
            return None
        return info

    @asyncio.coroutine
    def destroy_key(self, key: str) -> bool:
        try:
            yield from self.redis_connection.execute(
                'del', key
            )
        except (aioredis.ReplyError, aioredis.ProtocolError):
            return False
        return True
