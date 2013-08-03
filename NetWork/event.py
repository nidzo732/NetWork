from .networking import NWSocket
from multiprocessing import Event
from .commcodes import CMD_SET_EVENT
from .workgroup import CNT_WORKERS
class WrongComputerError(Exception):pass
runningOnMaster=None
masterAddress=None
events=None
class NWEvent:
    def __init__(self, id, workgroup=None):
        self.id=id
        self.workgroup=workgroup
        events[id]=Event()
    
    def waitOnWorker(self):
        events[self.id].wait()
    
    def setOnWorker(self):
        masterSocket=NWSocket()
        masterSocket.connect(masterAddress)
        masterSocket.send(CMD_SET_EVENT+str(self.id).encode(encoding='ASCII'))
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
    
    def __setstate__(self, state):
        self.id=state["id"]
        self.workgroup=state["workgroup"]
    
    def __getstate__(self):
        return {"id":self.id, "workgroup":None}

def setEvent(request, controlls, commqueue):
    id=int(request.getContents())
    for worker in controlls[CNT_WORKERS]:
        if worker.alive:
            worker.setEvent(id)
    events[id].set()
    
def registerEvent(request, controlls, commqueue):
    id=int(request.getContents())
    for worker in controlls[CNT_WORKERS]:
        if worker.alive:
            worker.registerEvent(id)
    