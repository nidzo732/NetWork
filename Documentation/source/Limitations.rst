Limitations of NetWork framework
********************************

The NetWork framework tries to make your network work like a single computer but there are some limitations caused
by the networked architecture.

Here are known limitations, bugs and problems in NetWork:

  *  No shared globals. On classic multiprocessing the child process gets a copy of all parrents' globals,
     this is not the case with NetWork, the child only gets standard Python globals, all other data must be passed
     manualy, for example with managers
  
  *  Custom objects created with :py:class:`NetWork.netobject.NetObject` cant use static attributes
  
  *  No automatic exception handling. If an exception is raised in one of the tasks you won't be notified
     automatically, you need to explicitly call
     :py:meth:`TaskHandler.exceptionRaised <NetWork.task.TaskHandler.exceptionRaised>`
     and  :py:meth:`TaskHandler.exception <NetWork.task.TaskHandler.exception>` to check and get exceptions.