# -*- encoding: utf-8 -*-
import asyncio
import aiozmq
import aiozmq.rpc


@asyncio.coroutine
def go():
    client = yield from aiozmq.rpc.connect_rpc(connect='tcp://127.0.0.1:1984')

    #arg1 = 1
    #arg2 = 2
    #ret = yield from client.call.remote_add(1, 2)
    #print("{} + {} = {}".format(arg1, arg2, ret))

    ret = yield from client.call.list_users()
    #print(type(ret))
    #print("{}".format(ret))
    for user in ret:
        print("User uuid:{}, user name: {}".format(user[0], user[1]))

    client.close()


def main():
    asyncio.set_event_loop_policy(aiozmq.ZmqEventLoopPolicy())
    asyncio.get_event_loop().run_until_complete(go())


if __name__ == "__main__":
    main()
