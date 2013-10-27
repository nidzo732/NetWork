"""
Locks are used to prevent simultaneous execution of taks
that would interfere with each others work if the ran simultaneously.

When a task enters a critical section of code, it calls :py:meth:`acquire <NWLock.acquire>`
method of the lock. If another task tries to acquire the same lock, it will be
put to sleep. When the first task finishes the critical section it calls 
:py:meth:`release <NWLock.release>` method of the lock and waiting task is waken up.

For more info about locks see `Python documentation page
<http://docs.python.org/3.3/library/threading.html#lock-objects>`_

::
    
    #Demonstration of Locks
    #Two running tasks check if an int variable called number should be incremented
    #If another task incremented the variable before, it would set
    #the shouldIncrease item in the manager to false
    #But because the tasks run at the same time, during the check
    #they could both see that shouldIncrease is False and they would
    #both increment number
    #Unless we use lock and put the acquire and release call around the
    #code that checks and increments number

    from NetWork import Workgroup, Lock, Manager
    def checkAndIncrement(manager, lock):
        lock.acquire()    #Make sure another tasks are not checking at the same time
        if manager.shouldIncrease:
            manager.shouldIncrease=False
            manager.number+=1
        lock.release()
    
    with Workgroup(addresses) as w:
        lock=Lock(w)
        manager=Manager(w)
        namespace=manager.namespace()
        namespace.shouldIncrement=True
        namespace.number=0
        task1=w.submit(target=checkAndIncrement, args=(namespace, lock))
        task2=w.submit(target=checkAndIncrement, args=(namespace, lock))
        time.sleep(2)    #Give them time to run
        print(namespace.number)    #This prints '1' but if we didn't use locks
                                   #if might have printed '2'

"""

from multiprocessing import Lock
from .networking import sendRequest
from .commcodes import CMD_WORKER_DIED
from .cntcodes import CNT_WORKERS
from .request import Request
from .worker import DeadWorkerError

CMD_REGISTER_LOCK = b"LCR"
CMD_ACQUIRE_LOCK = b"LCA"
CMD_RELEASE_LOCK = b"LCU"
CNT_LOCK_COUNT = "LOCK_COUNT"

runningOnMaster = None
locks = None
lockHandlers = None
lockLocks = None
masterAddress = None


def masterInit(workgroup):
    global locks, lockHandlers, lockLocks, runningOnMaster
    locks = {-1: None}
    lockHandlers = {-1: None}
    lockLocks = {-1: None}
    runningOnMaster = True
    workgroup.controls[CNT_LOCK_COUNT] = 0


def workerInit():
    global locks, runningOnMaster
    locks = {-1: None}
    runningOnMaster = False


class NWLock:
    """
    The lock class used to prevent simultaneous execution.
    When entering critical section call :py:meth:`acquire` and when exiting :py:meth:`release`.

    :type workgroup: NetWork.workgroup.Workgroup
    :param workgroup: workgroup that will be using this Lock
    """

    def __init__(self, workgroup):
        self.workgroup = workgroup
        self.workgroup.controls[CNT_LOCK_COUNT] += 1
        self.id = self.workgroup.controls[CNT_LOCK_COUNT]
        if runningOnMaster:
            lockLocks[self.id] = Lock()
            lockHandlers[self.id] = MasterLockHandler(self.id)
        locks[self.id] = Lock()
        locks[self.id].acquire()

        self.workgroup.sendRequest(CMD_REGISTER_LOCK,
                                   {
                                       "ID": self.id
                                   })

    def acquireOnMaster(self):
        self.workgroup.sendRequest(CMD_ACQUIRE_LOCK,
                                   {
                                       "ID": self.id
                                   })
        locks[self.id].acquire()

    def releaseOnMaster(self):
        self.workgroup.sendRequest(CMD_RELEASE_LOCK,
                                   {
                                       "ID": self.id
                                   })

    def acquireOnWorker(self):
        sendRequest(CMD_ACQUIRE_LOCK,
                    {
                        "ID": self.id
                    })
        locks[self.id].acquire()

    def releaseOnWorker(self):
        sendRequest(CMD_RELEASE_LOCK,
                    {
                        "ID": self.id
                    })

    def acquire(self):
        """
        Call this when entering critical section, all other tasks that call
        :py:meth:`acquire` on this lock will be put to sleep until :py:meth:`release`
        is called.
        """
        if runningOnMaster:
            self.acquireOnMaster()
        else:
            self.acquireOnWorker()

    def release(self):
        """
        Call this when exiting critical section. Wake a task that was trying to
        acquire this lock.
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


class MasterLockHandler:
    #A class used to hold information about locks on the master
    #It has a waiters list that holds a list of workers waiting to acquire
    #the lock, when the lock is released a message is send to the first waiter
    #in the list
    def __init__(self, id):
        lockLocks[id].acquire()
        self.id = id
        self.locked = False
        self.waiters = []
        lockLocks[id].release()

    def acquire(self, requester, controlls):
        #Acquire lock or wait for release
        lockLocks[self.id].acquire()
        if self.locked:
            self.waiters.append(requester)
        else:
            self.locked = True
            if requester == -1:
                locks[self.id].release()
            else:
                controlls[CNT_WORKERS][requester].sendRequest(CMD_RELEASE_LOCK,
                                                              {
                                                                  "ID": self.id
                                                              })
        lockLocks[self.id].release()

    def release(self, controlls):
        #Release lock and wake up the first from the waiting list
        lockLocks[self.id].acquire()
        if self.waiters:
            id = self.waiters.pop(0)
            if id == -1:
                locks[self.id].release()
            else:
                controlls[CNT_WORKERS][id].sendRequest(CMD_RELEASE_LOCK,
                                                       {
                                                           "ID": self.id
                                                       })
        else:
            self.locked = False
        lockLocks[self.id].release()


def registerLockMaster(request, controlls, commqueue):
    #A handler used by Workgroup.dispatcher
    id = request["ID"]
    for worker in controlls[CNT_WORKERS]:
        try:
            worker.sendRequest(CMD_REGISTER_LOCK, {"ID": id})
        except DeadWorkerError:
            commqueue.put(Request(CMD_WORKER_DIED,
                                  {"WORKER": worker}))


def acquireLockMaster(request, controlls, commqueue):
    #A handler used by Workgroup.dispatcher
    try:
        lockHandlers[request["ID"]].acquire(request.requester, controlls)
    except DeadWorkerError as error:
        commqueue.put(Request(CMD_WORKER_DIED,
                              {"WORKER": controlls[CNT_WORKERS][error.id]}))


def releaseLockMaster(request, controlls, commqueue):
    #A handler used by Workgroup.dispatcher
    try:
        lockHandlers[request["ID"]].release(controlls)
    except DeadWorkerError as error:
        commqueue.put(Request(CMD_WORKER_DIED,
                              {"WORKER": controlls[CNT_WORKERS][error.id]}))


def registerLockWorker(request):
    locks[request["ID"]] = Lock()
    locks[request["ID"]].acquire()


def releaseLockWorker(request):
    locks[request["ID"]].release()

masterHandlers = {CMD_REGISTER_LOCK: registerLockMaster, CMD_ACQUIRE_LOCK: acquireLockMaster,
                  CMD_RELEASE_LOCK: releaseLockMaster}
workerHandlers = {CMD_RELEASE_LOCK: releaseLockWorker, CMD_REGISTER_LOCK: registerLockWorker}