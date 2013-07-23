from .networking import NWSocket
from multiprocessing import Pipe
class WrongComputerError(Exception):pass
runningOnMaster=None
masterAddress=None
events=None
class NWEvent:
    def __init__(self, id, workgroup=None):
        self.id=id
        self.workgroup=workgroup
    
    def waitOnWorker(self):
        events[self.id].wait()
    
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
    
    