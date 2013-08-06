"""
This file implements a worker class that is used to represent
one worker computer

Created on Jan 12, 2013
"""
class WorkerUnavailableError(Exception):pass
class DeadWorkerError(Exception): pass
from .networking import NWSocket
import pickle
from .commcodes import *
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
    
    def sendMessage(self, message):
        if not self.alive:
            raise DeadWorkerError
        try:
            workerSocket=NWSocket()
            workerSocket.connect(self.address)
            workerSocket.send(message)
            workerSocket.close()
        except OSError:
            self.alive=False
            raise DeadWorkerError()
    
    def sendMessageWithResponse(self, message):
        if not self.alive:
            raise DeadWorkerError
        try:
            workerSocket=NWSocket()
            workerSocket.connect(self.address)
            workerSocket.send(message)
            response=workerSocket.recv()
            workerSocket.close()
            return response
        except OSError:
            self.alive=False
            raise DeadWorkerError()
       
    def executeTask(self, task):
        #self.myTasks[task.id]=task
        self.sendMessage(b"TSK"+task)
        
        
    def getResult(self, id):
        return pickle.loads(self.sendMessageWithResponse(b"RSL"+str(id).encode(encoding="ASCII")))
    
    def terminateTask(self, id):
        self.sendMessage(b"TRM"+str(id).encode(encoding="ASCII"))
    
    def taskRunning(self, id):
        return self.sendMessageWithResponse(b"TRN"+str(id).encode(encoding="ASCII"))
    
    def getException(self, id):
        return pickle.loads(self.sendMessageWithResponse(b"EXC"+str(id).encode(encoding="ASCII")))
    
    def exceptionRaised(self, id):
        return pickle.loads(self.sendMessageWithResponse(b"EXR"+str(id).encode(encoding="ASCII")))
    
    def setEvent(self, id):
        self.sendMessage(b"EVS"+str(id).encode(encoding="ASCII"))
    
    def registerEvent(self, id):
        self.sendMessage(b"EVR"+str(id).encode(encoding="ASCII"))
    
    def registerQueue(self, id):
        self.sendMessage(b"QUR"+str(id).encode(encoding="ASCII"))
    
    def putOnQueue(self, id, data):
        self.sendMessage(b"QUP"+str(id).encode(encoding="ASCII")+b"ID"+data)
    
    def registerLock(self, id):
        self.sendMessage(CMD_REGISTER_LOCK+str(id).encode(encoding="ASCII"))
    
    def releaseLock(self, id):
        self.sendMessage(CMD_RELEASE_LOCK+str(id).encode(encoding="ASCII"))
