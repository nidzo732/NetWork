Inner workings of the NetWork framework
***************************************

This document describes how NetWork works internaly. You don't need to read this document to use NetWork properly but if you want to know more about NetWork or if you want to help in development the contents of this document could be useful.

Basic structure of the network
##############################

The workgroup in NetWork is made of one master computer and one or more worker computers.  Workers run a server program that receives instructions from the master. When that server starts it listens on port 32151 and waits for master to register.
When an instance of Workgroup is created the constructor is given a list of IP addresses. 

The constructor sends a test code (NetWork.networking.COMCODE_CHECKALIVE) to each of the given IPs and waits for response, when the server program on the worker receives the test code it responds with a return code (NetWork.networking.COMCODE_ISALIVE), if all goes well and the codes are received the worker is added to the workgroup.

Once the workgroup starts working the master computer manages all communication, worker computers can't communicate between themselves. All multiprocessing tools send request to the master when used on worker computers.

Low level networking
####################

NetWork relies heavily on network communication. Classes used for networking are defined in NetWork.networking.

When communicating all parts of the framework use the NetWork.networking.NWSocket class, this class is set to the default socket class in NetWork (currently that's NetWork.networking.NWSocketTCP). 

The default class can be changed to adapt to various types of networks, but all networking classes must implement certain methods and must be self contained, when adapting to another network, no part of NetWork should be changed but the NetWork.networking module.

All socket classes must have these methods and members:

:NWSocket:
  
  listen : method
    Start listening for incoming connections, after call to this method the socket must be ready to accept requests. There is no bind method, binding must be done automaticaly by the class.

  accept : method
    Accept a new request, return an instance of a socket class that will be used to receive and respond to that request.

  connect(address) : method
  	Connect to given address, addres can be any object, anything given to the Workgroup constructor is passed directly to the connect method

  send(data) : method
    Send given data to the other side. All data must be handled safely, no buffer overflows, no parital messages. There won't be two sends on the same socket. Usually one message is sent, a response is received and the socket is closed.

  recv : method
    Receive all data sent from the other side. All data must be handled safely, no buffer overflows, no parital messages. Messages have variable length, it is the responsibility of the socket class to know that length and receive the entire message.

  close : method
    Close the socket, it will no longer be used for communication.

  address : member
  	The address of the remote computer to whitch this socket is connected to, used to identify which worker sent the request.

  checkAvailability(address) : static method
  	Check if a worker is present at the given address. This method is called on startup when adding workers.

Any class implementing these methods can be used in NetWork, just change the default class to your own
::

	NetWork.networking.NWSocket=MySocketClass




