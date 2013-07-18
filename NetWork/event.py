from .networking import NWSocket
class WrongComputerError(Exception):pass
eventManager=None
runningOnMaster=None
masterAddress=None
class WorkerEvent:
    def __init__(self, eventId):
        self.eventId=eventId
    
    def verifiyWorker(self):
        if runningOnMaster:
            raise WrongComputerError("This method should be ran on worker nodes")
    
    def wait(self):
        self.verifiyWorker()
        eventManager[self.eventId][0].recv()
    
    def set(self):
        self.verifiyWorker()
        masterSocket=NWSocket()
        masterSocket.connect(masterAddress)
        masterSocket.send(b"EVS"+str(self.eventId).encode(encoding='ASCII'))
        masterSocket.close()

class MasterEvent:
    def __init__(self, eventId, workgroup):    
        self.eventId=eventId
        self.workgroup=workgroup
    
    def verifiyMaster(self):
        if not runningOnMaster:
            raise WrongComputerError("This method should be ran on master nodes")
    
    def wait(self):
        self.verifiyMaster()
        self.workgroup.waitForEvent(self.eventId)
    
    def set(self, v):
        self.verifiyMaster()
        self.workgroup.setEvent(self.eventId)