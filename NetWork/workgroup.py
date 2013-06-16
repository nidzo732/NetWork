"""
This file implements a WorkGroup class. It will define a group of worker
computers, distribute their work and provide communication between them.

Created on Jan 11, 2013
"""

from multiprocessing import Process, Queue, Manager, Event
from .networking import NWSocket
from .handlers import receiveSocketData
from threading import Thread
from .worker import Worker, WorkerUnavailableError
from .task import Task, TaskHandler

CNT_WORKERS=0
CNT_SHOULD_STOP=2
CNT_LISTEN_SOCKET=3
CNT_WORKER_COUNT=4
CNT_TASK_COUNT=5

CMD_HALT=b"HLT"  

class NoWorkersError(Exception):pass

def receiveSocketData(socket, commqueue):
    commqueue.put(CMD_SOCKET_MESSAGE+socket.recv())


class Workgroup:    #Not yet implemented

    def __init__(self, workerAddresses, skipBadWorkers=True):
        self.controlls=Manager().list(range(10)) 
        self.controlls[CNT_WORKERS]=[]
        self.controlls[CNT_WORKER_COUNT]=0
        self.controlls[CNT_TASK_COUNT]=0
        self.listenerSocket=NWSocket()
        workerList=[]
        for workerAddress in workerAddresses:
            try:
                newWorker=Worker(workerAddress,
                                 self.controlls[CNT_WORKER_COUNT+1])
                workerList.append(newWorker)
                self.controlls[CNT_WORKER_COUNT]+=1
            except WorkerUnavailableError as workerError:
                if not skipBadWorkers:
                    raise workerError
        self.controlls[CNT_WORKERS]=workerList
        self.currentWorker=-1
        self.commqueue=Queue()
        self.startServing()
    
    def startServing(self):
        self.listenerSocket.listen()
        self.networkListener=Process(target=self.listenerProcess, 
                                     args=(self.listenerSocket, self.commqueue))
        self.dispatcher=Process(target=self.dispatcherProcess, 
                                args=(self.commqueue, self.controlls))
        self.dispatcher.start()
        self.networkListener.start()
    
    def submit(self, target, args=(), kwargs={}):
        self.currentWorker+=1
        self.currentWorker%=self.controlls[CNT_WORKER_COUNT]
        self.controlls[CNT_TASK_COUNT]+=1
        newTask=Task(target, kwargs, self.controlls[CNT_TASK_COUNT])
        self.controlls[CNT_WORKERS][self.currentWorker].executeTask(newTask)
        return TaskHandler(newTask.id, self, self.currentWorker)
    
    def __del__(self):
        self.networkListener.terminate()
        self.dispatcher.terminate()
        self.listenerSocket.close()
        
    
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
        
    
            
