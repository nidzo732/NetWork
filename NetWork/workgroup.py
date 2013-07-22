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
from NetWork import event

CNT_WORKERS=0
CNT_SHOULD_STOP=2
CNT_LISTEN_SOCKET=3
CNT_WORKER_COUNT=4
CNT_TASK_COUNT=5
CNT_LIVE_WORKERS=6
CNT_EVENT_COUNT=7
CNT_EVENTS=8

CMD_HALT=b"HLT"
CMD_SET_EVENT=b"EVS"
CMD_REGISTER_EVENT=b"EVR"

class NoWorkersError(Exception):pass

def receiveSocketData(socket, commqueue):
    commqueue.put(CMD_SOCKET_MESSAGE+socket.recv())


class Workgroup:

    def __init__(self, workerAddresses, skipBadWorkers=True, 
                 handleDeadWorkers=False):
        self.controlls=Manager().list(range(10)) 
        self.controlls[CNT_WORKER_COUNT]=0
        self.controlls[CNT_TASK_COUNT]=0
        self.controlls[CNT_EVENT_COUNT]=0
        self.controlls[CNT_EVENTS]=[None]
        self.listenerSocket=NWSocket()
        self.workerList={-1:None}
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
        event.runningOnMaster=True
        event.eventLocks={-1:None}
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
                                     args=(self.listenerSocket, self.commqueue))
        self.dispatcher=Process(target=self.dispatcherProcess, 
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
        waiterPipe=controlls[CNT_EVENTS][id].wait()
        event.eventLocks[self.id].acquire()
        event.eventManager[self.id]=eventManager[self.id]
        event.eventLocks[self.id].release()
        if waiterPipe:
            waiterPipe.recv()
            return True
        return True
    
    def setEvent(self, id):
        self.commqueue.put(CMD_SET_EVENT+str(id).encode(encoding='ASCII'))
    
    def registerEvent(self):
        self.controlls[CNT_EVENT_COUNT]+=1
        event.eventLocks[CNT_EVENT_COUNT]=Lock()
        self.commqueue.put(CMD_REGISTER_EVENT+
                           str(self.controlls[CNT_EVENT_COUNT]).encode(encoding='ASCII'))
        return event.NWEvent(self.controlls[CNT_EVENT_COUNT], self)
    
    def fixDeadWorker(self, id=None, worker=None):
        salvageDeadWorker(self, id, worker)
    
    def stopServing(self):
        Workgroup.onExit(self)
    
        
        
    
    @staticmethod
    def listenerProcess(listenerSocket, commqueue):
        while True:
            receivedRequest=listenerSocket.accept()
            handlerThread=Thread(target=receiveSocketData, 
                                 args=(receivedRequest, commqueue))
            handlerThread.start()
                
    
    @staticmethod
    def dispatcherProcess(commqueue, controlls):
        request=commqueue.get()
        while not request==CMD_HALT:
            print(request)
            handlerList[request[:3]](request[3:], controlls, commqueue)
            request=commqueue.get()
    
    @staticmethod
    def onExit(target):
        #CLEAN UP WORKERS#####################################
        if (target.running):
            #Need to fix this for a nice exit, preferably with join#########
            target.networkListener.terminate()
            target.dispatcher.terminate() 
            target.listenerSocket.close()
            target.running=False
        
    
            
