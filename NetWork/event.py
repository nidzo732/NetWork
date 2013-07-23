from .networking import NWSocket
from multiprocessing import Pipe
class WrongComputerError(Exception):pass
runningOnMaster=None
masterAddress=None
eventLocks=None
eventPipes=None
eventStates=None
class NWEvent:
    def __init__(self, id, workgroup=None):
        self.id=id
        self.workgroup=workgroup
    
    def waitOnWorker(self):
        eventLocks[self.id].acquire()
        if eventStates[self.id]:
            eventLocks[self.id].release()
            return True
        else:
            pipeList=eventPipes[self.id]
            pipeList.append(Pipe())
            myPipe=len(pipeList)-1
            eventPipes[self.id]=pipeList
            eventLocks[self.id].release()
            eventPipes[self.id][myPipe][1].recv()
            return True
    
    def setOnWorker(self):
        masterSocket=NWSocket()
        masterSocket.connect(masterAddress)
        masterSocket.send(b"EVS"+str(self.id).encode(encoding='ASCII'))
        masterSocket.close()
    
    def waitOnMaster(self):
        return self.workgroup.waitForEvent(self.id)
    
    def setOnMaster(self):
        self.workgroup.setEvent(self.id)
    
    def set(self):
        if runningOnMaster:
            self.setOnMaster()
        else:
            self.setOnWorker()
    
    def wait(self):
        if runningOnMaster:
            self.waitOnMaster()
        else:
            self.waitOnWorker()
    
    @staticmethod
    def setLocalEvent(id):
        eventLocks[id].acquire()
        eventStates[id]=True
        for pipePair in eventPipes[id]:
            pipePair[0].send(b"EVS")
        eventLocks[id].release()
    
    