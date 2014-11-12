Semantics
=========

Before you are able to connect an emitter to the :ref:`frontend` or a worker
to the :ref:`backend`, you'll need to understand the xbus broker semantics.

The most importants terms are:

  - emitter
  - emitter profile
  - worker
  - consumer
  - service
  - role
  - envelope
  - event type
  - event node

Event
-----

In the Xbus semantics the core of what we transfer between actors of the IT
infrastructure are considered as events. Events are arbitrary collections of
data structures. An event will be received by the frontend and propagated to
all the consumers that have registered to receive it.

Event Type
----------

Each and every event in xbus needs only on thing: an event type. This is only
a  name, but this means a lot: Xbus does not try by itself to assert
anything about the datastructure it transports and forwards. But at the same
time it is necessary for the consumers (receivers) to know what kind of
data they will receive. The event type is that contract. IE: if I say to
the bus that I emit `new_clients` the consumers may rely on the bus to make
sure that the same kind of datastructure will be served to them each time.


Emitter
-------

An emitter is an independant program in your IT infrastructure that needs to
send information about a change, a new item or whatever. In fact anything
