"""
The Workgroup class is defined in this file, along with accompanying classes
and functions.
Created on Jan 11, 2013
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
    """
    A class used to send commands to the Workgroup.dispatcher thread
    Used internaly by workgroup, not by user
    """
    def __init__(self, contents, requester, socket=None):
        #Create a command to be passed to Workgroup.dispatcher thread,
        self.contents=contents  #request itself
        self.requester=requester#id of a worker who sent the request, -1 for master
        self.socket=socket      #used to send the responsed back
    
    def getContents(self):
        #Get the request without the 3-character type code
        return self.contents[3:]
    
    def type(self):
        #Get the 3-character type code
        return self.contents[:3]
    
    def close(self):
        #Close internal socket
        if self.socket:
            self.socket.close()
    
    def respond(self, response):
        #Send response
        self.socket.send(response)

def receiveSocketData(socket, commqueue, controlls):
    #Internaly used to receive requests from workers and pass them
    #to the Workgroup.dispatcher
    workerId=-1
    for worker in controlls[CNT_WORKERS]:   #Check which worker sent the request
        if socket.address==worker.address:
            workerId=worker.id
    if workerId==-1:
        return
    commqueue.put(Command(socket.recv(), workerId, socket))


class Workgroup:
    """
    Defines the group of computers that will execute the tasks, handles requests
    from the user and from the worker computers, controlls execution, messaging
    and concurrency. Handles Locks, Queues, Managers, Events and other tools.
    
    In order for the Workgroup to be functional, the dispatcher and listener 
    threads must be started and they must be terminated properly on exit. The
    recomended way to do this is to use the 'with' statement, it will ensure
    proper termination event in case of an exception.
    
    with Workgroup (....) as w:
        w.doSomething()
    
    If you don't want to use 'with', you can use startServing and stopServing
    methods when starting and exiting.
    
    Important members:
    controlls-> manager used to hold data of the workgroup like number of workers,
                number of managers, task->worker mappings etc.
    workerList-> workers in the workgroup
    currentWorker-> used to select next worker for the task, incremented on
                    every submit and reset to zero when last worker is reached
    dispatcher-> a threads that receives and handles requests for task
                 submission, Queue puts and gets, Event control etc.
    networkListener-> a thread that listens to network requests and passes
                      them to dispatcher
    """  

    def __init__(self, workerAddresses, skipBadWorkers=False, 
                 handleDeadWorkers=False):
        """
        Create a new workgroup:
        workerAddressed-> An iterable of addresses of workers in the workgroup
        skipBadWorkers-> Whether to raise an error when adding the worker fails
                         or to continue to the next worker
        handleDeadWorkers-> Currently not working, leave as it is
        """
        self.controlls=Manager().list(range(20))#Contains various properties
        self.controlls[CNT_WORKER_COUNT]=0      #Number of workers
        self.controlls[CNT_TASK_COUNT]=0        #Number of running task
        self.controlls[CNT_EVENT_COUNT]=0       #Number of events
        self.controlls[CNT_QUEUE_COUNT]=0       #Numer of queues
        self.controlls[CNT_LOCK_COUNT]=0        #Number of locks
        self.controlls[CNT_TASK_EXECUTORS]={-1:None}    #A table that links tasks
                                                        #the workers thar run them
                                        
        self.controlls[CNT_MANAGER_COUNT]=0     #Number of managers
        self.currentWorker=-1
        self.listenerSocket=NWSocket()  #Used to receive requests from workers
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
        self.commqueue=Queue()  #used to pass messages to the dispatcher
        #Set up other controll tools
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
        #For the with statement
        self.startServing()
        return self
    
    def __exit__(self, exceptionType, exceptionValue, traceBack):
        #When exiting with block
        self.stopServing()
    
    def startServing(self):
        """
        Start the dipatcher and listener threads, the workgroup is ready
        for work after this.
        Instead of running this method manually it is recomened to use
        the 'with' statement
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
        target-> function to be executed
        args-> optional tuple of positional arguments
        kwargs-> optional dictionary of keyword arguments
        Return: a TaskHandler object from NetWork.handler
        """
        self.currentWorker+=1   #Select next workger
        self.currentWorker%=self.controlls[CNT_WORKER_COUNT]
        self.controlls[CNT_TASK_COUNT]+=1
        
        newTask=Task(target=target, args=args, kwargs=kwargs, 
                     id=self.controlls[CNT_TASK_COUNT])
        
        self.commqueue.put(Command(CMD_SUBMIT_TASK+     #Send command to execute
                           str(self.currentWorker).encode(encoding='ASCII')+
                           b"WID"+newTask.marshal(), -1))
        
        executors=self.controlls[CNT_TASK_EXECUTORS]    #Link task to the worker
        executors[newTask.id]=self.currentWorker
        self.controlls[CNT_TASK_EXECUTORS]=executors
        return TaskHandler(newTask.id, self, self.currentWorker)
    
    def getResult(self, id, worker):
        """
        Get the return value of the task #id running on #worker
        returns none if the task is still running
        This method should not be invoked directly but by 
        NetWork.task.TaskHandler
        """
        resultQueue=self.registerQueue()
        self.commqueue.put(Command(CMD_GET_RESULT+str(id).encode(encoding="ASCII")+
                           b"TID"+str(resultQueue.id).encode(encoding="ASCII"), -1))
        result=resultQueue.get()
        del resultQueue
        return result
        
    
    def cancelTask(self, id, worker):
        """
        Terminate task #id running on #worker
        This method should not be invoked directly but by 
        NetWork.task.TaskHandler
        """
        #return self.controlls[CNT_WORKERS][worker].terminateTask(id)
        self.commqueue.put(Command(CMD_TERMINATE_TASK+
                           str(id).encode(encoding='ASCII'), -1))
    
    
    def taskRunning(self, id, worker):
        """
        Check if task #id on #worker is still running
        This method should not be invoked directly but by 
        NetWork.task.TaskHandler
        """
        resultQueue=self.registerQueue()
        self.commqueue.put(Command(CMD_TASK_RUNNING+str(id).encode(encoding="ASCII")+
                           b"TID"+str(resultQueue.id).encode(encoding="ASCII"), -1))
        result=resultQueue.get()
        del resultQueue
        return result
    
    def getException(self, id, worker):
        """
        Get exception raised by task #id on #worker
        This method should not be invoked directly but by 
        NetWork.task.TaskHandler
        """
        resultQueue=self.registerQueue()
        self.commqueue.put(Command(CMD_GET_EXCEPTION+str(id).encode(encoding="ASCII")+
                           b"TID"+str(resultQueue.id).encode(encoding="ASCII"), -1))
        result=resultQueue.get()
        del resultQueue
        return result
    
    def exceptionRaised(self, id, worker):
        """
        Check if task #id on #worker has raised an exception
        This method should not be invoked directly but by 
        NetWork.task.TaskHandler
        """
        resultQueue=self.registerQueue()
        self.commqueue.put(Command(CMD_CHECK_EXCEPTION+str(id).encode(encoding="ASCII")+
                           b"TID"+str(resultQueue.id).encode(encoding="ASCII"), -1))
        result=resultQueue.get()
        del resultQueue
        return result
    
    def waitForEvent(self, id):
        """
        Wait for event #id to be set
        This method should not be invoked directly but by 
        NetWork.event.NWEvent
        """
        event.events[id].wait()
    
    def setEvent(self, id):
        """
        Set event #id
        This method should not be invoked directly but by 
        NetWork.event.NWEvent
        """
        self.commqueue.put(Command(CMD_SET_EVENT+str(id).encode(encoding='ASCII'), -1))
    
    def registerEvent(self):
        """
        Create a new event to be used by the tasks
        Returns an instance of NetWork.event.NWEvent
        """
        self.controlls[CNT_EVENT_COUNT]+=1
        id=self.controlls[CNT_EVENT_COUNT]
        self.commqueue.put(Command(CMD_REGISTER_EVENT+
                           str(id).encode(encoding='ASCII'), -1))
        return event.NWEvent(id, self)
    
    def registerQueue(self):
        """
        Create a new queue to be used by the tasks
        Returns an instance of NetWork.queue.NWQueue
        """
        self.controlls[CNT_QUEUE_COUNT]+=1
        id=self.controlls[CNT_QUEUE_COUNT]
        self.commqueue.put(Command(CMD_REGISTER_QUEUE+str(id).encode(encoding='ASCII'), -1))
        return queue.NWQueue(id, self)
    
    def putOnQueue(self, id, data):
        """
        Put data on queue #id
        This method should not be invoked directly but by 
        NetWork.queue.NWQueue
        """
        self.commqueue.put(Command(CMD_PUT_ON_QUEUE+str(id).encode(encoding='ASCII')+
                           b"ID"+data, -1))
    
    def getFromQueue(self, id):
        """
        Get data from queue #id
        This method should not be invoked directly but by 
        NetWork.queue.NWQueue
        """
        self.commqueue.put(Command(CMD_GET_FROM_QUEUE+str(id).encode(encoding='ASCII'), -1))
        data=queue.queues[id].get()
        return data
    
    def registerLock(self):
        """
        Create a new lock to be used by the tasks
        Returns an instance of NetWork.lock.NWLock
        """
        self.controlls[CNT_LOCK_COUNT]+=1
        id=self.controlls[CNT_LOCK_COUNT]
        self.commqueue.put(Command(CMD_REGISTER_LOCK+str(id).encode(encoding='ASCII'), -1))
        return NWLock(id, self)
    
    def registerManager(self):
        """
        Create a new manager to be used by the tasks
        Returns an instance of NetWork.manager.NWManager
        """
        self.controlls[CNT_MANAGER_COUNT]+=1
        return NWManager(self.controlls[CNT_MANAGER_COUNT], self)
    
    def setManagerItem(self, id, item, value):
        """
        Set new value for the item in the manager #id
        This method should not be invoked directly but by 
        NetWork.manager.NWManager
        """
        self.commqueue.put(Command(CMD_SET_MANAGER_ITEM+pickle.dumps({"ID":id,
                                                                      "ITEM":item,
                                                                      "VALUE":value}), -1))
    
    
        
    
    def acquireLock(self, id):
        """
        Acquire lock #id
        This method should not be invoked directly but by 
        NetWork.lock.NWLock
        """
        self.commqueue.put(Command(CMD_ACQUIRE_LOCK+str(id).encode(encoding='ASCII'), -1))
        lock.locks[id].acquire()
    
    def releaseLock(self, id):
        """
        Release lock #id
        This method should not be invoked directly but by 
        NetWork.lock.NWLock
        """
        self.commqueue.put(Command(CMD_RELEASE_LOCK+str(id).encode(encoding='ASCII'), -1))
    
    def fixDeadWorker(self, id=None, worker=None):
        """
        Handle dead worker
        Not yet complete, NOT WORKING
        """
        salvageDeadWorker(self, id, worker)
    
    def stopServing(self):
        """
        Stop the dispatcher and listener threads
        also invoked when exiting whe 'with' block
        """
        Workgroup.onExit(self)
    
        
        
    
    @staticmethod
    def listenerProcess(listenerSocket, commqueue, controlls):
        """
        A thread that gets requests from workers and passes them to
        dispatcher
        Used internaly by workgroup, not by user
        """
        while True:
            receivedRequest=listenerSocket.accept()
            handlerThread=Thread(target=receiveSocketData, 
                                 args=(receivedRequest, commqueue, controlls))
            handlerThread.start()
                
    
    @staticmethod
    def dispatcherProcess(commqueue, controlls):
        """
        A thread that gets requests from master and workers
        and processes them by calling the apropriate functions from
        NetWork.handlers
        Used internaly by workgroup, not by user
        """
        request=commqueue.get()
        while not request==CMD_HALT:
            #print("REQUEST", request.contents, "FROM", request.requester)
            handlerList[request.type()](request, controlls, commqueue)
            request.close()
            request=commqueue.get()
    
    @staticmethod
    def onExit(target):
        """
        Run on exit to ensure proper cleanup
        Used internaly by workgroup, not by user
        """
        #CLEAN UP WORKERS#####################################
        if (target.running):
            #Need to fix this for a nice exit, preferably with join#########
            target.networkListener.terminate()
            target.commqueue.put(CMD_HALT)
            target.dispatcher.join()
            target.listenerSocket.close()
            target.running=False
        
    
            
