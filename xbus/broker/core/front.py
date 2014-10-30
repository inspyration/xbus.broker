# -*- encoding: utf-8 -*-
__author__ = 'faide'

import asyncio
import json
from aiozmq import rpc

from sqlalchemy import func
from sqlalchemy.sql import select

from xbus.broker.model import role
from xbus.broker.model import validate_password
from xbus.broker.model import emitter
from xbus.broker.model import envelope
from xbus.broker.model import event
from xbus.broker.model import event_type
from xbus.broker.model import emitter_profile_event_type_rel
from xbus.broker.model import item

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

        emitter_row = yield from self.find_emitter_by_login(login)
        emitter_id, emitter_pwd, emitter_profile_id = emitter_row

        if validate_password(emitter_pwd, password):
            token = self.new_token()
            info = {'id': emitter_id, 'login': login,
                    'profile_id': emitter_profile_id}
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

    @rpc.method
    @asyncio.coroutine
    def start_envelope(self, token: str) -> str:
        """Start a new envelope.

        :param token:
         the emitter's connection token, obtained from the
         :meth:`.XbusBrokerFront.login` method which is exposed on the same
         0mq socket.

        :return:
         The UUID of the new envelope if successful, an empty string otherwise
        """
        emitter_json = yield from self.get_key_info(token)
        if emitter_json is None:
            return ""

        try:
            # lookup the emitters table and find a matching "login"
            emitter_info = json.loads(emitter_json)
            emitter_id = emitter_info['id']
        except (ValueError, SyntaxError, KeyError):
            return ""

        envelope_id = self.new_envelope()
        info = {'emitter_id': emitter_id}
        info_json = json.dumps(info)
        yield from self.save_key(envelope_id, info_json)

        yield from self.log_new_envelope(envelope_id, emitter_id)

        return envelope_id

    @rpc.method
    @asyncio.coroutine
    def start_event(self, token: str, envelope_id: str,
                    event_name: str, estimate: int) -> str:
        """Start a new event inside an envelop. Conceptually an event is the
        container of items (which are emitted using :meth:`.XbusBrokerFront
        .login` method on the same 0mq socket. An event is also contained
        inside an envelope with other events potentially of different types.

        :param token:
         the emitter's connection token, obtained from the
         :meth:`.XbusBrokerFront.login` method which is exposed on the same
         0mq socket.

        :param envelope_id:
         the UUID of an envelope previously opened by the emitter using the
         :meth:`.XbusBrokerFront.start_envelope` method which is exposed on
         the same 0mq socket.

        :param event_name:
         the name of the event's type

        :return:
         The UUID of the new event if successful, an empty string otherwise
        """
        emitter_json = yield from self.get_key_info(token)
        if emitter_json is None:
            return ""

        try:
            emitter_info = json.loads(emitter_json)
            emitter_id = emitter_info['id']
            profile_id = emitter_info['profile_id']
        except (ValueError, SyntaxError, KeyError):
            return ""

        envelope_json = yield from self.get_key_info(envelope_id)
        if envelope_json is None:
            return ""

        try:
            envelope_info = json.loads(envelope_json)
            envelope_emitter_id = envelope_info['emitter_id']
        except (ValueError, SyntaxError, KeyError):
            return ""

        if emitter_id != envelope_emitter_id:
            return ""

        type_id = yield from self.find_event_type_by_name(event_name)

        access = yield from self.check_event_access(profile_id, type_id)
        if access is False:
            return ""

        event_id = self.new_event()
        info = {'emitter_id': emitter_id, 'envelope_id': envelope_id,
                'type_id': type_id}
        info_json = json.dumps(info)
        yield from self.save_key(event_id, info_json)

        yield from self.log_new_event(event_id, envelope_id, emitter_id,
                                      type_id, estimate)

    @rpc.method
    @asyncio.coroutine
    def send_item(self, token: str, envelope_id: str, event_id: str,
                  index: int, data: bytes) -> bool:
        """Send an item through XBUS.

        :param token:
         the emitter's connection token, obtained from the
         :meth:`.XbusBrokerFront.login` method which is exposed on the same
         0mq socket.

        :param envelope_id:
         the UUID of an envelope previously opened by the emitter using the
         :meth:`.XbusBrokerFront.start_envelope` method which is exposed on
         the same 0mq socket.

        :param event_id:
         the UUID of the event

        :param index:
         the item index

        :param data:
         the item data

        :return:
         True if successful, False otherwise
        """
        emitter_json = yield from self.get_key_info(token)
        if emitter_json is None:
            return False

        try:
            emitter_info = json.loads(emitter_json)
            emitter_id = emitter_info['id']
        except (ValueError, SyntaxError, KeyError):
            return False

        event_json = yield from self.get_key_info(event_id)
        if event_json is None:
            return False

        try:
            envelope_info = json.loads(event_json)
            event_envelope_id = envelope_info['envelope_id']
            event_emitter_id = envelope_info['emitter_id']
        except (ValueError, SyntaxError, KeyError):
            return False

        if emitter_id != event_emitter_id or envelope_id != event_envelope_id:
            return False

        yield from self.log_sent_item(event_id, index, data)

        return True

    @asyncio.coroutine
    def find_emitter_by_login(self, login: str):
        with (yield from self.dbengine) as conn:
            query = select(emitter.c.id, emitter.c.password,
                           emitter.c.profile_id)
            query = query.where(
                emitter.c.login == login
            ).limit(1)

            res = yield from conn.execute(query)
            return res[0]

    @asyncio.coroutine
    def find_role_by_login(self, login: str):
        with (yield from self.dbengine) as conn:
            query = select(role.c.id, role.c.password)
            query = query.where(
                role.c.login == login
            ).limit(1)

            res = yield from conn.execute(query)
            return res[0]

    @asyncio.coroutine
    def check_event_access(self, profile_id: str, type_id: str) -> bool:
        with (yield from self.dbengine) as conn:
            query = select(func.count(emitter_profile_event_type_rel))
            query = query.where(
                emitter_profile_event_type_rel.c.profile_id == profile_id and
                emitter_profile_event_type_rel.c.type_id == type_id
            )

            res = yield from conn.execute(query)
            return True if res > 0 else False

    @asyncio.coroutine
    def log_new_envelope(self, envelope_id: str, emitter_id: str):
        with (yield from self.dbengine) as conn:
            insert = envelope.insert()
            insert = insert.values(id=envelope_id, state='emit',
                                   emitter_id=emitter_id)
            conn.execute(insert)

    @asyncio.coroutine
    def log_new_event(self, event_id: str, envelope_id: str, emitter_id: str,
                      type_id: str, estimate: int):
        with (yield from self.dbengine) as conn:
            insert = event.insert()
            insert = insert.values(id=event_id, envelope_id=envelope_id,
                                   emitter_id=emitter_id, type_id=type_id,
                                   estimated_items=estimate)
            conn.execute(insert)

    @asyncio.coroutine
    def log_sent_item(self, event_id: str, index: int, data: bytes):
        with (yield from self.dbengine) as conn:
            insert = item.insert()
            insert = insert.values(event_id=event_id, index=index, data=data)
            conn.execute(insert)

    @asyncio.coroutine
    def find_event_type_by_name(self, name: str) -> str:
        with (yield from self.dbengine) as conn:
            query = select(event_type.c.id)
            query = query.where(event_type.c.name == name)
            query = query.limit(1)

            res = yield from conn.execute(query)
            return res[0]


@asyncio.coroutine
def get_frontserver(engine_callback, config, socket):
    """A helper function that is used internally to create a running server for
    the front part of Xbus

    :param engine_callback:
     the engine constructor we will "yield from" to get a real dbengine

    :param config:
     the application configuration instance
     :class:`configparser.ConfigParser` it MUST contain a `redis` section and
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
