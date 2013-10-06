"""
The Workgroup class is defined in this file, along with accompanying classes
and functions.
"""

from multiprocessing import Queue, Manager
from threading import Thread

import NetWork.networking
from .handlers import receiveSocketData, handlerList, plugins
from .worker import Worker, WorkerUnavailableError
from .task import Task, TaskHandler
from .commcodes import *
from .cntcodes import *
from NetWork.queue import NWQueue
from .request import Request


class NoWorkersError(Exception):pass


class Workgroup:
    """
    Defines the group of computers that will execute the tasks, handles requests
    from the user and from the worker computers, controls execution, messaging
    and concurrency. Handles :py:mod:`Locks <NetWork.lock>`, :py:mod:`Queues NetWork.queue`,
    :py:mod:`Managers <NetWork.manager>`, :py:mod:`Events <NetWork.event>` and other tools.
    
    In order for the Workgroup to be functional, the ``dispatcher`` and ``listener`` 
    threads must be started and they must be terminated properly on exit. The
    recomended way to do this is to use the ``with`` statement, it will ensure
    proper termination even in case of an exception.
    
    ::
    
        with Workgroup (....) as w:
            w.doSomething()
        
    
    If you don't want to use ``with``, you can use :py:meth:`startServing` and :py:meth:`stopServing`
    methods when starting and exiting.

    Constructor:
    
    :Parameters:
      workerAddresses : iterable
        An iterable of connection parameters for communicating with
        workers in the workgroup. If default ``socketType`` is used,
        these should be IP addresses of the workers, if secure sockets
        are used, parameters should contain keys for each worker.
        
      skipBadWorkers : bool
        Whether to raise an error when adding the worker fails or to 
        continue to the next worker
        
      handleDeadWorkers : Currently not working, leave as it is
      
      socketType : string
        NetWork has several socket types used internaly to communicate.
        Default is an ordinary TCP socket with no protection, other
        available values for this parameter are:
          
          * ``"HMAC"`` Use HMAC verification on messages. Worker connection
            parameters must follow this format ``(IP, HMACKey)``
          * ``"AES"`` Encrypt messages with AES encryption. Worker connection
            parameters must follow this format ``(IP, AESKey)``
          * ``"AES+HMAC"`` Encrypt messages with AES and verify them with HMAC.
            Worker connection parameters must follow this format 
            ``(IP, HMACKey, AESKey)``
      
      keys : dict
        If you selected a protected socket type, you need to provide keys
        for decrypting and/or verifying incomming messages from workers.
        Items to put in this dictionary:
        
          * ``"ListenerAES"`` AES key used to decrypt messages from workers,
            must be specified if AES is enabled
          * ``"ListenerHMAC"`` HMAC key used to verify messages from the workers,
            must be specified if HMAC is enabled

    """

    def __init__(self, workerAddresses, skipBadWorkers=False, 
                 socketType="TCP", keys=None):
        self.controls=dict()
        self.controls[CNT_WORKER_COUNT]=0
        self.controls[CNT_TASK_COUNT]=0
        self.controls[CNT_TASK_EXECUTORS]={-1:None}
        self.controls[CNT_DEAD_WORKERS]=set()
        self.currentWorker=-1
        for plugin in plugins:
            plugin.masterInit(self)
        NetWork.networking.setUp(socketType, keys)
        self.listenerSocket=NetWork.networking.NWSocket()
        self.workerList=[]
        for workerAddress in workerAddresses:
            try:
                newWorker=Worker(workerAddress,
                                 self.controls[CNT_WORKER_COUNT])
                self.workerList.append(newWorker)
                self.controls[CNT_WORKER_COUNT]+=1
            except WorkerUnavailableError as workerError:
                if not skipBadWorkers:
                    raise workerError
        if not self.controls[CNT_WORKER_COUNT]:
            raise NoWorkersError("No workers were successfully added to workgroup")
        self.controls[CNT_WORKERS]=self.workerList
        self.commqueue=Queue()
        self.running=False
        
    def __enter__(self):
        self.startServing()
        return self
    
    def __exit__(self, exceptionType, exceptionValue, traceBack):
        self.stopServing()
    
    def deadWorkers(self):
        return self.controls[CNT_DEAD_WORKERS]
    
    def startServing(self):
        """
        Start the dipatcher and listener threads, the workgroup is ready
        for work after this.
        Instead of running this method manually it is recomened to use
        the ``with`` statement
        """
        self.listenerSocket.listen()
        self.networkListener=Thread(target=self.listenerProcess, 
                                     args=(self.listenerSocket, self.commqueue,
                                           self.controls))
        self.networkListener.daemon=True
        self.dispatcher=Thread(target=self.dispatcherProcess, 
                                args=(self.commqueue, self.controls))
        self.dispatcher.start()
        self.networkListener.start()
        self.running=True
    
    def selectNextWorker(self):
        if self.controls[CNT_WORKER_COUNT]==0:
            raise NoWorkersError("All workers have died")
        self.currentWorker+=1
        self.currentWorker%=self.controls[CNT_WORKER_COUNT]
        while not self.controls[CNT_WORKERS][self.currentWorker].alive:
            self.currentWorker+=1
            self.currentWorker%=self.controls[CNT_WORKER_COUNT]
         
    def submit(self, target, args=(), kwargs={}):
        """
        Submit a task to be executed by the workgroup
        
        :Parameters:
         target : callable
           function to be executed
         
         args : iterable
           optional tuple of positional arguments
         
         kwargs : dict
           optional dictionary of keyword arguments
         
        :Return: an instance of :py:class:`TaskHandler <NetWork.task.TaskHandler>`
        """
        self.selectNextWorker()
        self.controls[CNT_TASK_COUNT]+=1
        newTask=Task(target=target, args=args, kwargs=kwargs, 
                     id=self.controls[CNT_TASK_COUNT])
        self.sendRequest(CMD_SUBMIT_TASK, 
                         {
                          "WORKER":self.currentWorker,
                          "TASK":newTask
                          })
        executors=self.controls[CNT_TASK_EXECUTORS]
        executors[newTask.id]=self.currentWorker
        self.controls[CNT_TASK_EXECUTORS]=executors
        return TaskHandler(newTask.id, self)
    
    def getResult(self, id):
        resultQueue=NWQueue(self)
        self.sendRequest(CMD_GET_RESULT,
                         {
                          "ID": id,
                          "QUEUE": resultQueue.id
                          })
        
        result=resultQueue.get()
        return result
        
    
    def cancelTask(self, id):
        self.sendRequest(CMD_TERMINATE_TASK,
                         {
                          "ID":id
                          })
    
    
    def taskRunning(self, id):
        resultQueue=NWQueue(self)
        self.sendRequest(CMD_TASK_RUNNING,
                         {
                          "ID":id,
                          "QUEUE":resultQueue.id
                          })
        result=resultQueue.get()
        return result
    
    def getException(self, id):
        resultQueue=NWQueue(self)
        self.sendRequest(CMD_GET_EXCEPTION,
                         {
                          "ID":id,
                          "QUEUE":resultQueue.id
                          })
        result=resultQueue.get()
        return result
    
    def exceptionRaised(self, id):
        resultQueue=NWQueue(self)
        self.sendRequest(CMD_CHECK_EXCEPTION,
                         {
                          "ID":id,
                          "QUEUE":resultQueue.id
                          })
        result=resultQueue.get()
        return result
    
    def sendRequest(self, type, contents):
        self.commqueue.put(Request(type, contents))
    
    def stopServing(self):
        """
        Stop the dispatcher and listener threads
        also invoked when exiting whe ``with`` block
        """
        Workgroup.onExit(self)
    
        
        
    
    @staticmethod
    def listenerProcess(listenerSocket, commqueue, controls):
        #A process that receives network requests
        while True:
            receivedRequest=listenerSocket.accept()
            handlerThread=Thread(target=receiveSocketData, 
                                 args=(receivedRequest, commqueue, controls))
            handlerThread.start()
                
    
    @staticmethod
    def dispatcherProcess(commqueue, controls):
        #A process that handles requests
        request=commqueue.get()
        while not request==CMD_HALT:
            #print(request)
            handlerList[request.getType()](request, controls, commqueue)
            request.close()
            request=commqueue.get()
    
    @staticmethod
    def onExit(target):
        #Ran on exit to clean up the workgroup
        if (target.running):
            target.commqueue.put(CMD_HALT)
            target.dispatcher.join()
            target.listenerSocket.close()
            target.running=False
