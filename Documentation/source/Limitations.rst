Limitations of NetWork framework
********************************

The NetWork framework tries to make your network work like a single computer but there are some limitations caused by the networked architecture.

Here are known limitations, bugs and problems in NetWork:

  *  No shared globals. On classic multiprocessing the child process gets a copy of all parrents' globals, this is not the case with NetWork, the child only gets standard Python globals, all other data must be passed manualy, for example with managers
  
  *  Custom objects limitation. If you plan to send instances of your own classes through the network those classes must be available on all worker computers and must be importable from standard Python path, the same applies for functions - all non standard functions must also be defined on the workers
  
  *  No automatic exception handling. If an exception is raised in one of the tasks you won't be notified automatically, you need to explicitly call :py:meth:`TaskHandler.exceptionRaised <NetWork.task.TaskHandler.exceptionRaised>` and  :py:meth:`TaskHandler.exception <NetWork.task.TaskHandler.exception>` to check and get exceptions.
  
  *  No printing. When you call print, the text will be printed on the screen of the worker not on the master where you'd probably like to see it. 
  
  *  Network communication between workers and master is currently very insecure, messages are unencrypted and no authentication is done. Use NetWork only in secure environment. Work is in progress to provide encryption and verification.