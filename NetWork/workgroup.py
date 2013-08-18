"""
The Workgroup class is defined in this file, along with accompanying classes
and functions.
"""

from multiprocessing import Process, Queue, Manager, Event
from .networking import NWSocket
from .handlers import receiveSocketData, handlerList
from threading import Thread
from .worker import Worker, WorkerUnavailableError, DeadWorkerError
from .task import Task, TaskHandler
from .deadworkerhandler import salvageDeadWorker
from .commcodes import *
from .cntcodes import *
from .lock import NWLock
from .manager import NWManager
from NetWork import event, queue, lock, manager
import pickle




class NoWorkersError(Exception):pass

class Command:
    #A class used to send commands to the Workgroup.dispatcher thread
    #Used internaly by workgroup, not by user
    def __init__(self, contents, requester, socket=None):
        self.contents=contents
        self.requester=requester
        self.socket=socket
    
    def getContents(self):
        return self.contents[3:]
    
    def type(self):
        return self.contents[:3]
    
    def close(self):
        if self.socket:
            self.socket.close()
    
    def respond(self, response):
        self.socket.send(response)

def receiveSocketData(socket, commqueue, controlls):
    workerId=-1
    for worker in controlls[CNT_WORKERS]:
        if socket.address==worker.address:
            workerId=worker.id
    if workerId==-1:
        return
    commqueue.put(Command(socket.recv(), workerId, socket))


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
        An iterable of addresses of workers in the workgroup
        
      skipBadWorkers : bool
        Whether to raise an error when adding the worker fails or to 
        continue to the next worker
        
      handleDeadWorkers : Currently not working, leave as it is
    """

    def __init__(self, workerAddresses, skipBadWorkers=False, 
                 handleDeadWorkers=False):
        self.controlls=Manager().list(range(20)) 
        self.controlls[CNT_WORKER_COUNT]=0
        self.controlls[CNT_TASK_COUNT]=0
        self.controlls[CNT_EVENT_COUNT]=0
        self.controlls[CNT_QUEUE_COUNT]=0
        self.controlls[CNT_LOCK_COUNT]=0
        self.controlls[CNT_TASK_EXECUTORS]={-1:None}
        self.controlls[CNT_MANAGER_COUNT]=0
        self.currentWorker=-1
        self.listenerSocket=NWSocket()
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
        self.controlls[CNT_LIVE_WORKERS]=self.controlls[CNT_WORKER_COUNT]
        self.controlls[CNT_WORKERS]=self.workerList
        self.commqueue=Queue()
        event.events={-1:None}
        event.runningOnMaster=True
        queue.queues={-1:None}
        queue.queueHandlers=Manager().dict()
        queue.queueLocks={-1:None}
        queue.runningOnMaster=True
        lock.locks={-1:None}
        lock.lockHandlers={-1:None}
        lock.lockLocks={-1:None}
        lock.runningOnMaster=True
        manager.runningOnMaster=True
        manager.managers={-1:None}
        self.handleDeadWorkers=handleDeadWorkers
        self.running=False
        
    def __enter__(self):
        self.startServing()
        return self
    
    def __exit__(self, exceptionType, exceptionValue, traceBack):
        self.stopServing()
    
    def startServing(self):
        """
        Start the dipatcher and listener threads, the workgroup is ready
        for work after this.
        Instead of running this method manually it is recomened to use
        the ``with`` statement
        """
        self.listenerSocket.listen()
        self.networkListener=Process(target=self.listenerProcess, 
                                     args=(self.listenerSocket, self.commqueue,
                                           self.controlls))
        self.dispatcher=Thread(target=self.dispatcherProcess, 
                                args=(self.commqueue, self.controlls))
        self.dispatcher.start()
        self.networkListener.start()
        self.running=True
         
    def submit(self, target, args=(), kwargs={}):
        """
        Submit a task to be executed by the workgroup
        
        :Parameters:
         target : function to be executed
         
         args : optional tuple of positional arguments
         
         kwargs : optional dictionary of keyword arguments
         
        :Return: an instance of :py:class:`TaskHandler <NetWork.task.TaskHandler>`
        """
        self.currentWorker+=1
        self.currentWorker%=self.controlls[CNT_WORKER_COUNT]
        self.controlls[CNT_TASK_COUNT]+=1
        newTask=Task(target=target, args=args, kwargs=kwargs, 
                     id=self.controlls[CNT_TASK_COUNT])
        self.commqueue.put(Command(CMD_SUBMIT_TASK+
                           str(self.currentWorker).encode(encoding='ASCII')+
                           b"WID"+newTask.marshal(), -1))
        executors=self.controlls[CNT_TASK_EXECUTORS]
        executors[newTask.id]=self.currentWorker
        self.controlls[CNT_TASK_EXECUTORS]=executors
        return TaskHandler(newTask.id, self, self.currentWorker)
    
    def getResult(self, id, worker):
        resultQueue=self.registerQueue()
        self.commqueue.put(Command(CMD_GET_RESULT+str(id).encode(encoding="ASCII")+
                           b"TID"+str(resultQueue.id).encode(encoding="ASCII"), -1))
        result=resultQueue.get()
        del resultQueue
        return result
        
    
    def cancelTask(self, id, worker):
        #return self.controlls[CNT_WORKERS][worker].terminateTask(id)
        self.commqueue.put(Command(CMD_TERMINATE_TASK+
                           str(id).encode(encoding='ASCII'), -1))
    
    
    def taskRunning(self, id, worker):
        resultQueue=self.registerQueue()
        self.commqueue.put(Command(CMD_TASK_RUNNING+str(id).encode(encoding="ASCII")+
                           b"TID"+str(resultQueue.id).encode(encoding="ASCII"), -1))
        result=resultQueue.get()
        del resultQueue
        return result
    
    def getException(self, id, worker):
        resultQueue=self.registerQueue()
        self.commqueue.put(Command(CMD_GET_EXCEPTION+str(id).encode(encoding="ASCII")+
                           b"TID"+str(resultQueue.id).encode(encoding="ASCII"), -1))
        result=resultQueue.get()
        del resultQueue
        return result
    
    def exceptionRaised(self, id, worker):
        resultQueue=self.registerQueue()
        self.commqueue.put(Command(CMD_CHECK_EXCEPTION+str(id).encode(encoding="ASCII")+
                           b"TID"+str(resultQueue.id).encode(encoding="ASCII"), -1))
        result=resultQueue.get()
        del resultQueue
        return result
    
    def waitForEvent(self, id):
        event.events[id].wait()
    
    def setEvent(self, id):
        self.commqueue.put(Command(CMD_SET_EVENT+str(id).encode(encoding='ASCII'), -1))
    
    def registerEvent(self):
        """
        Create a new event to be used by the tasks
        
        :Return: instance of :py:class:`NWEvent <NetWork.event.NWEvent>`
        """
        self.controlls[CNT_EVENT_COUNT]+=1
        id=self.controlls[CNT_EVENT_COUNT]
        self.commqueue.put(Command(CMD_REGISTER_EVENT+
                           str(id).encode(encoding='ASCII'), -1))
        return event.NWEvent(id, self)
    
    def registerQueue(self):
        """
        Create a new queue to be used by the tasks
        
        :Return: instance of :py:class:`NWQueue <NetWork.queue.NWQueue>`
        """
        self.controlls[CNT_QUEUE_COUNT]+=1
        id=self.controlls[CNT_QUEUE_COUNT]
        self.commqueue.put(Command(CMD_REGISTER_QUEUE+str(id).encode(encoding='ASCII'), -1))
        return queue.NWQueue(id, self)
    
    def putOnQueue(self, id, data):
        self.commqueue.put(Command(CMD_PUT_ON_QUEUE+str(id).encode(encoding='ASCII')+
                           b"ID"+data, -1))
    
    def getFromQueue(self, id):
        self.commqueue.put(Command(CMD_GET_FROM_QUEUE+str(id).encode(encoding='ASCII'), -1))
        data=queue.queues[id].get()
        return data
    
    def registerLock(self):
        """
        Create a new lock to be used by the tasks
        
        :Return: instance of :py:class:`NWLock <NetWork.lock.NWLock>`
        """
        self.controlls[CNT_LOCK_COUNT]+=1
        id=self.controlls[CNT_LOCK_COUNT]
        self.commqueue.put(Command(CMD_REGISTER_LOCK+str(id).encode(encoding='ASCII'), -1))
        return NWLock(id, self)
    
    def registerManager(self):
        """
        Create a new manager to be used by the tasks
        
        :Return: instance of :py:class:`NWManager <NetWork.manager.NWManager>`
        """
        self.controlls[CNT_MANAGER_COUNT]+=1
        return NWManager(self.controlls[CNT_MANAGER_COUNT], self)
    
    def setManagerItem(self, id, item, value):
        self.commqueue.put(Command(CMD_SET_MANAGER_ITEM+pickle.dumps({"ID":id,
                                                                      "ITEM":item,
                                                                      "VALUE":value}), -1))
    
    
        
    
    def acquireLock(self, id):
        self.commqueue.put(Command(CMD_ACQUIRE_LOCK+str(id).encode(encoding='ASCII'), -1))
        lock.locks[id].acquire()
    
    def releaseLock(self, id):
        self.commqueue.put(Command(CMD_RELEASE_LOCK+str(id).encode(encoding='ASCII'), -1))
    
    def fixDeadWorker(self, id=None, worker=None):
        salvageDeadWorker(self, id, worker)
    
    def stopServing(self):
        """
        Stop the dispatcher and listener threads
        also invoked when exiting whe ``with`` block
        """
        Workgroup.onExit(self)
    
        
        
    
    @staticmethod
    def listenerProcess(listenerSocket, commqueue, controlls):
        while True:
            receivedRequest=listenerSocket.accept()
            handlerThread=Thread(target=receiveSocketData, 
                                 args=(receivedRequest, commqueue, controlls))
            handlerThread.start()
                
    
    @staticmethod
    def dispatcherProcess(commqueue, controlls):
        request=commqueue.get()
        while not request==CMD_HALT:
            #print("REQUEST", request.contents, "FROM", request.requester)
            handlerList[request.type()](request, controlls, commqueue)
            request.close()
            request=commqueue.get()
    
    @staticmethod
    def onExit(target):
        #CLEAN UP WORKERS#####################################
        if (target.running):
            #Need to fix this for a nice exit, preferably with join#########
            target.networkListener.terminate()
            target.commqueue.put(CMD_HALT)
            target.dispatcher.join()
            target.listenerSocket.close()
            target.running=False
        
    
            
