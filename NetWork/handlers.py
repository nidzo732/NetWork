"""
Functions that handle messages on the master computer.
Each function is associated with a 3 letter code from commcodes.py
"""
from NetWork import event, lock, manager, queue, semaphore
import pickle
from .event import setEvent, registerEvent
from .commcodes import *
from .cntcodes import *
from .queue import registerQueue, putOnQueue, getFromQueue
from .lock import registerLock, releaseLock, acquireLock
from .manager import setManagerItem, getManagerItem
from .request import Request
from .worker import DeadWorkerError
from .semaphore import registerSemaphore, releaseSemaphore, acquireSemaphore

plugins = [event, lock, manager, queue, semaphore]


class NoWorkersError(Exception): pass


def receiveSocketData(socket, commqueue, controls):
    workerId = -1
    for worker in controls[CNT_WORKERS]:
        if socket.address == worker.realAddress:
            workerId = worker.id
    if workerId == -1:
        return
    try:
        receivedData = socket.recv()
    except OSError as error:
        print("Network communication failed from address", socket.address, error)
        return
    if not receivedData[:3] in handlerList:
        print("Request came with an invalid identifier code", receivedData[:3])
        return
    commqueue.put(Request(receivedData[:3],
                          pickle.loads(receivedData[3:]), workerId, socket))


def submitTask(request, controls, commqueue):
    workerId = request["WORKER"]
    task = request["TASK"]
    try:
        controls[CNT_WORKERS][workerId].executeTask(task)
    except DeadWorkerError:
        commqueue.put(Request(CMD_WORKER_DIED,
                              {"WORKER": controls[CNT_WORKERS][workerId]}))


def taskRunning(request, controls, commqueue):
    taskId = request["ID"]
    queueId = request["QUEUE"]
    workerId = controls[CNT_TASK_EXECUTORS][taskId]
    try:
        queue.queues[queueId].put(controls[CNT_WORKERS][workerId].taskRunning(taskId))
    except DeadWorkerError:
        commqueue.put(Request(CMD_WORKER_DIED,
                              {"WORKER": controls[CNT_WORKERS][workerId]}))


def terminateTask(request, controls, commqueue):
    taskId = request["ID"]
    workerId = controls[CNT_TASK_EXECUTORS][taskId]
    try:
        controls[CNT_WORKERS][workerId].terminateTask(taskId)
    except DeadWorkerError:
        commqueue.put(Request(CMD_WORKER_DIED,
                              {"WORKER": controls[CNT_WORKERS][workerId]}))


def getException(request, controls, commqueue):
    taskId = request["ID"]
    queueId = request["QUEUE"]
    workerId = controls[CNT_TASK_EXECUTORS][taskId]
    try:
        queue.queues[queueId].put(controls[CNT_WORKERS][workerId].getException(taskId))
    except DeadWorkerError:
        commqueue.put(Request(CMD_WORKER_DIED,
                              {"WORKER": controls[CNT_WORKERS][workerId]}))


def checkException(request, controls, commqueue):
    taskId = request["ID"]
    queueId = request["QUEUE"]
    workerId = controls[CNT_TASK_EXECUTORS][taskId]
    try:
        queue.queues[queueId].put(controls[CNT_WORKERS][workerId].exceptionRaised(taskId))
    except DeadWorkerError:
        commqueue.put(Request(CMD_WORKER_DIED,
                              {"WORKER": controls[CNT_WORKERS][workerId]}))


def getResult(request, controls, commqueue):
    taskId = request["ID"]
    queueId = request["QUEUE"]
    workerId = controls[CNT_TASK_EXECUTORS][taskId]
    try:
        queue.queues[queueId].put(controls[CNT_WORKERS][workerId].getResult(taskId))
    except DeadWorkerError:
        commqueue.put(Request(CMD_WORKER_DIED,
                              {"WORKER": controls[CNT_WORKERS][workerId]}))


def deathHandler(request, controls, commqueue):
    deadWorkerSet = controls[CNT_DEAD_WORKERS]
    for worker in deadWorkerSet:
        if worker.id == request["WORKER"].id:
            break
    else:
        controls[CNT_WORKER_COUNT] -= 1
        deadWorkerSet.add(request["WORKER"])
        controls[CNT_DEAD_WORKERS] = deadWorkerSet
        if controls[CNT_WORKER_COUNT] == 0:
            raise NoWorkersError("All workers died, unable to continue working")


handlerList = {CMD_SET_EVENT: setEvent, CMD_REGISTER_EVENT: registerEvent,
               CMD_REGISTER_QUEUE: registerQueue, CMD_GET_FROM_QUEUE: getFromQueue,
               CMD_PUT_ON_QUEUE: putOnQueue, CMD_SUBMIT_TASK: submitTask,
               CMD_TASK_RUNNING: taskRunning, CMD_GET_EXCEPTION: getException,
               CMD_CHECK_EXCEPTION: checkException, CMD_TERMINATE_TASK: terminateTask,
               CMD_GET_RESULT: getResult, CMD_ACQUIRE_LOCK: acquireLock,
               CMD_REGISTER_LOCK: registerLock, CMD_RELEASE_LOCK: releaseLock,
               CMD_SET_MANAGER_ITEM: setManagerItem,
               CMD_GET_MANAGER_ITEM: getManagerItem,
               CMD_WORKER_DIED: deathHandler,
               CMD_ACQUIRE_SEMAPHORE: acquireSemaphore,
               CMD_REGISTER_SEMAPHORE: registerSemaphore,
               CMD_RELEASE_SEMAPHORE: releaseSemaphore,
               }
