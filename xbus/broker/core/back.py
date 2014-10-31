# -*- encoding: utf-8 -*-
__author__ = 'jgavrel'

import asyncio
import json
import aiozmq
from aiozmq import rpc

from sqlalchemy.sql import select

from xbus.broker.model import role
from xbus.broker.model import validate_password

from xbus.broker.core import XbusBrokerBase


class BrokerBackError(Exception):
    pass


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

    def __init__(self, dbengine, frontsocket, socket):
        super(XbusBrokerBack, self).__init__(dbengine)

        self.frontsocket = frontsocket
        self.socket = socket

        self.node_registry = {}

        self.envelopes = []
        self.events = {}

    @asyncio.coroutine
    def register_on_front(self):
        """This method tries to register the backend on the frontend. If
        everything goes well it should return True.
        If we have an error during the registration process this method will
        raise a :class:`BrokerBackError`

        :return:
         True

        :raises:
         :class:`BrokerBackError`
        """
        client = yield from aiozmq.rpc.connect_rpc(connect=self.frontsocket)
        result = yield from client.call.register_backend(self.socket)
        if result is None:
            # yeeeks we got an error here ...
            # let's do something stupid and b0rk out
            raise BrokerBackError('Cannot register ourselves on the front')
        else:
            return True

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

    @rpc.method
    @asyncio.coroutine
    def register_node(self, token: str, uri: str) -> bool:
        """Register a worker / consumer on the broker. This worker will be
        known by the
        broker and called when some work is available.

        :param token:
         the token your worker previously obtained by using the
         :meth:`XbusBrokerBack.login` method

        :param uri:
         a unicode object representing the socket address on which your
         worker is available. The worker is effectivly a server and must
         answer on the designated socket when we need it.

        :return:
         True if the registration went well and the broker now knows the worker
         False if something went wrong during registration and the broker
         does not recognize the worker as being part of its active graph.
        """
        token_data = yield from self.get_key_info(token)

        if token_data is None:
            # token was invalid, return False to inform our potential worker of
            # the issue
            return False
        else:
            role_login = token_data.get('login', None)
            if role_login is None:
                return False

        # then connect to our worker's socket
        node_client = yield from aiozmq.rpc.connect_rpc(
            connect=uri
        )
        # keep a reference to our connected worker to be able to call him
        # later-on when we have work for him to do
        self.node_registry[role_login] = node_client
        return True

    @rpc.method
    @asyncio.coroutine
    def start_envelope(self, envelope_id: str) -> str:
        """Start a new envelop giving its envelop UUID.
        This is just a way to register the envelop existance with the broker
        backend. This permits to cancel this envelop further down the road.

        :param envelope_id:
         the UUID of the envelop you want to start
        expressed as a string

        :return:
         the envelop id you just started
        """
        self.envelopes.append(envelope_id)
        return envelope_id

    @rpc.method
    @asyncio.coroutine
    def end_envelope(self, envelope_id: str) -> str:
        """
        :param envelope_id:
         the envelope id you want to mark as finished

        :return:
         a dict containing information about the result like so
         {'success': True, 'message': "1200 lines inserted, import_id: 23455"}
        """
        # TODO: we must call all the active consumers that are concerned by
        # the envelope we are ending and make sure they are aware they can
        # now commit their respective changes
        return {
            'success': False,
            'envelope_id': envelope_id,
            'message': 'broker backend not yet implemented'
        }

    @rpc.method
    @asyncio.coroutine
    def cancel_envelope(self, envelope_id: str) -> str:
        """This is used to cancel a previously started envelop and make sure
        the consumers will rollback their changes

        :param envelope_id:
         the UUID of the envelope you want to cancel

        :return:
         the UUID of the envelope that has just been cancelled
        """
        # TODO: call all the active consumers that are concerned so they can
        # rollback their current work on the envelope
        return envelope_id

    @rpc.method
    @asyncio.coroutine
    def start_event(
            self, envelope_id: str, event_id: str, targets=None
    ) -> tuple:
        """Begin a new event inside an envelope opened against this broker
        backend.

        :param envelope_id:
         the previously opened envelope UUID to which this event is attached.
         If the envelope is unknown to the broker backend this will return an
         error code.

        :param event_id:
         the UUID representing the new event. If the UUID is already known to
         the broker backend (ie: already in use at the moment. We won't verify
         in the whole event history) then this method will return an error code
         instead of processing your data.

        :param targets:
         the list of consumer ids you want to specifically target with this
         event. It is optional and in most normal cases (ie: first time the
         frontend sends an event) it will not be used. The rationale behind
         this is that you may have situations when a specific node failed
         and the bus knows that it could not try to send data to the
         consumers that were situated after the failed node.
         In this particular situation the bus will mark the consumers as "not
         properly finished" and stamp the envelope as "not properly finished".
         When a human operator sees this situation in the management console
         they will be able to correct the defect and ask for a replay of the
         failed branches.
         This will re-emit the event through a subset of the network composed
         of the branches that lead to "not properly finished" consumers.

        :return:
         a 2 tuple with the success code and a message:

           - success -> (0, '<event_id>')
           - failure -> (1, "No such envelope : 87654345678")
        """
        if envelope_id in self.envelopes and not event_id in self.events:
            res = (0, "{}".format(event_id))

        else:
            msg = ""
            if envelope_id not in self.envelopes:
                msg += "No such envelope : {}\n".format(envelope_id)

            if event_id not in self.events:
                msg += "Event already started: {}\n".format(event_id)

            res = (1, msg)

        return res

    @rpc.method
    @asyncio.coroutine
    def end_event(self, event_id: str):
        """Finish an event normally.

        :param event_id:
         the event UUID you previously started

        :return:
         to be defined
        """
        pass

    @rpc.method
    @asyncio.coroutine
    def send_item(self, event_id: str, data: bytes):
        """Send an item to the XBUS network.

        :param event_id:
         event UUID previously opened onto which this item will be sent

        :param data:
         the raw data of the item. This data will not be opened or
         interpreted by the bus itself, but forwarded to all the workers and
         ultimately the consumers of the graph.

        :return:
         to be defined
        """
        # if we have an event_id this means we already have a precomputed graph
        # for this event... so lets send the item to the corresponding nodes
        pass

    @asyncio.coroutine
    def find_role_by_login(self, login: str) -> tuple:
        """internal helper method used to find a role
        (id, password, service_id) by looking up in the database its login

        :param login:
         the login that identifies the role you are searching

        :return:
         a 3-tuple containing (id, password, service_id), if nothing is found
         the tuple will contain (None, None, None)
        """
        with (yield from self.dbengine) as conn:
            query = select(role.c.id, role.c.password, role.c.service_id)
            query = query.where(role.c.login == login).limit(1)

            res = yield from conn.execute(query)
            res = res[0]
            if res is None:
                res = (None, None, None)

            return res


@asyncio.coroutine
def get_backserver(engine_callback, config, socket, b2fsocket):
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
     a future that is waiting for a closed() call before being
     fired back.
    """
    dbengine = yield from engine_callback(config)
    broker_back = XbusBrokerBack(dbengine, b2fsocket, socket)

    redis_host = config.get('redis', 'host')
    redis_port = config.getint('redis', 'port')

    yield from broker_back.prepare_redis(redis_host, redis_port)
    yield from broker_back.register_on_front()

    zmqserver = yield from rpc.serve_rpc(
        broker_back,
        bind=socket
    )
    yield from zmqserver.wait_closed()


# we don't want our imports to be visible to others...
__all__ = ["XbusBrokerBack", "get_backserver"]
