'''
Created on Feb 1, 2013

@author: nidzo
'''
from NetWork import event, queue
from pickle import dumps
from .event import setEvent, registerEvent
from .commcodes import *
from .workgroup import *
from .queue import registerQueue, putOnQueue, getFromQueue

def receiveSocketData(socket, commqueue):
    commqueue.put(socket.recv())
    socket.close()

def submitTask(request, controlls, commqueue):
    contents=request.getContents()
    workerId=int(contents[:contents.find(b"WID")])
    task=contents[contents.find(b"WID")+3:]
    controlls[CNT_WORKERS][workerId].executeTask(task)

def taskRunning(request, controlls, commqueue):
    contents=request.getContents()
    taskId=int(contents[:contents.find(b"TID")])
    queueId=int(contents[contents.find(b"TID")+3:])
    workerId=controlls[CNT_TASK_EXECUTORS][taskId]
    queue.queues[queueId].put(dumps(controlls[CNT_WORKERS][workerId].taskRunning(taskId)))

def terminateTask(request, controlls, commqueue):
    contents=request.getContents()
    taskId=int(contents)
    workerId=controlls[CNT_TASK_EXECUTORS][taskId]
    controlls[CNT_WORKERS][workerId].terminateTask(taskId)
    
def getException(request, controlls, commqueue):
    contents=request.getContents()
    taskId=int(contents[:contents.find(b"TID")])
    queueId=int(contents[contents.find(b"TID")+3:])
    workerId=controlls[CNT_TASK_EXECUTORS][taskId]
    queue.queues[queueId].put(dumps(controlls[CNT_WORKERS][workerId].getException(taskId)))

def checkException(request, controlls, commqueue):
    contents=request.getContents()
    taskId=int(contents[:contents.find(b"TID")])
    queueId=int(contents[contents.find(b"TID")+3:])
    workerId=controlls[CNT_TASK_EXECUTORS][taskId]
    queue.queues[queueId].put(dumps(controlls[CNT_WORKERS][workerId].exceptionRaised(taskId)))

def getResult(request, controlls, commqueue):
    contents=request.getContents()
    taskId=int(contents[:contents.find(b"TID")])
    queueId=int(contents[contents.find(b"TID")+3:])
    workerId=controlls[CNT_TASK_EXECUTORS][taskId]
    queue.queues[queueId].put(dumps(controlls[CNT_WORKERS][workerId].getResult(taskId)))

    
        
handlerList={CMD_SET_EVENT:setEvent, CMD_REGISTER_EVENT:registerEvent, 
             CMD_REGISTER_QUEUE:registerQueue, CMD_GET_FROM_QUEUE:getFromQueue, 
             CMD_PUT_ON_QUEUE:putOnQueue, CMD_SUBMIT_TASK:submitTask,
             CMD_TASK_RUNNING:taskRunning, CMD_GET_EXCEPTION:getException,
             CMD_CHECK_EXCEPTION:checkException, CMD_TERMINATE_TASK:terminateTask,
             CMD_GET_RESULT:getResult}
