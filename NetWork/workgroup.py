"""
The Workgroup class is defined in this file, along with accompanying classes
and functions.
"""

from multiprocessing import Process, Queue, Manager, Event
import NetWork.networking
from .handlers import receiveSocketData, handlerList, plugins
from threading import Thread
from .worker import Worker, WorkerUnavailableError, DeadWorkerError
from .task import Task, TaskHandler
from .commcodes import *
from .cntcodes import *
from .manager import NWManager
from NetWork import event, queue, lock, manager, semaphore
import pickle
from .request import Request


class NoWorkersError(Exception):pass


def receiveSocketData(socket, commqueue, controlls):
    workerId=-1
    for worker in controlls[CNT_WORKERS]:
        if socket.address==worker.realAddress:
            workerId=worker.id
    if workerId==-1:
        return
    try:
        receivedData=socket.recv()
    except OSError as error:
        print("Network communication failed from address", socket.address, error)
        return
    if not receivedData[:3] in handlerList:
        print("Request came with an invalid identifier code", receivedData[:3])
        return
    commqueue.put(Request(receivedData[:3], 
                          pickle.loads(receivedData[3:]), workerId, socket))


class Workgroup:
    """
    Defines the group of computers that will execute the tasks, handles requests
    from the user and from the worker computers, controlls execution, messaging
    and concurrency. Handles Locks, Queues, :py:mod:`Managers <NetWork.manager>`, :py:mod:`Events <NetWork.event>` and other tools.
    
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
                 handleDeadWorkers=False, socketType="TCP", keys=None):
        self.controlls=Manager().dict() 
        self.controlls[CNT_WORKER_COUNT]=0
        self.controlls[CNT_TASK_COUNT]=0
        self.controlls[CNT_EVENT_COUNT]=0
        self.controlls[CNT_QUEUE_COUNT]=0
        self.controlls[CNT_LOCK_COUNT]=0
        self.controlls[CNT_TASK_EXECUTORS]={-1:None}
        self.controlls[CNT_MANAGER_COUNT]=0
        self.controlls[CNT_DEAD_WORKERS]=set()
        self.controlls[CNT_SEMAPHORE_COUNT]=0
        self.currentWorker=-1
        for plugin in plugins:
            plugin.masterInit()
        NetWork.networking.setUp(socketType, keys)
        self.listenerSocket=NetWork.networking.NWSocket()
        self.workerList=[]
        for workerAddress in workerAddresses:
            try:
                newWorker=Worker(workerAddress,
                                 self.controlls[CNT_WORKER_COUNT])
                self.workerList.append(newWorker)
                self.controlls[CNT_WORKER_COUNT]+=1
            except WorkerUnavailableError as workerError:
                if not skipBadWorkers:
                    raise workerError
        if not self.controlls[CNT_WORKER_COUNT]:
            raise NoWorkersError("No workers were successfully added to workgroup")
        self.controlls[CNT_WORKERS]=self.workerList
        self.commqueue=Queue()
        self.handleDeadWorkers=handleDeadWorkers
        self.running=False
        
    def __enter__(self):
        self.startServing()
        return self
    
    def __exit__(self, exceptionType, exceptionValue, traceBack):
        self.stopServing()
    
    def deadWorkers(self):
        return self.controlls[CNT_DEAD_WORKERS]
    
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
                                           self.controlls))
        self.networkListener.daemon=True
        self.dispatcher=Thread(target=self.dispatcherProcess, 
                                args=(self.commqueue, self.controlls))
        self.dispatcher.start()
        self.networkListener.start()
        self.running=True
    
    def selectNextWorker(self):
        if self.controlls[CNT_WORKER_COUNT]==0:
            raise NoWorkersError("All workers have died")
        self.currentWorker+=1
        self.currentWorker%=self.controlls[CNT_WORKER_COUNT]
        while not self.controlls[CNT_WORKERS][self.currentWorker].alive:
            self.currentWorker+=1
            self.currentWorker%=self.controlls[CNT_WORKER_COUNT]
         
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
        self.controlls[CNT_TASK_COUNT]+=1
        newTask=Task(target=target, args=args, kwargs=kwargs, 
                     id=self.controlls[CNT_TASK_COUNT])
        self.sendRequest(CMD_SUBMIT_TASK, 
                         {
                          "WORKER":self.currentWorker,
                          "TASK":newTask
                          })
        executors=self.controlls[CNT_TASK_EXECUTORS]
        executors[newTask.id]=self.currentWorker
        self.controlls[CNT_TASK_EXECUTORS]=executors
        return TaskHandler(newTask.id, self)
    
    def getResult(self, id):
        resultQueue=self.registerQueue()
        self.sendRequest(CMD_GET_RESULT,
                         {
                          "ID":id,
                          "QUEUE":resultQueue.id
                          })
        
        result=resultQueue.get()
        return result
        
    
    def cancelTask(self, id):
        self.sendRequest(CMD_TERMINATE_TASK,
                         {
                          "ID":id
                          })
    
    
    def taskRunning(self, id):
        resultQueue=self.registerQueue()
        self.sendRequest(CMD_TASK_RUNNING,
                         {
                          "ID":id,
                          "QUEUE":resultQueue.id
                          })
        result=resultQueue.get()
        return result
    
    def getException(self, id):
        resultQueue=self.registerQueue()
        self.sendRequest(CMD_GET_EXCEPTION,
                         {
                          "ID":id,
                          "QUEUE":resultQueue.id
                          })
        result=resultQueue.get()
        return result
    
    def exceptionRaised(self, id):
        resultQueue=self.registerQueue()
        self.sendRequest(CMD_CHECK_EXCEPTION,
                         {
                          "ID":id,
                          "QUEUE":resultQueue.id
                          })
        result=resultQueue.get()
        return result
    
    def sendRequest(self, type, contents):
        self.commqueue.put(Request(type, contents))
            
    def registerEvent(self):
        """
        Create a new event to be used by the tasks
        
        :Return: instance of :py:class:`NWEvent <NetWork.event.NWEvent>`
        """
        self.controlls[CNT_EVENT_COUNT]+=1
        id=self.controlls[CNT_EVENT_COUNT]
        self.sendRequest(CMD_REGISTER_EVENT,
                         {
                          "ID":id
                          })
        return event.NWEvent(id, self)
    
    def registerQueue(self):
        """
        Create a new queue to be used by the tasks
        
        :Return: instance of :py:class:`NWQueue <NetWork.queue.NWQueue>`
        """
        self.controlls[CNT_QUEUE_COUNT]+=1
        id=self.controlls[CNT_QUEUE_COUNT]
        self.sendRequest(CMD_REGISTER_QUEUE,
                         {
                          "ID":id
                          })
        return queue.NWQueue(id, self)
    
    def registerLock(self):
        """
        Create a new lock to be used by the tasks
        
        :Return: instance of :py:class:`NWLock <NetWork.lock.NWLock>`
        """
        self.controlls[CNT_LOCK_COUNT]+=1
        id=self.controlls[CNT_LOCK_COUNT]
        self.sendRequest(CMD_REGISTER_LOCK,
                         {
                          "ID":id
                          })
        return lock.NWLock(id, self)
    
    def registerSemaphore(self, value):
        """
        Create a new semaphore to be used by the tasks
        
        :Parameters:
          value : int
            Counter value for the semaphore
        
        :Return: instance of :py:class:`NWSemaphore <NetWork.semaphore.NWSemaphore>`
        """
        self.controlls[CNT_SEMAPHORE_COUNT]+=1
        id=self.controlls[CNT_LOCK_COUNT]
        self.sendRequest(CMD_REGISTER_SEMAPHORE,
                         {
                          "ID":id,
                          "VALUE":value
                          })
        return semaphore.NWSemaphore(id, self, value)
    
    def registerManager(self):
        """
        Create a new manager to be used by the tasks
        
        :Return: instance of :py:class:`NWManager <NetWork.manager.NWManager>`
        """
        self.controlls[CNT_MANAGER_COUNT]+=1
        id=self.controlls[CNT_MANAGER_COUNT]
        return NWManager(self.controlls[CNT_MANAGER_COUNT], self)        
    
    def stopServing(self):
        """
        Stop the dispatcher and listener threads
        also invoked when exiting whe ``with`` block
        """
        Workgroup.onExit(self)
    
        
        
    
    @staticmethod
    def listenerProcess(listenerSocket, commqueue, controlls):
        #A process that receives network requests
        while True:
            receivedRequest=listenerSocket.accept()
            handlerThread=Thread(target=receiveSocketData, 
                                 args=(receivedRequest, commqueue, controlls))
            handlerThread.start()
                
    
    @staticmethod
    def dispatcherProcess(commqueue, controlls):
        #A process that handles requests
        request=commqueue.get()
        while not request==CMD_HALT:
            #print(request)
            handlerList[request.getType()](request, controlls, commqueue)
            request.close()
            request=commqueue.get()
    
    @staticmethod
    def onExit(target):
        #Ran on exit to clean up the workgroup
        if (target.running):
            #Need to fix this for a nice exit, preferably with join#########
            target.commqueue.put(CMD_HALT)
            target.dispatcher.join()
            target.listenerSocket.close()
            target.running=False
        
    
            
