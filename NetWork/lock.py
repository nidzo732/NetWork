from multiprocessing import Lock
from .networking import NWSocket
from .commcodes import CMD_ACQUIRE_LOCK, CMD_RELEASE_LOCK
from .cntcodes import CNT_WORKERS
runningOnMaster=None
locks=None
lockHandlers=None
lockLocks=None

class NWLock:
    
    def __init__(self, id, workgroup):
        self.id=id
        self.workgroup=workgroup
        if runningOnMaster:
            lockLocks[id]=Lock()
            lockHandlers[id]=MasterLockHandler(id)
        locks[id]=Lock()
        locks[id].acquire()
    
    def acquireOnMaster(self):
        self.workgroup.acquireLock()
    
    def releaseOnMaster(self):
        self.workgroup.releaseLock()
    
    def acquireOnWorker(self):
        masterSocket=NWSocket()
        masterSocket.connect(masterAddress)
        masterSocket.send(CMD_ACQUIRE_LOCK+str(self.id).encode(encoding='ASCII'))
        masterSocket.close()
        locks[self.id].acquire()
    
    def releaseOnWorker(self):
        masterSocket=NWSocket()
        masterSocket.connect(masterAddress)
        masterSocket.send(CMD_RELEASE_LOCK+str(self.id).encode(encoding='ASCII'))
        masterSocket.close()
    
    def acquire(self):
        if runningOnMaster:
            self.acquireOnMaster()
        else:
            self.acquireOnWorker()
    
    def release(self):
        if runningOnMaster:
            self.releaseOnMaster()
        else:
            self.releaseOnWorker()
    
    def __setstate__(self, state):
        self.id=state["id"]
        self.workgroup=state["workgroup"]
    
    def __getstate__(self):
        return {"id":self.id, "workgroup":None}

class MasterLockHandler:
    
    def __init__(self, id):
        lockLocks[id].acquire()
        self.id=id
        self.locked=False
        self.waiters=[]
        lockLocks[id].release()
    
    def acquire(self, requester, controlls):
        lockLocks[self.id].acquire()
        if self.locked:
            self.waiters.append(requester)
        else:
            self.locked=True
            controlls[requester].releaseLock(self.id)
        lockLocks[self.id].release()
    
    def release(self, controlls):
        lockLocks[self.id].acquire()
        if self.waiters:
            id=self.waiters.pop(0)
            if id==-1:
                locks[self.id].release()
            else:
                controlls[CNT_WORKERS].releaseLock(self.id)
        else:
            self.locked=False
        lockLocks[self.id].release()

def registerLock(request, controlls, commqueue):
    id=int(request.contents())
    for worker in controlls[CNT_WORKERS]:
        worker.registerLock(id)

def acquireLock(request, controlls, commqueue):
    lockHandlers[int(request.contents())].acquire(request.requester, controlls)

def releaseLock(request, controlls, commqueue):
    lockHandlers[int(request.contents())].release(controlls)
        
    
    