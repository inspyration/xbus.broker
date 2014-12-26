# -*- encoding: utf-8 -*-
__author__ = 'jgavrel'

import asyncio
from xbus.broker.model.logging import envelope
from xbus.broker.core.back.event import Event


class Envelope(object):
    """An Envelope instance represents a transactional unit and controls its
    execution through the network. It can contain several events."""

    def __init__(self, envelope_id: str, dbengine=None, loop=None):
        """Initializes a new Envelope instance.

        :param envelope_id:
         the UUID of the envelope

        :param dbengine:
         the database engine

        :param loop:
         the event loop used by the backend
        """
        self.envelope_id = envelope_id
        self.client_calls = set()
        self.events = {}
        self.dbengine = dbengine
        self.loop = loop
        self.stopped = False
        self.trigger = asyncio.Future(loop=loop)
        self.start_event_timeout = 60
        self.send_item_timeout = 60
        self.end_event_timeout = 60
        self.end_envelope_timeout = 60

    def new_event(self, event_id, type_name, type_id):
        """Create a new :class:`.Event` instance and add it to the envelope.

        :param event_id:
         the generated UUID of the event

        :param type_id:
         the internal UUID that corresponds to the type of the event

        :param type_name:
         the name of the type of the started event
        """
        event = Event(self.envelope_id, event_id, type_name, type_id, self.loop)
        self.events[event_id] = event
        return event

    @asyncio.coroutine
    def watch_call(self, call, timeout):
        """
        :param call:
        :param timeout:
        """
        task = asyncio.async(call, loop=self.loop)
        self.client_calls.add(task)
        try:
            res = yield from asyncio.wait_for(task, timeout, loop=self.loop)
            self.client_calls.remove(task)
            return res
        except asyncio.TimeoutError as e:
            asyncio.async(self.stop_envelope(), loop=self.loop)
            raise e

    @asyncio.coroutine
    def end_envelope(self):
        """Wait until every event in the envelope is fully treated, then
        signal the end of envelope to the workers & consumers of all events.

        :return:
         None
        """

        all_nodes = {}
        for key, event in self.events.items():
            all_nodes.update(event.nodes)

        worker_nodes = []
        consumer_nodes = []
        for node in all_nodes.values():
            if node.is_consumer():
                consumer_nodes.append(node)
            else:
                worker_nodes.append(node)

        while not all(node.done for node in consumer_nodes):
            trigger_res = yield from self.trigger
            if trigger_res is False:
                return False

        tasks = []

        for node in consumer_nodes:
            task = asyncio.async(
                self.consumer_end_envelope(node),
                loop=self.loop
            )
            tasks.append(task)

        for node in worker_nodes:
            asyncio.async(
                self.worker_end_envelope(node),
                loop=self.loop
            )

        res = yield from asyncio.gather(tasks, loop=self.loop)
        if all(res):
            yield from self.update_envelope_state_done()

    @asyncio.coroutine
    def stop_envelope(self, cancelled=False):
        """
        :param cancelled:
         True if the envelope has been cancelled by the emitter.
        """
        if self.stopped:
            return
        self.stopped = True

        for call in self.client_calls:
            call.cancel()

        all_nodes = {}
        for key, event in self.events.items():
            all_nodes.update(event.nodes)

        if not cancelled:
            yield from self.update_envelope_state_stopped()

        for node in all_nodes.values():
            node.cancel_trigger()
            if node.is_consumer():
                coro = self.consumer_stop_envelope
            else:
                coro = self.worker_stop_envelope
            asyncio.async(coro(node), loop=self.loop)

    @asyncio.coroutine
    def worker_start_event(self, node, event) -> bool:
        """Forward the new event to the workers.

        :param node:
         the worker node object

        :param event:
         the event object

        :return:
         True if successful, False otherwise
        """
        if self.stopped:
            return False

        call = node.client.call.start_event(
            self.envelope_id, event.event_id, event.type_name
        )
        res = yield from self.watch_call(call, self.start_event_timeout)
        if res:
            for child_id in node.children:
                child = event[child_id]
                if child.is_consumer():
                    coro = self.consumer_start_event
                else:
                    coro = self.worker_start_event
                asyncio.async(coro(child, event), loop=self.loop)

            node.next_trigger()
            return True

        else:
            asyncio.async(self.stop_envelope(), loop=self.loop)
            return False

    @asyncio.coroutine
    def worker_send_item(
            self, node, event, indices: list, data: bytes, forward_index: int
    ) -> bool:
        """Forward the item to the workers.

        :param node:
         the worker node object

        :param event:
         the event object

        :param indices:
         the item indices

        :param data:
         the item data

        :param forward_index:
         an index that corresponds to the ordering of the items sent by the
         worker's parent.

        :return:
         True if successful, False otherwise
        """
        trigger_res = yield from node.wait_trigger(forward_index)
        if trigger_res is False or self.stopped:
            return False

        call = node.client.call.send_item(
            self.envelope_id, event.event_id, indices, data
        )
        reply = yield from self.watch_call(call, self.send_item_timeout)
        if reply:
            for child_id in node.children:
                child = event[child_id]
                for i, (rep_indices, rep_data) in enumerate(reply):
                    if child.is_consumer():
                        coro = self.consumer_send_item
                    else:
                        coro = self.worker_send_item
                    asyncio.async(
                        coro(child, event, rep_indices, rep_data, node.sent),
                        loop=self.loop
                    )
                node.sent += 1

            node.next_trigger()
            return True

        else:
            asyncio.async(self.stop_envelope(), loop=self.loop)
            return False

    @asyncio.coroutine
    def worker_end_event(self, node, event, nb_items: int) -> bool:
        """Forward the end of the event to the workers.

        :param node:
         the worker node object

        :param event:
         the event object

        :param nb_items:
         the total number of items sent by the worker's parent

        :return:
         True if successful, False otherwise
        """
        trigger_res = yield from node.wait_trigger(nb_items)
        if trigger_res is False or self.stopped:
            return False

        call = node.client.call.end_event(self.envelope_id, event.event_id)
        reply = yield from self.watch_call(call, self.end_event_timeout)
        if reply:
            for child_id in node.children:
                child = event[child_id]
                if child.is_consumer:
                    coro = self.consumer_end_event
                else:
                    coro = self.worker_end_event
                asyncio.async(
                    coro(child, event, node.sent), loop=self.loop
                )

        else:
            asyncio.async(self.stop_envelope(), loop=self.loop)
            return False

    @asyncio.coroutine
    def worker_end_envelope(self, node) -> bool:
        """Forward the end of the envelope to the backend.

        :param node:
         the worker node object

        :return:
         True if successful, False otherwise
        """
        if self.stopped:
            return False

        call = node.client.call.end_envelope(self.envelope_id)
        reply = yield from self.watch_call(call, self.end_envelope_timeout)
        if reply:
            return True
        else:
            asyncio.async(self.stop_envelope(), loop=self.loop)
            return False

    @asyncio.coroutine
    def worker_stop_envelope(self, node):
        """Forward the cancellation of the envelope to the workers.

        :param node:
         the worker node object

        :return:
         True if successful, False otherwise
        """
        corobj = node.client.call.stop_envelope(self.envelope_id)
        asyncio.async(corobj, loop=self.loop)

    @asyncio.coroutine
    def consumer_start_event(self, node, event) -> bool:
        """Forward the new event to the consumers.

        :param node:
         the consumer node object

        :param event:
         the event object

        :return:
         True if successful, False otherwise
        """
        if self.stopped:
            return False

        tasks = []
        for client in node.clients:
            call = client.call.start_event(
                self.envelope_id, event.event_id, event.type_name
            )
            corobj = self.watch_call(call, self.start_event_timeout)
            tasks.append(asyncio.async(corobj, loop=self.loop))

        res = yield from asyncio.gather(*tasks, loop=self.loop)
        if all(res):
            node.next_trigger()
            return True
        else:
            asyncio.async(self.stop_envelope(), loop=self.loop)

    @asyncio.coroutine
    def consumer_send_item(
            self, node, event, indices: list, data: bytes, forward_index: int
    ) -> bool:
        """Forward the item to the consumers.

        :param node:
         the consumer node object

        :param event:
         the event object

        :param indices:
         the item indices

        :param data:
         the item data

        :param forward_index:
         an index that corresponds to the ordering of the items sent by the
         consumer's parent.

        :return:
         True if successful, False otherwise
        """
        trigger_res = yield from node.wait_trigger(forward_index)
        if trigger_res is False or self.stopped:
            return False

        tasks = []
        for client in node.clients:
            call = client.call.send_item(
                self.envelope_id, event.event_id, indices, data
            )
            corobj = self.watch_call(call, self.send_item_timeout)
            tasks.append(asyncio.async(corobj, loop=self.loop))

        res = yield from asyncio.gather(*tasks, loop=self.loop)
        if all(res):
            node.next_trigger()
            return True
        else:
            asyncio.async(self.stop_envelope(), loop=self.loop)
            return False

    @asyncio.coroutine
    def consumer_end_event(self, node, event, nb_items: int) -> bool:
        """Forward the end of the event to the consumers.

        :param node:
         the consumer node object

        :param event:
         the event object

        :param nb_items:
         the total number of items sent by the consumer's parent

        :return:
         True if successful, False otherwise
        """
        trigger_res = yield from node.wait_trigger(nb_items)
        if trigger_res is False or self.stopped:
            return False

        tasks = []
        for client in node.clients:
            call = client.call.end_event(self.envelope_id, event.event_id)
            corobj = self.watch_call(call, self.end_event_timeout)
            tasks.append(asyncio.async(corobj, loop=self.loop))

        res = yield from asyncio.gather(*tasks, loop=self.loop)
        if all(res):
            node.done = True
            if self.trigger._callbacks:
                self.trigger.set_result(True)
                self.trigger = asyncio.Future(loop=self.loop)
            return True
        else:
            asyncio.async(self.stop_envelope(), loop=self.loop)
            return False

    @asyncio.coroutine
    def consumer_end_envelope(self, node) -> bool:
        """Forward the end of the envelope to the consumers.

        :param node:
         the consumer node object

        :return:
         True if successful, False otherwise
        """
        if self.stopped:
            return False

        tasks = []
        for client in node.clients:
            call = client.call.end_envelope(self.envelope_id)
            corobj = self.watch_call(call, self.end_envelope_timeout)
            tasks.append(asyncio.async(corobj, loop=self.loop))

        res = yield from asyncio.gather(*tasks, loop=self.loop)
        if all(res):
            return True
        else:
            asyncio.async(self.stop_envelope(), loop=self.loop)
            return False

    @asyncio.coroutine
    def consumer_stop_envelope(self, node):
        """Forward the cancellation of the envelope to the consumers.

        :param node:
         the consumer node object

        :return:
         True if successful, False otherwise
        """

        for client in node.clients:
            corobj = client.call.stop_envelope(self.envelope_id)
            asyncio.async(corobj, loop=self.loop)

    @asyncio.coroutine
    def update_envelope_state_done(self):
        """Internal helper method used to log the successful execution of all
        events in the envelope.
        """
        with (yield from self.dbengine) as conn:
            update = envelope.update()
            update = update.where(envelope.c.id == self.envelope_id)
            update = update.values(state='done')
            yield from conn.execute(update)

    @asyncio.coroutine
    def update_envelope_state_stopped(self):
        """Internal helper method used to log the successful execution of all
        events in the envelope.
        """
        with (yield from self.dbengine) as conn:
            update = envelope.update()
            update = update.where(envelope.c.id == self.envelope_id)
            update = update.values(state='stop')
            yield from conn.execute(update)

    def __getitem__(self, key):
        return self.events[key]

    def __setitem__(self, key, value):
        self.events[key] = value
