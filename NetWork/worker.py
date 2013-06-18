"""
This file implements a worker class that is used to describe
one worker computer

Created on Jan 12, 2013
"""
class WorkerUnavailableError(Exception):pass
from .networking import NWSocket
from concurrent.futures import ProcessPoolExecutor

class Worker:   
    def __init__(self, address, id):
        workerAvailable=NWSocket.checkAvailability(address)
        if not workerAvailable:
            #Need a better message, I know 
            raise WorkerUnavailableError("Worker refused to cooperate")
        else:
            self.address=address
            self.id=id
        
    def executeTask(self, task):
        pass
        
    def getResult(self, id):
        pass
    
            
            
        
        