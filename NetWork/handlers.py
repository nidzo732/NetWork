"""
Functions that handle messages on the master computer.
Each function is associated with a 3 letter code from commcodes.py
"""
import pickle

from NetWork import event, lock, manager, queue, semaphore, netprint, netobject
from .commcodes import *
from .cntcodes import *
from .request import Request
from .worker import DeadWorkerError


plugins = [event, lock, manager, queue, semaphore, netprint, netobject]


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


def submitTask(request, controls):
    workerId = request["WORKER"]
    task = request["TASK"]
    controls[CNT_WORKERS][workerId].executeTask(task)


def taskRunning(request, controls):
    taskId = request["ID"]
    workerId = controls[CNT_TASK_EXECUTORS][taskId]
    request.respond(controls[CNT_WORKERS][workerId].taskRunning(taskId))


def terminateTask(request, controls):
    taskId = request["ID"]
    workerId = controls[CNT_TASK_EXECUTORS][taskId]
    controls[CNT_WORKERS][workerId].terminateTask(taskId)


def getException(request, controls):
    taskId = request["ID"]
    workerId = controls[CNT_TASK_EXECUTORS][taskId]
    request.respond(controls[CNT_WORKERS][workerId].getException(taskId))


def checkException(request, controls):
    taskId = request["ID"]
    workerId = controls[CNT_TASK_EXECUTORS][taskId]
    request.respond(controls[CNT_WORKERS][workerId].exceptionRaised(taskId))


def getResult(request, controls):
    taskId = request["ID"]
    workerId = controls[CNT_TASK_EXECUTORS][taskId]
    request.respond(controls[CNT_WORKERS][workerId].getResult(taskId))


def deathHandler(request, controls):
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


handlerList = {CMD_SUBMIT_TASK: submitTask,
               CMD_TASK_RUNNING: taskRunning, CMD_GET_EXCEPTION: getException,
               CMD_CHECK_EXCEPTION: checkException, CMD_TERMINATE_TASK: terminateTask,
               CMD_GET_RESULT: getResult,
               CMD_WORKER_DIED: deathHandler,
               }

for plugin in plugins:
    handlerList.update(plugin.masterHandlers)
