# -*- encoding: utf-8 -*-
import asyncio
import aiozmq
import multiprocessing
import time
import traceback
from aiozmq import rpc


def debug(func):
    """Add this decorator to print exceptions raised by RPC calls.
    It must be placed after the asyncio.coroutine and rpc.method decorators.
    """
    def _debug(*a, **k):
        try:
            return func(*a, **k)
        except Exception as e:
            traceback.print_exc()
            raise e
    return _debug


class XBusBackClient(rpc.AttrHandler):

    def __init__(
        self, url: str, back_url: str, login: str, password: str, loop=None
    ):
        self.url = url
        self.back_url = back_url
        self.login = login
        self.password = password
        if loop is None:
            loop = aiozmq.ZmqEventLoopPolicy().new_event_loop()
        self.loop = loop
        self.client = None
        self.token = None
        super(rpc.AttrHandler, self).__init__()

    @asyncio.coroutine
    def start(self):
        self.client = yield from rpc.connect_rpc(
            connect=self.back_url, loop=self.loop
        )
        self.token = yield from self.client.call.login(
            self.login, self.password
        )
        res = yield from self.client.call.register_node(self.token, self.url)
        server = yield from rpc.serve_rpc(self, bind=self.url, loop=self.loop)
        return server

    @rpc.method
    @asyncio.coroutine
    def start_event(
        self, envelope_id: str, event_id: str, type_name: str
    ) -> bool:
        res = self.do_start_event(type_name)
        return res

    @rpc.method
    @asyncio.coroutine
    def send_item(
        self, envelope_id: str, event_id: str, indices: list, data: bytes
    ) -> list:
        return self.do_send_item(indices, data)

    @rpc.method
    @asyncio.coroutine
    def end_event(self, envelope_id: str, event_id: str) -> bool:
        return self.do_end_event()

    @rpc.method
    @asyncio.coroutine
    def end_envelope(self, envelope_id: str) -> bool:
        return self.do_end_envelope()

    def do_start_event(self, type_name: str) -> bool:
        return True

    def do_send_item(self, indices: list, data: bytes) -> list:
        return [(indices, data)]

    def do_end_event(self) -> bool:
        return True

    def do_end_envelope(self) -> bool:
        return True


class Worker(XBusBackClient):

    @rpc.method
    @asyncio.coroutine
    def start_event(
        self, envelope_id: str, event_id: str, type_name: str
    ) -> bool:
        ready = self.client.call.ready(self.token)
        asyncio.async(ready, loop=self.loop)
        return super(Worker, self).start_event(
            envelope_id, event_id, type_name
        )

    def do_start_event(self, event_type) -> bool:
        print('Worker: start event of type:', event_type)
        return True

    def do_send_item(self, indices: list, data: bytes) -> list:
        print('Worker: received', data)
        data += b'_WORK'
        return [(indices, data)]

    def do_end_event(self) -> bool:
        print('Worker: end event')
        return True

    def do_end_envelope(self) -> bool:
        print('Worker: end envelope')
        return True


class Consumer(XBusBackClient):

    def do_start_event(self, event_type) -> bool:
        print('Consumer: start event of type:', event_type)
        return True

    def do_send_item(self, indices: list, data: bytes) -> list:
        print('Consumer: received', data)
        return []

    def do_end_event(self) -> bool:
        print('Consumer: end event')
        return True

    def do_end_envelope(self) -> bool:
        print('Consumer: end envelope')
        return True


@asyncio.coroutine
def coro_consumer(
    consumer_url: str, back_url: str, login: str, password: str, loop
):
    consumer_rpc = Consumer(consumer_url, back_url, login, password, loop)
    consumer_server = yield from consumer_rpc.start()
    return consumer_server


@asyncio.coroutine
def coro_worker(
    worker_url: str, back_url: str, login: str, password: str, loop
):
    worker_rpc = Worker(worker_url, back_url, login, password, loop)
    worker_server = yield from worker_rpc.start()
    return worker_server


@asyncio.coroutine
def coro_emitter(
        front_url: str, login: str, password: str, nb_envelopes: int,
        nb_items: int, loop
    ):
    print("Establishing RPC connection...")
    client = yield from rpc.connect_rpc(connect=front_url, loop=loop)
    print("RPC connection OK")
    token = yield from client.call.login(login, password)
    print("Got connection token:", token)

    for _ in range(nb_envelopes):
        envelope_id = yield from client.call.start_envelope(token)
        print("Started envelope:", envelope_id)
        event_id = yield from client.call.start_event(
            token, envelope_id, 'test_event', 0
        )
        print("Started event:", event_id)
        print("Sending {} items...".format(nb_items))
        for i in range(nb_items):
            yield from client.call.send_item(
                token, envelope_id, event_id, b'data' + str(i).encode()
            )
        print("Sent {} items".format(nb_items))
        yield from client.call.end_event(token, envelope_id, event_id)
        print("Ended event:", event_id)
        yield from client.call.end_envelope(token, envelope_id)
        print("Ended envelope:", envelope_id)

    client.close()


def main():
    frnt_url = 'tcp://127.0.0.1:1984'
    cons_url = 'tcp://127.0.0.1:9148'
    work_url = 'tcp://127.0.0.1:8419'
    back_url = 'tcp://127.0.0.1:4891'
    emit_log = 'test_emitter'
    emit_pwd = 'password'
    work_log = 'worker_role'
    work_pwd = 'password'
    cons_log = 'consumer_role'
    cons_pwd = 'password'
    multiprocess = True

    loop = aiozmq.ZmqEventLoopPolicy().new_event_loop()
    if multiprocess:
        emit_loop = loop
        work_loop = aiozmq.ZmqEventLoopPolicy().new_event_loop()
        cons_loop = aiozmq.ZmqEventLoopPolicy().new_event_loop()
    else:
        work_loop = cons_loop = emit_loop = loop
    emitter = coro_emitter(frnt_url, emit_log, emit_pwd, 5, 1000, emit_loop)
    worker = coro_worker(work_url, back_url, work_log, work_pwd, work_loop)
    consumer = coro_consumer(cons_url, back_url, cons_log, cons_pwd, cons_loop)

    if multiprocess:
        asyncio.async(emitter, loop=emit_loop)
        asyncio.async(worker, loop=work_loop)
        asyncio.async(consumer, loop=cons_loop)

        work_run_proc = multiprocessing.Process(target=work_loop.run_forever)
        cons_run_proc = multiprocessing.Process(target=cons_loop.run_forever)
        time.sleep(1)
        emit_run_proc = multiprocessing.Process(target=emit_loop.run_forever)

        emit_run_proc.start()
        work_run_proc.start()
        cons_run_proc.start()

    else:
        loop.run_until_complete(asyncio.gather(worker, consumer, loop=loop))
        loop.run_until_complete(emitter)
        loop.run_forever()
        worker.close()
        consumer.close()


if __name__ == "__main__":
    main()
