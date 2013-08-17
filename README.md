#NetWork


The NetWork library gives you the ability to distibute tasks on multiple networked 
computers. It tries to mimic the standard Python concurrent.futures and multiprocessing 
module, but instead of being limited to CPUs and cores on local computer you get
to run the function on any computer you can access. Basically this is a library
for creating and running a computing cluster. 
It gives you all the IPC an concurrency
controll tools available in the Python multiprocessing module. The advantage of this
library over other distributed computing tools like RPC systems is that it gives you
better control of excecution and easier message passing, unlike RPC where programs always
have to be avare that they are not running on a same computers, the NetWork library hides
all the low level communication and gives you the standard tools like Locks an Queues for
communication.
NetWork mimics the Python multiprocessing module so it should be fairly easy to port Python
programs to run on a cluster wit this library.

###How it works?
####(high level overview)

You have one master computer and several "worker" computers. The central one
runs the program you made that uses the NetWork library. The "worker" computers
run a server that receives the orders from the central computer. When your program
gives a request for a function to be executed, the NetWork sends it to one of the
workers and starts the execution.
You get a handler object that can be used to controll the running process (get return value, 
check for exceptions, terminate the process).

###How to use
Basic usage instructions:
* Make sure that the port 32151 is open on every computer you want to use
* Run server.py and leave it running on every worker computer
* On master computer create an instance of NetWork.workgroup.Workgroup class
  and pass the IP addresses of all workers to the constructor, and run it's startServing method
```Python
   w=Workgroup(["135.179.12.11", "156.75.123.15", ..., "192.168.1.5"])
   w.startServing()
```

* Use submit method to tell the workgroup to run a function, optionally you can give it a
  tuple with positional arguments and/or a dictionary of keyword arguments
```Python
   handler=w.submit(target=functionToRun, args=("arg1"), kwargs={"A1":"kwarg1})
```
* You get a handler and it's methods can be use to get the return value, get exceptions or terminate
  the process
* For more information and how to use multiprocessing tools visit the (not yet completed) documentation
  on [the project documentation page](http://nidzo732.github.io/NetWork)

###Advantages

* Portability (Python runs anywhere)
* Ease of use (If you are familiar with the Python multiprocessing module, learning this should be easy)
* More controll (Better concurrency controll and message passing than most RPC systems)

###Disadvantages
* Network latency and speed (of course networks are way slower than the internal computer busses
if the network transfer time takes more than the execution then use of this package makes no sense
choose wisely what you send over the network
* Python speed (being a very high level interpreted language Python can be a litle slow, you could of course
implement the heavy stuff in C, make a library, put it on every "worker" and call it from a Python function)

###Current state of the project
The main features (running processes, Locks, Events, Queues, Managers) are working and are reasonably stable

###Can I help
If you want to help, please contact me (nidzo732)


