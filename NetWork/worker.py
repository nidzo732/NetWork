"""
This file implements a worker class that is used to describe
one worker computer

Created on Jan 12, 2013
"""
class WorkerUnavailableError(Exception):pass
class DeadWorkerError(Exception): pass
from .networking import NWSocket
from concurrent.futures import ProcessPoolExecutor
import pickle
COMCODE_TASK_STARTED=b"TASKSTART"

class Worker:   
    def __init__(self, address, id):
        workerAvailable=NWSocket.checkAvailability(address)
        if not workerAvailable:
            #Need a better message, I know 
            raise WorkerUnavailableError("Worker refused to cooperate")
        else:
            self.address=address
            self.id=id
            self.myTasks={"-1":None}
            self.alive=True
       
    def executeTask(self, task):
        if not self.alive:
            raise DeadWorkerError
        self.myTasks[task.id]=task
        try:
            workerSocket=NWSocket()
            workerSocket.connect(self.address)
            workerSocket.send(b"TSK"+task.marshal())
            if workerSocket.recv()==COMCODE_TASK_STARTED:
                return True
            else:
                raise DeadWorkerError()
        except OSError:
            self.alive=False
            raise DeadWorkerError()
        
        
    def getResult(self, id):
        if not self.alive:
            raise DeadWorkerError
        try:
            workerSocket=NWSocket()
            workerSocket.connect(self.address)
            workerSocket.send(b"RSL"+str(id).encode(encoding="ASCII"))
            return (pickle.loads(workerSocket.recv()))
        except OSError:
            self.alive=False
            raise DeadWorkerError()
    
    def cancelTask(self, id):
        if not self.alive:
            raise DeadWorkerError
        try:
            workerSocket=NWSocket()
            workerSocket.connect(self.address)
            workerSocket.send(b"CNC"+str(id).encode(encoding="ASCII"))
            return (pickle.loads(workerSocket.recv()))
        except OSError:
            self.alive=False
            raise DeadWorkerError()
    
    def taskCancelled(self, id):
        if not self.alive:
            raise DeadWorkerError
        try:
            workerSocket=NWSocket()
            workerSocket.connect(self.address)
            workerSocket.send(b"TCN"+str(id).encode(encoding="ASCII"))
            return (pickle.loads(workerSocket.recv()))
        except OSError:
            self.alive=False
            raise DeadWorkerError()
    
    def taskRunning(self, id):
        if not self.alive:
            raise DeadWorkerError
        try:
            workerSocket=NWSocket()
            workerSocket.connect(self.address)
            workerSocket.send(b"TRN"+str(id).encode(encoding="ASCII"))
            return (pickle.loads(workerSocket.recv()))
        except OSError:
            self.alive=False
            raise DeadWorkerError()
    
    def done(self, id):
        if not self.alive:
            raise DeadWorkerError
        try:
            workerSocket=NWSocket()
            workerSocket.connect(self.address)
            workerSocket.send(b"DON"+str(id).encode(encoding="ASCII"))
            return (pickle.loads(workerSocket.recv()))
        except OSError:
            self.alive=False
            raise DeadWorkerError()
    
    def getException(self, id):
        if not self.alive:
            raise DeadWorkerError
        try:
            workerSocket=NWSocket()
            workerSocket.connect(self.address)
            workerSocket.send(b"EXC"+str(id).encode(encoding="ASCII"))
            return (pickle.loads(workerSocket.recv()))
        except OSError:
            self.alive=False
            raise DeadWorkerError()
    
    
    
            
            
        
        