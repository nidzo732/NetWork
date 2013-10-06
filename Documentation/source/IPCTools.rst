IPC and concurrency control tools
*********************************
One of the main advantages of NetWork are IPC and concurrency control tools that behave just like their equivalents used for multiprocessing on single computer.
The tools are simple to use, you don't have to wory about network communication and low level stuff, just use them like you're running on a single computer.
They are regular classes imported from NetWork

::

    from NetWork import Manager, Event, Lock, Queue, Semaphore


Here are the tools currently available

.. toctree::
   :maxdepth: 1
   
   Manager <NetWork.manager>
   Event <NetWork.event>
   Lock <NetWork.lock>
   Queue <NetWork.queue>
   Semaphore <NetWork.semaphore>
