Semantics
=========

Before you are able to connect an emitter to the :ref:`frontend <frontend>`
or a worker to the :ref:`backend <backend>`, you'll need to understand the xbus
broker
semantics.

The most importants terms are:

  - :ref:`event <event>`
  - :ref:`event type <event_type>`
  - :ref:`event node <event_node>`
  - :ref:`emitter <emitter>`
  - :ref:`emitter profile <emitter_profile>`
  - :ref:`worker <worker>`
  - :ref:`consumer <consumer>`
  - :ref:`service <service>`
  - :ref:`role <role>`
  - :ref:`envelope <envelope>`

.. _event:

Event
-----

In the Xbus semantics the core of what we transfer between actors of the IT
infrastructure are considered as events. Events are arbitrary collections of
data structures. An event will be received by the frontend and propagated to
all the consumers that have registered to receive it.

.. _event_type:

Event Type
----------

Each and every event in xbus needs only on thing: an event type. This is only
a name, but this means a lot: Xbus does not try by itself to assert
anything about the datastructure it transports and forwards. But at the same
time it is necessary for the consumers (receivers) to know what kind of
data they will receive. The event type is that contract. IE: if I say to
the bus that I emit `new_clients` the consumers may rely on the bus to make
sure that the same kind of datastructure will be served to them each time.


.. _event_node:

Event Node
----------

Internally we use the term `event node` to describe a node in our graph that
will handle an event. This is specifically used in the backend part of the
broker and refers to eitheir a worker or a consumer


.. _emitter:

Emitter
-------

An emitter is an independant program in your IT infrastructure that needs to
send information about a change, a new item or whatever. In the internal Xbus
database each emitter is assigned an emitter row that contains its login /
password pair. An emitter is just that, it does not directly declares what is
wants to listen to.

This is declared by the Xbus administrator using :ref:`emitter profiles
<emitter_profile>`

The emitter however declares what profile it is using.

.. _emitter_profile:

Emitter Profile
---------------

A profile is used to link one or more emitters to a list of allowed
:ref:`event types <event_type>`

An :ref:`emitter <emitter>` can only emit the type of events that are linked
to its profile. Xbus will refuse any other event type.

.. _worker:

Worker
------

A worker is an independant program that connects to the xbus
:ref:`backend <backend>` and declares itself ready to handle events as they
are emitted in the network.

It is important to understand that a worker is not intended to be used as a
final node of a graph but instead as an intermediate node that will process
data, transform or enrich it and then return it back to the broker.

The contract between a worker and the :ref:`xbus backend <backend>` is that
the bus will send all items of an event down to a worker and that the worker
must send back some item (modified or not)


.. _consumer:

Consumer
--------

A consumer on the contrary of a :ref:`worker node <worker>` is still an
independant program that connects to the :ref:`xbus backend <backend>`,
but it is considered as a final node that will not return data for each item
received.

On the contrary it will wait for the end of an envelope to give some kind of
answer to the :ref:`backend <backend>`.


.. _service:

Service
-------

TBD

.. _role:

Role
----

TBD

.. _envelope:

Envelope
--------

TBD
