# -*- encoding: utf-8 -*-
__author__ = 'faide'

import uuid
import asyncio
import aiozmq
import aioredis
import json
from aiozmq import rpc

from sqlalchemy.sql import select

from xbus.broker.model import user
from xbus.broker.model import role
from xbus.broker.model import validate_password
from xbus.broker.model import emitter


def prepare_event_loop():
    asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())


class XbusBrokerFront(rpc.AttrHandler):

    def __init__(self, dbengine):
        self.dbengine = dbengine
        self.redis_connection = None
        super(rpc.AttrHandler, self).__init__()

    def prepare_redis(self, redis_host, redis_port):
        self.redis_connection = yield from aioredis.create_connection(
            (redis_host, redis_port)
        )

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

        :param login: the login you want to authenticate against
        :param password: the password that must match your login
        :return: returns a unicode token that can be used during the session
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
def frontserver(engine_callback, config, socket):
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
