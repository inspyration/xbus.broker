# -*- encoding: utf-8 -*-
__author__ = 'faide'

import unittest
import asyncio
import aiozmq
from unittest.mock import Mock

from xbus.broker.core.front import XbusBrokerFront
from aiozmq import rpc
from xbus.broker.model.auth.helpers import gen_password

import logging
logging.basicConfig(level=logging.DEBUG)


class Test(unittest.TestCase):

    def setUp(self):
        asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())
        self.loop = asyncio.new_event_loop()
        # feed None to asyncio.set_event_loop() to directly specify the
        # fact that the library should not rely on global loop existence
        # and safely work by explicit loop passing
        asyncio.set_event_loop(None)
        self.front_socket = 'inproc://#test'

    @asyncio.coroutine
    def get_front_broker(self, uid, password, profile_id):

        # no dbengine for the broker :)
        broker = XbusBrokerFront(None)

        # new token always returns the same testable uuid...
        broker.new_token = Mock(
            return_value="989def91-b42b-442e-8ab9-685b10900748"
        )
        # TODO: this mocker should return a future
        broker.find_emitter_by_login = Mock(
            return_value=(uid, password, profile_id)
        )
        zmqserver = yield from rpc.serve_rpc(
            broker,
            bind=self.front_socket,
            loop=self.loop
        )
        yield from zmqserver.wait_closed()

    def test_login(self):
        @asyncio.coroutine
        def gotest():

            # instantiate the front
            front = yield from self.get_front_broker(1, 'testpass', 1)

            client = yield from aiozmq.rpc.connect_rpc(
                connect=self.front_socket,
                loop=self.loop
            )

            ret = yield from client.call.login('test', 'testpass')
            client.close()
            front.close()
            assert ret == "989def91-b42b-442e-8ab9-685b10900748"

        self.loop.run_until_complete(gotest())
