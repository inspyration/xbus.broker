# -*- encoding: utf-8 -*-
__author__ = 'jgavrel'

import asyncio
import json
from aiozmq import rpc

from sqlalchemy.sql import select

from xbus.broker.model import role
from xbus.broker.model import validate_password

from xbus.broker.core import XbusBrokerBase


class XbusBrokerBack(XbusBrokerBase):
    """the XbusBrokerBack is in charge of handling workers and consumers
    on a specific 0mq socket.

    Before you can call any useful methods on the XbusBrokerBack you'll need
    to obtain a token through the login() call. Once you have a token you will
    need to give it to all subsequent calls.

    If you have finished your session you SHOULD call the logout() method.
    This is important in order to protect yourself. Calling logout will
    invalidate the token and make sure no one can reuse it ever.
    """

    @rpc.method
    @asyncio.coroutine
    def login(self, login: str, password: str) -> str:
        """Before doing anything useful you'll need to login into the broker
        we a login/password. If the authentication phase is ok you'll get a
        token that must be provided during other method calls.

        :param login:
         the login you want to authenticate against

        :param password:
         the password that must match your login

        :return:
         a unicode token that can be used during the session
        """

        role_row = yield from self.find_role_by_login(login)
        role_id, role_pwd, service_id = role_row
        if validate_password(role_pwd, password):
            token = self.new_token()
            info = {'id': role_id, 'login': login, 'service_id': service_id}
            info_json = json.dumps(info)
            yield from self.save_key(token, info_json)
        else:
            token = ""

        return token

    @rpc.method
    @asyncio.coroutine
    def logout(self, token: str) -> bool:
        """When you are done using the broker you should call this method to
        make sure your token is destroyed and no one can reuse it

        :param token:
         the token you want to invalidate
        :return:
         True if successful, False otherwise
        """
        res = yield from self.destroy_key(token)
        return res

    @asyncio.coroutine
    def find_role_by_login(self, login: str):
        with (yield from self.dbengine) as conn:
            query = select(role.c.id, role.c.password, role.c.service_id)
            query = query.where(role.c.login == login).limit(1)

            res = yield from conn.execute(query)
            return res[0]


@asyncio.coroutine
def get_backserver(engine_callback, config, socket):
    """A helper function that is used internally to create a running server for
    the back part of Xbus

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
    broker = XbusBrokerBack(dbengine)

    redis_host = config.get('redis', 'host')
    redis_port = config.getint('redis', 'port')
    broker.prepare_redis(redis_host, redis_port)

    zmqserver = yield from rpc.serve_rpc(
        broker,
        bind=socket
    )
    yield from zmqserver.wait_closed()


# we don't want our imports to be visible to others...
__all__ = ["XbusBrokerBack", "get_backserver"]
