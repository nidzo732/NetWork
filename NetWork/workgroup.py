"""
This file implements a WorkGroup class. It will define a group of worker
computers, distribute their work and provide communication between them.

Created on Jan 11, 2013
"""

from multiprocessing import Process, Queue, Manager, Event
from .networking import NWSocket
from .handlers import receiveSocketData, handlerList
from threading import Thread
from .worker import Worker, WorkerUnavailableError, DeadWorkerError
from .task import Task, TaskHandler
from .deadworkerhandler import salvageDeadWorker
from NetWork import event, queue

CNT_WORKERS=0
CNT_SHOULD_STOP=2
CNT_LISTEN_SOCKET=3
CNT_WORKER_COUNT=4
CNT_TASK_COUNT=5
CNT_LIVE_WORKERS=6
CNT_EVENT_COUNT=7
CNT_QUEUE_COUNT=8

CMD_HALT=b"HLT"
CMD_SET_EVENT=b"EVS"
CMD_REGISTER_EVENT=b"EVR"
CMD_REGISTER_QUEUE=b"QUR"
CMD_PUT_ON_QUEUE=b"QUP"
CMD_GET_FROM_QUEUE=b"QUG"

class NoWorkersError(Exception):pass

class Command:
    def __init__(self, contents, requester):
        self.contents=contents
        self.requester=requester
    
    def getContents(self):
        return self.contents[3:]
    
    def type(self):
        return self.contents[:3]

def receiveSocketData(socket, commqueue, controlls):
    workerId=0
    for worker in controlls[CNT_WORKERS]:
        if socket.address==worker.address:
            workerId=worker.id
    if not workerId:
        return
    commqueue.put(Command(workerId, socker.recv()))
    socket.close()


class Workgroup:

    def __init__(self, workerAddresses, skipBadWorkers=False, 
                 handleDeadWorkers=False):
        self.controlls=Manager().list(range(20)) 
        self.controlls[CNT_WORKER_COUNT]=0
        self.controlls[CNT_TASK_COUNT]=0
        self.controlls[CNT_EVENT_COUNT]=0
        self.controlls[CNT_QUEUE_COUNT]=0
        self.listenerSocket=NWSocket()
        self.workerList=[]
        for workerAddress in workerAddresses:
            try:
                newWorker=Worker(workerAddress,
                                 self.controlls[CNT_WORKER_COUNT+1])
                self.workerList.append(newWorker)
                self.controlls[CNT_WORKER_COUNT]+=1
            except WorkerUnavailableError as workerError:
                if not skipBadWorkers:
                    raise workerError
        self.currentWorker=-1
        self.controlls[CNT_LIVE_WORKERS]=self.controlls[CNT_WORKER_COUNT]
        self.controlls[CNT_WORKERS]=self.workerList
        self.commqueue=Queue()
        event.events={-1:None}
        event.runningOnMaster=True
        queue.queues={-1:None}
        queue.queueHandlers=Manager().dict()
        queue.queueLocks={-1:None}
        self.handleDeadWorkers=handleDeadWorkers
        self.running=False
        
    def __enter__(self):
        self.startServing()
        return self
    
    def __exit__(self, exceptionType, exceptionValue, traceBack):
        self.stopServing()
    
    def startServing(self):
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
        self.currentWorker+=1
        self.currentWorker%=self.controlls[CNT_WORKER_COUNT]
        while not self.controlls[CNT_WORKERS][self.currentWorker].alive:
            self.currentWorker+=1
            self.currentWorker%=self.controlls[CNT_WORKER_COUNT]
        self.controlls[CNT_TASK_COUNT]+=1
        newTask=Task(target=target, args=args, kwargs=kwargs, 
                     id=self.controlls[CNT_TASK_COUNT])
        try:
            self.controlls[CNT_WORKERS][self.currentWorker].executeTask(newTask)
        except DeadWorkerError:
            self.fixDeadWorker(worker=self.currentWorker)
            return self.submit(target, args, kwargs)
        return TaskHandler(newTask.id, self, self.currentWorker)
    
    def getResult(self, id, worker):
        return self.controlls[CNT_WORKERS][worker].getResult(id)
    
    def cancelTask(self, id, worker):
        return self.controlls[CNT_WORKERS][worker].terminateTask(id)
    
    
    def taskRunning(self, id, worker):
        return self.controlls[CNT_WORKERS][worker].taskRunning(id)
    
    def getException(self, id, worker):
        return self.controlls[CNT_WORKERS][worker].getException(id)
    
    def exceptionRaised(self, id, worker):
        return self.controlls[CNT_WORKERS][worker].exceptionRaised(id)
    
    def waitForEvent(self, id):
        event.events[id].wait()
    
    def setEvent(self, id):
        self.commqueue.put(Command(CMD_SET_EVENT+str(id).encode(encoding='ASCII'), 0))
    
    def registerEvent(self):
        self.controlls[CNT_EVENT_COUNT]+=1
        id=self.controlls[CNT_EVENT_COUNT]
        event.events[id]=Event()
        self.commqueue.put(Command(CMD_REGISTER_EVENT+
                           str(id).encode(encoding='ASCII'), 0))
        return event.NWEvent(id, self)
    
    def registerQueue(self):
        self.controlls[CNT_QUEUE_COUNT]+=1
        id=self.controlls[CNT_QUEUE_COUNT]
        queue.queueHandlers[id]=queue.MasterQueueHandler(id)
        queue.queues[id]=Queue()
        queue.queueLocks[id]=Lock()
        self.commqueue.put(Command(CMD_REGISTER_QUEUE+str(id).encode(encoding='ASCII'), 0))
        return queue.NWQueue(id, self)
    
    def putOnQueue(self, id, data):
        self.commqueue.put(Command(CMD_PUT_ON_QUEUE+str(id).encode(encoding='ASCII')+
                           b"ID"+data, 0))
    
    def getFromQueue(self, id):
        self.commqueue.put(Command(CMD_GET_FROM_QUEUE+str(id).encode(encoding='ASCII'), 0))
        return queue.queues[id].get()
    
    def fixDeadWorker(self, id=None, worker=None):
        salvageDeadWorker(self, id, worker)
    
    def stopServing(self):
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
            #print(request)
            handlerList[request.type()](request, controlls, commqueue)
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
        
    
            
