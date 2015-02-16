# -*- encoding: utf-8 -*-
__author__ = 'jgavrel'

import asyncio
from datetime import datetime
from uuid import uuid4
from sqlalchemy import func
from xbus.broker.model.logging import envelope
from xbus.broker.model.logging import event_error
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
        self.end_event_timeout = 3600
        self.end_envelope_timeout = 3600
        self.stop_envelope_timeout = 60

    def new_event(self, event_id, type_name, type_id):
        """Create a new :class:`.Event` instance and add it to the envelope.

        :param event_id:
         the generated UUID of the event

        :param type_id:
         the internal UUID that corresponds to the type of the event

        :param type_name:
         the name of the type of the started event
        """
        event = Event(
            self.envelope_id,
            event_id,
            type_name,
            type_id,
            self.loop
        )
        self.events[event_id] = event
        return event

    @asyncio.coroutine
    def watch_call(self, call, timeout):
        """Call a coroutine with a timeout. The created :class:`asyncio.Task`
        instance is stored in the Envelope object and will be cancelled if the
        :meth:`stop_envelope` method is called.
        This method was primarily intended to be used for the start_event,
        send_data and end_event RPC calls on workers and consumers.

        :param call:
         a remote call to a worker or consumer's method.

        :param timeout:
         the period of time in seconds after which the call is cancelled.

        :raises asyncio.TimeoutError:
         if the timeout occurs before the call is completed.
        """
        task = asyncio.async(call, loop=self.loop)
        self.client_calls.add(task)
        try:
            res = yield from asyncio.wait_for(task, timeout, loop=self.loop)
            return res
        finally:
            try:
                self.client_calls.remove(task)
            except KeyError:
                pass

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
                self.consumer_end_envelope(node), loop=self.loop
            )
            tasks.append(task)

        for node in worker_nodes:
            asyncio.async(self.worker_end_envelope(node), loop=self.loop)

        res = yield from asyncio.gather(tasks, loop=self.loop)
        if all(res):
            yield from self.update_envelope_state_done()

    @asyncio.coroutine
    def stop_envelope(self, cancelled=False):
        """
        Stops the envelope by cancelling any planned or ongoing RPC call,
        updating the envelope's state in the database, and calling the
        stop_envelope RPC method of every worker and consumer involved.
        :param cancelled:
         True if the envelope has been cancelled by the emitter.
        """
        if self.stopped:
            return
        self.stopped = True

        # Cancel ongoing RPC calls
        for call in self.client_calls:
            call.cancel()

        all_nodes = {}
        # Cancel planned (ie blocked by wait_trigger) RPC calls
        for key, event in self.events.items():
            all_nodes.update(event.nodes)

        # Update the envelope's state, unless the front-end already did so.
        if not cancelled:
            yield from self.update_envelope_state_stopped()

        # Warn the workers and consumers
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

        call = node.recipient.socket.call.start_event(
            self.envelope_id, event.event_id, event.type_name
        )
        try:
            res = yield from self.watch_call(call, self.start_event_timeout)
            success, reply = res
        except (TypeError, ValueError):
            success, reply = False, [([], "Malformed reply to start_event.")]
        except asyncio.TimeoutError:
            success, reply = False, [([], "Worker timed out.")]

        if success:
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
            yield from self.log_event_errors(reply, event, node)
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

        call = node.recipient.socket.call.send_item(
            self.envelope_id, event.event_id, indices, data
        )
        try:
            res = yield from self.watch_call(call, self.send_item_timeout)
            success, reply = res
        except (TypeError, ValueError):
            success, reply = False, [(indices, "Malformed reply data.")]
        except asyncio.TimeoutError:
            success, reply = False, [(indices, "Worker timed out.")]

        if success:
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
            yield from self.log_event_errors(reply, event, node)
            asyncio.async(self.stop_envelope(), loop=self.loop)
            return False

    @asyncio.coroutine
    def worker_end_event(
        self, node, event, nb_items: int, immediate_reply: bool
    ) -> bool:
        """Forward the end of the event to the workers.

        :param node:
         the worker node object

        :param event:
         the event object

        :param nb_items:
         the total number of items sent by the worker's parent

        :param immediate_reply: Whether an immediate reply is expected; refer
        to the "Immediate reply" section of the Xbus documentation for details.

        :return: 2-element tuple:
        - Boolean indicating success (True when succesful).
        - Nothing (reserved for future use).
        """
        trigger_res = yield from node.wait_trigger(nb_items)
        if trigger_res is False or self.stopped:
            return False, None

        call = node.recipient.socket.call.end_event(
            self.envelope_id, event.event_id
        )
        try:
            res = yield from self.watch_call(call, self.end_event_timeout)
            success, reply = res
        except (TypeError, ValueError):
            success, reply = False, [([], "Malformed reply to end_event.")]
        except asyncio.TimeoutError:
            success, reply = False, [([], "Worker timed out.")]

        if success:
            for child_id in node.children:
                child = event[child_id]
                if child.is_consumer:
                    coro = self.consumer_end_event
                else:
                    coro = self.worker_end_event
                asyncio.async(
                    coro(child, event, node.sent, immediate_reply),
                    loop=self.loop
                )
        else:
            yield from self.log_event_errors(reply, event, node)
            asyncio.async(self.stop_envelope(), loop=self.loop)
            return False, None

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

        call = node.recipient.socket.call.end_envelope(self.envelope_id)
        timeout = self.end_envelope_timeout
        try:
            res = yield from asyncio.wait_for(call, timeout, loop=self.loop)
            success, reply = res
        except (TypeError, ValueError):
            success, reply = False, [([], "Malformed reply to end_envelope.")]
        except asyncio.TimeoutError:
            success, reply = False, [([], "Worker timed out.")]

        if success:
            return True
        else:
            yield from self.log_event_errors(reply, None, node)
            return False

    @asyncio.coroutine
    def worker_stop_envelope(self, node) -> bool:
        """Forward the cancellation of the envelope to the workers.

        :param node:
         the worker node object

        :return:
         True if successful, False otherwise
        """
        call = node.recipient.socket.call.stop_envelope(self.envelope_id)
        timeout = self.stop_envelope_timeout
        try:
            yield from asyncio.wait_for(call, timeout, loop=self.loop)
            return True
        except asyncio.TimeoutError:
            return False

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
        for recipient in node.recipients:
            call = recipient.socket.call.start_event(
                self.envelope_id, event.event_id, event.type_name
            )
            corobj = self.watch_call(call, self.start_event_timeout)
            tasks.append(asyncio.async(corobj, loop=self.loop))

        try:
            res = yield from asyncio.gather(*tasks, loop=self.loop)
            errors = [
                reply for success, replies in res if not success
                for reply in replies
            ]
        except (TypeError, ValueError):
            errors = [([], "Malformed reply to end_envelope.")]
        except asyncio.TimeoutError:
            errors = [([], "Consumer timed out.")]
        if not errors:
            node.next_trigger()
            return True
        else:
            yield from self.log_event_errors(errors, event, node)
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
        for recipient in node.recipients:
            call = recipient.socket.call.send_item(
                self.envelope_id, event.event_id, indices, data
            )
            corobj = self.watch_call(call, self.send_item_timeout)
            tasks.append(asyncio.async(corobj, loop=self.loop))

        try:
            res = yield from asyncio.gather(*tasks, loop=self.loop)
            errors = [
                reply for success, replies in res if not success
                for reply in replies
            ]
        except (TypeError, ValueError):
            errors = [(indices, "Malformed reply data.")]
        except asyncio.TimeoutError:
            errors = [([], "Consumer timed out.")]

        if not errors:
            node.next_trigger()
            return True
        else:
            yield from self.log_event_errors(errors, event, node)
            asyncio.async(self.stop_envelope(), loop=self.loop)
            return False

    @asyncio.coroutine
    def consumer_end_event(
        self, node, event, nb_items: int, immediate_reply: bool
    ) -> tuple:
        """Forward the end of the event to the consumers.

        :param node:
         the consumer node object

        :param event:
         the event object

        :param nb_items:
         the total number of items sent by the consumer's parent

        :param immediate_reply: Whether an immediate reply is expected; refer
        to the "Immediate reply" section of the Xbus documentation for details.

        :return: 2-element tuple:
        - Boolean indicating success (True when succesful).
        - Data sent back by the consumer, when using the "immediate reply"
        feature; None otherwise.
        """

        trigger_res = yield from node.wait_trigger(nb_items)
        if trigger_res is False or self.stopped:
            return False, None

        tasks = []
        for recipient in node.recipients:
            call = recipient.socket.call.end_event(
                self.envelope_id, event.event_id
            )
            corobj = self.watch_call(call, self.end_event_timeout)
            tasks.append(asyncio.async(corobj, loop=self.loop))

        reply_data = []
        errors = []
        try:
            reply_data = yield from asyncio.gather(*tasks, loop=self.loop)
            errors = [
                reply
                for success, replies in reply_data
                if not success
                for reply in replies
            ]
        except (TypeError, ValueError):
            errors = [([], "Malformed reply to end_envelope.")]
        except asyncio.TimeoutError:
            errors = [([], "Consumer timed out.")]

        if errors:
            yield from self.log_event_errors(errors, event, node)
            asyncio.async(self.stop_envelope(), loop=self.loop)
            return False, None

        node.done = True

        if self.trigger._callbacks:
            self.trigger.set_result(True)
            self.trigger = asyncio.Future(loop=self.loop)

        # Transmit the first (and only) reply back when using the "immediate
        # reply" feature.
        immediate_reply_data = None
        if immediate_reply:
            first_reply_data = reply_data[0]
            immediate_reply_data = first_reply_data[1]  # (success, data)

        return True, immediate_reply_data

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
        for recipient in node.recipients:
            call = recipient.socket.call.end_envelope(self.envelope_id)
            corobj = self.watch_call(call, self.end_envelope_timeout)
            tasks.append(asyncio.async(corobj, loop=self.loop))

        try:
            res = yield from asyncio.gather(*tasks, loop=self.loop)
            errors = [
                reply for success, replies in res if not success
                for reply in replies
            ]
        except (TypeError, ValueError):
            errors = [([], "Malformed reply to end_envelope.")]
        except asyncio.TimeoutError:
            errors = [([], "Consumer timed out.")]

        if not errors:
            return True
        else:
            yield from self.log_event_errors(errors, None, node)
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

        for recipient in node.recipients:
            corobj = recipient.socket.call.stop_envelope(self.envelope_id)
            asyncio.async(corobj, loop=self.loop)

    @asyncio.coroutine
    def update_envelope_state_done(self):
        """Internal helper method used to log the successful execution of all
        events in the envelope.
        """
        with (yield from self.dbengine) as conn:
            update = envelope.update()
            update = update.where(envelope.c.id == self.envelope_id)
            update = update.values(state='done', done_date=func.localtimestamp)
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

    @asyncio.coroutine
    def log_event_errors(self, errors, event=None, node=None):
        envelope_id = self.envelope_id
        event_id = event.event_id if event else None
        node_id = node.node_id if node else None
        insert = event_error.insert().values([
            dict(
                id=uuid4(), envelope_id=envelope_id, event_id=event_id,
                node_id=node_id, items=items, message=message,
                error_date=datetime.utcnow(), state='unprocessed'
            ) for items, message in self.error_format(errors)
        ])
        with (yield from self.dbengine) as conn:
            yield from conn.execute(insert)

    @staticmethod
    def error_format(errors):
        try:
            errors_iter = iter(errors)
        except TypeError:
            yield (None, "Invalid error format")
            return
        for error in errors_iter:
            try:
                indices, message = error
                items = ','.join(str(i) for i in indices)
                if isinstance(message, str):
                    yield (items, message)
                else:
                    yield (items, "Invalid error message")
            except (TypeError, ValueError):
                yield (None, "Invalid error format")

    def __getitem__(self, key):
        return self.events[key]

    def __setitem__(self, key, value):
        self.events[key] = value
