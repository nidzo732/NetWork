"""
This file implements a WorkGroup class. It will define a group of worker
computers, distribute their work and provide communication between them.

Created on Jan 11, 2013
"""

from multiprocessing import Process, Queue, Manager, Event
from .networking import NWSocket
from .handlers import receiveSocketData
from threading import Thread
from .worker import Worker, WorkerUnavailableError, DeadWorkerError
from .task import Task, TaskHandler

CNT_WORKERS=0
CNT_SHOULD_STOP=2
CNT_LISTEN_SOCKET=3
CNT_WORKER_COUNT=4
CNT_TASK_COUNT=5
CNT_LIVE_WORKERS=6

CMD_HALT=b"HLT"  

class NoWorkersError(Exception):pass
class AllWorkersDeadError(Exception):pass

def receiveSocketData(socket, commqueue):
    commqueue.put(CMD_SOCKET_MESSAGE+socket.recv())


class Workgroup:

    def __init__(self, workerAddresses, skipBadWorkers=True):
        self.controlls=Manager().list(range(10)) 
        self.controlls[CNT_WORKER_COUNT]=0
        self.controlls[CNT_TASK_COUNT]=0
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
        self.commqueue=Queue()
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
        while not self.workerList[self.currentWorker].alive:
            self.currentWorker+=1
            self.currentWorker%=self.controlls[CNT_WORKER_COUNT]
        self.controlls[CNT_TASK_COUNT]+=1
        newTask=Task(target=target, args=args, kwargs=kwargs, 
                     id=self.controlls[CNT_TASK_COUNT])
        try:
            self.workerList[self.currentWorker].executeTask(newTask)
        except DeadWorkerError:
            self.fixDeadWorker(worker=currentWorker)
            return self.submit(target, args, kwargs)
        return TaskHandler(newTask.id, self, self.currentWorker)
    
    def getResult(self, id, worker):
        return self.workerList[worker].getResult(id)
    
    def cancelTask(self, id, worker):
        return self.workerList[worker].cancelTask(id)
    
    def taskCancelled(self, id, worker):
        return self.workerList[worker].taskCancelled(id)
    
    def taskRunning(self, id, worker):
        return self.workerList[worker].taskRunning(id)
    
    def done(self, id, worker):
        return self.workerList[worker].taskDone(id)
    
    def getException(self, id, worker):
        return self.workerList[worker].getException(id)
    
    def fixDeadWorker(self, id=None, worker=None):
        if id:
            if self.workerList[worker].alive:
                self.controlls[CNT_LIVE_WORKERS]-=1
                if not self.controlls[CNT_LIVE_WORKERS]:
                    raise AllWorkersDeadError("Lost connection to all workers")
                self.workerList[worker].alive=False
            failedTask=self.workerList[worker].myTasks[id]
            newHandler=self.submit(failedTask.target, failedTask.args, 
                                   failedTask.kwargs)
            return newHandler
        else:
            self.controlls[CNT_LIVE_WORKERS]-=1
            if not self.controlls[CNT_LIVE_WORKERS]:
                raise AllWorkersDeadError("Lost connection to all workers")
            self.workerList[worker].alive=False
    
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
            request=commqueue.get()
    
    @staticmethod
    def onExit(target):
        #CLEAN UP WORKERS#####################################
        if (target.running):
            target.networkListener.terminate()
            target.dispatcher.terminate()
            target.listenerSocket.close()
            target.running=False
        
    
            
