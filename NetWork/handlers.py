"""
Functions that handle messages on the master computer.
Each function is associated with a 3 letter code from commcodes.py
"""
import pickle

from NetWork import event, lock, manager, queue, semaphore, netprint, netobject, task
from .commcodes import *
from .cntcodes import *
from .request import Request


plugins = [event, lock, manager, queue, semaphore, netprint, netobject, task]


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


def deathHandler(request, controls):
    deadWorkerSet = controls[CNT_DEAD_WORKERS]
    for worker in deadWorkerSet:
        if worker == request["WORKER"]:
            break
    else:
        controls[CNT_WORKER_COUNT] -= 1
        deadWorkerSet.add(request["WORKER"])
        controls[CNT_DEAD_WORKERS] = deadWorkerSet
        if controls[CNT_WORKER_COUNT] == 0:
            raise NoWorkersError("All workers died, unable to continue working")


handlerList = {CMD_WORKER_DIED: deathHandler}

for plugin in plugins:
    handlerList.update(plugin.masterHandlers)
