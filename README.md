#NetWork

##Note: this project is far from finished, actually it doesn't run at all currently. If you'd like to help please contact me (nidzo732).

The aim of this project is to create a package that will enable its users
to run multiple processes on multiple networked computers. It tries to mimic
the standard Python concurrent.futures and multiprocessing module, but instead 
of being limited to CPUs and cores on local computer you get to run the function 
on any computer you can access. Basically this should be a library for creating 
and running a simple computing cluster. I've just started this project, when it's 
finished it will be capable of creating a multiprocessing environment on networked 
computers with all the controll tools such as Locks, Events, Managers...

###How it works?
####(high level overview)

You have one central computer and several "worker" computers. The central one
runs the program you made that uses the NetWork library. The "worker" computers
run a server that receives the orders from the central computer. When your program
gives a request for a function to be executed, the NetWork sends it to one of the
workers and starts the execution. Here's a Python like pseudocode description of
the process

The central computer runs:

    np=NetProcess(target=myFunction, args=(a1, a2), kwargs={"kw1":5, "kw2":6})
    np.start()
    returnValue=np.getReturnValue()
    print("The function returned", returnValue)

And the "worker":

    task=getNextTask()
    args=getrgs()
    kwargs=getkwargs()
    returnValue=task(*args, **kwargs)
    commSocket.send(returnValue)

This is a very simplified high level example. The point is to show that you don't need
to care how the tasks are executed. You just use the tools very similar to those of the
standard multiprocessing module.

###Advantages

* Portability (Python runs anywhere)
* Ease of use (If you are familiar with the Python multiprocessing module, learning this should be easy)
* Flexibility (Any type of computer or CPU or computer can be in the workgroup, anything that runs Python)

###Disadvantages
* Network latency and speed (of course networks are way slower than the internal computer busses
if the network transfer time takes more than the execution then use of this package makes no sense
choose wisely what you send over the network
* Python speed (being a very high level interpreted language Python can be a litle slow, you could of course
implement the heavy stuff in C, make a library, put it on every "worker" and call it from a Python function)

###Current state of the project
I've just started the project and it's nowhere near usability, don't expect anything great soon
there's a lot of work

###Will it realy work
I've managed to make a basic proof of concept, everything else revolves arround this code. I've even
managed to send a function from a PC to an Android phone. The phone runs the function and sends
the result back to the PC. You can try it:<br/>
Run this first on the "worker" computer that will run the function:

    import socket
    import marshal
    import types
    
    WORKER_IP_ADDR="192.168.1.2" #Addres of the computer that runs the function
    PORT=8888
    s=socket.socket()
    s.bind((WORKER_IP_ADDR, PORT))
    s.listen(5)
    sock, addr=s.accept()
    fcode=sock.recv(8096)
    myFunction=types.FunctionType(marshal.loads(fcode), globals())
    returnValue=myFunction()
    sock.send(returnValue)
And run this on the computer that will request a function to be executed:

    import socket
    import marshal
    def myFunction():
        return b"Hello running from other place"
    
    WORKER_IP_ADDR="192.168.1.2" #Addres of the computer that runs the function
    PORT=8888
    s=socket.socket()
    fcode=marshal.dumps(myFunction.__code__)
    s.connect((WORKER_IP_ADDR, PORT))
    s.send(fcode)
    returnValue=s.recv(8096)
    s.close()
    print("Got a return value:", returnValue)

Replace WORKER_IP_ADDR with the address of the "worker" computer. The function from the
second file will be marshaled and sent to the "worker" computer over the network. The "worker"
is running the first file and it receives the function, unmarshals it, runs it and sends
its return value back to computer that runs the second file.<br/>
You should get a following output on the computer that sent the function:<br/>
    Got a return value: b'Hello running from other place'
If you get a network error, try checking your network and firewall.

###Can I help
If this seems interesting try experimenting with the proof of concept, for example
try sending function arguments.
If you want to help, please contact me (nidzo732)


