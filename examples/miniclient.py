# -*- encoding: utf-8 -*-
import asyncio
import aiozmq
from aiozmq import rpc


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
        super(rpc.AttrHandler, self).__init__()

    @asyncio.coroutine
    def start(self):
        client = yield from rpc.connect_rpc(
            connect=self.back_url, loop=self.loop
        )
        ticket = yield from client.call.login(self.login, self.password)
        res = yield from client.call.register_node(ticket, self.url)
        client.close()
        server = yield from rpc.serve_rpc(self, bind=self.url, loop=self.loop)
        return server

    @rpc.method
    @asyncio.coroutine
    def start_event(
        self, envelope_id: str, event_id: str, type_name: str
    ) -> bool:
        return self.do_start_event(type_name)

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
def coro_emitter(front_url: str, login: str, password: str, loop):
    print("Establishing RPC connection...")
    client = yield from rpc.connect_rpc(connect=front_url, loop=loop)
    print("RPC connection OK")

    token = yield from client.call.login(login, password)
    print("Got connection token:", token)
    envelope_id = yield from client.call.start_envelope(token)
    print("Started envelope:", envelope_id)
    event_id = yield from client.call.start_event(
        token, envelope_id, 'test_event', 0
    )
    print("Started event:", event_id)
    yield from client.call.send_item(token, envelope_id, event_id, 0, b'data0')
    print("Sent item: 'data_0'")
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

    loop = aiozmq.ZmqEventLoopPolicy().new_event_loop()
    emitter = coro_emitter(frnt_url, emit_log, emit_pwd, loop)
    worker = coro_worker(work_url, back_url, work_log, work_pwd, loop)
    consumer = coro_consumer(cons_url, back_url, cons_log, cons_pwd, loop)

    loop.run_until_complete(asyncio.gather(worker, consumer, loop=loop))
    loop.run_until_complete(emitter)
    loop.run_forever()
    worker.close()
    consumer.close()


if __name__ == "__main__":
    main()
