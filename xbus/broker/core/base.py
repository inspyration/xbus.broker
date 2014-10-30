# -*- encoding: utf-8 -*-
__author__ = 'faide'

import aioredis
from aiozmq import rpc


class XbusBrokerBase(rpc.AttrHandler):

    def __init__(self, dbengine):
        self.dbengine = dbengine
        self.redis_connection = None
        super(rpc.AttrHandler, self).__init__()

    def prepare_redis(self, redis_host, redis_port):
        self.redis_connection = yield from aioredis.create_connection(
            (redis_host, redis_port)
        )
