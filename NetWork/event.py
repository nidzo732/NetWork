from .networking import NWSocket
class WrongComputerError(Exception):pass
eventManager=None
runningOnMaster=None
masterAddress=None
eventLocks=None
class NWEvent:
    def __init__(self, eventId, workgroup=None):
        self.eventId=eventId
        self.workgroup=workgroup
    
    def waitOnWorker(self):
        waiterPipe=eventManager[self.id].wait()
        eventLocks[self.id].acquire()
        eventManager[self.id]=eventManager[self.id]
        eventLocks[self.id].release()
        if waiterPipe:
            waiterPipe.recv()
            return True
        return True
    
    def setOnWorker(self):
        self.verifiyWorker()
        masterSocket=NWSocket()
        masterSocket.connect(masterAddress)
        masterSocket.send(b"EVS"+str(self.eventId).encode(encoding='ASCII'))
        masterSocket.close()
    
    def waitOnMaster(self):
        return self.workgroup.waitForEvent(self.eventId)
    
    def setOnMaster(self):
        self.workgroup.setEvent(self.eventId)
    
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

class LocalEventHandler:
    
    def __init__(self, id):
        self.id=id
        self.isSet=False
        self.pipes=[]
    
    def set(self):
        eventLocks[self.id].acquire()
        self.isSet=True
        for currentPipe in self.pipes:
            currentPipe[0].send(b"SET")
        eventLocks[self.id].release()
    
    def wait(self):
        eventLocks[self.id].acquire()
        if self.isSet:
            eventLocks[self.id].release()
            return None
        else:
            self.pipes.append(Pipe())
            pipeIndex=len(self.pipes)-1
            eventLocks[self.id].release()
            return self.pipes[pipeIndex]
    
    