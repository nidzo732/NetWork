Inner workings of the NetWork framework
***************************************

This document describes how NetWork works internaly. You don't need to read this document to use NetWork properly
but if you want to know more about NetWork or if you want to help in development the contents of this document
could be useful.

Basic structure of the network
##############################

The workgroup in NetWork is made of one master computer and one or more worker computers.  Workers run a server
program that receives instructions from the master. When that server starts it listens on port **32151**
and waits for master to register.
When an instance of Workgroup is created the constructor is given a list of IP addresses. 

The constructor sends a test code (:py:const:`NetWork.networking.COMCODE_CHECKALIVE`) to each of the given IPs
and waits for response, when the server program on the worker receives the test code it responds with a return
code (:py:const:`NetWork.networking.COMCODE_ISALIVE`), if all goes well and the codes are received the worker
is added to the workgroup.

Once the workgroup starts working the master computer manages all communication, worker computers can't
communicate between themselves. All multiprocessing tools send request to the master when used on worker computers.

Low level networking
####################

NetWork relies heavily on network communication. Classes used for networking are defined in
:py:mod:`NetWork.networking`.

When communicating all parts of the framework use the :py:class:`NetWork.networking.NWSocket` class,
this class is set to the default socket class in NetWork
(currently that's :py:class:`NetWork.networking.NWSocketTCP`). There are also classes for secure communication
using AES encryption, HMAC verification and SSL.

The default class can be changed to adapt to various types of networks, but all networking classes must
implement certain methods and must be self contained, when adapting to another network, no part of NetWork
should be changed but the :py:mod:`NetWork.networking module`.

All socket classes must have these methods and members:

:NWSocket:
  
  listen : method
    Start listening for incoming connections, after call to this method the socket must be ready to accept
    requests. There is no bind method, binding must be done automaticaly by the class.

  accept : method
    Accept a new request, return an instance of a socket class that will be used to receive and respond to that
    request.

  connect(parameters) : method
    Parameters used to connect to another computer. The paramets usually contain just an address, but if secure
    networking is used keys are passed in parameters.

  send(data) : method
    Send given data to the other side. All data must be handled safely, no buffer overflows, no parital messages.
     There won't be two sends on the same socket. Usually one message is sent, a response is received and the
     socket is closed.

  recv : method
    Receive all data sent from the other side. All data must be handled safely, no buffer overflows, no parital
    messages. Messages have variable length, it is the responsibility of the socket class to know that length and
    receive the entire message.

  close : method
    Close the socket, it will no longer be used for communication.

  address : member
    The address of the remote computer to whitch this socket is connected to, used to identify which worker
    sent the request.

  checkAvailability(address) : static method
    Check if a worker is present at the given address. This method is called on startup when adding workers.

  setUp(parameters) : static method
    Get the class ready for operation, this method is calleb before any objects are created. It's usually used
    to set keys or SSL certificate files. The socketParams argument of Workgroup.__init__ gets passed to this
    function.

Any class implementing these methods can be used in NetWork, just change the default class to your own
::

    NetWork.networking.NWSocket=MySocketClass

Network security
----------------
In addition to the default NWSocketTCP class, NetWork also comes with socket classes that implement message
encryption and verification.

SSL Authentication/Encryption
=============================
NetWork supports SSL for communication between master and workers. Master has it's own SSL
certificate and private key, and every worker has a key and certificate. The verification is done both ways,
workers and master both need to have certs.

The certificates are set with setUp method. On the master, the setUp gets worker certificates and
masters key and certificate. On the worker the setUp gets worker key and certificate and master certificate

HMAC authentication
===================
The NWSocketHMAC impements HMAC authentication of messages, when sending a message it appends an SHA256 HMAC
hash to the message, the receiving end strips the hash of the received message and calculates its own, if they
both have the same keys the message is valid and it gets passed on.

AES encryption/decryption
=========================
This type of security relies on PyCrypto module and it is enabled only if the import of PyCrypto succeeds.
When sending, the message is encrypted with the given key, the actual key is not used but an SHA256 hash of the
key is generated to ensure that the key length is a multiple of 16 as per AES requirement, the receiving end t
ries to decrypt the message with its own key and if the key is valid the message is decrypted successfully.

Key management
==============
For every protection type (AES or HMAC) the master has a listener key and a key for each worker, the listner
key is used to decrypt and/or authenticate messages from workers and it is set up using the :py:data:`socketParams`
parameter of the :py:class:`Workgroup` constructor. The worker keys are passed allong with addresses in
the :py:data:`workerAddresses` parameter of the :py:class:`Workgroup` constructor.

Every worker computer has two keys given via command line arguments, its own listener key used to
decrypt/authenticate messages from the master and the master key that is used when sending messages to the master.

Listener keys are set through :py:meth:`setUp` method.


	
:py:class:`NetWork.workgroup.Workgroup` internals
#################################################


:py:meth:`__init__`
-------------------
When a new instance is created the constructor goes through the given list of IPs, for each of thos IPs it tries
to create an instance of :py:class:`NetWork.worker.Worker` class, the worker uses
:py:func:`NetWork.networking.NWSocket.checkAvailability` to test if the IP is valid, if all goes well without
exception the worker is added to the workgroup.

After the workers are added initialization is done on other modules
(:py:mod:`NetWork.event`, :py:mod:`NetWork.manager`...) their internal variables
(:py:data:`runningOnMaster`, various dictionaries of items etc) are set to their apropriate initial values.

Dispatcher, Listener, :py:data:`commqueue` and commands
-------------------------------------------------------
The workgroup has two internal threads that run in the background to receive
requests from workers and from the main program that runs on the master computer and uses this Workgroup. These
threads don't start during :py:meth:`__init__`, they are run manualy using the :py:meth:`startServing` method
and are stoped with :py:meth:`stopServing`.

networkListener
===============
Listener has a server socket that listens on port **32151** and accepts requests from the workers, for each new
connection it starts a thread that receives the actual request and sends it through the :py:data:`commqueue` to
the dispatcher thread.

dispatcher
==========
Dispatcher is one of the most important part of the workgroup, all IPC and concurrency control tools are handled
by dispatcher. The dispatcher receives requests through the :py:data:`commqueue`.

Requests begin with a 3 letter code that determines their handler function. The dispatcher looks for handler
functions in :py:data:`NetWork.handlers.handlerList`, a dictionary that maps the 3 letter codes to their handlers,
once the handle function is found the dispatcher runs it and gives it the request.

commqueue
=========
Commqueue is a queue created during :py:meth:`__init__` and is used to pass commands to the dispatcher. All
requests are passed through this queue, when tasks on workers use a tool it sends a message to
:py:attr:`networkListener` and it passes it via :py:attr:`commqueue` to the dispatcher. Tools on the master put
their requests directly to this queue using :py:meth:`NetWork.request.sendRequest`.

Request
=======
:py:class:`NetWork.request.Request` is a class used to pack requests that are passed to the dispatcher, 
in addition to the request itself. All handlers get their :py:data:`request` parameter that can be used to get the 
contents of that request and to send response to the sender of that request.

:py:func:`NetWork.request.sendRequest` is used as a unified way to send requests, regardles of whether the
sender is on the worker or on the master.
the Request also has additional data:
  
  * ID number of the worker who sent the request, if the request was sent from the master the ID is -1
  * if the request was sent over the network a socket is also passed to the dispatcher and the handler, this way
    the handler can respond to the request if needed, if the request is a local, a queue is used to pass the response
  

controls
---------
controls is a dictionary used by the Workgroup and multiprocessing tools to store various properties like list of
workers, nubmer of registered queues etc.

Communication with workers
##############################
Each worker in the workgroup is represented with an instance of :py:class:`NetWork.worker.Worker` class, these
objects are used to control the workers. Workes have methods that are used for controling tasks and generic they
also have generic :py:meth:`sendMessage` and :py:meth:`sendMessageWithResponse` methods used by other tools.

Passing requests
################
Most of the functionality of NetWork relies on passing requests, over the network and through the
:py:data:`commqueue` to the dispatcher.

These requests have to be identified and handled by a proper handler function. To identify them 3-letter codes
are prepended to each request, the core codes are defined in :py:mod:`NetWork.commcodes`, codes used by
multiprocessing tools are in their respective modules. Every code has its handler function.

When a request is received (in dispatcher or on the worker server) a dictionary
(:py:data:`NetWork.handlers.handlerList` for dispatcher, :py:data:`server.handlers` on worker) is searched for
the appropriate handler function.

Worker server relations
#######################
Each worker runs server.py program. When it starts it creates a server socket and listens for incomming connection,
when the master connects and the checks are done it initializes all other module, just like
:py:meth:`Workgroup.__init__ <NetWork.workgroup.Workgroup.__init__>` on
the master.

After init it starts receiving requests from the master, just like the dispatcher on the master it also has a
dictionary of handler functions linked to their 3-letter codes, when it receives a request it searches that
dictionary and passes the request to an apropriate function.

Task handling
-------------

Running
=======
When :py:meth:`Workgroup.submit` is called the target function and its arguments are packed in an instance of
NetWork.task.Task class. :py:class:`Task` is then pickled and sent over the network to the worker. Each task has
its own ID, :py:meth:`submit` returns a :py:class:`NetWork.task.TaskHandler` instance that contains that ID and the
ID of the worker who's running the task.

When a worker receives a request to run a task it creates a new instance of
:py:class:`NetWork.workerprocess.WorkerProcess` and passes the task to the constructor. :py:class:`WorkerProcess`
has an internal manager used to save information about running function and it also has methods to control the
running task. The :py:class:`Task` is then pased to a separate process that unpickles it and runs it, the process
also has additional code to detect exceptions and retreive the return value and then put it to the internal manager
of the :py:class:`WorkerProcess`.

Controling and getting information
==================================
:py:class:`TaskHandler` has multiple methods related to the running task, they all use :py:class:`Workgroup`
methods to pass requests to the :py:attr:`commqueue` and then to the worker, the worker receives the request and
runs the apropriate method in the :py:class:`WorkerProcess`. If the user asks for information, the worker sends it
back through the socket and handler passes it back with :py:meth:`respond` method of the Request.


Multiprocessing tools
#####################
Despite serving difrent purposes all multiprocessing tools have some common properties. 
Each instance of a tool has its own integer ID, every queue, lock, manager or event has its own ID. When requests
are sent to the dispatcher an ID is also sent to identify which item is used.

Most of them also have local dictionaries containing stuff that is used to handle them localy, for example - for
every :py:class:`NWQueue` an instance of :py:class:`multiprocessing.Queue` is added to
:py:data:`NetWork.queue.queues` dictionary on every computer in the workgroup, and the position of those queues
in the dictionary is determined by the ID of the particular :py:class:`NWQueue`.
They use :py:meth:`Workgroup.sendRequest` and :py:meth:`Worker.sendRequest` to communicate with workgroup and
workers`

Plugin system
-------------
Eaach of these multiprocessing tools is treated as a plugin. Plugins are modules that have special functions
and variables which enable NetWork to use them.

Functions in plugins
====================
Each plugin has two functions that NetWork uses during initialization (in :py:meth:`Workgroup.__init__` or in
:py:mod:`server.py`) that
are suposed to make that plugin ready for work. These functions are called :py:meth:`masterInit` and
:py:meth:`workerInit`, they are
called on startup and they usually add entries to Workgroup.controls, set up dictionaries etc.

Variables in plugins
====================
Each plugin defines two dictionaries, :py:data:`masterHandlers` and :py:data:`workerHandlers` that contain functions
used to handle
requests. During startup, these dictionaries are added to handler dictionaries in :py:mod:`NetWork.handlers` and
:py:mod:`server.py`.

Creating instances of multiprocessing tools
-------------------------------------------
Instances are usually created by calling the constructor of their classes. The constructor gets a parameter
that points to their Workgroup, they can use it to send a registration request and other requests later.

Events
------
Registration
============
On creation register event command is sent to the dispatcher and the handler sends a register event message
to all workers, along with the message an
event ID is passed. On the workers and on the master a new instance of :py:class:`multiprocessing.Event` is added
to :py:data:`NetWork.event.events` dictionary.

Waiting
=======
The :py:meth:`NWEvent.wait` method looks the same on both the master and the worker, it simply runs wait method
of the apropriate event in :py:data:`NetWork.event.events` dictionary.

Set
===
Set is different depending on whether it's run on master or the worker. On the master it passes set event mesage
allong with the ID to the dispatcher, on the worker it connects to the listener on the master and

In both cases the dispatcher receives the request and sends set event message
to all workers and sets the local event on the  master.

Locks
-----
Registration
============
On creation a register lock command is sent to the dispatcher
and the handler sends a register lock message to all workers. On the master a new instance
of :py:class:`NetWork.lock.MasterLockHandler` is added to :py:class:`NetWork.lock.lockHandlers` dictionary. On the
master and the workers, a new instance of :py:class:`multiprocessing.Lock` is added
:py:data:`NetWork.lock.locks` dictionary, after that it's acquired.

:py:class:`MasterLockHandler`
=============================
A class that is used on the master to hold information about locks, each lock has one. It has a boolean value
telling whether the lock is locked and it has a list of waiters that tried to acquire the lock when it was locked.

Acquiring
=========
When :py:meth:`NWLock.acquire` is called it sends a message to the dispacher
that it wants to acquire the lock, after that it runs the acquire
method on the apropriate lock in :py:data:`NetWork.lock.locks`.

When dispatcher receives the message it check apropriate :py:class:`MasterLockHandler` in
:py:data:`NetWork.lock.lockHandlers`, :py:class:`MasterLockHandler` has a boolean value telling whether its locked.
If it is not locked, a release lock message is sent to the worker that tried to acquire the lock, when the message
is received the appropriate lock in :py:data:`NetWork.lock.locks` is released and the process that called acquire on
it continues its work.

If the master called acquire and the lock is unlocked then a lock in :py:data:`NetWork.lock.locks` on the master is
released.

If :py:class:`MasterLockHandler` is locked the requester ID is added to the waiting list until the lock is released.

Releasing
=========
A message is sent to the dispatcher to release the lock. When releasing it checks
the waiter list in :py:class:`MasterLockHandler`, if there are waiters it gets the ID of the first one, if the ID
is -1 (master ID) the local lock on :py:data:`NetWork.lock.locks` is released, for other IDs a message is sent to
the worker to release the lock, when the worker receives the message it releases the required lock.

Managers
--------
Registration
============
On creation a message is sent to the dispatcher
and a new :py:class:`multiprocessing.manager.dict` is added to
:py:data:`NetWork.mananager.managers` on the master, no registration is performed on the workers.

Setting items
=============
When :py:meth:`NWManager.setItem` is called a request is sent to the dispatcher
with the manager ID, item key and the new value, when the dispatcher receives
the message it sets that item to a new value on the local manager in :py:data:`NetWork.manager.managers`

Getting items
=============
If :py:meth:`NWManager.getItem` is called on the master it simply reads it from
:py:data:`NetWork.manager.managers`. If it's called on the worker it sends the request over the network and the
dispatcher responds with the value of that item through the same socket.

Queues
------
Registration
============
On creation a message is sent through the dispatcher
On the master and the workers a new instance of :py:class:`multiprocessing.Queue` is added to
:py:data:`NetWork.queue.queues` dictionary. On the master a new instance of :py:data:`NetWork.queue.MasterQueue`
handler is added to :py:data:`NetWork.queue.queueHandlers`.

:py:class:`MasterQueueHandler`
==============================
A class that is used on the master to hold information about queues, each queue has one. It contains two lists,
:py:attr:`items` and :py:attr:`waiters`. When an item is put on the queue it's added to the items list,
when :py:meth:`get` is called the requester is added to the waiters list. :py:class:`MasterQueueHandler` has a
distribute method that check these lists and if both items and waiters are available it sends the first available
item to the first waiter.

Getting items
=============
The worker (or master) sends a get request allong with the queue ID and calls :py:meth:`get` on the local queue.
The dispatcher receives request, adds the worker to the waiter list and calls :py:meth:`distribute`.

Putting items
=============
A put item request is sent to dispatcher, handler adds that item to the item list on
the appropriate :py:class:`MasterQueueHandler`, after adding the item it calls its :py:meth:`distribute` method.

Distribution
============
If the waiters and items list of :py:class:`MasterQueueHandler` are not empty it sends the first item from the
items list to the first worker on the waiters list, the worker receives the item and puts it to an aprropriate queue
in :py:data:`NetWork.queue.queues`, it the waiter is master dispatcher just puts the item on a local queue in
:py:data:`NetWork.queue.queues`.

Semaphores
----------
Registration
============
On creation a register semaphore command is sent to the dispatcher
and the handler sends a register semaphore message to all workers. On the master
a new instance of :py:class:`NetWork.semaphore.MasterSemaphoreHandler` is
added to :py:class:`NetWork.semaphore.semaphoreHandlers` dictionary. On the master and the workers, a new
instance of :py:class:`multiprocessing.Semaphore` is added :py:data:`NetWork.semaphore.semaphores` dictionary.
All created :py:class:`multiprocessing.Semaphore` have the counter value given to
:py:meth:`Workgroup.registerSemaphore`, and upong creation they a loop acquires them to set their counter to zero. 

:py:class:`MasterSemaphoreHandler`
==================================
A class that is used on the master to hold information about semaphores, each semaphore has one. It has a counter
value, and it has a list of waiters that tried to acquire the semaphore when the counter was zero.

Acquiring
=========
When :py:meth:`NWSemaphore.acquire` is called it sends a message to the dispacher
that it wants to acquire the semaphore, after that it runs the
acquire method on the apropriate semaphore in :py:data:`NetWork.semaphore.semaphores`.

When dispatcher receives the message it checks apropriate :py:class:`MasterSemaphoreHandler` in
:py:data:`NetWork.semaphore.semaphoreHandlers`, :py:class:`MasterSemaphoreHandler` has a counter value telling
whether the semaphore can be acquired. If it is greater than zero it gets decremented, a release semaphore message
is sent to the worker that tried to acquire the semaphore, when the message is received the appropriate semaphore
in :py:data:`NetWork.semaphore.semaphores` is released and the process that called acquire on it continues its work.

If the master called acquire and the counter is greather than zero the counter gets decremented and then a semaphore
 in :py:data:`NetWork.semaphore.semaphores` on the master is released.

If the counter is zero the requester ID is added to the waiting list until the semaphore is released.

Releasing
=========
A message is sent to the dispatcher to release the semaphore. When releasing
it checks the waiter list in :py:class:`MasterSemaphoreHandler`, if there are waiters it gets the ID of the first
one, if the ID is -1 (master ID) the local semaphore on :py:data:`NetWork.semaphore.semaphores` is released, for
other IDs a message is sent to the worker to release the semaphore, when the worker receives the message it releases
the required semaphore. If there are no waiters the counter gets increased.

NetWork specific tools
######################
These tools don't mimic those from multiprocessing module but are somtimes needed because of the diferences between
NetWork and a regular single-computer environment.

netPrint
--------
By default a call to print function prints the output on the screen of the worker. The netPrint function solves this
by sending a request to the master with the stuff that needs to be printed, a handler on the master does the actual
printing.

NetObject
---------
Instances of classes that don't belong to Python builtins or NetWork fail to unpickle on the workers because they are
not defined there.
To solve this, when a new instance of :py:class:`NetWork.netobject.NetObject` is created the methods of the wrapped
class get sent to all workers,
where they are put in :py:data:`classDescriptors` dictionary (each class has its own ID used to locate it in the dict).

When a new instance of a wrapped object is created, the :py:meth:`__call__` method of NetObject is called, it searches for
the :py:meth:`__init__` method of that class in :py:meth:`classDescriptors` and calls it.

The instance of that object is then put in a container object, instance of NetObjectInstance. It has
:py:meth:`__getattr__` and :py:meth:`__setattr__` methods that are used to access attributes and methods of that
instance, it also has a dict called :py:data:`attrs`
that holds the attributes.

The methods get "unbound" during pickling and unpickling and because of that Python doesn't automatically pass the
self parameter to them, to solve this the methods get wrapped in :py:class:`NetWork.netobject.MethodWrapper` before
calling, this class holds the
pointer to the actual instance that will be passed to the method when :py:meth:`__call__` is called.

Static methods don't need the self argument and they get passed to the user without wrapping.