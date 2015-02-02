Xbus recipient API
==================

Description of the API Xbus recipients must implement in order to register into
an Xbus network.

Version of this document: 0.1.

Methods described in this document:

- get_metadata
- ping
- has_clearing
- has_immediate_reply
- start_event
- send_item
- end_event
- end_envelope
- stop_envelope


get_metadata
------------

Required.

Called to ask for information about the recipient.

Parameters: None.

Returns: A dictionary.

Required return dictionary keys:

- name (string): Name of the recipient.
- version (float): Version of the recipient.
- api_version (float): Version of the Xbus recipient API.
- host (string): Host name of the server hosting the recipient.
- start_date (string): ISO 8601 date-time of When the recipient was started.
- local_time (string): ISO 8601 time on the recipient server.


Optional return dictionary keys:

- locale (string): Locale code, in a format specified by BCP 47
  <http://tools.ietf.org/html/bcp47>.


ping
----

Required.

Called when Xbus wants to check whether the recipient is up.

Parameters:

- token: String that must be sent back.

Returns: The token string sent as parameter.


has_clearing
------------

Required.

Called to determine whether the recipient supports the "data clearing" feature;
and if it does, to get more information about that process.

Parameters: None.

Returns: 2-element tuple:

- Boolean indicating whether the feature is supported.
- URL of the data clearing database (or nothing if the feature is not
  supported). The database must respect the schema described in the
  "Data clearing" section of the Xbus documentation.


has_immediate_reply
-------------------

Required.

Called to determine whether the recipient supports the "immediate reply"
feature.

Parameters: None.

Returns: 1-element tuple:

- Boolean indicating whether the feature is supported.


start_event
-----------

Required.

Called when a new event is available.

Parameters:

- envelope_id: [TODO] String.
- event_id: [TODO] String.
- type_name: [TODO] String.

Returns: [TODO] tuple.


send_item
---------

Required.

Called to send the recipient an item.

Parameters:

- envelope_id: [TODO] String.
- event_id: [TODO] String.
- indices: [TODO] List.
- data: [TODO] Byte array.

Returns: [TODO] tuple.


end_event
---------

Required.

Called at the end of an event.

Parameters:

- envelope_id: [TODO] String.
- event_id: [TODO] String.

Returns: [TODO] tuple.


end_envelope
------------

Required.

Called once an envelope (and its individual events) has been sent.

Parameters:

- envelope_id: [TODO] String.

Returns: [TODO] tuple.


stop_envelope
-------------

Required.

Called to signal an early envelope exit.

Parameters:

- envelope_id: [TODO] String.

Returns: [TODO] boolean.
