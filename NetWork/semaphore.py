"""
Semaphores are used to limit simultaneous execution of taks.

All semaphores have a counter value that determines how many paralel tasks
can acquire the semaphore. When a task enters a critical section of code, 
it calls :py:meth:`acquire <NWSemaphore.acquire>` method, if the counter
value is greater than zero it gets decremented and the task goes on, if
the value is zero the task is put to sleep until one of the tasks that 
has acquired the semaphore calls :py:meth:`release <NWSemaphore.release>` 
method.

For more info about semaphores see `Python documentation page
<http://docs.python.org/2/library/threading.html#semaphore-objects>`_
"""
from multiprocessing import Semaphore, Lock
from .networking import sendRequest
from .commcodes import CMD_WORKER_DIED
from .cntcodes import CNT_WORKERS
from .request import Request
from .worker import DeadWorkerError

CMD_REGISTER_SEMAPHORE = b"SER"
CMD_ACQUIRE_SEMAPHORE = b"SEA"
CMD_RELEASE_SEMAPHORE = b"SEU"
CNT_SEMAPHORE_COUNT = "SEMAPHORE_COUNT"

runningOnMaster = None
semaphores = None
semaphoreHandlers = None
semaphoreLocks = None
masterAddress = None


def masterInit(workgroup):
    global semaphores, runningOnMaster, semaphoreLocks, semaphoreHandlers
    semaphores = {-1: None}
    runningOnMaster = True
    semaphoreLocks = {-1: None}
    semaphoreHandlers = {-1: None}
    workgroup.controls[CNT_SEMAPHORE_COUNT] = 0


def workerInit():
    global runningOnMaster, semaphores
    semaphores = {-1: None}
    runningOnMaster = False


class NWSemaphore:
    """
    The semaphore class used to limit simultaneous execution.
    When entering critical section call :py:meth:`acquire` and when exiting :py:meth:`release`.

    :type workgroup: NetWork.workgroup.Workgroup
    :param workgroup: workgroup that will be using this Event
    :type value: int
    :param value: initial value for the semaphore counter
    """

    def __init__(self, workgroup, value=1):
        self.value = value
        self.workgroup = workgroup
        self.workgroup.controls[CNT_SEMAPHORE_COUNT] += 1
        self.id = self.workgroup.controls[CNT_SEMAPHORE_COUNT]
        if runningOnMaster:
            semaphoreLocks[self.id] = Lock()
            semaphoreHandlers[self.id] = MasterSemaphoreHandler(self.id, self.value)
        semaphores[self.id] = Semaphore(self.value)
        for i in range(self.value):
            semaphores[self.id].acquire()
        sendRequest(CMD_REGISTER_SEMAPHORE,
                                   {
                                       "ID": self.id,
                                       "VALUE": self.value
                                   })

    def acquireOnMaster(self):
        sendRequest(CMD_ACQUIRE_SEMAPHORE,
                                   {
                                       "ID": self.id
                                   })
        semaphores[self.id].acquire()

    def releaseOnMaster(self):
        sendRequest(CMD_RELEASE_SEMAPHORE,
                                   {
                                       "ID": self.id
                                   })

    def acquireOnWorker(self):
        sendRequest(CMD_ACQUIRE_SEMAPHORE,
                    {
                        "ID": self.id
                    })
        semaphores[self.id].acquire()

    def releaseOnWorker(self):
        sendRequest(CMD_RELEASE_SEMAPHORE,
                    {
                        "ID": self.id
                    })

    def acquire(self):
        """
        Acquire the semaphore and decrement counter value.
        If the counter is zero sleep until some other task
        releases the semaphore
        """
        if runningOnMaster:
            self.acquireOnMaster()
        else:
            self.acquireOnWorker()

    def release(self):
        """
        Release the semaphore, increment the counter value,
        wake firs task from waiter list.
        """
        if runningOnMaster:
            self.releaseOnMaster()
        else:
            self.releaseOnWorker()

    def __setstate__(self, state):
        self.id = state["id"]
        self.workgroup = state["workgroup"]

    def __getstate__(self):
        return {"id": self.id, "workgroup": None}


class MasterSemaphoreHandler:
    #A class used to hold information about semaphores on the master
    #It has a waiters list that holds a list of workers waiting to acquire
    #the semaphore, when the semaphore
    #is released a message is send to the first waiter in the list
    def __init__(self, id, value):
        semaphoreLocks[id].acquire()
        self.id = id
        self.value = value
        self.waiters = []
        semaphoreLocks[id].release()

    def acquire(self, requester, controlls):
        #Acquire semaphore or wait for release
        semaphoreLocks[self.id].acquire()
        if not self.value:
            self.waiters.append(requester)
        else:
            self.value -= 1
            if requester == -1:
                semaphores[self.id].release()
            else:
                controlls[CNT_WORKERS][requester].sendRequest(CMD_RELEASE_SEMAPHORE,
                                                              {
                                                                  "ID": self.id
                                                              })
        semaphoreLocks[self.id].release()

    def release(self, controlls):
        #Release semaphore and wake up the first from the waiting list
        semaphoreLocks[self.id].acquire()
        if self.waiters:
            id = self.waiters.pop(0)
            if id == -1:
                semaphores[self.id].release()
            else:
                controlls[CNT_WORKERS][id].sendRequest(CMD_RELEASE_SEMAPHORE,
                                                       {
                                                           "ID": self.id
                                                       })
        else:
            self.value += 1
        semaphoreLocks[self.id].release()


def registerSemaphoreMaster(request, controlls, commqueue):
    #A handler used by Workgroup.dispatcher
    id = request["ID"]
    value = request["VALUE"]
    for worker in controlls[CNT_WORKERS]:
        try:
            worker.sendRequest(CMD_REGISTER_SEMAPHORE, {"ID": id, "VALUE": value})
        except DeadWorkerError:
            commqueue.put(Request(CMD_WORKER_DIED,
                                  {"WORKER": worker}))


def acquireSemaphoreMaster(request, controlls, commqueue):
    #A handler used by Workgroup.dispatcher
    try:
        semaphoreHandlers[request["ID"]].acquire(request.requester, controlls)
    except DeadWorkerError as error:
        commqueue.put(Request(CMD_WORKER_DIED,
                              {"WORKER": controlls[CNT_WORKERS][error.id]}))


def releaseSemaphoreMaster(request, controlls, commqueue):
    #A handler used by Workgroup.dispatcher
    try:
        semaphoreHandlers[request["ID"]].release(controlls)
    except DeadWorkerError as error:
        commqueue.put(Request(CMD_WORKER_DIED,
                              {"WORKER": controlls[CNT_WORKERS][error.id]}))


def registerSemaphoreWorker(request):
    id = request["ID"]
    value = request["VALUE"]
    semaphores[id] = Semaphore(value)
    for i in range(value):
        semaphores[id].acquire()


def releaseSemaphoreWorker(request):
    semaphores[request["ID"]].release()

masterHandlers = {CMD_REGISTER_SEMAPHORE: registerSemaphoreMaster, CMD_ACQUIRE_SEMAPHORE: acquireSemaphoreMaster,
                  CMD_RELEASE_SEMAPHORE: releaseSemaphoreMaster}
workerHandlers = {CMD_RELEASE_SEMAPHORE: releaseSemaphoreWorker, CMD_REGISTER_SEMAPHORE: registerSemaphoreWorker}