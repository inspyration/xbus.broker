# -*- encoding: utf-8 -*-
__author__ = 'faide'


class Event(object):
    """an Event instance represents the event datastructure that is manipulated
    by the backend and dispatched to all workers and consumers that need it"""

    def __init__(self, uuid: str, type_name: str, type_id: str):
        """create a new event instance that will be manipulated by the backend,
        it provides a few helper methods and some interesting attributes like
        the event type name and event type id
        """
        self.uuid = uuid
        self.type_name = type_name
        self.type_id = type_id
