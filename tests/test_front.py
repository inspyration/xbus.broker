# -*- encoding: utf-8 -*-
__author__ = 'faide'

import unittest
import asyncio
import aiozmq
import json
from unittest.mock import Mock

from xbus.broker.core.front import XbusBrokerFront
from aiozmq import rpc
from xbus.broker.model.auth.helpers import gen_password
from xbus.broker.model.auth.helpers import validate_password

import logging
logging.basicConfig(level=logging.DEBUG)


class TestAuth(unittest.TestCase):
    def test_validate_password_works(self):
        """ensure that our gen_password and validate_password helpers a
        working properly"""
        password = 'test'
        res = gen_password(password)
        assert validate_password(password, res), "Equal passwords should be ok"

    def test_validate_password_false(self):
        """ensure that our gen_password and validate_password helpers a
        working properly"""
        password = 'test'
        res = gen_password(password)
        password2 = 'test2'
        assert not validate_password(password2, res), (
            "Non Equal passwords should not be ok")


class TestLogin(unittest.TestCase):

    def error_handler(self, loop, info):
        print('Error occured: {}'.format(info))

    def setUp(self):
        asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())
        self.loop = asyncio.new_event_loop()
        # feed None to asyncio.set_event_loop() to directly specify the
        # fact that the library should not rely on global loop existence
        # and safely work by explicit loop passing
        asyncio.set_event_loop(None)
        self.front_socket = 'inproc://#test'
        self.token = "989def91-b42b-442e-8ab9-685b10900748"

    @asyncio.coroutine
    def get_front_broker(self, uid, password, profile_id):
        """a helper function to call from inside a test to setup your login
        :param uid:
         role id you want to assume during tests

        :param password:
         the password you want to use in your test

        :param profile_id:
         the profile id your login must be attached to

        :return:
         a zmqserver future you can yield from. Don't forget to
         close() it when you are done with it
        """

        # no dbengine for the broker :)
        broker = XbusBrokerFront(None)

        # new token always returns the same testable uuid...
        broker.new_token = Mock(
            return_value=self.token
        )
        self.login_info = (uid, gen_password(password), profile_id)
        broker.find_emitter_by_login = self.get_mock_emitter
        broker.save_key = self.mock_save_key

        zmqserver = yield from rpc.serve_rpc(
            broker,
            bind=self.front_socket,
            loop=self.loop
        )
        #yield from zmqserver.wait_closed()
        self.loop.set_exception_handler(self.error_handler)
        return zmqserver

    @asyncio.coroutine
    def mock_save_key(self, *args, **kwargs):
        return True

    @asyncio.coroutine
    def get_mock_emitter(self, *args, **kwargs):
        return self.login_info

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
            assert ret == self.token, "We should have obtained our token!"

        self.loop.run_until_complete(gotest())


class TestFrontBase(unittest.TestCase):

    def error_handler(self, loop, info):
        print('Error occured: {}'.format(info))

    def setUp(self):
        asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())
        self.loop = asyncio.new_event_loop()
        # feed None to asyncio.set_event_loop() to directly specify the
        # fact that the library should not rely on global loop existence
        # and safely work by explicit loop passing
        asyncio.set_event_loop(None)
        self.front_socket = 'inproc://#test'

    @asyncio.coroutine
    def get_mock_frontbroker(self, **attrs):
        """Create a mock front-end broker, using the given arguments to
        override the object's methods and attributes with dummy values.

        The given values will be converted whenever necessary:
          _ to a mock function returning the new value, if the overridden
          value is callable and the new value isn't ;
          _ then to a coroutine, if the overridden value is also a coroutine
          and the new value isn't.

        :param attrs:
         a dictionary which maps overridden attributes to their new value.
        :return:
         a zmqserver future you can yield from. Don't forget to
         close() it when you are done with it
        """
        broker = XbusBrokerFront(None, loop=self.loop)
        print(dir(broker))

        for attr, value in attrs.items():

            old_value = getattr(broker, attr)
            if old_value:

                if hasattr(old_value, '__call__'):
                    if not hasattr(value, '__call__'):
                        value = Mock(return_value=value)

                    if asyncio.iscoroutinefunction(old_value) is True:
                        if asyncio.iscoroutinefunction(value) is not True:
                            value = asyncio.coroutine(value)

            setattr(broker, attr, value)

        zmqserver = yield from rpc.serve_rpc(
            broker,
            bind=self.front_socket,
            loop=self.loop
        )
        self.loop.set_exception_handler(self.error_handler)
        return zmqserver


class TestNewEnvelope(TestFrontBase):

    def setUp(self):
        super().setUp()
        self.emitter_id = 1
        self.token = "989def91-b42b-442e-8ab9-685b10900748"
        self.envelope_id = "989def91-b42b-442e-8ab9-685b10900749"

    def test_new_envelope(self):

        @asyncio.coroutine
        def gotest():

            front = yield from self.get_mock_frontbroker(
                get_key_info=json.dumps({'id': self.emitter_id}),
                new_envelope=self.envelope_id,
                save_key=True,
                log_new_envelope=True,
                backend_start_envelope=True
            )

            client = yield from aiozmq.rpc.connect_rpc(
                connect=self.front_socket,
                loop=self.loop
            )

            ret = yield from client.call.start_envelope(self.token)
            client.close()
            front.close()
            assert ret == self.envelope_id, (
                "We should have obtained our envelope UUID!"
            )

        self.loop.run_until_complete(gotest())
