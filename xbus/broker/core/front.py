# -*- encoding: utf-8 -*-
__author__ = 'faide'

import uuid
import asyncio
import json
from aiozmq import rpc

from sqlalchemy.sql import select

from xbus.broker.model import user
from xbus.broker.model import role
from xbus.broker.model import validate_password
from xbus.broker.model import emitter

from xbus.broker.core import XbusBrokerBase


class XbusBrokerFront(XbusBrokerBase):
    """the XbusBrokerFront is in charge of handling emitters on a specific 0mq
    socket. It implements login/logout & new_envelop, new_event

    Before you can call any useful methods on the XbusBrokerFront you'll need
    to obtain a token through the login() call. Once you have a token you will
    need to give it to all subsequent calls.

    If you have finished your session you SHOULD call the logout() method.
    This is important in order to protect yourself. Calling logout will
    invalidate the token and make sure no one can reuse it ever.
    """

    @rpc.method
    def remote_add(self, arg1: int, arg2: int) -> int:
        return arg1 + arg2

    @rpc.method
    @asyncio.coroutine
    def list_users(self) -> list:
        users = yield from self.find_users()
        return users

    @rpc.method
    @asyncio.coroutine
    def login(self, login: str, password: str) -> str:
        """Before doing anything usefull you'll need to login into the broker
        we a login/password. If the authentication phase is ok you'll get a
        token that must be provided during other method calls.

        :param login:
         the login you want to authenticate against

        :param password:
         the password that must match your login

        :return:
         a unicode token that can be used during the session
        """
        role_cols = yield from self.find_rolepasswd_by_login(login)
        if validate_password(role_cols['password'], password):
            token = uuid.uuid4()
            yield from self.redis_connection.execute(
                'set', token, json.dumps({'login': login})
            )
        else:
            token = ""

        return token

    @rpc.method
    @asyncio.coroutine
    def logout(self, token: str):
        """When you are done using the broker you should call this method to
        make sure your token is destroyed and no one can reuse it

        :param token: the token you want to invalidate
        :return: None
        """
        pass

    @rpc.method
    @asyncio.coroutine
    def new_envelop(self, login):
        # lookup the emitters table and find a matching "login"
        emitter = yield from self.find_emitter_by_login(login)

        # then do something
        pass

    @asyncio.coroutine
    def find_emitter_by_login(self, login):
        with (yield from self.dbengine) as conn:
            query = emitter.select()
            query = query.where(
                emitter.c.login == login
            ).limit(1)

            res = yield from conn.execute(query)
            return res[0]

    @asyncio.coroutine
    def find_rolepasswd_by_login(self, login):
        with (yield from self.dbengine) as conn:
            query = select(role.c.password)
            query = query.where(
                role.c.login == login
            ).limit(1)

            res = yield from conn.execute(query)
            return res[0]

    @asyncio.coroutine
    def find_users(self):
        with (yield from self.dbengine) as conn:
            res = yield from conn.execute(user.select())
            users = []
            for row in res:
                users.append(("%.32x" % row.user_id, row.user_name))

            return users


@asyncio.coroutine
def get_frontserver(engine_callback, config, socket):
    """A helper function that is used internally to create a running server for
    the front part of Xbus

    :param engine_callback:
     the engine constructor we will be to "yield from" to get a real dbengine

    :param config:
     the application configuration instance
     :class:`configparser.ConfigParser` it MUST contain a section redis and
     two keys: 'host' and 'port'

    :param socket:
     a string representing the socker address on which we will spawn our 0mq
     listener

    :return:
     a future that is waiting for a wait_closed() call before being
     fired back.
    """
    dbengine = yield from engine_callback(config)
    broker = XbusBrokerFront(dbengine)

    redis_host = config.get('redis', 'host')
    redis_port = config.getint('redis', 'port')
    broker.prepare_redis(redis_host, redis_port)

    zmqserver = yield from rpc.serve_rpc(
        broker,
        bind=socket
    )
    yield from zmqserver.wait_closed()


# we don't want our imports to be visible to others...
__all__ = ["XbusBrokerFront", "get_frontserver"]
