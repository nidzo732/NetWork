"""
This file implements a worker class that is used to represent
one worker computer and send messages to that computer.
"""
class WorkerUnavailableError(Exception):pass
class DeadWorkerError(Exception):
    def __init__(self, id, message=None):
        self.id=id
        Exception.__init__(self, message)

from .networking import NWSocket
import pickle
from .commcodes import *
COMCODE_TASK_STARTED=b"TASKSTART"

class Worker:   
    #A class used to handle one worker
    def __init__(self, address, id):
        workerAvailable=NWSocket.checkAvailability(address)
        if not workerAvailable:
            #Need a better message, I know 
            raise WorkerUnavailableError("Worker "+str(address)+" refused to cooperate")
        else:
            self.address=address
            self.id=id
            self.myTasks={"-1":None}
            self.alive=True
    
    def sendRequest(self, type, contents):
        #Send message to ther worker
        if not self.alive:
            raise DeadWorkerError(self.id)
        try:
            workerSocket=NWSocket()
            workerSocket.connect(self.address)
            workerSocket.send(type+pickle.dumps(contents))
            workerSocket.close()
        except OSError:
            self.alive=False
            raise DeadWorkerError(self.id)
    
    def sendRequestWithResponse(self, type, contents):
        #Send message to the worker and get the response
        if not self.alive:
            raise DeadWorkerError(self.id)
        try:
            workerSocket=NWSocket()
            workerSocket.connect(self.address)
            workerSocket.send(type+pickle.dumps(contents))
            response=workerSocket.recv()
            workerSocket.close()
            return response
        except OSError:
            self.alive=False
            raise DeadWorkerError(self.id)
       
    def executeTask(self, task):
        self.myTasks[task.id]=task
        self.sendRequest(CMD_SUBMIT_TASK, {"TASK":task})
        
        
    def getResult(self, id):
        return pickle.loads(self.sendRequestWithResponse(CMD_GET_RESULT,
                                                         {
                                                          "ID":id
                                                          }))
    
    def terminateTask(self, id):
        self.sendRequest(CMD_TERMINATE_TASK,
                         {
                          "ID":id
                          })
    
    def taskRunning(self, id):
        return pickle.loads(self.sendRequestWithResponse(CMD_TASK_RUNNING,
                                            {
                                             "ID":id
                                             }))
    
    def getException(self, id):
        return pickle.loads(self.sendRequestWithResponse(CMD_GET_EXCEPTION,
                                                         {
                                                          "ID":id
                                                          }))
    
    def exceptionRaised(self, id):
        return pickle.loads(self.sendRequestWithResponse(CMD_CHECK_EXCEPTION,
                                                         {
                                                          "ID":id
                                                          }))
