.. NetWork documentation master file, created by
   sphinx-quickstart on Fri Aug 16 17:37:59 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to NetWork's documentation!
===================================

**THIS DOCUMENTATION IS STILL INCOMPLETE**

NetWork is a Python framework for distributed computing. It enables your program to make use of the processing power of computers on a local network.

NetWork tries to imitate multithreading environment, but instead of limiting you to use only the processors on your local machines it will distribute the load between multiple connected machines.

If you have 10 dual core computers, your program gets all the power of those 20 cores for parallel work. This may sound a lot like Remote Procedure Call systems but it adds you the ability to better control the processes running on different machines. You get pipes, queues and other types of message passing, concurrency control tools like locks and events. NetWork tries to mimic Python's multiprocessing and concurrent.futures modules making it easy to port ordinary multithreaded program to run on a network.

To learn how to use NetWork see the links below, if you are new start with the Tutorial, if you want to learn more about using the tools NetWork gives
you see IPC and concurrency control tools.

If you are curious or want to help with the development see the page about internal workings of NetWork.

.. toctree::
   :maxdepth: 1
   
   Tutorial
   IPC and concurrency control tools <IPCTools>
   Internal workings <InnerWorkings>



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

