'''
Created on Feb 1, 2013

@author: nidzo
'''
from .event import MasterEvent
CNT_WORKERS=0
CNT_WORKERS=0
CNT_SHOULD_STOP=2
CNT_LISTEN_SOCKET=3
CNT_WORKER_COUNT=4
CNT_TASK_COUNT=5
CNT_LIVE_WORKERS=6
CNT_EVENT_COUNT=7

def receiveSocketData(socket, commqueue):
    commqueue.put(socket.recv())
    socket.close()

def setEvent(request, controlls, commqueue):
    for worker in controlls[CNT_WORKERS]:
        if worker.alive:
            worker.setEvent(int(request))

def registerEvent(request, controlls, commqueue):
    print("REGISTERING")
    for worker in controlls[CNT_WORKERS]:
        if worker.alive:
            worker.registerEvent(int(request))
        
handlerList={b"EVS":setEvent, b"EVR":registerEvent}
