# -*- encoding: utf-8 -*-
__author__ = 'faide'

from xbus.broker.core.back.node import WorkerNode
from xbus.broker.core.back.node import ConsumerNode


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
         the event loop for the backend

        """
        self.envelope_id = envelope_id
        self.event_id = event_id
        self.type_name = type_name
        self.type_id = type_id
        self.nodes = {}
        self.start = []
        self.loop = loop

    def new_worker(self, node_id, role_id, client, child_id, is_start):
        node = WorkerNode(
            self.envelope_id, self.event_id, node_id, role_id, client,
            child_id, self.loop
        )
        self._add_node(node, is_start)
        return node

    def new_consumer(self, node_id, role_ids, clients, is_start):
        node = ConsumerNode(
            self.envelope_id, self.event_id, node_id, role_ids, clients,
            self.loop
        )
        self._add_node(node, is_start)
        return node

    def _add_node(self, node, is_start):
        self.nodes[node.node_id] = node
        if is_start:
            self.start.append(node)

    def __getitem__(self, key):
        return self.nodes[key]
