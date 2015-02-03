Data clearing Xbus feature
==========================

This document describes the "data clearing" feature Xbus recipient nodes may
implement.

If they do, they must appropriately answer the "has_clearing" API call (see the
section of the Xbus documentation describing Xbus recipient API calls for
details).


Feature dependencies
--------------------

Xbus recipient nodes providing data clearing MUST also support:

- Immediate replies.


Database schema
---------------

A database must be available and initialized with the schema described below.

TODO


Monitor-consumer communication
------------------------------

This section describes how the Xbus monitor and Xbus recipient nodes providing
data clearing communicate.

For general duties, the Xbus monitor directly accesses the database announced
by Xbus recipient node providing data clearing.

Certain specific operations, however, happen via requests emitted through the
Xbus broker.

- Theses requests are enclosed into regular Xbus envelopes / events / items.
- The requests use the "immediate reply" feature (so a specific event type).
- The Xbus monitor is the emitter of these requests.
- Xbus recipient nodes providing data clearing are consumers of these requests.

Each data blob sent in "send_item" calls is a dictionary with an "action" key,
referencing one of the following actions:

- "get_item_details": Provide details about a data clearing item.

  Compulsory dictionary keys:

  * item_id: ID of the data clearing item to clear.

- "clear_items": "Clear" a data clearing item.
  Compulsory dictionary keys:

  * item_id: ID of the data clearing item to clear.

  * values.
