"""
Functions that handle messages on the master computer.
Each function is associated with a 3 letter code from commcodes.py
"""
from NetWork import event
from NetWork import queue
from pickle import dumps
from .event import setEvent, registerEvent
from .commcodes import *
from .cntcodes import *
from .queue import registerQueue, putOnQueue, getFromQueue
from .lock import registerLock, releaseLock, acquireLock
from .manager import setManagerItem, getManagerItem

def receiveSocketData(socket, commqueue):
    commqueue.put(socket.recv())
    socket.close()

def submitTask(request, controlls, commqueue):
    workerId=request["WORKER"]
    task=request["TASK"]
    controlls[CNT_WORKERS][workerId].executeTask(task)

def taskRunning(request, controlls, commqueue):
    taskId=request["ID"]
    queueId=request["QUEUE"]
    workerId=controlls[CNT_TASK_EXECUTORS][taskId]
    queue.queues[queueId].put(dumps(controlls[CNT_WORKERS][workerId].taskRunning(taskId)))

def terminateTask(request, controlls, commqueue):
    taskId=request["ID"]
    workerId=controlls[CNT_TASK_EXECUTORS][taskId]
    controlls[CNT_WORKERS][workerId].terminateTask(taskId)
    
def getException(request, controlls, commqueue):
    taskId=request["ID"]
    queueId=request["QUEUE"]
    workerId=controlls[CNT_TASK_EXECUTORS][taskId]
    queue.queues[queueId].put(dumps(controlls[CNT_WORKERS][workerId].getException(taskId)))

def checkException(request, controlls, commqueue):
    taskId=request["ID"]
    queueId=request["QUEUE"]
    workerId=controlls[CNT_TASK_EXECUTORS][taskId]
    queue.queues[queueId].put(dumps(controlls[CNT_WORKERS][workerId].exceptionRaised(taskId)))

def getResult(request, controlls, commqueue):
    taskId=request["ID"]
    queueId=request["QUEUE"]
    workerId=controlls[CNT_TASK_EXECUTORS][taskId]
    queue.queues[queueId].put(dumps(controlls[CNT_WORKERS][workerId].getResult(taskId)))

    
        
handlerList={CMD_SET_EVENT:setEvent, CMD_REGISTER_EVENT:registerEvent, 
             CMD_REGISTER_QUEUE:registerQueue, CMD_GET_FROM_QUEUE:getFromQueue, 
             CMD_PUT_ON_QUEUE:putOnQueue, CMD_SUBMIT_TASK:submitTask,
             CMD_TASK_RUNNING:taskRunning, CMD_GET_EXCEPTION:getException,
             CMD_CHECK_EXCEPTION:checkException, CMD_TERMINATE_TASK:terminateTask,
             CMD_GET_RESULT:getResult, CMD_ACQUIRE_LOCK:acquireLock,
             CMD_REGISTER_LOCK:registerLock, CMD_RELEASE_LOCK:releaseLock,
             CMD_SET_MANAGER_ITEM:setManagerItem, 
             CMD_GET_MANAGER_ITEM:getManagerItem}
