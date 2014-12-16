# -*- encoding: utf-8 -*-
__author__ = 'jgavrel'

import asyncio


class Envelope(object):

    def __init__(self, uuid: str, dbengine=None, loop=None):
        self.uuid = uuid
        self.events = {}
        self.dbengine = dbengine
        self.loop = loop
        self.trigger = asyncio.Future(loop=loop)

    @asyncio.coroutine
    def async_end_envelope(self):

        all_nodes = {}
        for key, event in self.events.items():
            if key == 'trigger':
                continue
            all_nodes.update(event.nodes)

        worker_nodes = []
        consumer_nodes = []
        for node in all_nodes.values():
            if node['consumer']:
                consumer_nodes.append(node)
            else:
                worker_nodes.append(node)

        while not all(node.get('done', False) for node in consumer_nodes):
            trigger_res = yield from self.trigger
            if trigger_res is False:
                # TODO: stop the envelope execution
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
            yield from self.update_envelope_state_done(self.uuid)

    @asyncio.coroutine
    def worker_start_event(
            self, node: dict, event_id: str, type_id: str, type_name: str
    ) -> bool:
        """Forward the new event to the workers.

        :param node:
         the worker node

        :param event_id:
         the generated UUID of the event

        :param type_id:
         the internal UUID that corresponds to the type of the event

        :param type_name:
         the name of the type of the started event

        :return:
         True if successful, False otherwise
        """
        worker_id = node['role_id']
        worker = self.node_registry[worker_id]
        event = self.events[event_id]
        res = yield from worker.call.start_event(
            self.envelope_id, event_id, type_name
        )
        if res:
            node['recv'] = 0
            children = node['children']
            for child in children.values():
                if child['consumer']:
                    coro = self.consumer_start_event
                else:
                    coro = self.worker_start_event
                asyncio.async(
                    coro(child, envelope_id, event_id, type_id, type_name),
                    loop=self.loop
                )

            if node['trigger']._callbacks:
                node['trigger'].set_result(True)
                node['trigger'] = asyncio.Future(loop=self.loop)
        else:
            # TODO: stop the envelope execution
            return False

    @asyncio.coroutine
    def worker_send_item(
            self, node: dict, envelope_id: str, event_id: str, indices: list,
            data: bytes, forward_index: int
    ) -> bool:
        """Forward the item to the workers.

        :param node:
         the worker node

        :param envelope_id:
         the UUID of the envelope which contains the event

        :param event_id:
         The UUID of the event

        :param indices:
         the item indices

        :param data:
         the item data

        :return:
         True if successful, False otherwise
        """
        yield from node.wait_trigger(forward_index)
        worker_id = node['role_id']
        worker = self.node_registry[worker_id]
        envelope = self.envelopes[envelope_id]
        event = envelope[event_id]
        reply = yield from worker.call.send_item(
            envelope_id, event_id, indices, data
        )
        if reply:
            children = node['children']
            sent = node['sent']
            for ri, rd in reply:
                for child in children.values():
                    if child['consumer']:
                        coro = self.consumer_send_item
                    else:
                        coro = self.worker_send_item
                    asyncio.async(
                        coro(child, envelope_id, event_id, ri, rd, sent),
                        loop=self.loop
                    )
                sent += 1
            node['sent'] = sent

            node.next_trigger()
            return True
        else:
            # TODO: stop the envelope execution
            return False

    @asyncio.coroutine
    def worker_end_event(
            self, node: dict, envelope_id: str, event_id: str, nb_items: int
    ) -> bool:
        """Forward the end of the event to the workers.

        :param node:
         the worker node

        :param envelope_id:
         the UUID of the envelope which contains the event

        :param event_id:
         the UUID of the event

        :return:
         True if successful, False otherwise
        """
        while node['recv'] < nb_items:
            trigger_res = yield from node['trigger']
            if trigger_res is False:
                # TODO: stop the envelope execution
                return False

        worker_id = node['role_id']
        worker = self.node_registry[worker_id]
        envelope = self.envelopes[envelope_id]
        event = envelope[event_id]
        reply = yield from worker.call.end_event(
            envelope_id, event_id
        )
        if reply:
            children = node['children']
            for child in children.values():
                if child['consumer']:
                    coro = self.consumer_end_event
                else:
                    coro = self.worker_end_event
                asyncio.async(
                    coro(child, envelope_id, event_id, node['sent']),
                    loop=self.loop
                )

        else:
            # TODO: stop the envelope execution
            return False

    @asyncio.coroutine
    def worker_end_envelope(
            self, node: dict, envelope_id: str
    ) -> bool:
        """Forward the end of the envelope to the backend.

        :param node:
         the worker node

        :param envelope_id:
         the UUID of the envelope

        :return:
         True if successful, False otherwise
        """
        worker_id = node['role_id']
        worker = self.node_registry[worker_id]
        envelope = self.envelopes[envelope_id]
        reply = yield from worker.call.end_envelope(envelope_id)
        if reply:
            return True
        else:
            # TODO: stop the envelope execution
            return False

    @asyncio.coroutine
    def worker_cancel_envelope(self, node: dict, envelope_id: str):
        """Forward the cancellation of the envelope to the workers.

        :param node:
         the worker node

        :param envelope_id:
         the UUID of the envelope

        :return:
         True if successful, False otherwise
        """

        # TODO: stop the envelope execution
        pass

    @asyncio.coroutine
    def consumer_start_event(
            self, node: dict, envelope_id: str, event_id: str,
            type_id: str, type_name: str
    ) -> bool:
        """Forward the new event to the consumers.

        :param node:
         the consumer node

        :param envelope_id:
         the UUID of the envelope which contains the event

        :param event_id:
         the generated UUID of the event

        :param type_id:
         the internal UUID that corresponds to the type of the event

        :param type_name:
         the name of the type of the started event

        :return:
         True if successful, False otherwise
        """
        consumer_ids = node['role_ids']
        tasks = []
        envelope = self.envelopes[envelope_id]
        event = envelope[event_id]
        for consumer_id in consumer_ids:
            consumer = self.node_registry[consumer_id]
            task = asyncio.async(
                consumer.call.start_event(envelope_id, event_id, type_name),
                loop=self.loop
            )
            tasks.append(task)

        res = yield from asyncio.gather(*tasks, loop=self.loop)

        if all(res):
            node['recv'] = 0
            if node['trigger']._callbacks:
                node['trigger'].set_result(True)
                node['trigger'] = asyncio.Future(loop=self.loop)
            return True
        else:
            # TODO: stop the envelope execution
            return False

    @asyncio.coroutine
    def consumer_send_item(
            self, node: dict, envelope_id: str, event_id: str, indices: list,
            data: bytes, forward_index: int
    ) -> bool:
        """Forward the item to the consumers.

        :param node:
         the consumer node

         :param envelope_id:
          the UUID of the envelope which contains the event

        :param event_id:
         The UUID of the event

        :param indices:
         the item indices

        :param data:
         the item data

        :return:
         True if successful, False otherwise
        """
        while node['recv'] < forward_index:
            trigger_res = yield from node['trigger']
            if trigger_res is False:
                # TODO: stop the envelope execution
                return False

        consumer_ids = node['role_ids']
        tasks = []
        envelope = self.envelopes[envelope_id]
        event = envelope[event_id]
        for consumer_id in consumer_ids:
            consumer = self.node_registry[consumer_id]
            task = asyncio.async(
                consumer.call.send_item(envelope_id, event_id, indices, data),
                loop=self.loop
            )
            tasks.append(task)

        res = yield from asyncio.gather(*tasks, loop=self.loop)

        if all(res):  # TODO: actual condition
            node['recv'] += 1
            if node['trigger']._callbacks:
                node['trigger'].set_result(True)
                node['trigger'] = asyncio.Future(loop=self.loop)
            return True
        else:
            # TODO: stop the envelope execution
            return False

    @asyncio.coroutine
    def consumer_end_event(
            self, node: dict, envelope_id: str, event_id: str, nb_items: int
    ) -> bool:
        """Forward the end of the event to the consumers.

        :param node:
         the consumer node

        :param envelope_id:
         the UUID of the envelope which contains the event

        :param event_id:
         the UUID of the event

        :return:
         True if successful, False otherwise
        """
        while node['recv'] < nb_items:
            trigger_res = yield from node['trigger']
            if trigger_res is False:
                # TODO: stop the envelope execution
                return False

        consumer_ids = node['role_ids']
        tasks = []
        envelope = self.envelopes[envelope_id]
        event = envelope[event_id]
        for consumer_id in consumer_ids:
            consumer = self.node_registry[consumer_id]
            task = asyncio.async(
                consumer.call.end_event(envelope_id, event_id),
                loop=self.loop
            )
            tasks.append(task)

        res = yield from asyncio.gather(*tasks, loop=self.loop)

        if all(res):
            node['done'] = True
            if envelope.trigger._callbacks:
                envelope.trigger.set_result(True)
                envelope.trigger = asyncio.Future(loop=self.loop)
            return True
        else:
            # TODO: stop the envelope execution
            return False

    @asyncio.coroutine
    def consumer_end_envelope(
            self, node: dict, envelope_id: str
    ) -> bool:
        """Forward the end of the envelope to the consumers.

        :param node:
         the consumer node

        :param envelope_id:
         the UUID of the envelope

        :return:
         True if successful, False otherwise
        """
        consumer_ids = node['role_ids']
        tasks = []
        for consumer_id in consumer_ids:
            consumer = self.node_registry[consumer_id]
            envelope = self.envelopes[envelope_id]
            task = asyncio.async(
                consumer.call.end_envelope(envelope_id),
                loop=self.loop
            )
            tasks.append(task)

        res = yield from asyncio.gather(*tasks, loop=self.loop)
        if all(res):
            return True
        else:
            # TODO: stop the envelope execution
            return False

    @asyncio.coroutine
    def consumer_cancel_envelope(self, node: dict, envelope_id: str):
        """Forward the cancellation of the envelope to the consumers.

        :param node:
         the consumer node

        :param envelope_id:
         the UUID of the envelope

        :return:
         True if successful, False otherwise
        """

        # TODO: stop the envelope execution
        pass


    def __getitem__(self, key):
        return self.events[key]

    def __setitem__(self, key, value):
        self.events[key] = value
