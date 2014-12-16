# -*- encoding: utf-8 -*-
__author__ = 'jgavrel'

import asyncio


class Node(object):
    """a Node instance represents one node in the event datastructure that is
    manipulated by the backend."""

    def __init__(self, envelope_id, event_id, loop=None):
        """create a new event instance that will be manipulated by the backend,
        it provides a few helper methods and some interesting attributes like
        the event type name and event type id
        """
        self.envelope_id = envelope_id
        self.event_id = event_id
        self.uuid = None
        self.sent = -1
        self.recv = -1
        self.loop = loop
        self.active = False
        self.done = False
        self.trigger = asyncio.Future(loop=loop)

    def wait_trigger(self, index=0):

        while self.recv < index:
            trigger_res = yield from self.trigger
            if trigger_res is False:
                return False
        return True

    def next_trigger(self):

        self.recv += 1
        if self.trigger._callbacks:
            self.trigger.set_result(True)
            self.trigger = asyncio.Future(loop=self.loop)


class WorkerNode(Node):

    def __init__(
        self, uuid: str, node_id: str, client, role_id, children, loop=None
    ):

        super(WorkerNode, self).__init__(uuid, node_id, client, loop)
        self.role_id = role_id
        self.children = children

    @staticmethod
    def is_consumer():
        return False


class ConsumerNode(Node):

    def __init__(self, uuid: str, node_id: str, client, role_ids, loop=None):

        super(ConsumerNode, self).__init__(uuid, node_id, client, loop)
        self.role_ids = role_ids

    @staticmethod
    def is_consumer():
        return True
