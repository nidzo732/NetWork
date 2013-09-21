from multiprocessing import Semaphore, Lock
from .networking import sendRequest
from .commcodes import CMD_ACQUIRE_SEMAPHORE, CMD_RELEASE_SEMAPHORE, CMD_REGISTER_SEMAPHORE, CMD_WORKER_DIED
from .cntcodes import CNT_WORKERS
from .request import Request
from .worker import DeadWorkerError
runningOnMaster=None
semaphores=None
semaphoreHandlers=None
semaphoreLocks=None
masterAddress=None

class NWSemaphore:
    """
    The semaphore class used to limit simultaneous execution.
    New instance is usually created with :py:meth:`Workgroup.registerSemaphore <NetWork.workgroup.Workgroup.registerLock>`.
    
    When entering critical section call :py:meth:`acquire` and when exiting :py:meth:`release`.
    """
    
    def __init__(self, id, workgroup, value):
        self.id=id
        self.workgroup=workgroup
        if runningOnMaster:
            semaphoreLocks[id]=Lock()
            semaphoreHandlers[id]=MasterSemaphoreHandler(id, value)
        semaphores[id]=Semaphore(value)
        for i in range(value):
            semaphores[id].acquire()
    
    def acquireOnMaster(self):
        self.workgroup.sendRequest(CMD_ACQUIRE_SEMAPHORE,
                                   {
                                    "ID":self.id
                                    })
        semaphores[self.id].acquire()
    
    def releaseOnMaster(self):
        self.workgroup.sendRequest(CMD_RELEASE_SEMAPHORE,
                                   {
                                    "ID":self.id
                                    })
    
    def acquireOnWorker(self):
        sendRequest(CMD_ACQUIRE_SEMAPHORE,
                    {
                     "ID":self.id
                     })
        semaphores[self.id].acquire()
    
    def releaseOnWorker(self):
        sendRequest(CMD_RELEASE_SEMAPHORE,
                    {
                     "ID":self.id
                     })
    
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

class MasterSemaphoreHandler:
    #A class used to hold information about semaphores on the master
    #It has a waiters list that holds a list of workers waiting to acquire
    #the semaphore, when the semaphore
    #is released a message is send to the first waiter in the list
    def __init__(self, id, value):
        semaphoreLocks[id].acquire()
        self.id=id
        self.value=value
        self.waiters=[]
        semaphoreLocks[id].release()
    
    def acquire(self, requester, controlls):
        #Acquire semaphore or wait for release
        semaphoreLocks[self.id].acquire()
        if not self.value:
            self.waiters.append(requester)
        else:
            self.value=self.value-1
            print(self.value)
            if requester==-1:
                semaphores[self.id].release()
            else:
                controlls[CNT_WORKERS][requester].sendRequest(CMD_RELEASE_SEMAPHORE,
                                                              {
                                                               "ID":self.id
                                                               })
        semaphoreLocks[self.id].release()
    
    def release(self, controlls):
        #Release semaphore and wake up the first from the waiting list
        semaphoreLocks[self.id].acquire()
        if self.waiters:
            id=self.waiters.pop(0)
            if id==-1:
                semaphores[self.id].release()
            else:
                controlls[CNT_WORKERS][id].sendRequest(CMD_RELEASE_SEMAPHORE,
                                                       {
                                                        "ID":self.id
                                                        })
        else:
            self.value+=1
        semaphoreLocks[self.id].release()

def registerSemaphore(request, controlls, commqueue):
    #A handler used by Workgroup.dispatcher
    id=request["ID"]
    value=request["VALUE"]
    for worker in controlls[CNT_WORKERS]:
        try:
            worker.sendRequest(CMD_REGISTER_SEMAPHORE, {"ID":id, "VALUE":value})
        except DeadWorkerError:
            commqueue.put(Request(CMD_WORKER_DIED, 
                          {"WORKER":worker}))
            
def acquireSemaphore(request, controlls, commqueue):
    #A handler used by Workgroup.dispatcher
    try:
        semaphoreHandlers[request["ID"]].acquire(request.requester, controlls)
    except DeadWorkerError as error:
        commqueue.put(Request(CMD_WORKER_DIED, 
                      {"WORKER":controlls[CNT_WORKERS][error.id]}))

def releaseSemaphore(request, controlls, commqueue):
    #A handler used by Workgroup.dispatcher
    try:
        semaphoreHandlers[request["ID"]].release(controlls)
    except DeadWorkerError as error:
        commqueue.put(Request(CMD_WORKER_DIED, 
                      {"WORKER":controlls[CNT_WORKERS][error.id]}))