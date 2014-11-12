# -*- encoding: utf-8 -*-
import asyncio
import aiozmq
import aiozmq.rpc


@asyncio.coroutine
def go():
    print("Establishing RPC connection...")
    client = yield from aiozmq.rpc.connect_rpc(connect='tcp://127.0.0.1:1984')
    print("RPC connection OK")

    token = yield from client.call.login('test_emitter', 'password')
    print("Got connection token:", token)
    envelope_id = yield from client.call.start_envelope(token)
    print("Started envelope:", envelope_id)
    event_id = yield from client.call.start_event(
        token, envelope_id, 'test_event', 0
    )
    print("Started event:", event_id)
    yield from client.call.end_event(token, envelope_id, event_id)
    print("Ended event:", event_id)
    yield from client.call.end_envelope(token, envelope_id)
    print("Ended envelope:", envelope_id)

    client.close()


def main():
    asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())
    asyncio.get_event_loop().run_until_complete(go())


if __name__ == "__main__":
    main()
