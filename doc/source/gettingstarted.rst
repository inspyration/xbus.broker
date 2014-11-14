Getting started
===============

With docker
-----------

Xbus is packaged using docker to help deploy it. To be continued... # TODO

Using the source code
---------------------

Copy the sample config file and edit it to suit your needs::

  $ cp config.ini.sample config.ini


Create your own virtualenv::

  $ virtualenv env-xbus
  $ source env-xbus/bin/activate
  (env-xbus)$ setup_xbusbroker -c config.ini


This should create your data tables into the database you chose in the
configuration file. You should now start the server::

  $ start_xbusbroker -c config.ini


Once this is done, the broker is running.
