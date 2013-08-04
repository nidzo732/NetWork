import pickle
from .networking import NWSocket
from .commcodes import CMD_PUT_ON_QUEUE, CMD_GET_FROM_QUEUE
from .cntcodes  import CNT_WORKERS
from multiprocessing import Lock, Queue

queues=None
queueHandlers=None
queueLocks=None
runningOnMaster=None
masterAddress=None
class NWQueue:
    
    def __init__(self, id, workgroup):
        self.id=id
        self.workgroup=workgroup
        if runningOnMaster:
            queueHandlers[id]=MasterQueueHandler(id)
            queueLocks[id]=Lock()
        queues[id]=Queue()
    
    def putOnWorker(self, data):
        masterSocket=NWSocket()
        masterSocket.connect(masterAddress)
        masterSocket.send(CMD_PUT_ON_QUEUE+str(self.id).encode(encoding='ASCII')+b"ID"+data)
        masterSocket.close()
    
    def putOnMaster(self, data):
        self.workgroup.putOnQueue(self.id, data)
    
    def getOnWorker(self):
        masterSocket=NWSocket()
        masterSocket.connect(masterAddress)
        masterSocket.send(CMD_GET_FROM_QUEUE+str(self.id).encode(encoding='ASCII'))
        masterSocket.close()
        return queues[self.id].get()
    
    def getOnMaster(self):
        return self.workgroup.getFromQueue(self.id)
    
    def put(self, data):
        pickledData=pickle.dumps(data)
        if runningOnMaster:
            self.putOnMaster(pickledData)
        else:
            self.putOnWorker(pickledData)
    
    def get(self):
        if runningOnMaster:
            return pickle.loads(self.getOnMaster())
        else:
            return pickle.loads(self.getOnWorker())
        
    def __setstate__(self, state):
        self.id=state["id"]
        self.workgroup=state["workgroup"]
    
    def __getstate__(self):
        return {"id":self.id, "workgroup":None}

class MasterQueueHandler:
    def __init__(self, id):
        self.id=id
        self.items=[]
        self.waiters=[]
    
    def putItem(self, data):
        self.items.append(data)
    
    def getItem(self):
        return self.items.pop(0)
    
    def putWaiter(self, id):
        self.waiters.append(id)
    
    def getWaiter(self):
        return self.waiters.pop(0)
    
    def hasWaiters(self):
        return self.waiters
    
    def hasItems(self):
        return self.items

    def distributeContents(self, controlls):
        #print("DISTRIBUTING", self.id, self.items, self.waiters)
        while self.hasItems() and self.hasWaiters():
            waiter=self.getWaiter()
            item=self.getItem()
            if waiter==-1:
                queues[self.id].put(item)
            else:
                controlls[CNT_WORKERS][waiter].putOnQueue(self.id, item)

def registerQueue(request, controlls, commqueue):
    id=int(request.getContents())
    for worker in controlls[CNT_WORKERS]:
        if worker.alive:
            worker.registerQueue(id)

def getFromQueue(request, controlls, commqueue):
    id=int(request.getContents())
    queueLocks[id].acquire()
    workerId=request.requester
    temporaryHandler=queueHandlers[id]
    temporaryHandler.putWaiter(workerId)
    temporaryHandler.distributeContents(controlls)
    queueHandlers[id]=temporaryHandler
    queueLocks[id].release()

def putOnQueue(request, controlls, commqueue):
    contents=request.getContents()
    id=int(contents[:contents.find(b"ID")])
    data=contents[contents.find(b"ID")+2:]
    queueLocks[id].acquire()
    temporaryHandler=queueHandlers[id]
    temporaryHandler.putItem(data)
    temporaryHandler.distributeContents(controlls)
    queueHandlers[id]=temporaryHandler
    queueLocks[id].release()
        