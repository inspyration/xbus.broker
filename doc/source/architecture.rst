.. _architecture_overview:

Architecture overview
=====================

Xbus is split into two distinct core components:

  - the frontend :class:`xbus.broker.core.front.XbusBrokerFront`: responsible
    to handle all emitters, talk to them, get their events and acknowledge
    their data as soon as it is safely stored
  - the backend :class:`xbus.broker.core.back.XbusBrokerBack`: responsible to
    forward event data to the network of workers and eventually consumers.


Those two parts speak together transparently and the end-user does not
necessarily sees a difference between the two.

Front and back both have their separate 0mq sockets. Emitters use the front
socket while workers and consumers use the backend socket.

When you start an xbus server it will generally start one frontend and one
backend attached to it.

.. _frontend:

Frontend
--------

:class:`xbus.broker.core.front.XbusBrokerFront` is the component that handles
all emitter connexions and provides the emitter API. It operates on its own
socket (by default listening on TCP/1984

.. _backend:

Backend
-------

:class:`xbus.broker.core.back.XbusBrokerBack` is the component that handles
all worker and consumer connexions. It operates on its own socket (by default
listening on TCP/4891

When a backend instance starts it tries to register itself to a given
frontend by connecting to an internal 0mq socket. The frontend will
acknowlege this and then use the normal backend socket to send all the events
it needs to send.
