Overview
========

Xbus is an Enterprise service bus. As such it aims to help IT departments
achieve a better application infrastructure layout by providing a way to
urbanize the IT systems.

The goals of urbanization are:

  - high coherence
  - low coupling


High coherence
--------------

This is important because everyone wants applications to behave in a coherent
way and not fall appart with bizzare errors in case of data failure. Think of
your accounting system or your CRM. You want the accounting to achieve data
consistency event if an incoming invoices batch fails to load properly.

Low coupling
------------

But this is not because you want coherence that you are happy with every
application in your infrastructure talking directly to the API of every other
application. This may seem appealing when you have 3 or 4 applications,
but quite rapidly you'll get tens or even hundreds of different interface
flows between many applications. All these flows must be maintained:

   - at the emitter side, because the emitter needs to implement the receiver
     API, or at least flat file layout
   - at the receiver side, because one day the receiver will want to change
     the file schema or the API it provides
   - at the operator side, (yup!), because when you begin have tens or more
     of nightly (or on demand) interface flows you will need to monitor them
     and make sure they get delivered. And you will also want to know when they
     fail and what to do in those cases (ie: is this because the receiver
     failed and we should retry or is this an emitter problem...)

When you don't use a Bus or Broker you are in a situation of high coupling.
Changing one component of your IT infrastructure may prove a big challenge,
just because it received interfaces from 3 different systems and provided
nightly data to 2 other.

Xbus
----

With the Xbus broker we try to address those issues registering all emitters,
all consumers and what kind of events they can emit or receive.

Since the emitter is not technically aware of who will consume its event data
it will not be necessary to change its side of the interface when replacing
a consumer by another in your infrastructure.
