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
from .networking import sendRequest
from .commcodes import CMD_PUT_ON_QUEUE, CMD_GET_FROM_QUEUE, CMD_REGISTER_QUEUE, CMD_WORKER_DIED
from .cntcodes import CNT_WORKERS
from .request import Request
from multiprocessing import Lock, Queue
from .worker import DeadWorkerError

queues = None
queueHandlers = None
queueLocks = None
runningOnMaster = None
masterAddress = None


def masterInit():
    global queues, queueHandlers, queueLocks, runningOnMaster
    queues = {-1: None}
    queueHandlers = {-1: None}
    queueLocks = {-1: None}
    runningOnMaster = True


def workerInit():
    global queues, runningOnMaster
    queues = {-1: None}
    runningOnMaster = False


class NWQueue:
    """
    The queue class used for inter-process communication.
    New instance is usually created with :py:meth:`Workgroup.registerQueue <NetWork.workgroup.Workgroup.registerQueue>`.
    
    To put data on the queue call :py:meth:`put` and call :py:meth:`get` to get it.
    """

    def __init__(self, id, workgroup):
        self.id = id
        self.workgroup = workgroup
        if runningOnMaster:
            queueHandlers[id] = MasterQueueHandler(id)
            queueLocks[id] = Lock()
        queues[id] = Queue()

    def putOnWorker(self, data):
        sendRequest(CMD_PUT_ON_QUEUE,
                    {
                        "ID": self.id,
                        "DATA": data
                    })

    def putOnMaster(self, data):
        self.workgroup.sendRequest(CMD_PUT_ON_QUEUE,
                                   {
                                       "ID": self.id,
                                       "DATA": data
                                   })

    def getOnWorker(self):
        sendRequest(CMD_GET_FROM_QUEUE,
                    {
                        "ID": self.id
                    })
        return queues[self.id].get()

    def getOnMaster(self):
        self.workgroup.sendRequest(CMD_GET_FROM_QUEUE,
                                   {
                                       "ID": self.id
                                   })
        return queues[self.id].get()

    def put(self, data):
        """
        Put data on the queue. A task that calls get will get that data
        
        :Parameters:
          data : any pickleable object
            item to be put on the queue
        """
        if runningOnMaster:
            self.putOnMaster(data)
        else:
            self.putOnWorker(data)

    def get(self):
        """
        Get next item off the queue. If queue is emtpy sleep until something
        gets put on it
        
        :Return: next item in the queue
        """
        if runningOnMaster:
            return self.getOnMaster()
        else:
            return self.getOnWorker()

    def __setstate__(self, state):
        self.id = state["id"]
        self.workgroup = state["workgroup"]

    def __getstate__(self):
        return {"id": self.id, "workgroup": None}


class MasterQueueHandler:
    #A class used on the master to hold information about the queue
    #It has two a list of workers waiting for an item and a list of items waiting
    #to be sent
    def __init__(self, id):
        self.id = id
        self.items = []
        self.waiters = []

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
            waiter = self.getWaiter()
            item = self.getItem()
            if waiter == -1:
                queues[self.id].put(item)
            else:
                controlls[CNT_WORKERS][waiter].sendRequest(CMD_PUT_ON_QUEUE,
                                                           {
                                                               "ID": self.id,
                                                               "DATA": item
                                                           })


def registerQueue(request, controlls, commqueue):
    #A handler used by Workgroup.dispatcher
    id = request["ID"]
    for worker in controlls[CNT_WORKERS]:
        try:
            worker.sendRequest(CMD_REGISTER_QUEUE, {"ID": id})
        except DeadWorkerError:
            commqueue.put(Request(CMD_WORKER_DIED,
                                  {"WORKER": worker}))


def getFromQueue(request, controlls, commqueue):
    #A handler used by Workgroup.dispatcher
    id = request["ID"]
    queueLocks[id].acquire()
    workerId = request.requester
    queueHandlers[id].putWaiter(workerId)
    try:
        queueHandlers[id].distributeContents(controlls)
    except DeadWorkerError as error:
        commqueue.put(Request(CMD_WORKER_DIED,
                              {"WORKER": controlls[CNT_WORKERS][error.id]}))
    queueLocks[id].release()


def putOnQueue(request, controlls, commqueue):
    #A handler used by Workgroup.dispatcher
    id = request["ID"]
    data = request["DATA"]
    queueLocks[id].acquire()
    queueHandlers[id].putItem(data)
    try:
        queueHandlers[id].distributeContents(controlls)
    except DeadWorkerError as error:
        commqueue.put(Request(CMD_WORKER_DIED,
                              {"WORKER": controlls[CNT_WORKERS][error.id]}))
    queueLocks[id].release()