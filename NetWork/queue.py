"""
Queues are tools used for inter process communication, they are similar to
pipes and fifos but they are thread-safe and can have multiple producers and
consumers. 
Any pickleable object can be sent throug a Queue using it's :py:meth:`put <NWQueue.put>`
method. One task puts an item and another task calls :py:meth:`get <NWQueue.get>` method
of the same queue and receives the sent item, if the queue is empty the task sleeps
until another task puts something on the queue.
The items are aranged in FIFO order, first item given to the :py:meth:`put <NWQueue.put>` method
is the first item returned by the :py:meth:`get <NWQueue.get>` method.

For more info about queues see `Python documentation page <http://docs.python.org/3.3/library/queue.html#module-queue>`_
::
    
    #Example of queue usage
    #Tasks are linked in a chain
    #Each task has inputQueue and outputQueue
    #A task gets a number from it's inputQueue increments it and puts it to outputQueue
    
    def getIncrementPut(inputQueue, outputQueue):
        number=inputQueue.get()
        number+=1
        outputQueue.put(number)
    
    with Workgroup(addresses) as w:
        queue1=w.registerQueue()
        queue2=w.registerQueue()
        queue3=w.registerQueue()
        queue4=w.registerQueue()
        queue5=w.registerQueue()
        task1=w.submit(target=getIncrementPut, args=(queue1, queue2))
        task2=w.submit(target=getIncrementPut, args=(queue2, queue3))
        task3=w.submit(target=getIncrementPut, args=(queue3, queue4))
        task4=w.submit(target=getIncrementPut, args=(queue4, queue5))
        queue1.put(1)
        print(queue5.get())    #Prints '5'

"""
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
    """
    The queue class used for inter-process communication.
    New instance is usually created with :py:meth:`Workgroup.registerQueue <NetWork.workgroup.Workgroup.registerQueue>`.
    
    To put data on the queue call :py:meth:`put` and call :py:meth:`get` to get it.
    """
    
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
        self.workgroup.sendRequest(CMD_PUT_ON_QUEUE+str(self.id).encode(encoding='ASCII')+
                           b"ID"+data,)
    
    def getOnWorker(self):
        masterSocket=NWSocket()
        masterSocket.connect(masterAddress)
        masterSocket.send(CMD_GET_FROM_QUEUE+str(self.id).encode(encoding='ASCII'))
        masterSocket.close()
        return queues[self.id].get()
    
    def getOnMaster(self):
        self.workgroup.sendRequest(CMD_GET_FROM_QUEUE+str(self.id).encode(encoding='ASCII'))
        return queues[self.id].get()
        
    
    def put(self, data):
        """
        Put data on the queue. A task that calls get will get that data
        
        :Parameters:
          data : any pickleable object
            item to be put on the queue
        """
        pickledData=pickle.dumps(data)
        if runningOnMaster:
            self.putOnMaster(pickledData)
        else:
            self.putOnWorker(pickledData)
    
    def get(self):
        """
        Get next item off the queue. If queue is emtpy sleep until something
        gets put on it
        
        :Return: next item in the queue
        """
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
    #A class used on the master to hold information about the queue
    #It has two a list of workers waiting for an item and a list of items waiting
    #to be sent
    def __init__(self, id):
        self.id=id
        self.items=[]
        self.waiters=[]
    
    def putItem(self, data):
        #put items on the queue
        self.items.append(data)
    
    def getItem(self):
        #get the first item from the items list
        return self.items.pop(0)
    
    def putWaiter(self, id):
        #add a waiter to the waiter list
        self.waiters.append(id)
    
    def getWaiter(self):
        #get the first waiter from the waiters list
        return self.waiters.pop(0)
    
    def hasWaiters(self):
        #check if queue has waiters
        return self.waiters
    
    def hasItems(self):
        #check if queue has items
        return self.items

    def distributeContents(self, controlls):
        #if there are both items and waiters, send items to the waiters
        #print("DISTRIBUTING", self.id, self.items, self.waiters)#used for debuging
        while self.hasItems() and self.hasWaiters():
            waiter=self.getWaiter()
            item=self.getItem()
            if waiter==-1:
                queues[self.id].put(item)
            else:
                controlls[CNT_WORKERS][waiter].putOnQueue(self.id, item)

def registerQueue(request, controlls, commqueue):
    #A handler used by Workgroup.dispatcher
    id=int(request.getContents())
    for worker in controlls[CNT_WORKERS]:
        if worker.alive:
            worker.registerQueue(id)

def getFromQueue(request, controlls, commqueue):
    #A handler used by Workgroup.dispatcher
    id=int(request.getContents())
    queueLocks[id].acquire()
    workerId=request.requester
    temporaryHandler=queueHandlers[id]
    temporaryHandler.putWaiter(workerId)
    temporaryHandler.distributeContents(controlls)
    queueHandlers[id]=temporaryHandler
    queueLocks[id].release()

def putOnQueue(request, controlls, commqueue):
    #A handler used by Workgroup.dispatcher
    contents=request.getContents()
    id=int(contents[:contents.find(b"ID")])
    data=contents[contents.find(b"ID")+2:]
    queueLocks[id].acquire()
    temporaryHandler=queueHandlers[id]
    temporaryHandler.putItem(data)
    temporaryHandler.distributeContents(controlls)
    queueHandlers[id]=temporaryHandler
    queueLocks[id].release()
        