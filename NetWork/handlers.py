'''
Created on Feb 1, 2013

@author: nidzo
'''
from NetWork import event
CNT_WORKERS=0
CNT_SHOULD_STOP=2
CNT_LISTEN_SOCKET=3
CNT_WORKER_COUNT=4
CNT_TASK_COUNT=5
CNT_LIVE_WORKERS=6
CNT_EVENT_COUNT=7
CNT_EVENT_PIPES=8
CNT_EVENT_STATES=9

def receiveSocketData(socket, commqueue):
    commqueue.put(socket.recv())
    socket.close()

def setEvent(request, controlls, commqueue):
    id=int(request)
    eventLocks[id].acquire()
    for worker in controlls[CNT_WORKERS]:
        if worker.alive:
            worker.setEvent(id)
    controlls[CNT_EVENT_STATES][id]=True
    for currentEvent in controlls[CNT_EVENT_PIPES][id]:
        currentEvent[0].send(b"EVS")
    eventLocks[id].release()
    
def registerEvent(request, controlls, commqueue):
    id=int(request)
    for worker in controlls[CNT_WORKERS]:
        if worker.alive:
            worker.registerEvent(id)
    controlls[CNT_EVENT_STATES].append(False)
    controlls[CNT_EVENT_PIPES].append([])
    
        
handlerList={b"EVS":setEvent, b"EVR":registerEvent}
