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

    from NetWork import Workgroup, Queue
    def getIncrementPut(inputQueue, outputQueue):
        number=inputQueue.get()
        number+=1
        outputQueue.put(number)
    
    with Workgroup(addresses) as w:
        queue1=Queue(w)
        queue2=Queue(w)
        queue3=Queue(w)
        queue4=Queue(w)
        queue5=Queue(w)
        task1=w.submit(target=getIncrementPut, args=(queue1, queue2))
        task2=w.submit(target=getIncrementPut, args=(queue2, queue3))
        task3=w.submit(target=getIncrementPut, args=(queue3, queue4))
        task4=w.submit(target=getIncrementPut, args=(queue4, queue5))
        queue1.put(1)
        print(queue5.get())    #Prints '5'

"""
from multiprocessing import Lock, Queue

from .request import sendRequest
from .commcodes import CMD_WORKER_DIED
from .cntcodes import CNT_WORKERS
from .request import Request
from .worker import DeadWorkerError


CMD_REGISTER_QUEUE = b"QUR"
CMD_PUT_ON_QUEUE = b"QUP"
CMD_GET_FROM_QUEUE = b"QUG"
CNT_QUEUE_COUNT = "QUEUE_COUNT"

queues = None
queueHandlers = None
queueLocks = None
runningOnMaster = None
masterAddress = None


def masterInit(workgroup):
    global queues, queueHandlers, queueLocks, runningOnMaster
    queues = {-1: None}
    queueHandlers = {-1: None}
    queueLocks = {-1: None}
    runningOnMaster = True
    workgroup.controls[CNT_QUEUE_COUNT] = 0


def workerInit():
    global queues, runningOnMaster
    queues = {-1: None}
    runningOnMaster = False


class NWQueue:
    """
    The queue class used for inter-process communication.
    To put data on the queue call :py:meth:`put` and call :py:meth:`get` to get it.

    :type workgroup: NetWork.workgroup.Workgroup
    :param workgroup: workgroup that will be using this Queue
    """

    def __init__(self, workgroup):
        self.workgroup = workgroup
        self.workgroup.controls[CNT_QUEUE_COUNT] += 1
        self.id = self.workgroup.controls[CNT_QUEUE_COUNT]
        if runningOnMaster:
            queueHandlers[self.id] = MasterQueueHandler(self.id)
            queueLocks[self.id] = Lock()
        queues[self.id] = Queue()
        sendRequest(CMD_REGISTER_QUEUE,
                                   {
                                       "ID": self.id
                                   })


    def put(self, data):
        """
        Put data on the queue. A task that calls get will get that data
        
        :type data: any pickleable object
        :param  data: item to be put on the queue
        """
        sendRequest(CMD_PUT_ON_QUEUE,
                                   {
                                       "ID": self.id,
                                       "DATA": data
                                   })

    def get(self):
        """
        Get next item off the queue. If queue is emtpy sleep until something
        gets put on it
        
        :return: next item in the queue
        """
        sendRequest(CMD_GET_FROM_QUEUE,
                    {
                        "ID": self.id
                    })
        return queues[self.id].get()

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


def registerQueueMaster(request, controlls):
    #A handler used by Workgroup.dispatcher
    id = request["ID"]
    for worker in controlls[CNT_WORKERS]:
        worker.sendRequest(CMD_REGISTER_QUEUE, {"ID": id})


def getFromQueueMaster(request, controlls):
    #A handler used by Workgroup.dispatcher
    id = request["ID"]
    queueLocks[id].acquire()
    workerId = request.requester
    queueHandlers[id].putWaiter(workerId)
    queueHandlers[id].distributeContents(controlls)
    queueLocks[id].release()


def putOnQueueMaster(request, controlls):
    #A handler used by Workgroup.dispatcher
    id = request["ID"]
    data = request["DATA"]
    queueLocks[id].acquire()
    queueHandlers[id].putItem(data)
    queueHandlers[id].distributeContents(controlls)
    queueLocks[id].release()


def putOnQueueWorker(request):
    id = request["ID"]
    queues[id].put(request["DATA"])


def registerQueueWorker(request):
    queues[request["ID"]] = Queue()

masterHandlers = {CMD_GET_FROM_QUEUE: getFromQueueMaster, CMD_PUT_ON_QUEUE: putOnQueueMaster,
                  CMD_REGISTER_QUEUE: registerQueueMaster}
workerHandlers = {CMD_REGISTER_QUEUE: registerQueueWorker, CMD_PUT_ON_QUEUE: putOnQueueWorker}