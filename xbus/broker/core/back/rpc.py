# -*- encoding: utf-8 -*-
__author__ = 'jgavrel'

import asyncio
import json
import aiozmq
from aiozmq import rpc
from collections import defaultdict

from sqlalchemy.sql import select

from xbus.broker.model import role
from xbus.broker.model import validate_password
from xbus.broker.model.helpers import get_event_tree
from xbus.broker.model.helpers import get_consumer_roles

from xbus.broker.core.base import XbusBrokerBase
from xbus.broker.core.back.envelope import Envelope


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

    def __init__(self, dbengine, frontsocket, socket, loop=None):
        super(XbusBrokerBack, self).__init__(dbengine, loop=loop)

        self.frontsocket = frontsocket
        self.socket = socket

        self.consumers = defaultdict(set)
        self.active_roles = defaultdict(set)
        self.node_registry = {}

        self.envelopes = {}

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
        yield from self.init_consumers()
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
        if validate_password(password, role_pwd):
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
        token_json = yield from self.get_key_info(token)
        token_data = json.loads(token_json)

        if token_data is None:
            # token was invalid, return False to inform our potential worker of
            # the issue
            return False
        else:
            role_id = token_data.get('id', None)
            service_id = token_data.get('service_id', None)

            service_roles = self.active_roles[service_id]
            if role_id in service_roles:
                service_roles.remove(role_id)
            try:
                del self.node_registry[role_id]
            except KeyError:
                pass
            res = yield from self.destroy_key(token)
        return res

    @rpc.method
    @asyncio.coroutine
    def register_node(self, token: str, uri: str) -> bool:
        """Register a worker / consumer on the broker. This worker will be
        known by the broker and called when some work is available.

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
        token_json = yield from self.get_key_info(token)
        token_data = json.loads(token_json)

        if token_data is None:
            # token was invalid, return False to inform our potential worker of
            # the issue
            return False
        else:
            role_id = token_data.get('id', None)
            if role_id is None:
                return False

        # then connect to our worker's socket
        node_client = yield from aiozmq.rpc.connect_rpc(
            connect=uri
        )
        # keep a reference to our connected worker to be able to call him
        # later-on when we have work for him to do
        self.node_registry[role_id] = node_client
        res = yield from self.ready(token)
        return res

    @rpc.method
    @asyncio.coroutine
    def ready(self, token: str) -> bool:
        """Register a worker / consumer on the broker. This worker will be
        called when some work is available.

        :param token:
         the token your worker previously obtained by using the
         :meth:`XbusBrokerBack.login` method
        """

        token_json = yield from self.get_key_info(token)
        token_data = json.loads(token_json)

        if token_data is None:
            # token was invalid, return False to inform our potential worker of
            # the issue
            return False
        else:
            role_id = token_data.get('id', None)
            service_id = token_data.get('service_id', None)
            if role_id is None or service_id is None:
                return False

            if role_id not in self.node_registry:
                return False
            service_roles = self.active_roles[service_id]
            service_roles.add(role_id)
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
        # TODO: replace new dict with a properly defined Envelope object?
        self.envelopes[envelope_id] = Envelope(
            envelope_id, self.dbengine, self.loop
        )
        return envelope_id

    @rpc.method
    @asyncio.coroutine
    def start_event(
            self, envelope_id: str, event_id: str, type_id: str,
            type_name: str, *, targets: list=None
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

        :param type_id:
         the internal UUID that corresponds to the type of the started event.

        :param type_name:
         the name of the type of the started event.

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
        envelope = self.envelopes.get(envelope_id, None)

        errors = []
        if envelope is None:
            errors.append("No such envelope : {}".format(envelope_id))

        elif event_id in envelope.events:
            errors.append("Event already started: {}".format(event_id))

        if errors:
            res = (1, "\n".join(errors))
            return res

        event = envelope.new_event(event_id, type_name, type_id)
        rows = yield from self.get_event_tree(type_id)
        nodes = {}

        for row in rows:
            node_id, service_id, is_start, child_ids = row.as_tuple()
            service_roles = self.active_roles[service_id]

            if child_ids:     # Workers
                if not service_roles:
                    return False
                role_id = service_roles.pop()
                client = self.node_registry[role_id]
                event.new_worker(node_id, role_id, client, child_ids, is_start)

            else:             # Consumers
                role_ids = list(service_roles)
                clients = [self.node_registry[r] for r in service_roles]
                event.new_consumer(node_id, role_ids, clients, is_start)
                consumers = self.consumers[service_id]
                inactive_consumers = consumers - service_roles
                # TODO do something with these...

        for node in event.start:
            if node.is_consumer():
                coro = envelope.consumer_start_event
            else:
                coro = envelope.worker_start_event
            asyncio.async(coro(node, event), loop=self.loop)
        res = (0, "{}".format(event_id))
        return res

    @rpc.method
    @asyncio.coroutine
    def send_item(
            self, envelope_id: str, event_id: str, index: int, data: bytes
    ) -> tuple:
        """Send an item to the XBUS network.

        :param event_id:
         event UUID previously opened onto which this item will be sent

        :param index:
         the item index number.

        :param data:
         the raw data of the item. This data will not be opened or
         interpreted by the bus itself, but forwarded to all the workers and
         ultimately the consumers of the graph.

        :return:
         to be defined
        """
        # if we have an event_id this means we already have a precomputed graph
        # for this event... so lets send the item to the corresponding nodes

        envelope = self.envelopes.get(envelope_id)
        if not envelope:
            res = (1, 'No such envelope')
            return res

        event = envelope.events.get(event_id)
        if not event:
            res = (1, 'No such event')
            return res

        for node in event.start:
            if node.is_consumer():
                coro = envelope.consumer_send_item
            else:
                coro = envelope.worker_send_item
            asyncio.async(
                coro(node, event, [index], data, index), loop=self.loop
            )

        res = (0, "{}".format(event_id))
        return res

    @rpc.method
    @asyncio.coroutine
    def end_event(
            self, envelope_id: str, event_id: str, nb_items: int
    ) -> tuple:
        """Finish an event normally.

        :param event_id:
         the event UUID you previously started

        :return:
         to be defined
        """

        envelope = self.envelopes[envelope_id]
        event = envelope.events.get(event_id)
        if not event:
            res = (1, "No such event")
            return res

        for node in event.start:
            if node.is_consumer():
                coro = envelope.consumer_end_event
            else:
                coro = envelope.worker_end_event
            asyncio.async(coro(node, event, nb_items), loop=self.loop)

        res = (0, event_id)
        return res

    @rpc.method
    @asyncio.coroutine
    def end_envelope(self, envelope_id: str) -> dict:
        """End an envelope normally.

        :param envelope_id:
         the envelope id you want to mark as finished

        :return:
         a dict containing information about the result like so
         {'success': True, 'message': "1200 lines inserted, import_id: 23455"}
        """

        envelope = self.envelopes.get(envelope_id)
        if not envelope:
            res = (1, 'No such envelope')
            return res

        asyncio.async(envelope.async_end_envelope(), loop=self.loop)
        return {
            'success': True,
            'envelope_id': envelope_id,
            'message': 'OK'
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

        envelope = self.envelopes[envelope_id]
        all_nodes = {}
        for event in envelope:
            all_nodes.update(event.nodes)

        for node in all_nodes.values():
            if node['consumer']:
                coro = self.consumer_cancel_envelope
            else:
                coro = self.worker_cancel_envelope
            asyncio.async(
                coro(node, envelope_id),
                loop=self.loop
            )

        return envelope_id

    @asyncio.coroutine
    def get_event_tree(self, type_id: str) -> list:
        """internal helper method used to find all nodes and the links
        between them that constitute the execution tree of an event type.

        See xbus_get_event_tree in xbus_monitor/xbus/monitor/scripts/func.sql

        :param type_id
         the UUID that corresponds to the type of the event.

        :return:
         the event nodes, as a list of 4-tuples containing
         (id, service_id, is_start, [child_id, child_id, ...])
        """
        with (yield from self.dbengine) as conn:
            event_tree = yield from get_event_tree(conn, type_id)
        return event_tree

    @asyncio.coroutine
    def init_consumers(self) -> bool:
        with (yield from self.dbengine) as conn:
            consumer_roles = yield from get_consumer_roles(conn)
        for row in consumer_roles:
            service_id, role_ids = row.as_tuple()
            self.consumers[service_id] = set(role_ids)
        return True

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
            query = select((role.c.id, role.c.password, role.c.service_id))
            query = query.where(role.c.login == login).limit(1)

            cr = yield from conn.execute(query)
            row = yield from cr.first()
            if row:
                return row.as_tuple()
            else:
                return None, None, None


@asyncio.coroutine
def get_backserver(engine_callback, config, socket, b2fsocket, loop=None):
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

    :param socket:
     the event loop the server must run with

    :return:
     a future that is waiting for a closed() call before being
     fired back.
    """
    dbengine = yield from engine_callback(config)
    broker_back = XbusBrokerBack(dbengine, b2fsocket, socket, loop=loop)

    redis_host = config.get('redis', 'host')
    redis_port = config.getint('redis', 'port')

    yield from broker_back.prepare_redis(redis_host, redis_port)
    yield from broker_back.register_on_front()

    zmqserver = yield from rpc.serve_rpc(
        broker_back,
        bind=socket,
        loop=loop,
    )
    yield from zmqserver.wait_closed()


# we don't want our imports to be visible to others...
__all__ = ["XbusBrokerBack", "get_backserver"]
