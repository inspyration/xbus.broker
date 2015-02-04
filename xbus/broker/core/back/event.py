# -*- encoding: utf-8 -*-
__author__ = 'faide'

from xbus.broker.core.back.node import WorkerNode
from xbus.broker.core.back.node import ConsumerNode
from xbus.broker.core.back.recipient import Recipient


class Event(object):
    """An Event instance represents the event datastructure that is manipulated
    by the backend and dispatched to all workers and consumers that need it"""

    def __init__(
        self, envelope_id: str, event_id: str, type_name: str, type_id: str,
        loop=None
    ):
        """Create a new event instance that will be manipulated by the backend,
        it provides a few helper methods and some interesting attributes like
        the event type name and event type id.

        :param envelope_id:
         the UUID of the envelope that contains the event

        :param event_id:
         the generated UUID of the event

        :param type_id:
         the internal UUID that corresponds to the type of the event

        :param type_name:
         the name of the type of the started event

        :param loop:
         the event loop used by the backend

        """
        self.envelope_id = envelope_id
        self.event_id = event_id
        self.type_name = type_name
        self.type_id = type_id
        self.nodes = {}
        self.start = []
        self.loop = loop

    def new_worker(
        self, node_id, role_id, recipient: Recipient, children, is_start
    ):
        """Create a new :class:`.WorkerNode` instance and add it to the event.

        :param node_id:
         the UUID of the worker node

        :param role_id:
         the UUID of the role that represents the selected worker.

        :param recipient:
         Information about the worker.

        :param children:
         the UUIDs of the children nodes.

        :param is_start:
         True if the node has no parent node, false otherwise.
        """
        node = WorkerNode(
            self.envelope_id, self.event_id, node_id, role_id, recipient,
            children, self.loop
        )
        self._add_node(node, is_start)
        return node

    def new_consumer(self, node_id, role_ids, recipients: list, is_start):
        """Create a new :class:`.ConsumerNode` instance and add it to the
        event.

        :param node_id:
         the UUID of the consumer node

        :param role_ids:
         the UUIDs of the roles that represent the listening consumers.

        :param recipients:
         Information about the consumers.
        :type recipients: List of Recipient objects.

        :param is_start:
         True if the node has no parent node, false otherwise.
        """
        node = ConsumerNode(
            self.envelope_id, self.event_id, node_id, role_ids, recipients,
            self.loop
        )
        self._add_node(node, is_start)
        return node

    def _add_node(self, node, is_start):
        """Add a node to the graph of the event.
        """
        self.nodes[node.node_id] = node
        if is_start:
            self.start.append(node)

    def __getitem__(self, key):
        return self.nodes[key]
