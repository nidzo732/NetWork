'''
Created on Feb 1, 2013

@author: nidzo
'''
from NetWork import event, queue
from pickle import dumps
from .event import setEvent, registerEvent
from queue import registerQueue, putOnQueue, getFromQueue
CNT_WORKERS=0
CNT_SHOULD_STOP=2
CNT_LISTEN_SOCKET=3
CNT_WORKER_COUNT=4
CNT_TASK_COUNT=5
CNT_LIVE_WORKERS=6
CNT_EVENT_COUNT=7
CNT_QUEUE_COUNT=8
CNT_TASK_EXECUTORS=9

CMD_HALT=b"HLT"
CMD_SET_EVENT=b"EVS"
CMD_REGISTER_EVENT=b"EVR"
CMD_REGISTER_QUEUE=b"QUR"
CMD_PUT_ON_QUEUE=b"QUP"
CMD_GET_FROM_QUEUE=b"QUG"
CMD_SUBMIT_TASK=b"TSK"
CMD_TERMINATE_TASK=b"TRM"
CMD_GET_RESULT=b"RSL"
CMD_TASK_RUNNING=b"TRN"
CMD_GET_EXCEPTION=b"EXC"
CMD_CHECK_EXCEPTION=b"EXR"

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

    
        
handlerList={b"EVS":setEvent, b"EVR":registerEvent, b"QUR":registerQueue,
             b"QUG":getFromQueue, b"QUP":putOnQueue, b"TSK":submitTask,
             CMD_TASK_RUNNING:taskRunning, CMD_GET_EXCEPTION:getException,
             CMD_CHECK_EXCEPTION:checkException, CMD_TERMINATE_TASK:terminateTask,
             CMD_GET_RESULT:getResult}
