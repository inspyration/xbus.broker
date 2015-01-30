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
  - :ref:`immediate reply <immediate_reply>`

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
data they will receive and how to treat it.
The event type is that contract.  IE: if I say to the bus that I emit
`new_clients` the consumers may rely on the bus to make sure that the same
kind of datastructure will be served to them each time.

.. _envelope:

Envelope
--------

Any :ref:`event <event>` sent into the bus must be enclosed into an envelope.
This is important because the evelope is a transactional unit that permits to
rollback operations at the envelope level if your consumers are transaction
aware.

This really depends on your application layout but you can easily imagine a
simple network that handles `invoices` and a final :ref:`consumer <consumer>`
that will write accounting lines into accounting books. If for `any` reason
the envelope failed in the middle you would want that NO single line was
written in your books. Putting all the `invoice lines` in a single envelope
you ensure that everything in the same envelope will be part of the same
transaction.

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
password pair. An emitter is just that, it does not directly declare what it
wants to emit.

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
must send back a list of items.


.. _consumer:

Consumer
--------

A consumer as a :ref:`worker node <worker>` is still an
independant program that connects to the :ref:`xbus backend <backend>`,
but it is considered as a final node that will not return data for each item
received.

On the contrary it will wait for the end of an envelope to give some kind of
answer to the :ref:`backend <backend>`.


.. _service:

Service
-------

An abstract representation of one or more :ref:`event nodes <event_node>` be
it a :ref:`worker <worker>` or :ref:`consumer <consumer>`. The service is the
link between an event node and one or more concrete workers.

Attached to the service we will find a role, which is the concrete distinct
instance of a :ref:`worker <worker>` or :ref:`consumer <consumer>`.

.. _role:

Role
----

The individual :ref:`worker <worker>` or :ref:`consumer <consumer>`. There is
a separation between :ref:`service <service>` and role because you can
connect many different roles to your bus that will provide the same service.

In effect, once you have described your work graph using a tree of
:ref:`event nodes <event_node>`, each one attached to a distinct service,
you'll be able to spawn as many real workers (programs that provide a
service) that will attach to one service.

The bus will automatically distribute the work between all the roles that
provide the same :ref:`service <service>`.


.. _immediate_reply:

Immediate reply
---------------

:ref:`Emitters <emitter>` of :ref:`events <event>` marked as wanting an
"immediate reply" will wait for a reply from the consumer once they have called
the "end_event" RPC call.

The reply will be sent via the return value of the "end_event" call.

The "immediate reply" flag is an attribute of :ref:`event types <event_type>`.

Note: Immediate replies are disallowed when more than one consumer is available
to the emitter wishing to send events with that flag.
