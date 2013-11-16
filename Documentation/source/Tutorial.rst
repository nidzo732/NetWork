Tutorial
********

This tutorial will introduce you to the basic features of NetWork - creating a workgroup, giving it tasks to run,
getting results and states of running tasks.

Notes:

  * In this tutorial and in the documentation, the term 'user' is often mentioned, it does not stand for the human
    user of your program, it stands for the program that uses the NetWork framework and its tools (the program that you
    write)
  
  * English is not my native language, I've tried to make this tutorial gramatically correct but errors can hapen.

Prepration
==========

Before starting your program you need a group of at least two computers, one computer will be the master, the program
you write will run on it, the others are workers they will run a server that will receive instructions from the master,
all of them must be able to communicate over a network. Make sure that port *32151* is opened on the firewall on every
computer.

On each worker you need to run a server, just run the program server.py located in the root of the NetWork folder.
Once started it will wait for the master to register and send orders.

Writing your distributed program
================================

Once you've set up the workers, you can create and run your distributed program from the master.

Creating a workgroup
--------------------

The key part of the program is an instance of :py:class:`Workgroup <NetWork.workgroup.Workgroup>` class, you control
everything from this object. It's constructor takes an iterable (list, tuple, whatever) of worker IPs like this:

::

    w=Workgroup(["192.168.1.25", "192.168.1.26", "192.168.1.27"])



It tries to contact each of the IPs and if it succeeds it adds the address to the workgroup, when you give it tasks
to execute it will send it to one of the computers in the list.
The workgroup is not ready yet, it has two internal processes the ``dispatcher`` and ``networkListener`` that
receive messages from workers and handle them, they need to be started in order for the workgroup to be fully
operational.
The easiest way to star them is to call the :py:meth:`startServing <NetWork.workgroup.Workgroup.startServing>`
method of the workgroup, the method will start them and you can use all facilities of the workgroup, when you're
done, call the :py:meth:`stopServing <NetWork.workgroup.Workgroup.stopServing>` method to ensure that they are
closed.
This method however is inelegant and doesn't ensure proper cleanup in case of an exception, it's better to use
the ``with`` statement, it'll ensure that the workgroup is closed properly when the program exits, normally or
abruptly.
Here's how to do it both ways:

::

    w=Workgroup(["192.168.1.25", "192.168.1.26", "192.168.1.27"])
    w.startServing()
    w.doSomething()
    w.stopServing()

or

::

    with Workgroup(["192.168.1.25", "192.168.1.26", "192.168.1.27"]) as w:
        w.doSomething()

Use the second method if you can.

Giving it something to execute
------------------------------

To give the workgroup a task to execute, use it's :py:meth:`submit <NetWork.workgroup.Workgroup.submit>` method, it
takes 3 arguments, the last two are optional:

::

    handler=w.submit(target=some_function, args=("a", "tuple", "of", "args"), kwargs={"A dict":"Of arguments"})


First argument is a function to be executed in the new task, the second optional argument is a tuple of positional
arguments that will be given to the function, the third optional argument is a dictionary of keyword arguments given
to the function.
The :py:meth:`submit <NetWork.workgroup.Workgroup.submit>` method returns an instance of
:py:class:`TaskHandler <NetWork.task.TaskHandler>`, which is use to control a running tasks. The handler has methods
for getting the return value, terminating, checking exceptions etc.
In this turorial we will use two methods, :py:meth:`result <NetWork.task.TaskHandler.result>` and
:py:meth:`running <NetWork.task.TaskHandler.running>`, for other methods see the documentation of
:py:class:`TaskHandler <NetWork.task.TaskHandler>` class.
Here is a program that gives three tasks to the workgroup, waits for them to finish and gets the results

::

    from NetWork.workgroup import Workgroup
    from time import sleep
    with Workgroup(["192.168.1.25", "192.168.1.26", "192.168.1.27"]) as w:
        handler1=w.submit(target=long_running_function1, args=(1,2,3))
        handler2=w.submit(target=long_running_function2, args=(4,5,6))
        handler3=w.submit(target=long_running_function3, args=(7,8,9))
        while handler1.running() or handler2.running() or handler3.running():
            sleep(0.5)
        print(handler1.result(), handler2.result(), handler3.result())

This program gives the workgroup 3 tasks and checks if they're done every 0.5 seconds, when
:py:meth:`running <NetWork.task.TaskHandler.running>` method returns ``False`` the tasks are done and their results
are obtained with the :py:meth:`result <NetWork.task.TaskHandler.result>` medod. Because we have 3 computers the
execution time should theoretically be up to 3 times shorter than running these on a single computer. This method
of waiting is used just for demonstration, the proper way would be to use :doc:`events <NetWork.event>` but that is
beyond the scope of this beginner tutorial.

What next
---------

You've learned the basics of using NetWork, but it's real advantage is in the tools it offers. for more
information see the pages on :doc:`IPC and concurrency control tools <IPCTools>`,
:doc:`NetWork specific tools <OtherTools>` and :ref:`Modules index <modindex>`.
You can also learn about the :doc:`Inner workings of the framework <InnerWorkings>`.
