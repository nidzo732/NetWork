"""
This file implements a worker class that is used to represent
one worker computer

Created on Jan 12, 2013
"""
class WorkerUnavailableError(Exception):pass
class DeadWorkerError(Exception): pass
from .networking import NWSocket
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
        #self.myTasks[task.id]=task
        try:
            workerSocket=NWSocket()
            workerSocket.connect(self.address)
            workerSocket.send(b"TSK"+task)
            workerSocket.close()
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
    
    def terminateTask(self, id):
        if not self.alive:
            raise DeadWorkerError
        try:
            workerSocket=NWSocket()
            workerSocket.connect(self.address)
            workerSocket.send(b"TRM"+str(id).encode(encoding="ASCII"))
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
    
    def exceptionRaised(self, id):
        if not self.alive:
            raise DeadWorkerError
        try:
            workerSocket=NWSocket()
            workerSocket.connect(self.address)
            workerSocket.send(b"EXR"+str(id).encode(encoding="ASCII"))
            return (pickle.loads(workerSocket.recv()))
        except OSError:
            self.alive=False
            raise DeadWorkerError()
    
    def setEvent(self, id):
        if not self.alive:
            raise DeadWorkerError
        try:
            workerSocket=NWSocket()
            workerSocket.connect(self.address)
            workerSocket.send(b"EVS"+str(id).encode(encoding="ASCII"))
        except OSError:
            self.alive=False
            raise DeadWorkerError()
    
    def registerEvent(self, id):
        if not self.alive:
            raise DeadWorkerError
        try:
            workerSocket=NWSocket()
            workerSocket.connect(self.address)
            workerSocket.send(b"EVR"+str(id).encode(encoding="ASCII"))
        except OSError:
            self.alive=False
            raise DeadWorkerError()
    
    def registerQueue(self, id):
        if not self.alive:
            raise DeadWorkerError
        try:
            workerSocket=NWSocket()
            workerSocket.connect(self.address)
            workerSocket.send(b"QUR"+str(id).encode(encoding="ASCII"))
        except OSError:
            self.alive=False
            raise DeadWorkerError()
    
    def putOnQueue(self, id, data):
        #print("WORKER", self.id, "(", self.address, ")", "PUTTING", data, "ON QUEUE", id)
        if not self.alive:
            raise DeadWorkerError
        try:
            workerSocket=NWSocket()
            workerSocket.connect(self.address)
            workerSocket.send(b"QUP"+str(id).encode(encoding="ASCII")+
                              b"ID"+data)
        except OSError:
            self.alive=False
            raise DeadWorkerError()
    
    
            
            
        
        