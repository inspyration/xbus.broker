# -*- encoding: utf-8 -*-
__author__ = 'jgavrel'

import asyncio

from xbus.broker.core.back.recipient import Recipient


class Node(object):
    """a Node instance represents one node in the event datastructure that is
    manipulated by the backend."""

    def __init__(self, envelope_id, event_id, node_id, loop=None):
        """create a new event instance that will be manipulated by the backend,
        it provides a few helper methods and some interesting attributes like
        the event type name and event type id

        :param envelope_id:
         The UUID of then envelope

        :param event_id:
         The UUID of the event

        :param node_id:
         The UUID of the node

        :param loop:
         the event loop used by the backend
        """
        self.envelope_id = envelope_id
        self.event_id = event_id
        self.node_id = node_id
        self.sent = 0
        self.recv = -1
        self.loop = loop
        self.active = False
        self.done = False
        self.trigger = asyncio.Future(loop=loop)

    @asyncio.coroutine
    def wait_trigger(self, index=0) -> bool:
        """A coroutine that waits until the node's recv attribute has reached a
        certain value or until the envelope is cancelled.

        :param index:
         The expected value for the node's recv attribute.
        :returns:
         True if the value has been reached, False if it has been cancelled.
        """

        while self.recv < index:
            trigger_res = yield from self.trigger
            if trigger_res is False:
                return False
        return True

    def next_trigger(self):
        """Increments the recv attribute and causes all pending wait_trigger
        coroutines for this node to reevaluate their condition.
        """

        self.recv += 1
        if self.trigger._callbacks:
            self.trigger.set_result(True)
            self.trigger = asyncio.Future(loop=self.loop)

    def cancel_trigger(self):
        """Cause all pending :meth:`wait_trigger` coroutines to return False.
        """
        self.trigger.set_result(False)


class WorkerNode(Node):

    def __init__(
        self, envelope_id: str, event_id: str, node_id: str, role_id: str,
        recipient: Recipient, children, loop=None
    ):
        """Create a new worker node instance

        :param envelope_id:
         the UUID of then envelope

        :param event_id:
         the UUID of the event

        :param node_id:
         the UUID of the node

        :param role_id:
         the UUID of the role that represents the selected worker.

        :param recipient:
         Information about the worker.

        :param children:
         the UUIDs of the children nodes.

        :param loop:
         the event loop used by the backend
        """
        super(WorkerNode, self).__init__(envelope_id, event_id, node_id, loop)
        self.role_id = role_id
        self.recipient = recipient
        self.children = children

    @staticmethod
    def is_consumer():
        return False


class ConsumerNode(Node):

    def __init__(
        self, envelope_id: str, event_id: str, node_id: str, role_ids: list,
        recipients: list, loop=None
    ):
        """create a new consumer node instance

        :param envelope_id:
         the UUID of then envelope

        :param event_id:
         the UUID of the event

        :param node_id:
         the UUID of the node

        :param role_ids:
         the UUIDs of the roles that represent the listening consumers.

        :param recipients:
         Information about the consumers.
        :type recipients: List of Recipient objects.

        :param loop:
         the event loop used by the backend
        """
        super(ConsumerNode, self).__init__(
            envelope_id, event_id, node_id, loop
        )
        self.role_ids = role_ids
        self.recipients = recipients
        self.done = False

    @staticmethod
    def is_consumer():
        return True
